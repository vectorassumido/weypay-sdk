"""Transporte: timeout explícito, retry só em leitura, Environment, e o modo FAKE sem rede.

Ver docs/ARCHITECTURE.md e docs/ENVIRONMENTS.md. Política de "que status code conta como
sucesso" é do provider, não daqui — cada gateway usa uma convenção diferente (200 vs 201 vs
200-299), por isso este módulo nunca levanta GatewayRejected sozinho; devolve sempre
``(data, GatewayCall)`` e é o provider que decide.
"""

from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import requests

from .errors import ConfigurationError, GatewayUnavailable, PaymentIndeterminate
from .redaction import redact
from .types import Environment, GatewayCall

DEFAULT_TIMEOUT: tuple[float, float] = (5, 15)  # (connect, read) segundos
_RETRYABLE_STATUS = frozenset({500, 502, 503, 504})
_MAX_RETRY_ATTEMPTS = 2
_BACKOFF_BASE_SECONDS = 0.5


@dataclass(frozen=True)
class GatewayEndpoints:
    """Base URLs de um provider, por ambiente. ``sandbox=None`` para gateways sem sandbox
    real (ex.: ifthenpay — ver docs/ENVIRONMENTS.md)."""

    production: str
    sandbox: str | None = None


def resolve_base_url(
    environment: Environment,
    endpoints: GatewayEndpoints,
    *,
    acknowledge_no_sandbox: bool = False,
) -> str:
    """Resolve a base URL real (SANDBOX/PRODUCTION). Nunca chamar com Environment.FAKE — esse
    modo não faz pedidos de rede, ver ``FakeResponseRegistry``."""
    if environment is Environment.PRODUCTION:
        return endpoints.production
    if environment is Environment.SANDBOX:
        if endpoints.sandbox is not None:
            return endpoints.sandbox
        if not acknowledge_no_sandbox:
            raise ConfigurationError(
                "este provider não tem sandbox real — Environment.SANDBOX bateria em "
                "produção. Passa acknowledge_no_sandbox=True se isso for mesmo intencional "
                "(ex.: chaves de teste ifthenpay contra o host de produção)."
            )
        return endpoints.production
    raise ConfigurationError(
        f"resolve_base_url não aceita {environment!r} — usa o transporte FAKE em vez disto."
    )


class FakeResponseRegistry:
    """Registo em memória de respostas gravadas, usado só por Environment.FAKE. Nunca abre
    rede — se não houver fixture registada para a chamada, levanta ConfigurationError em vez
    de cair silenciosamente para uma chamada real."""

    def __init__(self) -> None:
        self._responses: dict[tuple[str, str], tuple[int, dict[str, Any]]] = {}

    def register(self, method: str, url: str, *, status_code: int, body: dict[str, Any]) -> None:
        self._responses[(method.upper(), url)] = (status_code, body)

    def get(self, method: str, url: str) -> tuple[int, dict[str, Any]]:
        key = (method.upper(), url)
        if key not in self._responses:
            raise ConfigurationError(
                f"Environment.FAKE: nenhuma fixture registada para {method} {url}. "
                "Regista uma via FakeResponseRegistry.register(), a partir de "
                "docs/observed/ ou dos exemplos da documentação oficial."
            )
        return self._responses[key]


