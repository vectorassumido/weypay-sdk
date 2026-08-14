from decimal import Decimal

import pytest
import responses

from weypay.errors import GatewayRejected
from weypay.money import Money
from weypay.providers.ifthenpay import pinpay
from weypay.types import PaymentStatus

GATEWAY_KEY = "GTW-SECRET-123"
URL = f"https://api.ifthenpay.com/gateway/pinpay/{GATEWAY_KEY}"


@responses.activate
def test_successful_checkout_creation() -> None:
    responses.add(
        responses.POST,
        URL,
        json={"PinCode": "1234567890", "RedirectUrl": "https://gateway.ifthenpay.com/url/r54"},
        status=200,
    )

    result = pinpay.create_payment(
        gateway_key=GATEWAY_KEY,
        id="123456789012345",
        amount=Money(Decimal("21.50")),
        description="Reserva Salão X",
    )

    assert result.redirect_url == "https://gateway.ifthenpay.com/url/r54"
    assert result.provider_payment_id == "1234567890"
    assert result.status == PaymentStatus.PENDING


@responses.activate
def test_gateway_key_never_appears_in_the_audit_url() -> None:
    responses.add(responses.POST, URL, json={"RedirectUrl": "https://x"}, status=200)
    result = pinpay.create_payment(gateway_key=GATEWAY_KEY, id="123", amount=Money(Decimal("1.00")))
    assert GATEWAY_KEY not in result.call.url
    assert result.call.url.endswith("/gateway/pinpay/***")


def test_id_must_be_numeric_and_at_most_15_chars() -> None:
    with pytest.raises(ValueError, match="numérico"):
        pinpay.create_payment(gateway_key=GATEWAY_KEY, id="not-numeric", amount=Money(Decimal("1")))
    with pytest.raises(ValueError, match="15"):
        pinpay.create_payment(gateway_key=GATEWAY_KEY, id="1" * 16, amount=Money(Decimal("1")))


@responses.activate
def test_description_truncated_to_200_chars() -> None:
    responses.add(responses.POST, URL, json={"RedirectUrl": "https://x"}, status=200)
    pinpay.create_payment(
        gateway_key=GATEWAY_KEY,
        id="1",
        amount=Money(Decimal("1")),
        description="x" * 300,
    )
    import json as _json

    request_body = responses.calls[0].request.body
    assert request_body is not None
    sent = _json.loads(request_body)
    assert len(sent["description"]) == pinpay.DESCRIPTION_MAX_LENGTH


@responses.activate
def test_missing_redirect_url_raises_gateway_rejected() -> None:
    responses.add(responses.POST, URL, json={"PinCode": "123"}, status=200)
    with pytest.raises(GatewayRejected):
        pinpay.create_payment(gateway_key=GATEWAY_KEY, id="1", amount=Money(Decimal("1")))


@responses.activate
def test_error_status_raises_gateway_rejected() -> None:
    responses.add(responses.POST, URL, json={"error": "bad request"}, status=400)
    with pytest.raises(GatewayRejected):
        pinpay.create_payment(gateway_key=GATEWAY_KEY, id="1", amount=Money(Decimal("1")))
