"""Suite de conformidade — porto de boxwey-serverless/api/integrations/ifthenpay/tests.py
(classe WebhookTests, 11 testes), sem Django.

O SDK só faz verificação + parsing — não conhece bases de dados, tenants nem state machines.
Por isso nem todos os 11 testes originais têm equivalente direto aqui:

- Os que testam efeitos de aplicação (enviar email, anular bilhetes, transições de estado,
  lookup de Order por referência, idempotência ao nível da BD) continuam a viver nos testes
  Django do `boxwey` — inalterados pela Fase 1 (zero-alteração-de-comportamento), portanto
  continuam a ser a prova de que esse comportamento se mantém.
- Os que testam verificação/parsing (chave, valor, vocabulário de estado) são portados aqui.

Uma divergência **intencional**, não um esquecimento: o teste original
``test_unknown_estado_is_rejected`` espera HTTP 400. Aqui, um estado desconhecido devolve
``PaymentStatus.UNKNOWN`` sem levantar — é exatamente a correção da Fase 2
(docs/SECURITY.md regra 6: nunca 4xx a um estado desconhecido, para não desencadear os "até
13" retries da ifthenpay). Decidir o código HTTP de resposta continua a ser da app.
"""

from decimal import Decimal

import pytest

from weypay.errors import WebhookVerificationError
from weypay.money import Money
from weypay.providers.ifthenpay.callback import (
    DEFAULT_MAPPING,
    extract_reference,
    parse_status,
    verify_amount,
    verify_and_parse,
    verify_key,
)
from weypay.types import PaymentStatus

CALLBACK_KEY = "anti-phishing-key"
REFERENCE = "abc123def456"


def _query(**overrides: str) -> dict[str, str]:
    defaults = {"chave": CALLBACK_KEY, "referencia": REFERENCE, "estado": "PAGO"}
    defaults.update(overrides)
    return defaults


def test_paid_callback_returns_paid_status() -> None:
    event = verify_and_parse(query=_query(estado="PAGO"), expected_key=CALLBACK_KEY)
    assert event.status == PaymentStatus.PAID
    assert event.provider_reference == REFERENCE
    assert event.raw_status == "PAGO"


def test_repeated_identical_callback_has_the_same_dedupe_key() -> None:
    """A app usa dedupe_key para detetar os retries redundantes da ifthenpay (até 13x)."""
    first = verify_and_parse(query=_query(), expected_key=CALLBACK_KEY)
    second = verify_and_parse(query=_query(), expected_key=CALLBACK_KEY)
    assert first.dedupe_key == second.dedupe_key


def test_bad_key_is_rejected() -> None:
    with pytest.raises(WebhookVerificationError, match="chave"):
        verify_and_parse(query=_query(chave="wrong-key"), expected_key=CALLBACK_KEY)


def test_blank_expected_key_rejects_everything() -> None:
    """Um tenant sem itp_callback_key configurada nunca deve conseguir confirmar nada."""
    with pytest.raises(WebhookVerificationError, match="chave"):
        verify_and_parse(query=_query(chave=""), expected_key="")


def test_amount_mismatch_is_rejected() -> None:
    with pytest.raises(WebhookVerificationError, match="não coincide"):
        verify_and_parse(
            query=_query(valor="999.99"),
            expected_key=CALLBACK_KEY,
            expected_amount=Money(Decimal("20.00")),
        )


def test_matching_amount_is_accepted() -> None:
    event = verify_and_parse(
        query=_query(valor="20.00"),
        expected_key=CALLBACK_KEY,
        expected_amount=Money(Decimal("20.00")),
    )
    assert event.status == PaymentStatus.PAID
    assert event.amount == Money(Decimal("20.00"))


def test_amount_absent_skips_verification() -> None:
    """⚠️ Fraqueza herdada do boxwey — se 'valor' não vier no template, não há como
    verificar o montante. Ver docs/OPEN-QUESTIONS.md #9 (garantir 'valor' no template)."""
    event = verify_and_parse(
        query=_query(),  # sem 'valor'
        expected_key=CALLBACK_KEY,
        expected_amount=Money(Decimal("999999.99")),  # seria óbvio se fosse verificado
    )
    assert event.status == PaymentStatus.PAID
    assert event.amount is None


