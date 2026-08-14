"""Fase 0b — OPEN-QUESTIONS #2 (parcial, com uma restrição de segurança deliberada).

A pergunta original era: a resposta de /api/v1.02/mbway/create (sem split) traz `entity`?
Responder por completo exigiria uma criação bem-sucedida, que dispara de imediato um push MB
WAY para o número indicado — SEM esperar por confirmação. Este agente não tem um número de
telefone de teste sob controlo, e adivinhar um número real seria notificar uma pessoa
desconhecida sem consentimento. Por isso este script usa deliberadamente um número **inválido**
(demasiado curto), para observar só a forma da resposta de erro — nunca tenta uma criação que
possa ter sucesso.

**Isto NÃO resolve a pergunta original.** Fica registado em OPEN-QUESTIONS.md como dependente
de um número de telefone de teste fornecido pelo utilizador — não de falta de sandbox.

Uso: python tests/manual/observe_eupago_mbway_invalid_phone.py
Grava em docs/observed/eupago_mbway_create_invalid_phone.json.
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from _env import load

OBSERVED = Path(__file__).resolve().parents[2] / "docs" / "observed"

# Deliberadamente inválido — poucos dígitos para nenhum número real de telemóvel português.
# NUNCA trocar por um número plausível sem ser fornecido explicitamente pelo utilizador.
INVALID_PHONE = "000000"


def main() -> None:
    env = load()
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"ApiKey {env['EUPAGO_API_KEY']}",
    }
    payload = {
        "payment": {
            "amount": {"currency": "EUR", "value": 1.00},
            "identifier": f"weypay-obs-invalid-{uuid.uuid4().hex[:8]}",
            "customerPhone": INVALID_PHONE,
            "countryCode": "+351",
        }
    }
    resp = requests.post(
        f"{env['EUPAGO_API_URL']}/api/v1.02/mbway/create",
        json=payload,
        headers=headers,
        timeout=15,
    )
    try:
        data = resp.json()
    except ValueError:
        data = resp.text

    record = {"request": payload, "status_code": resp.status_code, "response": data}
    OBSERVED.mkdir(parents=True, exist_ok=True)
    out = OBSERVED / "eupago_mbway_create_invalid_phone.json"
    out.write_text(json.dumps(record, indent=2, ensure_ascii=False))
    print(f"HTTP {resp.status_code} -> {out}")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print(
        "\nNOTA: número deliberadamente inválido — isto só mostra a forma do erro, "
        "não responde se uma criação bem-sucedida traz 'entity'. Ver OPEN-QUESTIONS.md."
    )


if __name__ == "__main__":
    main()
