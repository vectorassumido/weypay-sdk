"""EuPago MB WAY (sem split). Ver docs/providers/eupago-mbway.md.

Módulo também exporta ``ENDPOINTS``/``_headers`` para os restantes providers EuPago
(split.py, pix.py) reutilizarem — todos partilham a mesma base URL e o mesmo esquema de auth.
"""

from __future__ import annotations

from ...errors import GatewayRejected
from ...http import GatewayEndpoints, perform_request, resolve_base_url
from ...money import Money
from ...types import Environment, PaymentResult, PaymentStatus

ENDPOINTS = GatewayEndpoints(
    production="https://clientes.eupago.pt/api",
    sandbox="https://sandbox.eupago.pt/api",
)


def _headers(api_key: str) -> dict[str, str]:
    return {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"ApiKey {api_key}",
    }


def create_payment(
    *,
    api_key: str,
    identifier: str,
    amount: Money,
    customer_phone: str,
    country_code: str = "+351",
    environment: Environment,
) -> PaymentResult:
    """MB WAY sem split — ``POST /v1.02/mbway/create``.

    ⚠️ A resposta desta variante (sem split) não está confirmada trazer ``entity`` — a spec
    documentada só promete ``transactionID``/``reference`` (ver
    docs/providers/eupago-mbway.md (d), docs/OPEN-QUESTIONS.md #2/#15). ``PaymentResult.entity``
    fica ``None`` aqui; se um dia se confirmar que o campo existe, atualizar sem quebrar o
    contrato (o campo já existe no tipo, só não é preenchido nesta função)."""
    base_url = resolve_base_url(environment, ENDPOINTS)
    url = f"{base_url}/v1.02/mbway/create"
    payload = {
        "payment": {
            "amount": {"currency": amount.currency, "value": amount.to_gateway_number()},
            "identifier": identifier,
            "customerPhone": customer_phone,
            "countryCode": country_code,
        }
    }

    data, call = perform_request(
        method="POST",
        url=url,
        provider="eupago.mbway",
        operation="create_payment",
        environment=environment,
        json_body=payload,
        headers=_headers(api_key),
    )
    if data is None or call.http_status is None or not (200 <= call.http_status < 300):
        raise GatewayRejected(
            call.http_status or 0, data if data is not None else (call.response or ""), call=call
        )

    return PaymentResult(
        provider="eupago.mbway",
        provider_payment_id=str(data.get("transactionID", "")),
        status=PaymentStatus.PENDING,
        raw_status=str(data.get("transactionStatus", "")),
        reference=data.get("reference"),
        call=call,
    )
