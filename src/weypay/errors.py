"""Hierarquia de exceções. Ver docs/ARCHITECTURE.md e docs/SECURITY.md regra 1."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .types import GatewayCall


class PaymentError(Exception):
    """Base de todas as exceções do weypay."""


class GatewayUnavailable(PaymentError):
    """O gateway não pôde ser contactado (erro de ligação, DNS, etc). O pedido nunca saiu —
    seguro tratar como falha."""


class GatewayRejected(PaymentError):
    """O gateway respondeu com um payload de erro estruturado (tipicamente 4xx).

    ``call``, quando o provider o fornece, é o ``GatewayCall`` completo da chamada rejeitada
    (já redigido) — permite à app auditar/registar mesmo uma chamada que falhou, sem ter de
    reconstruir a informação a partir de ``status_code``/``payload`` sozinha."""

    def __init__(
        self, status_code: int, payload: dict[str, Any] | str, call: GatewayCall | None = None
    ) -> None:
        self.status_code = status_code
        self.payload = payload
        self.call = call
        super().__init__(f"o gateway rejeitou o pedido: HTTP {status_code} {payload}")


class PaymentIndeterminate(PaymentError):
    """Timeout de leitura — não se sabe se o pedido chegou ao gateway nem se um pagamento
    real foi despoletado. NUNCA tratar isto como falha; ver docs/SECURITY.md regra 1."""


class ConfigurationError(PaymentError):
    """Credencial em falta ou configuração inválida (ex.: SANDBOX sem
    acknowledge_no_sandbox=True num provider sem sandbox real)."""


class WebhookVerificationError(PaymentError):
    """A verificação de um callback/webhook falhou (chave, assinatura ou decifra)."""
