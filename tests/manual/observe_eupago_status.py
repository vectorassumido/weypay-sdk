"""Fase 0b — OPEN-QUESTIONS #1: /clientes/rest_api/multibanco/info (path legado, usado pelo
`bookwey`) devolve `estado` ou `estado_referencia`? É o mesmo schema do endpoint documentado
atual, /multibanco/info?

Seguro de correr: cria uma referência PIX (sem push a ninguém — ver observe_eupago_pix.py) e
consulta o estado dela nos dois paths. Só observa o estado "pendente" — confirmar a transição
para "paga"/"paid" exigiria um pagamento real, fora do que este script faz.

Uso: python tests/manual/observe_eupago_status.py
Grava em docs/observed/eupago_status_legacy_path.json e eupago_status_documented_path.json.
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


def _safe_json(resp: requests.Response) -> dict[str, Any] | str:
    try:
        result: dict[str, Any] = resp.json()
        return result
    except ValueError:
        return resp.text


def main() -> None:
    env = load()
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"ApiKey {env['EUPAGO_API_KEY']}",
    }
    base = env["EUPAGO_API_URL"]

    # 1. Criar uma referência PIX para ter algo a consultar.
    identifier = f"weypay-obs-status-{uuid.uuid4().hex[:8]}"
    create_resp = requests.post(
        f"{base}/api/v1.02/pix/create",
        json={"payment": {"amount": {"currency": "EUR", "value": 5.00}, "identifier": identifier}},
        headers=headers,
        timeout=15,
    )
    create_data = _safe_json(create_resp)
    print(
        "Criação PIX:",
        create_resp.status_code,
        json.dumps(create_data, indent=2, ensure_ascii=False),
    )

    if not isinstance(create_data, dict) or "reference" not in create_data:
        print(
            "\nSem 'reference' na resposta de criação — não é possível consultar o estado. Parar."
        )
        return

    reference = create_data["reference"]

    OBSERVED.mkdir(parents=True, exist_ok=True)
    for label, path in [
        ("legacy_path", "/clientes/rest_api/multibanco/info"),
        ("documented_path", "/multibanco/info"),
    ]:
        status_resp = requests.post(
            f"{base}{path}",
            json={"referencia": reference, "chave": env["EUPAGO_API_KEY"]},
            headers=headers,
            timeout=15,
        )
        status_data = _safe_json(status_resp)
        record = {
            "path": path,
            "request": {"referencia": reference, "chave": "***"},
            "status_code": status_resp.status_code,
            "response": status_data,
        }
        out = OBSERVED / f"eupago_status_{label}.json"
        out.write_text(json.dumps(record, indent=2, ensure_ascii=False))
        print(f"\n{label} ({path}): HTTP {status_resp.status_code} -> {out}")
        print(json.dumps(status_data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
