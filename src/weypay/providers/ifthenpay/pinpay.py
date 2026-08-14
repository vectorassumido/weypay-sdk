"""ifthenpay Pay by Link / PINPAY (Gateway). Ver docs/providers/ifthenpay-pinpay.md.

Produto distinto do MB WAY direto (mbway.py): checkout hospedado que agrega vários métodos
(MB WAY, cartão, Apple/Google Pay) atrás de um único link. Usado hoje só pelo `bookwey`.
"""

from __future__ import annotations

from ...errors import GatewayRejected
from ...http import GatewayEndpoints, perform_request, resolve_base_url
from ...money import Money
from ...types import Environment, PaymentResult, PaymentStatus

DESCRIPTION_MAX_LENGTH = 200
ID_MAX_LENGTH = 15


def _endpoints(gateway_key: str) -> GatewayEndpoints:
    # A GATEWAY_KEY vai no path, não no corpo — ver redact_url_values abaixo e
    # docs/providers/ifthenpay-pinpay.md (a). Sem sandbox real, tal como o MB WAY.
    return GatewayEndpoints(production=f"https://api.ifthenpay.com/gateway/pinpay/{gateway_key}")


def create_payment(
    *,
    gateway_key: str,
    id: str,  # nome do campo do protocolo ifthenpay ("id"), mantido para clareza
    amount: Money,
    description: str = "",
    lang: str = "pt",
    accounts: str | None = None,
    success_url: str | None = None,
    error_url: str | None = None,
    cancel_url: str | None = None,
    expire_date: str | None = None,
    environment: Environment = Environment.PRODUCTION,
    acknowledge_no_sandbox: bool = False,
) -> PaymentResult:
    """Cria um checkout PINPAY e devolve o ``redirect_url`` para onde encaminhar o comprador.

    ``id`` tem de ser numérico com no máximo 15 caracteres (limite do protocolo — ver
    docs/providers/ifthenpay-pinpay.md (b)); ``description`` é truncada a 200 caracteres.
    """
    if not id or len(id) > ID_MAX_LENGTH or not id.isdigit():
        raise ValueError(
            f"id tem de ser numérico com no máximo {ID_MAX_LENGTH} caracteres, recebeu {id!r}"
        )

    endpoints = _endpoints(gateway_key)
    url = resolve_base_url(environment, endpoints, acknowledge_no_sandbox=acknowledge_no_sandbox)

    payload: dict[str, str] = {
        "id": id,
        "amount": amount.to_gateway_string(),
        "lang": lang,
    }
    if description:
        payload["description"] = description[:DESCRIPTION_MAX_LENGTH]
    if accounts:
        payload["accounts"] = accounts
    if success_url:
        payload["success_url"] = success_url
    if error_url:
        payload["error_url"] = error_url
    if cancel_url:
        payload["cancel_url"] = cancel_url
    if expire_date:
        payload["expiredate"] = expire_date

    data, call = perform_request(
        method="POST",
        url=url,
        provider="ifthenpay.pinpay",
        operation="create_payment",
        environment=environment,
        json_body=payload,
        redact_url_values=frozenset({gateway_key}),
    )

    if data is None or call.http_status is None or not (200 <= call.http_status < 300):
        raise GatewayRejected(
            call.http_status or 0, data if data is not None else (call.response or ""), call=call
        )

    redirect_url = data.get("RedirectUrl")
    if not redirect_url:
        raise GatewayRejected(call.http_status, data, call=call)

    return PaymentResult(
        provider="ifthenpay.pinpay",
        provider_payment_id=str(data.get("PinCode", "")),
        status=PaymentStatus.PENDING,
        raw_status="",
        redirect_url=redirect_url,
        call=call,
    )
