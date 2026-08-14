"""Fase 0b — OPEN-QUESTIONS #3: successUrl/failUrl/backUrl no PIX são aceites, ignorados
ou causam erro?

Seguro de correr: a criação de um pagamento PIX não envia nada a ninguém — devolve uma
referência/QR para o comprador escolher pagar, não dispara nenhuma notificação. Por isso não
há restrição de "número de telefone controlado" aqui, ao contrário do MB WAY (ver
observe_eupago_mbway_invalid_phone.py e a nota em docs/OPEN-QUESTIONS.md).

Uso: python tests/manual/observe_eupago_pix.py
Grava as duas respostas cruas em docs/observed/eupago_pix_with_urls.json e
docs/observed/eupago_pix_without_urls.json.
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import Any

import requests

sys.path.insert(0, str(Path(__file__).parent))
from _env import load

OBSERVED = Path(__file__).resolve().parents[2] / "docs" / "observed"


def _base_payload(identifier: str) -> dict[str, Any]:
    return {
        "payment": {
            "amount": {"currency": "EUR", "value": 5.00},
            "identifier": identifier,
        },
        "customer": {
            "name": "Teste Weypay",
            "email": "teste@example.com",
            "countryCode": "+351",
            "phoneNumber": "912345678",
            "notify": False,
        },
    }


def main() -> None:
    env = load()
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"ApiKey {env['EUPAGO_API_KEY']}",
    }
    url = f"{env['EUPAGO_API_URL']}/api/v1.02/pix/create"

    with_urls = _base_payload(f"weypay-obs-{uuid.uuid4().hex[:8]}")
    with_urls["payment"]["successUrl"] = "https://example.test/success"
    with_urls["payment"]["failUrl"] = "https://example.test/fail"
    with_urls["payment"]["backUrl"] = "https://example.test/back"

    without_urls = _base_payload(f"weypay-obs-{uuid.uuid4().hex[:8]}")

    OBSERVED.mkdir(parents=True, exist_ok=True)
    for name, payload in [("with_urls", with_urls), ("without_urls", without_urls)]:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        record = {
            "request": payload,
            "status_code": resp.status_code,
            "response": _safe_json(resp),
        }
        out = OBSERVED / f"eupago_pix_{name}.json"
        out.write_text(json.dumps(record, indent=2, ensure_ascii=False))
        print(f"{name}: HTTP {resp.status_code} -> {out}")
        print(json.dumps(record["response"], indent=2, ensure_ascii=False))
        print()


def _safe_json(resp: requests.Response) -> dict[str, Any] | str:
    try:
        result: dict[str, Any] = resp.json()
        return result
    except ValueError:
        return resp.text


if __name__ == "__main__":
    main()
