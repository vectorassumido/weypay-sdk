"""Referências com prefixo de sistema. Ver docs/providers/ifthenpay-callbacks.md.

Decidido em backlog-ideias#25: a ifthenpay confirmou que uma conta não tem vários callbacks
(sem fan-out), por isso cada sistema (bookwey, p8a, boxwey) passa a ter a sua própria conta,
com a sua própria chave. O prefixo deixa de ser um mecanismo de pertença entre contas
partilhadas — já não há nenhuma — e passa a ser só uma defesa de baixo custo: torna visível, só
pelo texto da referência (em logs, auditoria, ou um callback mal configurado), de que sistema é
um pagamento.
"""

from __future__ import annotations

import secrets

# ✅ Confirmado pela ifthenpay (backlog-ideias#25, 2026-10-20): `orderId`/`referencia` até 15
# caracteres em ambos os métodos (MB WAY `SetPedidoJson` e PINPAY).
REFERENCE_MAX_LENGTH = 15

SYSTEM_PREFIXES: dict[str, str] = {
    "bookwey": "71",
    "p8a": "72",
    "boxwey": "73",
}


def new_reference(system: str) -> str:
    """Gera uma referência nova: o prefixo de ``system`` + dígitos aleatórios até
    ``REFERENCE_MAX_LENGTH``. Só dígitos — o PINPAY exige ``id`` numérico (ver pinpay.py); o
    MB WAY aceita qualquer string, por isso usar o mesmo formato nos dois é mais simples do que
    ter dois geradores.

    ``system`` tem de ser uma chave de ``SYSTEM_PREFIXES`` — levanta ``KeyError`` caso
    contrário."""
    prefix = SYSTEM_PREFIXES[system]
    digits_needed = REFERENCE_MAX_LENGTH - len(prefix)
    suffix = "".join(secrets.choice("0123456789") for _ in range(digits_needed))
    return f"{prefix}{suffix}"


def has_prefix(reference: str, system: str) -> bool:
    """Confirma que ``reference`` tem o prefixo esperado para ``system``.

    ``system`` tem de ser uma chave de ``SYSTEM_PREFIXES`` — levanta ``KeyError`` caso
    contrário."""
    return reference.startswith(SYSTEM_PREFIXES[system])
