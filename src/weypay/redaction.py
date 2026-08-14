"""Redação de segredos na fronteira do SDK. Ver docs/SECURITY.md regra 3."""

from __future__ import annotations

from typing import Any

REDACTED = "***"


def redact(payload: Any, secret_keys: frozenset[str]) -> Any:
    """Substitui os valores de qualquer chave em ``secret_keys`` por ``"***"``,
    recursivamente em dicts aninhados e listas. As chaves em si nunca são tocadas — só
    valores. Tipos que não são dict/list (str, int, None, ...) devolvem-se inalterados."""
    if isinstance(payload, dict):
        return {
            key: (REDACTED if key in secret_keys else redact(value, secret_keys))
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [redact(item, secret_keys) for item in payload]
    return payload
