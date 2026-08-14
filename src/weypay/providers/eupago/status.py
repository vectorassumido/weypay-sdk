"""EuPago — consulta de estado de referência. Ver docs/providers/eupago-status.md.

Usa o path LEGADO (``/clientes/rest_api/multibanco/info``), confirmado a funcionar em
sandbox na Fase 0b — o path documentado publicamente (``/multibanco/info``) devolve 404
neste host. Não trocar sem reobservar.
"""

from __future__ import annotations

from ...errors import GatewayRejected
from ...http import GatewayEndpoints, perform_request, resolve_base_url
from ...types import Environment, PaymentStatus

ENDPOINTS = GatewayEndpoints(
    production="https://clientes.eupago.pt/api",
    sandbox="https://sandbox.eupago.pt/api",
)

# ✅ observado em sandbox (Fase 0b): "pendente" confirmado real. ⚠️ valor de sucesso "paga"
# herdado do código atual do bookwey, nunca observado (não testável sem um pagamento real —
# ver docs/OPEN-QUESTIONS.md).
STATUS_PENDING = "pendente"
STATUS_PAID = "paga"


def get_reference_status(
    *,
    api_key: str,
    reference: str,
    entity: str | None = None,
    environment: Environment,
    base_url: str | None = None,
) -> tuple[PaymentStatus, dict[str, object]]:
    """Consulta de leitura — faz retry (2 tentativas, só em erro de ligação/5xx, nunca 4xx;
    ver docs/SECURITY.md regra 1). ``base_url``: ver docstring de mbway.create_payment."""
    resolved_base_url = base_url or resolve_base_url(environment, ENDPOINTS)
    url = f"{resolved_base_url}/clientes/rest_api/multibanco/info"
    payload: dict[str, str] = {"referencia": reference, "chave": api_key}
    if entity:
        payload["entidade"] = entity

    data, call = perform_request(
        method="POST",
        url=url,
        provider="eupago.status",
        operation="get_reference_status",
        environment=environment,
        json_body=payload,
        headers={"accept": "application/json", "Content-Type": "application/json"},
        secret_keys=frozenset({"chave"}),
        retry=True,
    )
    if data is None or call.http_status is None or not (200 <= call.http_status < 300):
        raise GatewayRejected(
            call.http_status or 0, data if data is not None else (call.response or ""), call=call
        )

    raw = str(data.get("estado_referencia", ""))
    if raw == STATUS_PAID:
        status = PaymentStatus.PAID
    elif raw == STATUS_PENDING:
        status = PaymentStatus.PENDING
    else:
        status = PaymentStatus.UNKNOWN
    return status, data
