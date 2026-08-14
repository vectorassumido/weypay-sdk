"""ifthenpay MB WAY v1 (SetPedidoJson). Ver docs/providers/ifthenpay-mbway.md.

Porto direto de boxwey-serverless/api/integrations/ifthenpay/client.py — mesmo
comportamento, mesmos limites (descricao <= 50 chars), para a Fase 1 do plano ser
zero-alteração-de-comportamento.
"""

from __future__ import annotations

from ...errors import GatewayRejected
from ...http import GatewayEndpoints, perform_request, resolve_base_url
from ...money import Money
from ...types import Environment, PaymentResult, PaymentStatus

CHANNEL = "03"
DESCRIPTION_MAX_LENGTH = 50
_SECRET_KEYS = frozenset({"MbWayKey"})

# ifthenpay não tem sandbox real — ver docs/ENVIRONMENTS.md. Environment.SANDBOX aqui exige
# acknowledge_no_sandbox=True (resolve_base_url levanta ConfigurationError sem isso).
ENDPOINTS = GatewayEndpoints(production="https://mbway.ifthenpay.com/ifthenpaymbw.asmx")

# Estado codes da resposta SÍNCRONA de SetPedidoJson (tabela oficial completa) — vocabulário
# numérico, distinto do estado TEXTUAL do callback assíncrono (ver callback.py). Não usado
# para decidir o status devolvido aqui (ver nota em request_payment) — só documentado.
SYNC_STATUS_SUCCESS = "000"
SYNC_STATUS_KNOWN_CODES = frozenset(
    {"000", "020", "048", "100", "104", "111", "113", "122", "123", "125"}
)


def request_payment(
    *,
    mbway_key: str,
    reference: str,
    amount: Money,
    phone: str,
    email: str,
    description: str,
    environment: Environment = Environment.PRODUCTION,
    acknowledge_no_sandbox: bool = False,
) -> PaymentResult:
    """Dispara um push MB WAY para ``phone``.

    AVISO DE SEGURANÇA (docs/SECURITY.md regra 10): esta chamada contacta o telefone indicado
    de IMEDIATO, antes de qualquer confirmação — nunca invocar com um número que não tenha
    sido explicitamente fornecido pelo utilizador final do sistema consumidor para este
    pagamento.

    O ``status`` devolvido é sempre ``PENDING`` numa criação aceite (``IdPedido`` presente) —
    ``Estado`` na resposta síncrona não é interpretado como confirmação de pagamento aqui,
    porque o código-fonte que este provider substitui (boxwey) também nunca o fez: a
    confirmação real chega sempre pelo callback assíncrono (ver callback.py). ``raw_status``
    leva o código cru para quem quiser interpretar por conta própria.
    """
    base_url = resolve_base_url(
        environment, ENDPOINTS, acknowledge_no_sandbox=acknowledge_no_sandbox
    )
    url = f"{base_url}/SetPedidoJson"

    payload = {
        "MbWayKey": mbway_key,
        "canal": CHANNEL,
        "referencia": reference,
        "valor": amount.to_gateway_string(),
        "nrtlm": phone,
        "email": email,
        "descricao": description[:DESCRIPTION_MAX_LENGTH],
    }

    data, call = perform_request(
        method="POST",
        url=url,
        provider="ifthenpay.mbway",
        operation="request_payment",
        environment=environment,
        json_body=payload,
        secret_keys=_SECRET_KEYS,
    )

    if data is None or call.http_status != 200:
        raise GatewayRejected(
            call.http_status or 0, data if data is not None else (call.response or ""), call=call
        )

    payment_id = str(data.get("IdPedido", "") or "")
    if not payment_id:
        raise GatewayRejected(call.http_status, data, call=call)

    raw_status = str(data.get("Estado", "") or "")

    return PaymentResult(
        provider="ifthenpay.mbway",
        provider_payment_id=payment_id,
        status=PaymentStatus.PENDING,
        raw_status=raw_status,
        call=call,
    )
