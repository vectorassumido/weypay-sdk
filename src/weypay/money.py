"""Dinheiro como Decimal, ponta-a-ponta — nunca float. Ver docs/SECURITY.md regra 4."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

_CENT = Decimal("0.01")


@dataclass(frozen=True)
class Money:
    """Um montante numa moeda, sempre quantizado ao cêntimo com ROUND_HALF_UP.

    Construir só a partir de Decimal — nunca de float. Quem tiver um float (ex.: um form)
    converte explicitamente via ``Decimal(str(x))``, nunca ``Decimal(x)`` (que herda o erro de
    representação binária do float).
    """

    amount: Decimal
    currency: str = "EUR"

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise TypeError(
                f"Money.amount tem de ser Decimal, não {type(self.amount).__name__}. "
                "Usa Decimal(str(x)), nunca Decimal(x) nem float(x)."
            )
        object.__setattr__(self, "amount", self.amount.quantize(_CENT, rounding=ROUND_HALF_UP))

    def __add__(self, other: Money) -> Money:
        self._check_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._check_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def _check_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise ValueError(f"moedas incompatíveis: {self.currency} vs {other.currency}")

    def to_gateway_string(self) -> str:
        """Formato com separador '.', ex. '20.00' — o que todos os gateways documentados até
        agora esperam (ifthenpay, EuPago). Se algum gateway precisar de vírgula, o provider
        respetivo formata a partir de ``self.amount`` diretamente, não muda este método."""
        return f"{self.amount:.2f}"

    @classmethod
    def parse(cls, value: str, currency: str = "EUR") -> Money:
        """Interpreta um montante devolvido por um gateway, tolerante a '.' e ',' como
        separador decimal."""
        normalized = value.strip().replace(",", ".")
        try:
            return cls(Decimal(normalized), currency)
        except InvalidOperation as exc:
            raise ValueError(f"não é possível interpretar {value!r} como Money") from exc
