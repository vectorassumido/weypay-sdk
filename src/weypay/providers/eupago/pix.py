"""EuPago EuroPix (PIX). Ver docs/providers/eupago-pix.md.

``success_url``/``fail_url``/``back_url`` não constam da especificação pública, mas
confirmado em sandbox (Fase 0b) que são aceites sem erro — ver
docs/observed/eupago_pix_with_urls.json / eupago_pix_without_urls.json.
"""

from __future__ import annotations

from dataclasses import dataclass

from ...errors import GatewayRejected
from ...http import perform_request, resolve_base_url
from ...money import Money
from ...types import Environment, PaymentResult, PaymentStatus
from .mbway import ENDPOINTS, _headers


@dataclass(frozen=True)
class PixCustomer:
    name: str
    email: str
    country_code: str
    phone_number: str
    notify: bool = True


def create_payment(
    *,
    api_key: str,
    identifier: str,
    amount: Money,
    customer: PixCustomer,
    success_url: str | None = None,
    fail_url: str | None = None,
    back_url: str | None = None,
    lang: str = "PT",
    environment: Environment,
    base_url: str | None = None,
) -> PaymentResult:
    """``POST /v1.02/pix/create``. ``base_url``: ver docstring de mbway.create_payment."""
    resolved_base_url = base_url or resolve_base_url(environment, ENDPOINTS)
    url = f"{resolved_base_url}/v1.02/pix/create"

    payment: dict[str, object] = {
        "amount": {"currency": amount.currency, "value": amount.to_gateway_number()},
        "identifier": identifier,
        "lang": lang,
    }
    if success_url:
        payment["successUrl"] = success_url
    if fail_url:
        payment["failUrl"] = fail_url
    if back_url:
        payment["backUrl"] = back_url

    payload = {
        "payment": payment,
        "customer": {
            "name": customer.name,
            "email": customer.email,
            "countryCode": customer.country_code,
            "phoneNumber": customer.phone_number,
            "notify": customer.notify,
        },
    }

    data, call = perform_request(
        method="POST",
        url=url,
        provider="eupago.pix",
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
        provider="eupago.pix",
        provider_payment_id=str(data.get("transactionID", "")),
        status=PaymentStatus.PENDING,
        raw_status=str(data.get("transactionStatus", "")),
        reference=data.get("reference"),
        call=call,
    )
