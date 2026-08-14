"""Resposta espelha docs/observed/eupago_status_legacy_path.json (observação real de
sandbox, Fase 0b) — não inventada."""

import pytest
import responses

from weypay.errors import GatewayRejected
from weypay.providers.eupago.status import get_reference_status
from weypay.types import Environment, PaymentStatus

URL = "https://sandbox.eupago.pt/api/clientes/rest_api/multibanco/info"


@responses.activate
def test_pending_status_matches_observed_sandbox_shape() -> None:
    responses.add(
        responses.POST,
        URL,
        json={
            "entidade": None,
            "referencia": "320653",
            "identificador": "weypay-obs-status-b7fb3550",
            "estado": 0,
            "data_criacao": "2026-08-14",
            "hora_criacao": "13:26:39",
            "estado_referencia": "pendente",
            "arquivada": False,
            "sucesso": True,
            "resposta": "OK",
        },
        status=200,
    )
    status, data = get_reference_status(
        api_key="KEY-1", reference="320653", environment=Environment.SANDBOX
    )
    assert status == PaymentStatus.PENDING
    assert data["estado_referencia"] == "pendente"


@responses.activate
def test_paid_status_maps_to_paid() -> None:
    """⚠️ Valor "paga" nunca observado em sandbox (não testável sem pagamento real) — herdado
    do código atual do bookwey. Ver docs/OPEN-QUESTIONS.md."""
    responses.add(
        responses.POST, URL, json={"estado_referencia": "paga", "referencia": "r"}, status=200
    )
    status, _ = get_reference_status(
        api_key="KEY-1", reference="r", environment=Environment.SANDBOX
    )
    assert status == PaymentStatus.PAID


@responses.activate
def test_unrecognized_status_value_maps_to_unknown() -> None:
    responses.add(
        responses.POST, URL, json={"estado_referencia": "cancelada", "referencia": "r"}, status=200
    )
    status, _ = get_reference_status(
        api_key="KEY-1", reference="r", environment=Environment.SANDBOX
    )
    assert status == PaymentStatus.UNKNOWN


@responses.activate
def test_uses_legacy_path_not_documented_path() -> None:
    """✅ observado em sandbox (Fase 0b): /multibanco/info devolve 404 neste host; o path
    legado /clientes/rest_api/multibanco/info é o único que funciona."""
    responses.add(responses.POST, URL, json={"estado_referencia": "pendente"}, status=200)
    get_reference_status(api_key="KEY-1", reference="r", environment=Environment.SANDBOX)
    assert responses.calls[0].request.url == URL


@responses.activate
def test_error_response_raises_gateway_rejected() -> None:
    responses.add(responses.POST, URL, json={"sucesso": False}, status=404)
    with pytest.raises(GatewayRejected):
        get_reference_status(api_key="KEY-1", reference="unknown", environment=Environment.SANDBOX)


@responses.activate
def test_entity_included_when_provided() -> None:
    responses.add(responses.POST, URL, json={"estado_referencia": "pendente"}, status=200)
    get_reference_status(
        api_key="KEY-1", reference="r", entity="12345", environment=Environment.SANDBOX
    )
    import json as _json

    body = responses.calls[0].request.body
    assert body is not None
    assert _json.loads(body)["entidade"] == "12345"


@responses.activate
def test_base_url_override() -> None:
    custom_url = "https://per-merchant.example.pt/api/clientes/rest_api/multibanco/info"
    responses.add(responses.POST, custom_url, json={"estado_referencia": "pendente"}, status=200)
    get_reference_status(
        api_key="K",
        reference="r",
        environment=Environment.SANDBOX,
        base_url="https://per-merchant.example.pt/api",
    )
    assert responses.calls[0].request.url == custom_url
