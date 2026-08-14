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
        """Formato com separador '.', ex. '20.00' — o que a maioria dos gateways documentados
        até agora espera como STRING (ifthenpay). Se algum gateway precisar de vírgula, o
        provider respetivo formata a partir de ``self.amount`` diretamente, não muda este
        método."""
        return f"{self.amount:.2f}"

    def to_gateway_number(self) -> float:
        """Exceção estreita e deliberada a "nunca float" (docs/SECURITY.md regra 4): alguns
        gateways (EuPago) exigem o montante como NÚMERO JSON, não string — e o módulo `json`
        da biblioteca padrão não serializa ``Decimal`` nativamente. A conversão acontece só
        aqui, na fronteira de serialização, nunca em aritmética — ``self.amount`` já está
        quantizado ao cêntimo antes desta chamada, e um double IEEE 754 representa sem perdas
        qualquer valor de 2 casas decimais até 15 dígitos significativos (bem acima dos limites
        documentados dos gateways, ex. 99 999€ na EuPago — 7 dígitos). Nunca usar o resultado
        para cálculos; só para colocar no payload."""
        return float(self.amount)

    @classmethod
    def parse(cls, value: str, currency: str = "EUR") -> Money:
        """Interpreta um montante devolvido por um gateway, tolerante a '.' e ',' como
        separador decimal."""
        normalized = value.strip().replace(",", ".")
        try:
            return cls(Decimal(normalized), currency)
        except InvalidOperation as exc:
            raise ValueError(f"não é possível interpretar {value!r} como Money") from exc
