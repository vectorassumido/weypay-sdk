"""Payloads de sucesso espelham docs/observed/eupago_pix_*.json (observação real de
sandbox, Fase 0b) — não inventados."""

from decimal import Decimal

import pytest
import responses

from weypay.errors import GatewayRejected
from weypay.money import Money
from weypay.providers.eupago.pix import PixCustomer, create_payment
from weypay.types import Environment, PaymentStatus

URL = "https://sandbox.eupago.pt/api/v1.02/pix/create"


def _customer() -> PixCustomer:
    return PixCustomer(
        name="Teste Weypay",
        email="teste@example.com",
        country_code="+351",
        phone_number="912345678",
    )


@responses.activate
def test_successful_payment_matches_observed_sandbox_shape() -> None:
    responses.add(
        responses.POST,
        URL,
        json={
            "transactionStatus": "Success",
            "transactionID": "01a0003ce522734d82924d3e142c8315",
            "reference": "320651",
            "pixCode": "0002...",
            "pixImage": "https://pagbrasil.com/x/img?...",
        },
        status=201,
    )
    result = create_payment(
        api_key="KEY-1",
        identifier="weypay-obs-6648a9bc",
        amount=Money(Decimal("5.00")),
        customer=_customer(),
        environment=Environment.SANDBOX,
    )
    assert result.provider_payment_id == "01a0003ce522734d82924d3e142c8315"
    assert result.reference == "320651"
    assert result.status == PaymentStatus.PENDING


@responses.activate
def test_success_url_fail_url_back_url_accepted_without_error() -> None:
    """✅ confirmado em sandbox (Fase 0b) — não constam da spec pública mas não quebram o
    pedido. Ver docs/providers/eupago-pix.md."""
    responses.add(
        responses.POST,
        URL,
        json={"transactionStatus": "Success", "transactionID": "x", "reference": "y"},
        status=201,
    )
    create_payment(
        api_key="KEY-1",
        identifier="id",
        amount=Money(Decimal("5.00")),
        customer=_customer(),
        success_url="https://example.test/success",
        fail_url="https://example.test/fail",
        back_url="https://example.test/back",
        environment=Environment.SANDBOX,
    )
    sent = responses.calls[0].request
    assert sent.body is not None
    import json as _json

    body = _json.loads(sent.body)
    assert body["payment"]["successUrl"] == "https://example.test/success"
    assert body["payment"]["failUrl"] == "https://example.test/fail"
    assert body["payment"]["backUrl"] == "https://example.test/back"


@responses.activate
def test_amount_sent_as_json_number_not_string() -> None:
    responses.add(
        responses.POST,
        URL,
        json={"transactionStatus": "Success", "transactionID": "x", "reference": "y"},
        status=201,
    )
    create_payment(
        api_key="KEY-1",
        identifier="id",
        amount=Money(Decimal("5.00")),
        customer=_customer(),
        environment=Environment.SANDBOX,
    )
    sent = responses.calls[0].request
    assert sent.body is not None
    import json as _json

    body = _json.loads(sent.body)
    assert body["payment"]["amount"]["value"] == 5.00
    assert isinstance(body["payment"]["amount"]["value"], float)


@responses.activate
def test_error_response_raises_gateway_rejected() -> None:
    responses.add(
        responses.POST,
        URL,
        json={"transactionStatus": "Rejected", "code": "APIKEY_MISSING", "text": "..."},
        status=401,
    )
    with pytest.raises(GatewayRejected) as exc_info:
        create_payment(
            api_key="",
            identifier="id",
            amount=Money(Decimal("5.00")),
            customer=_customer(),
            environment=Environment.SANDBOX,
        )
    assert exc_info.value.call is not None
    assert exc_info.value.call.http_status == 401


def test_production_and_sandbox_hosts() -> None:
    from weypay.providers.eupago.mbway import ENDPOINTS

    assert ENDPOINTS.production == "https://clientes.eupago.pt/api"
    assert ENDPOINTS.sandbox == "https://sandbox.eupago.pt/api"
