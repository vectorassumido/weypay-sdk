"""EuPago — consulta de estado de referência. Ver docs/providers/eupago-status.md.

Usa o path LEGADO (``/clientes/rest_api/multibanco/info``), confirmado a funcionar em
sandbox na Fase 0b — o path documentado publicamente (``/multibanco/info``) devolve 404
neste host. Não trocar sem reobservar.

Bug real corrigido em 2026-08-14 (teste local com pagamento real): ao contrário de
``mbway.py``/``split.py``/``pix.py`` (cujos sufixos de endpoint, ex. ``/v1/split-payments/
mbway``, assumem uma base já terminada em ``/api``), o path legado deste ficheiro **não**
leva ``/api`` — o código original do `bookwey` chama
``f"{merchant.eupago_api_url}/clientes/rest_api/multibanco/info"``, sem ``/api`` a meio.
``ENDPOINTS`` tinha ``/api`` por engano (copiado dos outros providers), fazendo qualquer
consulta de estado devolver 404. Nunca detetado antes porque a suite de testes tinha o
mesmo engano embutido no URL esperado.
Ver ``docs/observed/eupago_status_mbway_split_reference_404.json``.
"""

from __future__ import annotations

from ...errors import GatewayRejected
from ...http import GatewayEndpoints, perform_request, resolve_base_url
from ...types import Environment, PaymentStatus

ENDPOINTS = GatewayEndpoints(
    production="https://clientes.eupago.pt",
    sandbox="https://sandbox.eupago.pt",
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
