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
# ✅ "MbWayKey" confirmado a mesma grafia em SetPedidoJson e EstadoPedidosJSON (chamada real,
# 2026-08-14) — a documentação sugeria "mbWayKey" (minúsculo) para o segundo, não confirmado.
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


# Vocabulário de EstadoPedidosJSON — mesmos códigos numéricos de SYNC_STATUS_*, mas aqui
# "000" significa "transação completada com sucesso" (estado FINAL), enquanto em
# SetPedidoJson "000" significa só "pedido enviado ao cliente" (aceitação do pedido). O mesmo
# código é ambíguo consoante o endpoint — não interpretar um sem saber de qual resposta veio.
STATUS_COMPLETED = "000"
# ✅ confirmado com uma recusa real (2026-08-15): "020" devolvido por EstadoPedidos[0].Estado
# quando o utilizador recusa o push no telemóvel, MsgDescricao "Operação financeira cancelada
# pelo utilizador" — bate certo com a tabela síncrona documentada. Os restantes códigos dessa
# tabela (048, 100, 104, 111, 113, 122, 125) ainda não foram observados especificamente aqui —
# mapeiam para UNKNOWN até serem confirmados, não para DECLINED por dedução.
STATUS_DECLINED_BY_USER = "020"
# ✅ dois códigos observados para expiração, em dois testes reais separados — não é o mesmo
# código nas duas vezes, e a diferença parece ser de TIMING, não de causa:
#
# - "101" ("Operação financeira expirada", MsgDescricao literal) — observado consultando
#   ~1 min depois da app MB WAY do utilizador já ter avisado por push que expirou (janela
#   real ~4-5 min), com `DataHoraPedidoAtualizado` a refletir o momento da expiração. Este é
#   o código ESTÁVEL, obtido depois de a ifthenpay já ter processado a expiração — não consta
#   da tabela síncrona documentada (nem "101" nem "expirada" aparecem lá), mas o código
#   original do `boxwey` (`client.py`, pré-migração) já incluía "101" no conjunto de recusa —
#   confirma que a equipa original já tinha topado com isto em produção, mesmo sem doc oficial.
# - "123" ("Operação financeira não encontrada") — observado num teste anterior, consultado
#   momentos depois de o utilizador confirmar a expiração (~4 min, sem margem extra). ⚠️
#   Hipótese não totalmente confirmada: pode ser um estado transitório de indexação, visível
#   só numa janela curta logo a seguir ao corte, antes de a ifthenpay assentar no "101"
#   estável. Mantido como EXPIRED também — ambos os testes eram genuinamente expirações reais,
#   nunca uma referência inventada, e um consumidor que polle logo a seguir ao corte não
#   deveria ver isto como "desconhecido".
STATUS_EXPIRED_CODES = frozenset({"101", "123"})


def get_order_status(
    *,
    mbway_key: str,
    payment_id: str,
    environment: Environment = Environment.PRODUCTION,
    acknowledge_no_sandbox: bool = False,
) -> tuple[PaymentStatus, dict[str, object]]:
    """``EstadoPedidosJSON`` — consulta de leitura, não contacta o telefone do cliente (ver
    docs/SECURITY.md regra 10, que só se aplica a `request_payment`). ``payment_id`` é o
    ``IdPedido`` devolvido por `request_payment`.

    ✅ Confirmado com uma consulta real (2026-08-14, pagamento €0,01 aceite pelo utilizador):
    o endpoint exige **GET com querystring** (POST com corpo JSON devolve 500 sem detalhe);
    **método é `EstadoPedidosJSON`**, todo maiúsculas em "JSON" — `EstadoPedidosJson` devolve
    500 com "Invalid method name" (o próprio erro revelou a grafia certa); o campo da chave é
    `MbWayKey` (igual a `SetPedidoJson`, não `mbWayKey` como a documentação sugeria). A
    resposta tem **dois níveis de `Estado`**: o de topo é do pedido HTTP em si (sempre "000"
    se a consulta correu bem, mesmo que o pagamento não esteja pago); o que importa é
    ``EstadoPedidos[0]["Estado"]``, o estado do pagamento propriamente dito.

    ✅ "020" (recusa pelo utilizador) confirmado com uma recusa real (2026-08-15) e mapeado
    para ``PaymentStatus.DECLINED``. ✅ "101" e "123" (janela de pagamento expirada sem
    resposta — dois testes reais separados devolveram códigos diferentes, ver
    ``STATUS_EXPIRED_CODES``) mapeados para ``PaymentStatus.EXPIRED``. Os restantes códigos da
    tabela síncrona ainda não foram observados neste endpoint especificamente — ficam
    ``UNKNOWN`` até o serem."""
    base_url = resolve_base_url(
        environment, ENDPOINTS, acknowledge_no_sandbox=acknowledge_no_sandbox
    )
    url = f"{base_url}/EstadoPedidosJSON"

    params = {
        "MbWayKey": mbway_key,
        "canal": CHANNEL,
        "idspagamento": payment_id,
    }

    data, call = perform_request(
        method="GET",
        url=url,
        provider="ifthenpay.mbway",
        operation="get_order_status",
        environment=environment,
        params=params,
        headers={"accept": "application/json"},
        secret_keys=_SECRET_KEYS,
        retry=True,
    )

    if data is None or call.http_status != 200:
        raise GatewayRejected(
            call.http_status or 0, data if data is not None else (call.response or ""), call=call
        )

    orders = data.get("EstadoPedidos")
    order_status = orders[0] if isinstance(orders, list) and orders else {}
    raw_status = str(order_status.get("Estado", "") or "")
    if raw_status == STATUS_COMPLETED:
        status = PaymentStatus.PAID
    elif raw_status == STATUS_DECLINED_BY_USER:
        status = PaymentStatus.DECLINED
    elif raw_status in STATUS_EXPIRED_CODES:
        status = PaymentStatus.EXPIRED
    else:
        status = PaymentStatus.UNKNOWN
    return status, data
