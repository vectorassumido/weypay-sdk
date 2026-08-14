from decimal import Decimal

import pytest
import responses

from weypay.errors import GatewayRejected
from weypay.money import Money
from weypay.providers.eupago.mbway import ENDPOINTS, create_payment
from weypay.types import Environment, PaymentStatus

URL = "https://sandbox.eupago.pt/api/v1.02/mbway/create"


@responses.activate
def test_successful_payment() -> None:
    responses.add(
        responses.POST,
        URL,
        json={"transactionStatus": "Success", "transactionID": "tx-1", "reference": "ref-1"},
        status=201,
    )
    result = create_payment(
        api_key="KEY-1",
        identifier="Salao-abc",
        amount=Money(Decimal("20.00")),
        customer_phone="912345678",
        environment=Environment.SANDBOX,
    )
    assert result.provider_payment_id == "tx-1"
    assert result.reference == "ref-1"
    assert result.status == PaymentStatus.PENDING
    assert result.entity is None  # ⚠️ não confirmado nesta variante — ver docstring do módulo


@responses.activate
def test_amount_sent_as_json_number() -> None:
    responses.add(
        responses.POST, URL, json={"transactionStatus": "Success", "reference": "r"}, status=201
    )
    create_payment(
        api_key="K",
        identifier="id",
        amount=Money(Decimal("20.00")),
        customer_phone="912345678",
        environment=Environment.SANDBOX,
    )
    import json as _json

    body = responses.calls[0].request.body
    assert body is not None
    sent = _json.loads(body)
    assert sent["payment"]["amount"]["value"] == 20.00
    assert sent["payment"]["customerPhone"] == "912345678"
    assert sent["payment"]["countryCode"] == "+351"


@responses.activate
def test_rejected_response_raises_gateway_rejected_with_call() -> None:
    responses.add(
        responses.POST,
        URL,
        json={"transactionStatus": "Rejected", "code": "CUSTOMERPHONE_INVALID", "text": "..."},
        status=400,
    )
    with pytest.raises(GatewayRejected) as exc_info:
        create_payment(
            api_key="K",
            identifier="id",
            amount=Money(Decimal("1")),
            customer_phone="000000",
            environment=Environment.SANDBOX,
        )
    assert exc_info.value.call is not None
    assert exc_info.value.call.http_status == 400


def test_endpoints_match_sandbox_and_production() -> None:
    assert ENDPOINTS.sandbox == "https://sandbox.eupago.pt/api"
    assert ENDPOINTS.production == "https://clientes.eupago.pt/api"


@responses.activate
def test_base_url_override_bypasses_canonical_resolution() -> None:
    """Para consumidores (bookwey) que guardam o URL exato por-conta e não podem assumir
    que bate certo com o host canónico da SDK — ver docs/migration/03-bookwey-adopt.md."""
    custom_url = "https://per-merchant.example.pt/api/v1.02/mbway/create"
    responses.add(
        responses.POST,
        custom_url,
        json={"transactionStatus": "Success", "reference": "r"},
        status=201,
    )
    create_payment(
        api_key="K",
        identifier="id",
        amount=Money(Decimal("1")),
        customer_phone="912345678",
        environment=Environment.SANDBOX,
        base_url="https://per-merchant.example.pt/api",
    )
    assert responses.calls[0].request.url == custom_url
