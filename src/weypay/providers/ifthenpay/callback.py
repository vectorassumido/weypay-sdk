"""Callback (webhook) MB WAY/PINPAY. Ver docs/providers/ifthenpay-callbacks.md.

Os nomes dos parâmetros e o vocabulário de ``estado`` são CONFIGURAÇÃO NOSSA — o template
registado no backoffice ifthenpay, não protocolo fixo por eles. ``CallbackMapping`` torna isso
explícito; o default corresponde ao template real do `boxwey` (MB WAY).

Fluxo em duas fases, porque a chave anti-phishing é por-tenant e só se sabe qual depois de
resolver o tenant a partir da referência — a app consumidora faz o lookup entre as duas
chamadas:

    reference = extract_reference(query)
    tenant = MyOrder.objects.get(provider_reference=reference).tenant   # app resolve
    event = verify_and_parse(query=query, expected_key=tenant.itp_callback_key)

``verify_key``/``verify_amount``/``parse_status`` são expostas separadamente (não só compostas
dentro de ``verify_and_parse``) porque uma app a migrar de um esquema de resposta HTTP mais
granular (ex.: 403 para chave inválida, 400 para valor divergente — dois códigos diferentes,
não um `WebhookVerificationError` genérico) precisa de distinguir a causa da falha sem fazer
parsing de mensagens de erro.
"""

from __future__ import annotations

import hmac
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from ...errors import WebhookVerificationError
from ...money import Money
from ...redaction import redact
from ...types import PaymentStatus, WebhookEvent


@dataclass(frozen=True)
class CallbackMapping:
    """Nomes dos parâmetros do template de callback + vocabulário de estado. O default é o
    template real do `boxwey` para MB WAY: ``?chave=...&referencia=...&valor=...&estado=...``.

    Para PINPAY, o template de fábrica sugerido pela ifthenpay usa nomes diferentes
    (``key``/``id``/``amount``/``payment_datetime``/``payment_method``, sem ``estado``
    textual) — mas como os nomes são escolha nossa, o `bookwey` pode registar o callback do
    PINPAY com este MESMO mapping, convergindo os dois produtos para um único parser (ver
    docs/PLAN.md §"Callbacks: uma URL comum?").
    """

    key_param: str = "chave"
    reference_param: str = "referencia"
    amount_param: str = "valor"
    status_param: str = "estado"
    paid_value: str = "PAGO"
    # ⚠️ Vocabulário herdado do código atual do boxwey, não confirmado contra o real vocabulário
    # textual do callback (ver docs/providers/ifthenpay-callbacks.md (c) e OPEN-QUESTIONS #6) —
    # preservado tal e qual para a Fase 1 ser zero-alteração-de-comportamento.
    refunded_value: str = "023"
    declined_values: frozenset[str] = frozenset({"020", "101", "113"})


DEFAULT_MAPPING = CallbackMapping()


def extract_reference(query: Mapping[str, str], mapping: CallbackMapping = DEFAULT_MAPPING) -> str:
    """Extrai só a referência — antes de se saber a chave esperada (que depende do tenant,
    resolvido pela app a partir desta referência). Levanta se estiver ausente/vazia."""
    reference = query.get(mapping.reference_param, "")
    if not reference:
        raise WebhookVerificationError(
            f"parâmetro '{mapping.reference_param}' em falta ou vazio no callback"
        )
    return reference


def verify_key(
    query: Mapping[str, str], expected_key: str, mapping: CallbackMapping = DEFAULT_MAPPING
) -> None:
    """Compara a chave recebida com a esperada, em tempo constante. Levanta
    ``WebhookVerificationError`` se ``expected_key`` estiver vazia (nunca aceitar "sem chave
    configurada" como válido) ou não coincidir."""
    received_key = query.get(mapping.key_param, "")
    if not expected_key or not hmac.compare_digest(received_key, expected_key):
        raise WebhookVerificationError("chave anti-phishing inválida ou não configurada")


def verify_amount(
    query: Mapping[str, str],
    expected_amount: Money | None,
    mapping: CallbackMapping = DEFAULT_MAPPING,
) -> Money | None:
    """Interpreta o parâmetro de valor, se presente, e — se ``expected_amount`` for dado —
    verifica que coincide. Devolve ``None`` se o parâmetro não vier no callback (⚠️ fraqueza
    conhecida — ver docs/OPEN-QUESTIONS.md #9: nem todos os templates têm este parâmetro)."""
    raw_amount = query.get(mapping.amount_param, "")
    if not raw_amount:
        return None
    try:
        amount = Money.parse(raw_amount)
    except ValueError as exc:
        raise WebhookVerificationError(f"valor '{raw_amount}' inválido no callback") from exc
    if expected_amount is not None:
        try:
            if Decimal(raw_amount.replace(",", ".")) != expected_amount.amount:
                raise WebhookVerificationError(
                    f"valor do callback ({raw_amount}) não coincide com o esperado "
                    f"({expected_amount.to_gateway_string()})"
                )
        except InvalidOperation as exc:
            raise WebhookVerificationError(f"valor '{raw_amount}' inválido") from exc
    return amount


def parse_status(raw_status: str, mapping: CallbackMapping = DEFAULT_MAPPING) -> PaymentStatus:
    """Mapeia o ``estado`` textual do callback para ``PaymentStatus``. Nunca levanta — um
    valor fora do vocabulário conhecido devolve ``PaymentStatus.UNKNOWN`` (ver
    docs/SECURITY.md regra 6: nunca 4xx a um estado desconhecido; decidir o que fazer com
    ``UNKNOWN``, incluindo o código HTTP de resposta, é da app consumidora)."""
    if raw_status == mapping.paid_value:
        return PaymentStatus.PAID
    if raw_status == mapping.refunded_value:
        return PaymentStatus.REFUNDED
    if raw_status in mapping.declined_values:
        return PaymentStatus.DECLINED
    return PaymentStatus.UNKNOWN


def verify_and_parse(
    *,
    query: Mapping[str, str],
    expected_key: str,
    mapping: CallbackMapping = DEFAULT_MAPPING,
    expected_amount: Money | None = None,
) -> WebhookEvent:
    """Verifica a chave anti-phishing e, se ``expected_amount`` for dado e o parâmetro de
    valor estiver presente, o montante. Levanta ``WebhookVerificationError`` em qualquer falha
    de verificação — nunca devolve um ``WebhookEvent`` de um callback não verificado.

    Composição de ``extract_reference``/``verify_key``/``verify_amount``/``parse_status`` —
    usar essas diretamente quando a app precisar de distinguir a causa de uma falha (ex.: 403
    para chave inválida vs 400 para valor divergente)."""
    reference = extract_reference(query, mapping)
    raw_status = query.get(mapping.status_param, "")
    if not raw_status:
        raise WebhookVerificationError(
            f"parâmetro '{mapping.status_param}' em falta ou vazio no callback"
        )

    verify_key(query, expected_key, mapping)
    amount = verify_amount(query, expected_amount, mapping)
    status = parse_status(raw_status, mapping)
    payload = redact(dict(query), frozenset({mapping.key_param}))

    return WebhookEvent(
        provider="ifthenpay",
        provider_reference=reference,
        status=status,
        raw_status=raw_status,
        dedupe_key=f"ifthenpay:{reference}:{raw_status}",
        payload=payload,
        amount=amount,
    )
