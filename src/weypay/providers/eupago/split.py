"""EuPago Split Payments. Ver docs/providers/eupago-mbway.md (c).

Distribui um pagamento por vários beneficiários (ex.: salão + comissão da plataforma). Só o
método ``mbway`` está exercitado pelo `bookwey` hoje, mas o endpoint aceita outros métodos —
ver docs/providers/eupago-mbway.md (c) para a lista completa.
"""

from __future__ import annotations

from dataclasses import dataclass

from ...errors import GatewayRejected
from ...http import perform_request, resolve_base_url
from ...money import Money
from ...types import Environment, PaymentResult, PaymentStatus
from .mbway import ENDPOINTS, _headers

# externKey identifica a conta de um beneficiário — redigido no registo de auditoria, tal
# como uma credencial (bookwey/utils.py despejava isto em claro via print(); ver
# docs/PLAN.md e docs/SECURITY.md regra 3).
_SECRET_KEYS = frozenset({"externKey"})


@dataclass(frozen=True)
class Beneficiary:
    extern_key: str
    amount: Money
    identifier: str
    immediate_payment: bool = False


def create_split_payment(
    *,
    api_key: str,
    method: str,
    identifier: str,
    amount: Money,
    beneficiaries: list[Beneficiary],
    admin_callback: str,
    alias: str | None = None,
    lang: str = "PT",
    environment: Environment,
) -> PaymentResult:
    """``POST /v1/split-payments/{method}``. ``method`` ∈ multibanco|mbway|pix|creditcard|
    applepay|googlepay (ver docs/providers/eupago-mbway.md (c)). ``alias`` é o telefone,
    só usado no método ``mbway``."""
    base_url = resolve_base_url(environment, ENDPOINTS)
    url = f"{base_url}/v1/split-payments/{method}"
    payload: dict[str, object] = {
        "amount": amount.to_gateway_number(),
        "identifier": identifier,
        "adminCallback": admin_callback,
        "lang": lang,
        "beneficiaries": [
            {
                "externKey": b.extern_key,
                "amount": b.amount.to_gateway_number(),
                "identifier": b.identifier,
                "immediatePayment": b.immediate_payment,
            }
            for b in beneficiaries
        ],
    }
    if alias:
        payload["alias"] = alias

    data, call = perform_request(
        method="POST",
        url=url,
        provider="eupago.split",
        operation=f"create_split_payment.{method}",
        environment=environment,
        json_body=payload,
        headers=_headers(api_key),
        secret_keys=_SECRET_KEYS,
    )
    if data is None or call.http_status is None or not (200 <= call.http_status < 300):
        raise GatewayRejected(
            call.http_status or 0, data if data is not None else (call.response or ""), call=call
        )

    return PaymentResult(
        provider="eupago.split",
        provider_payment_id=str(data.get("reference", "")),
        status=PaymentStatus.PENDING,
        raw_status=str(data.get("transactionStatus", "")),
        entity=data.get("entity"),
        reference=data.get("reference"),
        call=call,
    )
