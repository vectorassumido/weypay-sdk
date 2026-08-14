"""Carrega tests/manual/../.env.manual sem depender de python-dotenv.

Usado só pelos scripts descartáveis de observação da Fase 0b (docs/migration/00-setup.md).
Nunca importado pelo SDK em si — não é parte da distribuição instalável.
"""

from __future__ import annotations

import os
from pathlib import Path

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env.manual"


def load() -> dict[str, str]:
    if not _ENV_FILE.exists():
        raise SystemExit(
            f"{_ENV_FILE} não existe. Ver docs/LOCAL-TESTING.md para as credenciais de sandbox."
        )
    values: dict[str, str] = {}
    for line in _ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    os.environ.update(values)
    return values
