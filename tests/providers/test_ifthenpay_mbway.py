"""Suite de conformidade — porto de boxwey-serverless/api/integrations/ifthenpay/tests.py
(classe ClientTests), sem Django, com `responses`. Ver docs/migration/00-setup.md.
"""

from decimal import Decimal

import pytest
import responses

from weypay.errors import GatewayRejected
from weypay.money import Money
from weypay.providers.ifthenpay import mbway
from weypay.types import Environment, PaymentStatus

URL = "https://mbway.ifthenpay.com/ifthenpaymbw.asmx/SetPedidoJson"


@responses.activate
def test_successful_payment_request() -> None:
    responses.add(
        responses.POST,
        URL,
        json={"IdPedido": "id-123", "Estado": "000", "MsgDescricao": "ok"},
        status=200,
    )

    result = mbway.request_payment(
        mbway_key="KEY-1",
        reference="ref123",
        amount=Money(Decimal("20.00")),
        phone="912345678",
        email="ana@example.com",
        description="Concerto — 2 bilhete(s)",
        environment=Environment.PRODUCTION,
    )

    assert result.provider_payment_id == "id-123"
    assert result.raw_status == "000"
    assert result.status == PaymentStatus.PENDING  # ver nota em mbway.py — nunca inferido de Estado
    assert result.call.request["MbWayKey"] == "***"  # a chave nunca é persistida em claro

    sent = responses.calls[0].request
    import json as _json

    assert sent.body is not None
    body = _json.loads(sent.body)
    assert body["MbWayKey"] == "KEY-1"
    assert body["canal"] == "03"
    assert body["valor"] == "20.00"


@responses.activate
def test_http_error_raises_gateway_rejected_with_call_attached() -> None:
    """.call permite à app auditar/registar mesmo uma chamada rejeitada — ver
    events/services/payments.py::_log_call no boxwey (Fase 2)."""
    responses.add(responses.POST, URL, json={"error": "boom"}, status=500)
    with pytest.raises(GatewayRejected) as exc_info:
        mbway.request_payment(
            mbway_key="K",
            reference="r",
            amount=Money(Decimal("1")),
            phone="9",
            email="a@b.pt",
            description="d",
        )
    assert exc_info.value.call is not None
    assert exc_info.value.call.http_status == 500
    assert exc_info.value.call.provider == "ifthenpay.mbway"


@responses.activate
def test_missing_id_pedido_raises_gateway_rejected_with_call_attached() -> None:
    responses.add(
        responses.POST, URL, json={"Estado": "999", "MsgDescricao": "invalid"}, status=200
    )
    with pytest.raises(GatewayRejected) as exc_info:
        mbway.request_payment(
            mbway_key="K",
            reference="r",
            amount=Money(Decimal("1")),
            phone="9",
            email="a@b.pt",
            description="d",
        )
    assert exc_info.value.call is not None
    assert exc_info.value.call.http_status == 200


@responses.activate
def test_description_is_truncated_to_50_chars() -> None:
    responses.add(responses.POST, URL, json={"IdPedido": "id-1", "Estado": "000"}, status=200)
    long_description = "x" * 80

    mbway.request_payment(
        mbway_key="K",
        reference="r",
        amount=Money(Decimal("1")),
        phone="9",
        email="a@b.pt",
        description=long_description,
    )

    import json as _json

    request_body = responses.calls[0].request.body
    assert request_body is not None
    sent_body = _json.loads(request_body)
    assert len(sent_body["descricao"]) == mbway.DESCRIPTION_MAX_LENGTH


def test_sandbox_without_acknowledgement_raises() -> None:
    """ifthenpay não tem sandbox real — ver docs/ENVIRONMENTS.md."""
    from weypay.errors import ConfigurationError

    with pytest.raises(ConfigurationError, match="não tem sandbox real"):
        mbway.request_payment(
            mbway_key="K",
            reference="r",
            amount=Money(Decimal("1")),
            phone="9",
            email="a@b.pt",
            description="d",
            environment=Environment.SANDBOX,
        )