def perform_request(
    *,
    method: str,
    url: str,
    provider: str,
    operation: str,
    environment: Environment,
    json_body: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: tuple[float, float] = DEFAULT_TIMEOUT,
    secret_keys: frozenset[str] = frozenset(),
    redact_url_values: frozenset[str] = frozenset(),
    retry: bool = False,
    fake_registry: FakeResponseRegistry | None = None,
) -> tuple[dict[str, Any] | None, GatewayCall]:
    """Executa um pedido HTTP (ou consulta o registo FAKE) e devolve sempre
    ``(data, GatewayCall)`` — nunca levanta por causa do status code da resposta.

    Levanta ``GatewayUnavailable`` em erro de ligação (o pedido nunca saiu — seguro tratar
    como falha) e ``PaymentIndeterminate`` em timeout de leitura (não se sabe se chegou ao
    gateway; NUNCA tratar como falha — ver docs/SECURITY.md regra 1).

    ``retry=True`` só deve ser passado por operações de leitura (consulta de estado) —
    2 tentativas, backoff exponencial com jitter, só em erro de ligação ou 5xx. Nunca usar em
    operações de escrita (criação de pagamento).

    ``redact_url_values``: alguns providers (a PINPAY da ifthenpay) embutem o segredo no
    *path* do URL, não no corpo — ``secret_keys`` não o apanha, porque só olha para dicts. Os
    valores aqui listados são substituídos por ``"***"`` no ``GatewayCall.url`` (nunca no URL
    real usado para o pedido HTTP).

    ``params``: query string (ex.: ifthenpay ``EstadoPedidosJSON``, que exige GET — a única
    chamada do SDK que não vai no corpo). Redigido em conjunto com ``json_body`` no registo de
    auditoria — os dois nunca coexistem na prática, por isso fundir é seguro.
    """
    correlation_id = str(uuid.uuid4())
    redacted_request = redact({**(json_body or {}), **(params or {})}, secret_keys)
    display_url = _redact_url(url, redact_url_values)

    if environment is Environment.FAKE:
        if fake_registry is None:
            raise ConfigurationError(
                "Environment.FAKE exige um fake_registry com a fixture da chamada."
            )
        status_code, body = fake_registry.get(method, url)
        call = GatewayCall(
            correlation_id=correlation_id,
            provider=provider,
            operation=operation,
            url=display_url,
            http_status=status_code,
            duration_ms=0,
            request=redacted_request,
            response=redact(body, secret_keys),
            outcome="fake",
            occurred_at=datetime.now(UTC),
        )
        return body, call

    attempts = _MAX_RETRY_ATTEMPTS if retry else 1
    last_exc: Exception | None = None

    for attempt in range(1, attempts + 1):
        start = time.monotonic()
        try:
            response = requests.request(
                method, url, json=json_body, params=params, headers=headers, timeout=timeout
            )
        except requests.exceptions.Timeout as exc:
            last_exc = exc
            if retry and attempt < attempts:
                _sleep_backoff(attempt)
                continue
            raise PaymentIndeterminate(
                f"{provider}.{operation}: timeout de leitura — o pagamento pode ter sido "
                "despoletado mesmo sem resposta. Nunca tratar como falha."
            ) from exc
        except requests.exceptions.RequestException as exc:
            last_exc = exc
            if retry and attempt < attempts:
                _sleep_backoff(attempt)
                continue
            raise GatewayUnavailable(f"{provider}.{operation}: {exc}") from exc

        duration_ms = int((time.monotonic() - start) * 1000)
        try:
            data: dict[str, Any] | None = response.json()
        except ValueError:
            data = None

        if retry and response.status_code in _RETRYABLE_STATUS and attempt < attempts:
            _sleep_backoff(attempt)
            continue

        call = GatewayCall(
            correlation_id=correlation_id,
            provider=provider,
            operation=operation,
            url=display_url,
            http_status=response.status_code,
            duration_ms=duration_ms,
            request=redacted_request,
            response=redact(data, secret_keys) if data is not None else response.text,
            outcome="success" if response.ok else "rejected",
            occurred_at=datetime.now(UTC),
        )
        return data, call

    raise GatewayUnavailable(f"{provider}.{operation}: esgotadas as tentativas") from last_exc


def _sleep_backoff(attempt: int) -> None:
    delay = _BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
    time.sleep(delay + random.uniform(0, delay * 0.25))  # noqa: S311 — jitter, não criptografia


def _redact_url(url: str, secret_values: frozenset[str]) -> str:
    redacted = url
    for value in secret_values:
        if value:
            redacted = redacted.replace(value, "***")
    return redacted
