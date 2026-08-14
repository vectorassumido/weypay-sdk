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


STATUS_URL = "https://mbway.ifthenpay.com/ifthenpaymbw.asmx/EstadoPedidosJSON"


@responses.activate
def test_get_order_status_paid_matches_observed_shape() -> None:
    """Payload espelha uma consulta real (2026-08-14, pagamento de €0,01 aceite pelo
    utilizador) — não inventado. Ver docs/providers/ifthenpay-mbway.md."""
    responses.add(
        responses.GET,
        STATUS_URL,
        json={
            "EstadoPedidos": [
                {
                    "IdPedido": "hDEXBPMUJ0drGAI7Fbqe",
                    "Estado": "000",
                    "DataHoraPedidoRegistado": "14-08-2026 23:56:19",
                    "DataHoraPedidoAtualizado": "14-08-2026 23:56:56",
                    "MsgDescricao": "Operação financeira concluída com sucesso",
                }
            ],
            "Estado": "000",
            "DataHora": "15-08-2026 00:00:11",
            "MsgDescricao": "Operação concluída com sucesso.",
        },
        status=200,
    )

    status, data = mbway.get_order_status(mbway_key="KEY-1", payment_id="hDEXBPMUJ0drGAI7Fbqe")

    assert status == PaymentStatus.PAID
    orders = data["EstadoPedidos"]
    assert isinstance(orders, list)
    assert orders[0]["Estado"] == "000"

    sent = responses.calls[0].request
    assert sent.method == "GET"
    assert sent.url is not None
    assert "MbWayKey=KEY-1" in sent.url
    assert "idspagamento=hDEXBPMUJ0drGAI7Fbqe" in sent.url


@responses.activate
def test_get_order_status_declined_by_user_matches_observed_shape() -> None:
    """Payload espelha uma recusa real (2026-08-15, utilizador recusou o push no telemóvel
    deliberadamente para testar este caminho) — não inventado. Ver
    docs/providers/ifthenpay-mbway.md."""
    responses.add(
        responses.GET,
        STATUS_URL,
        json={
            "EstadoPedidos": [
                {
                    "IdPedido": "1L0UjIcVp3EzAF9iogWv",
                    "Estado": "020",
                    "DataHoraPedidoRegistado": "15-08-2026 00:06:28",
                    "DataHoraPedidoAtualizado": "15-08-2026 00:06:40",
                    "MsgDescricao": "Operação financeira cancelada pelo utilizador",
                }
            ],
            "Estado": "000",
            "DataHora": "15-08-2026 00:06:51",
            "MsgDescricao": "Operação concluída com sucesso.",
        },
        status=200,
    )

    status, data = mbway.get_order_status(mbway_key="KEY-1", payment_id="1L0UjIcVp3EzAF9iogWv")

    assert status == PaymentStatus.DECLINED
    orders = data["EstadoPedidos"]
    assert isinstance(orders, list)
    assert orders[0]["Estado"] == "020"


@responses.activate
def test_get_order_status_uses_the_nested_estado_not_the_top_level_one() -> None:
    """A resposta tem dois `Estado`: o de topo é do pedido HTTP (sempre "000" se a consulta
    correu), o que importa é o de dentro de EstadoPedidos[0]. "100" nunca foi observado neste
    endpoint especificamente (só documentado na tabela síncrona) — fica UNKNOWN, não DECLINED,
    até ser confirmado por observação real, ao contrário de "020" (ver teste dedicado)."""
    responses.add(
        responses.GET,
        STATUS_URL,
        json={
            "EstadoPedidos": [{"IdPedido": "id-1", "Estado": "100", "MsgDescricao": "pendente"}],
            "Estado": "000",
            "MsgDescricao": "Operação concluída com sucesso.",
        },
        status=200,
    )

    status, _ = mbway.get_order_status(mbway_key="KEY-1", payment_id="id-1")

    assert status == PaymentStatus.UNKNOWN


@responses.activate
def test_get_order_status_http_error_raises_gateway_rejected() -> None:
    responses.add(responses.GET, STATUS_URL, json={"Message": "error"}, status=500)
    with pytest.raises(GatewayRejected):
        mbway.get_order_status(mbway_key="K", payment_id="id-1")


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