def test_refund_status_code_maps_to_refunded() -> None:
    event = verify_and_parse(query=_query(estado="023"), expected_key=CALLBACK_KEY)
    assert event.status == PaymentStatus.REFUNDED


def test_declined_status_code_maps_to_declined() -> None:
    event = verify_and_parse(query=_query(estado="020"), expected_key=CALLBACK_KEY)
    assert event.status == PaymentStatus.DECLINED


def test_unknown_estado_maps_to_unknown_and_does_not_raise() -> None:
    """Divergência intencional do comportamento original — ver docstring do módulo."""
    event = verify_and_parse(query=_query(estado="ZZZ"), expected_key=CALLBACK_KEY)
    assert event.status == PaymentStatus.UNKNOWN
    assert event.raw_status == "ZZZ"


def test_missing_reference_raises() -> None:
    with pytest.raises(WebhookVerificationError, match="referencia"):
        verify_and_parse(query=_query(referencia=""), expected_key=CALLBACK_KEY)


def test_missing_status_raises() -> None:
    with pytest.raises(WebhookVerificationError, match="estado"):
        verify_and_parse(query=_query(estado=""), expected_key=CALLBACK_KEY)


def test_extract_reference_works_before_key_is_known() -> None:
    """O fluxo real: extrair a referência primeiro (para a app resolver o tenant), só depois
    verificar a chave — não é possível inverter, a chave é por-tenant."""
    assert extract_reference(_query()) == REFERENCE


def test_extract_reference_missing_raises() -> None:
    with pytest.raises(WebhookVerificationError, match="referencia"):
        extract_reference({"estado": "PAGO"})


# --- funções granulares (verify_key/verify_amount/parse_status) --------------------------
# Expostas separadamente para apps que precisam de distinguir a causa de uma falha por código
# HTTP diferente (ex.: 403 chave inválida vs 400 valor divergente) sem fazer parsing de
# mensagens de erro do WebhookVerificationError genérico.


def test_verify_key_accepts_matching_key() -> None:
    verify_key(_query(), CALLBACK_KEY)  # não levanta


def test_verify_key_rejects_mismatch() -> None:
    with pytest.raises(WebhookVerificationError):
        verify_key(_query(chave="wrong"), CALLBACK_KEY)


def test_verify_key_rejects_blank_expected() -> None:
    with pytest.raises(WebhookVerificationError):
        verify_key(_query(chave=""), "")


def test_verify_amount_returns_none_when_absent() -> None:
    assert verify_amount(_query(), Money(Decimal("20.00"))) is None


def test_verify_amount_matches() -> None:
    result = verify_amount(_query(valor="20.00"), Money(Decimal("20.00")))
    assert result == Money(Decimal("20.00"))


def test_verify_amount_mismatch_raises() -> None:
    with pytest.raises(WebhookVerificationError):
        verify_amount(_query(valor="999.99"), Money(Decimal("20.00")))


def test_verify_amount_without_expected_still_parses() -> None:
    result = verify_amount(_query(valor="20.00"), None)
    assert result == Money(Decimal("20.00"))


def test_parse_status_maps_known_values() -> None:
    assert parse_status("PAGO") == PaymentStatus.PAID
    assert parse_status("023") == PaymentStatus.REFUNDED
    assert parse_status("020") == PaymentStatus.DECLINED


def test_parse_status_unknown_never_raises() -> None:
    assert parse_status("ZZZ") == PaymentStatus.UNKNOWN


def test_payload_never_contains_the_key_in_clear() -> None:
    event = verify_and_parse(query=_query(), expected_key=CALLBACK_KEY)
    assert event.payload["chave"] == "***"
    assert CALLBACK_KEY not in str(event.payload)


def test_default_mapping_matches_the_real_boxwey_template() -> None:
    """https://api.boxwey.com/.../ifthenpay/?chave=...&referencia=...&valor=...&estado=...
    — confirmado pelo utilizador, ver docs/providers/ifthenpay-callbacks.md (a)."""
    assert DEFAULT_MAPPING.key_param == "chave"
    assert DEFAULT_MAPPING.reference_param == "referencia"
    assert DEFAULT_MAPPING.amount_param == "valor"
    assert DEFAULT_MAPPING.status_param == "estado"
    assert DEFAULT_MAPPING.paid_value == "PAGO"
