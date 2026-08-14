# Arquitetura

O core do SDK — tudo o que é comum aos três gateways, e é onde vivem hoje a maioria dos bugs
que este trabalho corrige. Ver `docs/PLAN.md` para o porquê de estar tudo num repo.

## Módulos

```
src/weypay/
├── money.py         Money(Decimal, currency)
├── errors.py        hierarquia de exceções
├── types.py         PaymentStatus, PaymentResult, WebhookEvent, GatewayCall, Environment
├── http.py          transporte: timeout, retry, correlação, redação na fronteira
├── redaction.py      redact(payload, secret_keys) -> dict
└── providers/
    ├── ifthenpay/    mbway.py · pinpay.py · callback.py
    ├── eupago/       mbway.py · split.py · pix.py · status.py · callbacks.py
    └── sibs/         spg/ · marketplace/
```

`providers/<x>/` nunca importa `providers/<y>/` — fronteira testada em
`tests/test_isolation.py`. É o que torna trivial extrair um gateway para um pacote próprio
mais tarde, se algum dia se justificar.

## `money.py`

```python
@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "EUR"
```

- Construído a partir de `Decimal`, nunca de `float` — quem tem um `float` (ex.: um form)
  converte explicitamente via `Decimal(str(x))`, nunca `Decimal(x)`.
- `quantize(Decimal("0.01"), ROUND_HALF_UP)` em qualquer operação aritmética.
- `to_gateway_string()` por provider — a ifthenpay quer `"20.00"` (separador `.`); confirmar
  na Fase 0b se algum gateway aceita vírgula (nenhum documentado até agora exige-o).
- `parse(s: str) -> Money`, tolerante a `.` e `,` como separador decimal — usado ao ler
  respostas e callbacks, nunca ao construir pedidos.

Corrige diretamente: `float(reservation_value)` espalhado por `bookwey/utils.py` (6 pontos).

## `errors.py`

```
PaymentError
├── GatewayUnavailable        # ConnectionError — o pedido não saiu, seguro reagir como falha
├── GatewayRejected           # 4xx do gateway com payload de erro estruturado
├── PaymentIndeterminate      # ReadTimeout — não se sabe se chegou ao gateway
├── ConfigurationError        # credencial em falta ou inválida
└── WebhookVerificationError  # assinatura/chave/decifra falhou
```

A distinção `GatewayUnavailable` vs `PaymentIndeterminate` é a correção mais importante da
Fase 2: o `boxwey` hoje trata os dois casos da mesma forma (`FAILED` terminal), e um timeout
não é prova de que o pagamento não aconteceu — só de que a resposta não chegou.

## `types.py`

```python
class PaymentStatus(Enum):
    PENDING = "pending"; PAID = "paid"; DECLINED = "declined"
    EXPIRED = "expired"; REFUNDED = "refunded"; UNKNOWN = "unknown"

@dataclass(frozen=True)
class PaymentResult:
    provider: str                 # "ifthenpay.mbway", "eupago.pix", ...
    provider_payment_id: str
    status: PaymentStatus
    raw_status: str                # o código/texto exato do gateway — sempre persistido
    redirect_url: str | None = None
    entity: str | None = None
    reference: str | None = None
    expires_at: datetime | None = None
    call: "GatewayCall"

@dataclass(frozen=True)
class WebhookEvent:
    provider: str
    provider_reference: str
    status: PaymentStatus
    raw_status: str
    amount: Money | None
    dedupe_key: str
    payload: dict                  # já redigido
    ack_body: dict | None = None   # a SIBS exige {"statusCode":"200",...}; as outras não

@dataclass(frozen=True)
class GatewayCall:
    correlation_id: str
    provider: str
    operation: str                 # "create_payment", "verify_webhook", ...
    url: str
    http_status: int | None
    duration_ms: int
    request: dict                  # já redigido
    response: dict | None          # já redigido
    outcome: str                   # "success" | "rejected" | "unavailable" | "indeterminate"
    occurred_at: datetime

class Environment(Enum):
    SANDBOX = "sandbox"; PRODUCTION = "production"; FAKE = "fake"
```

`raw_status` viaja sempre ao lado do `PaymentStatus` normalizado e é o que se persiste — a
normalização é para lógica de negócio, o valor cru é para auditoria e depuração.

## `http.py` — o transporte

Regras (detalhe e porquê em `SECURITY.md`):
- Timeout sempre explícito, `(connect=5, read=15)` por omissão, configurável por chamada.
- `ConnectionError` → `GatewayUnavailable`. `ReadTimeout` → `PaymentIndeterminate`. Nenhum
  dos dois faz retry automático numa operação de escrita (criar pagamento).
- Só `get_status`/consultas fazem retry: 2 tentativas, backoff exponencial + jitter, apenas
  em erro de ligação e 5xx — nunca em 4xx.
- Devolve sempre `(data, GatewayCall)` — o `GatewayCall` já com `request`/`response`
  redigidos, pronto a persistir pela aplicação sem tratamento adicional.
- Resolve a base URL a partir de `Environment` + provider (ver `ENVIRONMENTS.md`).

## `redaction.py`

```python
def redact(payload: dict, secret_keys: frozenset[str]) -> dict
```
Substitui os valores das chaves indicadas (não as chaves em si) por `"***"`, recursivamente
em dicts aninhados e listas de dicts. Cada provider declara o seu conjunto de
`secret_keys` (ex.: ifthenpay: `{"MbWayKey", "chave"}`; EuPago: chave no header, não no
corpo — nada a redigir aí; SIBS: `webhookSecret`, `bearer_token`).

Generaliza o `{**payload, "MbWayKey": "***"}` manual do `boxwey` e substitui os `print(payload)`
do `bookwey`, que hoje despejam `externKey` de beneficiários para stdout sem redação nenhuma.

## O que fica fora do SDK, deliberadamente

Base de dados, ORM, máquina de estados, idempotência (`select_for_update`, unique index),
resolução de tenant, encriptação de credenciais em repouso. Cada aplicação já resolve isto à
sua maneira — o `GatewayCallLog` é um dataclass puro do lado do SDK; a tabela Django que o
persiste é escrita uma vez por projeto (ver `SECURITY.md` #8).

**Anti-overengineering, explicitamente de fora**: registry de plugins/entry points, cliente
async, pydantic (os dataclasses `frozen=True` bastam), ABCs de provider (um `Protocol` para
tipagem chega), outbox/event bus, circuit breaker.
