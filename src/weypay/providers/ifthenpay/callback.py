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
"""

from __future__ import annotations

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


def verify_and_parse(
    *,
    query: Mapping[str, str],
    expected_key: str,
    mapping: CallbackMapping = DEFAULT_MAPPING,
    expected_amount: Money | None = None,
) -> WebhookEvent:
    """Verifica a chave anti-phishing (tempo constante) e, se ``expected_amount`` for dado e o
    parâmetro de valor estiver presente, o montante. Levanta ``WebhookVerificationError`` em
    qualquer falha de verificação — nunca devolve um ``WebhookEvent`` de um callback não
    verificado.

    Um ``status`` fora do vocabulário conhecido devolve ``PaymentStatus.UNKNOWN`` (não
    levanta) — decidir o que fazer com isso, incluindo o código HTTP de resposta ao gateway, é
    da app consumidora (ver docs/SECURITY.md regra 6: nunca 4xx a um estado desconhecido).
    """
    import hmac

    reference = extract_reference(query, mapping)
    raw_status = query.get(mapping.status_param, "")
    if not raw_status:
        raise WebhookVerificationError(
            f"parâmetro '{mapping.status_param}' em falta ou vazio no callback"
        )

    received_key = query.get(mapping.key_param, "")
    if not expected_key or not hmac.compare_digest(received_key, expected_key):
        raise WebhookVerificationError("chave anti-phishing inválida ou não configurada")

    amount = None
    raw_amount = query.get(mapping.amount_param, "")
    if raw_amount:
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

    if raw_status == mapping.paid_value:
        status = PaymentStatus.PAID
    elif raw_status == mapping.refunded_value:
        status = PaymentStatus.REFUNDED
    elif raw_status in mapping.declined_values:
        status = PaymentStatus.DECLINED
    else:
        status = PaymentStatus.UNKNOWN

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
