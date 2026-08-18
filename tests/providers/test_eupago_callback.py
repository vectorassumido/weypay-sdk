"""Testes do provider EuPago Webhooks 2.0.

⚠️ O corpo JSON usado aqui segue exatamente o exemplo da documentação oficial
(docs/providers/eupago-webhooks.md (a)) — ainda não confirmado por um payload real observado
(isso só é possível depois de configurar o canal Webhooks 2.0 no backoffice e receber um
pagamento real). A assinatura HMAC-SHA256 em si é calculada aqui com o mesmo algoritmo
documentado (hash_hmac('sha256', $data, $key, true), comparado ao base64-decode do header) —
essa parte é protocolo verificável independentemente de um payload real.
"""

from __future__ import annotations

import base64
import hmac
import json
from decimal import Decimal
from hashlib import sha256

import pytest

from weypay.errors import WebhookVerificationError
from weypay.providers.eupago.callback import verify_and_parse, verify_signature
from weypay.types import PaymentStatus

KEY = "chave-de-encriptacao-do-backoffice"


def _sign(body: bytes, key: str = KEY) -> str:
    digest = hmac.new(key.encode(), body, sha256).digest()
    return base64.b64encode(digest).decode()


def _body(**overrides: object) -> bytes:
    transaction = {
        "entity": 12345,
        "reference": "320780",
        "identifier": "agendamento-123",
        "method": "Mbway",
        "amount": {"value": 15.0, "currency": "EUR"},
        "fees": {"amount": 0.18, "currency": "EUR"},
        "date": "2026-08-18T22:59:02Z",
        "trid": 29751801,
        "status": "Paid",
    }
    transaction.update(overrides)
    return json.dumps({"transactions": transaction, "channel": {"name": "VECTORASSUMIDO"}}).encode()


# --- verify_signature ------------------------------------------------------------------


def test_verify_signature_accepts_a_correctly_signed_body() -> None:
    body = _body()
    verify_signature(body=body, signature=_sign(body), key=KEY)  # não levanta


def test_verify_signature_rejects_wrong_key() -> None:
    body = _body()
    with pytest.raises(WebhookVerificationError, match="assinatura"):
        verify_signature(body=body, signature=_sign(body, key="chave-errada"), key=KEY)


def test_verify_signature_rejects_tampered_body() -> None:
    body = _body()
    signature = _sign(body)
    tampered = _body(status="Cancel")
    with pytest.raises(WebhookVerificationError, match="assinatura"):
        verify_signature(body=tampered, signature=signature, key=KEY)


def test_verify_signature_requires_a_configured_key() -> None:
    body = _body()
    with pytest.raises(WebhookVerificationError, match="não configurada"):
        verify_signature(body=body, signature=_sign(body), key="")


def test_verify_signature_requires_the_header() -> None:
    with pytest.raises(WebhookVerificationError, match="em falta"):
        verify_signature(body=_body(), signature="", key=KEY)


def test_verify_signature_rejects_non_base64_signature() -> None:
    with pytest.raises(WebhookVerificationError, match="base64"):
        verify_signature(body=_body(), signature="not-base64!!!", key=KEY)


# --- verify_and_parse --------------------------------------------------------------------


def test_paid_maps_to_paid_status() -> None:
    body = _body(status="Paid")
    event = verify_and_parse(body=body, signature=_sign(body), key=KEY)

    assert event.status == PaymentStatus.PAID
    assert event.raw_status == "Paid"
    assert event.provider_reference == "320780"
    assert event.provider == "eupago"
    assert event.amount is not None
    assert event.amount.amount == Decimal("15.00")


@pytest.mark.parametrize(
    ("raw_status", "expected"),
    [
        ("Refund", PaymentStatus.REFUNDED),
        ("Cancel", PaymentStatus.DECLINED),
        ("Expired", PaymentStatus.EXPIRED),
    ],
)
def test_known_statuses_map_correctly(raw_status: str, expected: PaymentStatus) -> None:
    body = _body(status=raw_status)
    event = verify_and_parse(body=body, signature=_sign(body), key=KEY)

    assert event.status == expected


def test_error_status_maps_to_unknown_not_declined() -> None:
    """⚠️ Deliberado: "Error" não está confirmado como falha definitiva do pagamento — nunca
    tratar como recusa sem confirmar (ver docs/SECURITY.md regra 6)."""
    body = _body(status="Error")
    event = verify_and_parse(body=body, signature=_sign(body), key=KEY)

    assert event.status == PaymentStatus.UNKNOWN


def test_unrecognized_status_maps_to_unknown() -> None:
    body = _body(status="SomethingNew")
    event = verify_and_parse(body=body, signature=_sign(body), key=KEY)

    assert event.status == PaymentStatus.UNKNOWN


def test_missing_reference_raises() -> None:
    body = _body(reference="")
    with pytest.raises(WebhookVerificationError, match="reference"):
        verify_and_parse(body=body, signature=_sign(body), key=KEY)


def test_body_without_transactions_field_raises() -> None:
    body = json.dumps({"channel": {"name": "x"}}).encode()
    with pytest.raises(WebhookVerificationError, match="transactions"):
        verify_and_parse(body=body, signature=_sign(body), key=KEY)


def test_non_json_body_raises() -> None:
    body = b"not json at all"
    with pytest.raises(WebhookVerificationError, match="JSON"):
        verify_and_parse(body=body, signature=_sign(body), key=KEY)


def test_signature_verified_before_json_is_even_parsed() -> None:
    """Um corpo inválido como JSON mas com assinatura errada tem de falhar por causa da
    assinatura, não do parsing — não deve revelar se o corpo "parece" JSON válido a quem não
    tem a chave."""
    body = b"not json at all"
    with pytest.raises(WebhookVerificationError, match="assinatura"):
        verify_and_parse(body=body, signature=_sign(body, key="chave-errada"), key=KEY)


def test_dedupe_key_includes_reference_status_and_trid() -> None:
    body = _body(status="Paid", trid=999)
    event = verify_and_parse(body=body, signature=_sign(body), key=KEY)

    assert event.dedupe_key == "eupago:320780:Paid:999"


def test_missing_amount_is_none_not_an_error() -> None:
    body = _body(amount=None)
    event = verify_and_parse(body=body, signature=_sign(body), key=KEY)

    assert event.amount is None


def test_payload_is_the_full_parsed_body() -> None:
    body = _body()
    event = verify_and_parse(body=body, signature=_sign(body), key=KEY)

    assert "transactions" in event.payload
    assert event.payload["transactions"]["reference"] == "320780"
