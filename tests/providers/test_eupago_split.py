from decimal import Decimal

import pytest
import responses

from weypay.errors import GatewayRejected
from weypay.money import Money
from weypay.providers.eupago.split import Beneficiary, create_split_payment
from weypay.types import Environment, PaymentStatus

URL = "https://sandbox.eupago.pt/api/v1/split-payments/mbway"


def _beneficiaries() -> list[Beneficiary]:
    return [
        Beneficiary(
            extern_key="salon-key-secret", amount=Money(Decimal("15.00")), identifier="Salao-1"
        ),
        Beneficiary(
            extern_key="owner-key-secret", amount=Money(Decimal("5.00")), identifier="Comissao-1"
        ),
    ]


@responses.activate
def test_successful_split_payment() -> None:
    responses.add(
        responses.POST,
        URL,
        json={
            "transactionStatus": "Success",
            "entity": "82307",
            "reference": "100502152",
            "amount": "20.00",
        },
        status=200,
    )
    result = create_split_payment(
        api_key="K",
        method="mbway",
        identifier="Salao-1",
        amount=Money(Decimal("20.00")),
        beneficiaries=_beneficiaries(),
        admin_callback="https://example.test/callback/1",
        alias="912345678",
        environment=Environment.SANDBOX,
    )
    assert result.entity == "82307"
    assert result.reference == "100502152"
    assert result.status == PaymentStatus.PENDING


@responses.activate
def test_beneficiary_extern_key_never_appears_in_audit_request() -> None:
    """Corrige o bug original: bookwey/utils.py:210 despejava externKey em claro via
    print(payload) — ver docs/PLAN.md e docs/SECURITY.md regra 3."""
    responses.add(responses.POST, URL, json={"transactionStatus": "Success"}, status=200)
    result = create_split_payment(
        api_key="K",
        method="mbway",
        identifier="id",
        amount=Money(Decimal("20.00")),
        beneficiaries=_beneficiaries(),
        admin_callback="https://example.test/cb",
        environment=Environment.SANDBOX,
    )
    assert "salon-key-secret" not in str(result.call.request)
    assert "owner-key-secret" not in str(result.call.request)
    assert result.call.request["beneficiaries"][0]["externKey"] == "***"


@responses.activate
def test_beneficiary_amounts_sent_as_json_numbers() -> None:
    responses.add(responses.POST, URL, json={"transactionStatus": "Success"}, status=200)
    create_split_payment(
        api_key="K",
        method="mbway",
        identifier="id",
        amount=Money(Decimal("20.00")),
        beneficiaries=_beneficiaries(),
        admin_callback="https://example.test/cb",
        environment=Environment.SANDBOX,
    )
    import json as _json

    body = responses.calls[0].request.body
    assert body is not None
    sent = _json.loads(body)
    assert sent["amount"] == 20.00
    assert sent["beneficiaries"][0]["amount"] == 15.00
    assert sent["beneficiaries"][1]["amount"] == 5.00


@responses.activate
def test_url_uses_the_given_method() -> None:
    multibanco_url = "https://sandbox.eupago.pt/api/v1/split-payments/multibanco"
    responses.add(responses.POST, multibanco_url, json={"transactionStatus": "Success"}, status=200)
    create_split_payment(
        api_key="K",
        method="multibanco",
        identifier="id",
        amount=Money(Decimal("20.00")),
        beneficiaries=_beneficiaries(),
        admin_callback="https://example.test/cb",
        environment=Environment.SANDBOX,
    )
    assert responses.calls[0].request.url == multibanco_url


@responses.activate
def test_error_response_raises_gateway_rejected() -> None:
    responses.add(
        responses.POST, URL, json={"transactionStatus": "Rejected", "code": "X"}, status=400
    )
    with pytest.raises(GatewayRejected):
        create_split_payment(
            api_key="K",
            method="mbway",
            identifier="id",
            amount=Money(Decimal("20.00")),
            beneficiaries=_beneficiaries(),
            admin_callback="https://example.test/cb",
            environment=Environment.SANDBOX,
        )


@responses.activate
def test_base_url_override() -> None:
    custom_url = "https://per-merchant.example.pt/api/v1/split-payments/mbway"
    responses.add(responses.POST, custom_url, json={"transactionStatus": "Success"}, status=200)
    create_split_payment(
        api_key="K",
        method="mbway",
        identifier="id",
        amount=Money(Decimal("20.00")),
        beneficiaries=_beneficiaries(),
        admin_callback="https://example.test/cb",
        environment=Environment.SANDBOX,
        base_url="https://per-merchant.example.pt/api",
    )
    assert responses.calls[0].request.url == custom_url
