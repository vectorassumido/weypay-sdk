from decimal import Decimal

import pytest

from weypay.money import Money


def test_quantizes_to_cent_on_construction() -> None:
    m = Money(Decimal("20.005"))
    assert m.amount == Decimal("20.01")  # ROUND_HALF_UP


def test_rejects_float() -> None:
    with pytest.raises(TypeError, match="Decimal"):
        Money(20.00)  # type: ignore[arg-type]


def test_addition_preserves_currency() -> None:
    total = Money(Decimal("10.00")) + Money(Decimal("5.50"))
    assert total == Money(Decimal("15.50"))


def test_addition_rejects_currency_mismatch() -> None:
    with pytest.raises(ValueError, match="moedas incompatíveis"):
        Money(Decimal("10.00"), "EUR") + Money(Decimal("10.00"), "USD")


def test_subtraction() -> None:
    result = Money(Decimal("10.00")) - Money(Decimal("3.33"))
    assert result == Money(Decimal("6.67"))


def test_to_gateway_string_uses_dot_separator() -> None:
    assert Money(Decimal("20")).to_gateway_string() == "20.00"
    assert Money(Decimal("4.5")).to_gateway_string() == "4.50"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("20.00", Decimal("20.00")),
        ("20,00", Decimal("20.00")),  # separador vírgula, tolerado ao interpretar
        ("4.68", Decimal("4.68")),
        (" 4.68 ", Decimal("4.68")),
    ],
)
def test_parse_tolerates_dot_and_comma(raw: str, expected: Decimal) -> None:
    assert Money.parse(raw).amount == expected


def test_parse_invalid_raises_value_error() -> None:
    with pytest.raises(ValueError, match="não é possível interpretar"):
        Money.parse("not-a-number")


def test_no_binary_float_drift_across_the_table() -> None:
    """Casos conhecidos por trair o float: soma repetida e valores .005."""
    total = Money(Decimal("0"))
    for _ in range(3):
        total = total + Money(Decimal("33.33"))
    assert total.amount == Decimal("99.99")


@pytest.mark.parametrize(
    "raw",
    ["0.01", "0.10", "0.15", "19.99", "100.00", "4.68", "33.33", "99999.99", "0.00"],
)
def test_to_gateway_number_is_lossless_within_documented_gateway_limits(raw: str) -> None:
    """to_gateway_number() é uma exceção estreita a "nunca float" — só na serialização, nunca
    em aritmética. Prova de que é sem perdas até ao limite documentado da EuPago (99 999€)."""
    money = Money(Decimal(raw))
    roundtrip = Decimal(str(money.to_gateway_number())).quantize(Decimal("0.01"))
    assert roundtrip == money.amount
