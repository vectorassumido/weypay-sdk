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


BO_KEY = "BO-SECRET-456"
LIST_URL = "https://api.ifthenpay.com/v2/payments/read"


@responses.activate
def test_get_order_status_matches_a_real_production_response_shape() -> None:
    """Espelha docs/observed/ifthenpay_list_of_payments_paid.json — resposta real de produção
    (2026-08-19), reconsultando um pagamento PINPAY (Apple Pay, €0,01) já confirmado numa
    sessão anterior. Confirma boKey válido (não 403) e o shape exato de um pagamento real."""
    order_id = "199928337085928"
    responses.add(
        responses.POST,
        LIST_URL,
        json={
            "message": "OK",
            "status": 200,
            "payments": [
                {
                    "amount": 0.01,
                    "entity": "APPLE",
                    "fee": 0.24,
                    "netAmount": -0.23,
                    "orderId": order_id,
                    "paymentDate": "18-08-2026 22:05:56",
                    "procDate": "20260819",
                    "reference": order_id,
                    "requestId": "AdUw3bki5g814Ztxle2Q",
                    "subEntity": "UND-423171",
                    "terminal": "12-VISA-PRT",
                }
            ],
        },
        status=200,
    )

    status, payment = pinpay.get_order_status(bo_key=BO_KEY, order_id=order_id)

    assert status == PaymentStatus.PAID
    assert payment["entity"] == "APPLE"
    assert payment["amount"] == 0.01


@responses.activate
def test_get_order_status_paid_when_order_id_present_in_the_list() -> None:
    responses.add(
        responses.POST,
        LIST_URL,
        json={
            "message": "OK",
            "status": 200,
            "payments": [
                {"orderId": "999999999999999", "amount": 21.5, "reference": "ABC"},
                {"orderId": "123456789012345", "amount": 1.0, "reference": "007875810"},
            ],
        },
        status=200,
    )

    status, payment = pinpay.get_order_status(bo_key=BO_KEY, order_id="123456789012345")

    assert status == PaymentStatus.PAID
    assert payment["reference"] == "007875810"


@responses.activate
def test_get_order_status_pending_when_order_id_absent() -> None:
    responses.add(
        responses.POST, LIST_URL, json={"message": "OK", "status": 200, "payments": []}, status=200
    )

    status, _data = pinpay.get_order_status(bo_key=BO_KEY, order_id="123456789012345")

    assert status == PaymentStatus.PENDING


@responses.activate
def test_get_order_status_sends_the_bo_key_in_the_request_body() -> None:
    """A chave real tem de ir no pedido — a redação (``secret_keys``) só se aplica ao registo
    de auditoria (``GatewayCall``), testada genericamente em test_redaction.py/test_http.py,
    não ao corpo efetivamente enviado ao gateway."""
    responses.add(
        responses.POST, LIST_URL, json={"message": "OK", "status": 200, "payments": []}, status=200
    )

    pinpay.get_order_status(bo_key=BO_KEY, order_id="1")

    request_body = responses.calls[0].request.body
    assert request_body is not None
    body_text = request_body if isinstance(request_body, str) else request_body.decode()
    assert BO_KEY in body_text


@responses.activate
def test_get_order_status_invalid_bo_key_raises_gateway_rejected() -> None:
    responses.add(
        responses.POST,
        LIST_URL,
        json={"message": "Invalid boKey", "status": 403, "payments": []},
        status=200,
    )

    with pytest.raises(GatewayRejected):
        pinpay.get_order_status(bo_key="wrong", order_id="1")


@responses.activate
def test_get_order_status_http_error_raises_gateway_rejected() -> None:
    responses.add(responses.POST, LIST_URL, json={"error": "server error"}, status=500)

    with pytest.raises(GatewayRejected):
        pinpay.get_order_status(bo_key=BO_KEY, order_id="1")
