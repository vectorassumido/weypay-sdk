# SDK de pagamentos partilhado — `weypay` (ifthenpay · EuPago · SIBS)

## Contexto

Três bases de código tocam gateways de pagamento portugueses, sem nada partilhado:

| Projeto | Gateway | Ficheiros | Estado |
|---|---|---|---|
| `boxwey-serverless/api` | **ifthenpay MB WAY v1** (`ifthenpaymbw.asmx/SetPedidoJson`) | `integrations/ifthenpay/{client,views}.py`, `events/services/payments.py` | Bom: timeout 15s, chave anti-phishing em `constant_time_compare`, verificação de valor, state machine, `simple_history`, 11 testes de webhook |
| `bookwey-serverless/booksys-be` | **EuPago** (MBWay, split, PIX, status) + **ifthenpay PINPAY** | `integrations/payments/utils.py` (520 linhas, 6 funções) | Mau: zero timeouts, zero retries, `print(payload)` a despejar chaves, `float()` em valores monetários, zero auditoria, zero testes de callback |
| `sibs-integration-project` | **SIBS** | `sibs-operator-sdk/sibs_sdk/` | Esboço de ~15 KB, sem git, sem testes, protocolo inteiramente adivinhado |

Ambos os backends são Django 5.2.11 / Python 3.12 / `requests`, e guardam credenciais **por tenant na base de dados** (`Merchant.eupago_*` / `Merchant.ifthenpay_*`; `Tenant.mbway_key` / `Tenant.itp_callback_key`) — nunca em settings globais.

"Um SDK por gateway" seria já o eixo errado: dentro da **ifthenpay** os dois projetos usam **dois produtos distintos** (MB WAY direto vs Gateway/PINPAY), com payloads e vocabulários de estado diferentes. O eixo real é `provider × produto`.

### Dois princípios que enquadram tudo o resto

**Os dois sistemas estão em produção a receber pagamentos reais.** As lacunas abaixo são risco latente e desvio face à especificação, não avaria: o caminho feliz funciona hoje e tem de continuar a funcionar. Nenhuma fase muda comportamento observável sem teste que o comprove, e a Fase 1 tem como critério explícito passar a suite atual **sem editar um único teste**.

**Verificado vs deduzido.** Tudo o que se segue está marcado como ✅ **verificado** (citado da documentação oficial ou lido no código) ou ⚠️ **a confirmar** (inferência plausível ainda não provada). Nenhum ⚠️ vira código sem antes ser observado contra a sandbox — é para isso que serve a Fase 0b. A mesma marcação é obrigatória em cada ficheiro de `docs/providers/`.

### O que a documentação oficial revelou

A leitura dos docs oficiais expôs divergências que passam a ser motivo autónomo para este trabalho:

✅ **ifthenpay MB WAY — `boxwey` está numa API descontinuada.** A v1 (`ifthenpaymbw.asmx`) está marcada **"API - MBWAY (Deprecated)"**; o índice atual lista `api/mbway/` (MB WAY REST) como a API corrente.
- ✅ `descricao` tem **máximo 50 caracteres**. `payments.py:41` envia `f"{event.name} — {n} bilhete(s)"` sem truncar. Que a ifthenpay o aceite hoje (trunca? ignora?) é ⚠️ — a testar com a conta de teste antes de mudar.
- ✅ Existe `EstadoPedidosJson` para consulta de estado — nunca portado, e é exatamente o endpoint de reconciliação que falta.
- ✅ Existe um **Webhook Tester** oficial que simula callbacks por método de pagamento — é a forma de exercitar o callback localmente sem esperar por um pagamento real.

**Dois vocabulários de estado distintos, e o callback é configurado pelo merchant.** O URL de callback é registado por conta no backoffice ifthenpay, com os nomes dos parâmetros escolhidos por nós e os valores substituídos a partir de placeholders — hoje:
```
https://api.boxwey.com/api/v1/webhooks/ifthenpay/?chave=[ANTI_PHISHING_KEY]&referencia=[REFERENCIA]&valor=[VALOR]&estado=[ESTADO]
```
Logo: os nomes `chave`/`referencia`/`valor`/`estado` **não são protocolo da ifthenpay**, são a nossa configuração; e `[ESTADO]` resolve para um valor textual (`PAGO`), não para os códigos numéricos. A tabela numérica oficial (`000, 020, 048, 100, 104, 111, 113, 122, 123, 125`) é o vocabulário da resposta **síncrona** do `SetPedidoJson`. O comentário em `client.py:24-27` está correto ao separar os dois.

Duas consequências:
- ⚠️ `STATUS_REFUNDED = "023"` e `STATUS_DECLINED = {"020","101","113"}` são comparados em `views.py:81-84` contra o `estado` do **callback**, que é textual — pelo que esses ramos possivelmente nunca disparam. Isto **não quebrou nada em produção**, porque o único caminho que importa (`PAGO`) funciona; o risco é que um estado fora do conjunto devolve HTTP 400 (`views.py:91`) e ✅ a ifthenpay repete até 13 vezes. Qual é o conjunto real de valores de `[ESTADO]` é pergunta para a ifthenpay — até haver resposta, responder 200 e registar é seguro em qualquer cenário, e é a única mudança que faço sem confirmação.
- ⚠️ Como os nomes dos parâmetros são nossos, o `valor` pode não estar no template de algumas contas — o que explicaria o `if valor:` condicional em `views.py:62`. A verificar conta a conta no backoffice (tarefa tua); garantir `[VALOR]` em todas é correção de configuração, custo zero.

**EuPago — o polling do `bookwey` pode nunca confirmar nada.** ✅ A resposta documentada de `/multibanco/info` traz o campo `estado` (exemplo oficial: `"entidade","referencia","identificador","estado","data_criacao","hora_criacao","arquivada","sucesso","resposta"`, com `"estado": "pendente"`); **não existe** `estado_referencia`. `api/services/payments.py:30,34` testa `data.get("estado_referencia") == "paga"`.
⚠️ **Mas não concluo daqui que o polling está morto**: o `bookwey` chama o path *legado* `/clientes/rest_api/multibanco/info`, e a especificação acima é a do endpoint atual — a API antiga pode muito bem devolver `estado_referencia`. É exatamente o tipo de dedução que não quero fazer, e agora não preciso: com as credenciais de sandbox, a Fase 0c chama o endpoint e regista a resposta real.
- ✅ Existe **Webhooks 2.0**: `POST`, assinatura **HMAC-SHA256 no header `X-Signature`** (comparada contra o base64-decode da assinatura, com a chave de encriptação gerada no backoffice), estados `Paid/Refund/Error/Cancel/Expired`, retry 3×2min e depois horário durante 24h. O `X-Initialization-Vector` é outra coisa — só existe para a cifra AES-256-CBC opcional, não para autenticação.
- ⚠️ O `bookwey` usa o **1.0**, cujos parâmetros ✅ incluem `chave_api` ("API Key used to create the reference"). Que sirva para *validar* o callback é **dedução minha** — a documentação não o diz. É segredo partilhado, portanto a inferência é razoável, mas confirma-se na Fase 0b antes de virar mecanismo de segurança.
- ✅ Produção é `clientes.eupago.pt` (troca-se `sandbox` por `clientes`) — hoje implícito num campo de texto por merchant, sem flag de ambiente.

✅ **SIBS — temos o protocolo real, e o esboço está errado em todos os pontos.**

| | Esboço | Real |
|---|---|---|
| Host | `api.sibsapi.com` (inventado) | `api.qly.sibspayments.com` (QLY) / `api.sibspayments.com` (PRD) |
| Fluxo | 1 passo, `POST /payments` | 2 passos: checkout → purchase específico do método |
| Auth | `Bearer` em tudo | `Bearer {AuthToken}` no checkout → **`Digest {transactionSignature}`** nos passos seguintes |
| Webhook | HMAC-SHA256 hex em `X-SIBS-Signature` | **AES-256-GCM**, `X-Initialization-Vector` + `X-Authentication-Tag`, corpo base64 |
| Ack | nenhum | `{"statusCode":"200","statusMsg":"Success","notificationID":"…"}` obrigatório, senão retry |
| `transactionID`/`transactionSignature` | ausentes | centrais |

Endpoints reais: `POST /api/v2/payments` (checkout) · `POST /{transactionID}/mbway-id/purchase` · `POST /{transactionID}/service-reference/generate` (Multibanco) · `GET /{transactionID}/status`. E o **Marketplace é uma família de API separada** do SPG: `/sibs/v2/submerchant` (onboarding) e `/sibs/v1/split/{split-type}` (split/payout), com código de submerchant de 8 dígitos e moeda `"968"`.

Por fim, o `bookwey` tem **duas falhas de segurança abertas** que este trabalho é a oportunidade natural de fechar (Fase 4) — e a documentação oficial confirma que ambos os gateways oferecem o mecanismo necessário.

---

## Resposta às perguntas

### 1. Um SDK por gateway, ou juntos? → **Juntos: um repo, um package, sub-packages por provider**

- A superfície partilhada é grande e é **exatamente onde estão os bugs**: transporte HTTP (timeouts, retry, correlação), dinheiro (`Decimal` ponta-a-ponta), redação de segredos, taxonomia de erros, normalização de estados, verificação de callbacks, auditoria. Separar duplicaria isto três vezes — ou obrigaria a um quarto package `core`, pior.
- Os consumidores precisam de **subconjuntos diferentes**; resolve-se com *extras* numa distribuição, sem custo — todos assentam em `requests`.
- Custo operacional: 1 changelog, 1 tag, 1 pipeline. Com 2 consumidores, 3–4 packages seriam a matriz de versões que ninguém mantém — **isso** é que seria overengineering.
- Isolamento por **fronteira de módulo**, não de package: `providers/<x>/` nunca importa `providers/<y>/`, com um teste que o prova. Extrair um gateway mais tarde é um `git mv` + um `pyproject.toml`.
- Os docs oficiais reforçam-no: os três gateways divergem no *protocolo* (1 vs 2 passos, query-string vs corpo cifrado) mas convergem no *que precisa de ser bem feito* — timeout, redação, `Decimal`, verificação, auditoria.

Contrapartida assumida: cadência de release acoplada. Mitigação — tag fixa nos consumidores; um patch que só toca `providers/eupago/` é trivialmente revisível e o teste de isolamento delimita o raio.

### 2. E a SIBS? → **Mesmo repo, extra próprio, e agora já implementável a sério**

- Antes de ler a documentação, a resposta seria "junto mas experimental". Com o protocolo real em mãos, `providers/sibs/` deixa de ser um esboço adivinhado e passa a ser **código escrito contra a especificação** — falta apenas contrato e credenciais, não informação.
- A tese do esboço estava certa e passa a ser o desenho do SDK inteiro: **stateless, credenciais injetadas por chamada**, o SDK não conhece tenants.
- A SIBS é o teste mais duro da abstração e é **por isso** que vale tê-la no mesmo repo: obriga a que o contrato de webhook seja `(headers, query, body, secrets) → WebhookEvent` — cobre o GET-com-`chave` da ifthenpay, o POST-com-`X-Signature` do EuPago 2.0 e o corpo AES-GCM da SIBS. Uma abstração desenhada só sobre a ifthenpay teria assumido "webhook = query params" e partia na primeira integração seguinte.
- Divide-se em `sibs/spg/` (pagamentos) e `sibs/marketplace/` (onboarding + split), que são famílias de API distintas.
- Argumento decisivo à parte: o `sibs-integration-project` **não tem repositório git nenhum**. Dobrá-lo no SDK dá-lhe histórico, testes e CI de graça.

---

## Desenho

```
weypay-sdk/                          # repo GitHub novo, público (só código de protocolo, zero segredos)
├── pyproject.toml                   # requires-python >=3.12; dep base: requests — e mais nenhuma
├── README.md · CHANGELOG.md
├── docs/                            # ver Fase 0a
├── src/weypay/
│   ├── money.py        # Money(Decimal, currency) — quantize ROUND_HALF_UP, parse "20.00" e "20,00"
│   ├── errors.py       # PaymentError → GatewayUnavailable | GatewayRejected |
│   │                   #   PaymentIndeterminate | ConfigurationError | WebhookVerificationError
│   ├── types.py        # PaymentStatus, PaymentResult, WebhookEvent, GatewayCall
│   ├── http.py         # transporte: timeouts, retry, correlation id, devolve (data, GatewayCall)
│   ├── redaction.py    # redact(payload, secret_keys)
│   └── providers/
│       ├── ifthenpay/  mbway.py · pinpay.py · callback.py    (mapa de parâmetros configurável)
│       ├── eupago/     mbway.py · split.py · pix.py · status.py · callbacks.py (1.0 e 2.0)
│       └── sibs/       spg/ (checkout · mbway · reference · status · webhook AES-GCM)
│                       marketplace/ (submerchant · split)
└── tests/  test_money · test_http · test_redaction · providers/… · test_isolation.py
```

Extras: `weypay[ifthenpay]`, `weypay[eupago]`, `weypay[sibs]`. Não são decorativos — o `sibs` traz mesmo uma dependência a mais (`cryptography`, para a decifra AES-256-GCM do webhook), que nem o `boxwey` nem o `bookwey` têm razão para instalar. `ifthenpay` e `eupago` bastam-se com `requests`.

**Tipos do core** (todos `@dataclass(frozen=True)`, sem pydantic):

- `PaymentStatus` — `PENDING · PAID · DECLINED · EXPIRED · REFUNDED · UNKNOWN`. O código cru do gateway (`"000"`, `"PAGO"`, `"pendente"`, `"Paid"`) viaja sempre em paralelo em `raw_status`, e é ele que se persiste.
- `PaymentResult` — `provider` (`"ifthenpay.mbway"`), `provider_payment_id`, `status`, `raw_status`, `redirect_url` (PINPAY), `entity`/`reference`/`expires_at` (Multibanco), `call`.
- `WebhookEvent` — `provider`, `provider_reference`, `status`, `raw_status`, `amount: Money | None`, `dedupe_key`, `payload` (redigido), `ack_body: dict | None` (a SIBS exige um corpo de confirmação específico).
- `GatewayCall` — auditoria: `correlation_id`, `provider`, `operation`, `url`, `http_status`, `duration_ms`, `request`/`response` (**já redigidos**), `outcome`, `occurred_at`.

**Contrato uniforme de webhook**, que os três protocolos reais obrigam a ter:
```python
def verify_and_parse(*, headers, query, body: bytes, secrets) -> WebhookEvent   # levanta WebhookVerificationError
```

Na ifthenpay os nomes dos parâmetros e os valores de estado são **configuração nossa** (o template registado no backoffice), não protocolo — logo o parser recebe um `CallbackMapping` (nomes dos params + vocabulário de estados) com o default a corresponder ao template atual do `boxwey`. Isto tem um efeito prático valioso: o `bookwey` pode registar o callback do PINPAY com **exatamente os mesmos nomes** que o `boxwey` usa no MB WAY, e os dois projetos convergem numa única forma de callback e num único parser, em vez de dois.

**O que o SDK faz e o que não faz.** Faz: transporte, formatação de payloads, normalização de estados, verificação criptográfica de callbacks, redação, produção do registo de auditoria. **Não faz**: base de dados, ORM, state machine, idempotência, resolução de tenant, encriptação de credenciais em repouso — tudo isso é da aplicação, e é onde os dois projetos divergem legitimamente.

**Sem `contrib.django`** (decidido): a única dependência é `requests`. O `GatewayCall` é um dataclass puro; cada projeto define o seu `GatewayCallLog` (~10 colunas, ~30 linhas).

**Distribuição**: repo GitHub público, tag exata em ambos os `requirements.txt`:
`weypay @ git+https://github.com/<org>/weypay-sdk@v0.1.0`. Nenhuma credencial no build do Docker.

### Ambientes e desenvolvimento local

Os três gateways **não** oferecem a mesma coisa, e tratá-los como se oferecessem seria perigoso:

| Gateway | Sandbox | Como se separa de produção |
|---|---|---|
| **EuPago** | Sim, host próprio | `sandbox.eupago.pt` ↔ `clientes.eupago.pt` (troca-se a palavra) |
| **SIBS** | Sim, host próprio | QLY `api.qly.sibspayments.com` ↔ PRD `api.sibspayments.com` |
| **ifthenpay** | **Não** | Mesmos endpoints de produção; o isolamento vem **só das chaves de teste**, pedidas à ifthenpay. O "Sandbox Mode" dos plugins deles é apenas uma flag que suprime callbacks — não é um ambiente |

Desenho que isto obriga:

- `Environment.SANDBOX | PRODUCTION` no SDK resolve as base URLs por provider — deixa de haver URL em texto livre por merchant (`merchant.eupago_api_url`, hoje o único indicador de ambiente no `bookwey`, sem qualquer flag).
- Para a ifthenpay, `SANDBOX` resolveria para o **mesmo host** de produção. Deixar isso implícito daria uma falsa sensação de segurança, por isso o SDK **não o faz em silêncio**: `Environment.SANDBOX` num provider sem sandbox real levanta erro salvo passagem explícita de `acknowledge_no_sandbox=True`, e o `GatewayCall` fica marcado como tendo corrido contra produção.
- **Terceiro modo, `Environment.FAKE`**, para desenvolvimento local: transporte que não abre socket nenhum e devolve respostas gravadas a partir dos exemplos da documentação oficial. É este o default em `config.settings.development` nos dois projetos — hoje o `boxwey` local nunca exercita o cliente (os testes fazem patch a `requests.post`) e o `bookwey` bateria em produção da ifthenpay se alguém corresse o fluxo à mão. As respostas gravadas são as mesmas fixtures que a suite de conformidade usa, portanto não há um segundo conjunto a manter.
- Regra derivada: **em `PRODUCTION` nunca se aceita uma chave de teste conhecida, e em `FAKE` nunca se abre rede** — ambas verificadas por teste.

### Callbacks: uma URL comum?

**Uma forma comum, sim; uma URL comum, não.** Três eixos, três respostas:

**Por projeto — obrigatoriamente separado.** `api.boxwey.com` e o `bookwey` são apps e bases de dados distintas. Não é uma escolha.

**Por tenant vs platform-wide — platform-wide.** O `boxwey` já o faz e está certo: uma só URL, a `Order` é localizada pela `provider_reference` com `.all_tenants()`, e só então a `chave` é comparada contra a chave **do tenant dessa order** (`views.py:47-60`). É a ordem correta — com uma URL única não se pode validar a chave primeiro, porque não se sabe qual esperar. O `bookwey` faz hoje o contrário: `adminCallback` é por-merchant (`{merchant.eupago_api_callback}/{agendamento_id}`, `utils.py:163`), o que multiplica URLs a configurar à mão e mete o nosso id no path em vez da referência do gateway. Deve convergir para a forma do `boxwey`.

Condição que isto impõe: **a referência tem de ser globalmente única e não adivinhável**, porque é ela que discrimina o tenant. O `boxwey` cumpre (`uuid4().hex[:12]`, 48 bits, `unique=True`). O `bookwey` **não**: `str(schedule.id.int)[-15:]` é derivado do UUID do `Schedule` e é devolvido ao browser como referência de polling. Passa a token aleatório na Fase 4 — **mas não em hex**: o PINPAY limita `id` a *15 caracteres numéricos*, pelo que a referência do `bookwey` tem de ser 15 dígitos aleatórios (≈50 bits), não `uuid4().hex[:12]`. Cada provider declara o seu formato de referência no SDK, em vez de se assumir um formato comum.

**Por gateway/produto — uma rota cada, com a mesma forma.** Além do problema de verificação acima, o método HTTP difere (ifthenpay GET, EuPago 2.0 POST, SIBS POST) e a resposta esperada também (a SIBS exige um corpo JSON com `notificationID`; as outras bastam-se com 200). Forma a adotar:

```
boxwey    /api/v1/webhooks/ifthenpay/     MB WAY   — MANTER exatamente como está
bookwey   /api/v1/webhooks/ifthenpay/     PINPAY   — mesmo path, outro domínio e outra BD
bookwey   /api/v1/webhooks/eupago/
(futuro)  /api/v1/webhooks/sibs/
```

O que é partilhado é o *interior*: `verify_and_parse` → `WebhookEvent` → `select_for_update` → transição idempotente → `GatewayCallLog` → 200. A rota fixa o provider; o resto é o mesmo código.

**As URLs de callback são contrato público estável.** Estão registadas à mão, por conta, no backoffice de cada gateway. Nunca renomear — versionar por adição. Em particular, `boxwey`'s `/api/v1/webhooks/ifthenpay/` **não muda** nesta migração: está registada e a funcionar com tenants reais, e renomeá-la seria trabalho manual × N contas por ganho nenhum.

### Segurança e auditoria — as regras não-negociáveis

Cada uma corrige um defeito real e presente; nada aqui é especulativo.

1. **Retry nunca em criação de pagamento.** `ConnectionError` (pedido não saiu) → `GatewayUnavailable`, seguro falhar. `ReadTimeout` → `PaymentIndeterminate`, e a app **não pode** marcar falhado — hoje o `boxwey` marca `FAILED` (estado sem saída) num timeout em que o push MB WAY pode perfeitamente ter disparado. Só leituras (`get_status`) fazem retry: 2 tentativas, backoff exponencial com jitter, apenas em erro de ligação e 5xx. Nunca em 4xx.
2. **Timeouts sempre explícitos**: `(connect=5, read=15)`. Hoje o `bookwey` não tem nenhum em 6 chamadas — um gateway pendurado segura o pedido até ao corte dos 60s do Cloud Run.
3. **Redação na fronteira do SDK.** `GatewayCall.request/response` saem redigidos, portanto a app persiste às cegas. Generaliza o `MbWayKey: "***"` do `boxwey` e mata o `print(payload)` do `bookwey`, que despeja chaves `externKey` de beneficiários para stdout.
4. **`Decimal` ponta-a-ponta.** `Money` formata por gateway (a ifthenpay exige separador `.`); acabam os `float(reservation_value)` num caminho de dinheiro.
5. **Comparação em tempo constante** de todas as chaves de callback.
6. **Um estado desconhecido nunca devolve 4xx ao gateway**: mapeia para `UNKNOWN`, regista, e responde 200 — devolver 400 só desencadeia os 13 retries da ifthenpay sem nada mudar. Os dois vocabulários (síncrono numérico vs callback textual) ficam em tabelas separadas e explicitamente nomeadas.
7. **Verificar sempre assinatura + referência + valor + moeda**; onde o esquema for fraco ou inexistente, **reconciliar contra o gateway** antes de confirmar (Fase 4).
8. **Auditoria**: uma tabela `GatewayCallLog` por projeto, escrita na iniciação e no webhook, read-only no admin.
9. **Idempotência na app**: `dedupe_key` estável + unique index + `select_for_update`. Nenhum projeto tranca a linha hoje.

**Deliberadamente de fora** (anti-overengineering): registry de plugins, cliente async, pydantic, ABCs de provider (só um `Protocol` para tipagem), outbox/event bus, encriptação de credenciais dentro do SDK, circuit breaker.

---

## Plano de migração

### Fase 0a — Criar o repositório e escrever a documentação (**antes de qualquer código**)

**Esta fase não produz código de implementação** — só o esqueleto do repo e a documentação. `src/weypay/` fica criado mas vazio. **Nenhum ficheiro dos projetos existentes é tocado em 0a, 0b ou 0c.**

1. `mkdir /home/chrisdo/projects/weypay-sdk && git init` (repositório **local**; o remote público em GitHub cria-se depois, quando houver o que publicar), mais `pyproject.toml`, `.gitignore`, `README.md`, `CHANGELOG.md`, `src/weypay/`, `tests/`, `docs/`, e commit inicial.
2. Criar a skill `weypay-phase` (protocolo de execução por fase + restrições) e `docs/PROGRESS.md` (estado retomável).
3. Escrever `docs/` na íntegra, a partir da documentação oficial já recolhida e do levantamento do código atual dos dois projetos:

```
docs/
├── PLAN.md                     este plano, versionado no repo
├── LOCAL-TESTING.md            ⭐ guião passo a passo para pagar localmente nos 2 projetos
├── ARCHITECTURE.md             core: Money, errors, types, http, redaction; contratos e porquês
├── ENVIRONMENTS.md             sandbox/produção/FAKE por gateway
├── SECURITY.md                 as 9 regras + modelo de ameaça dos callbacks + o que já falhou
├── OPEN-QUESTIONS.md           o que falta confirmar, por gateway, com quem, e o que bloqueia
├── providers/
│   ├── ifthenpay-mbway.md      ├── eupago-mbway.md      ├── sibs-spg.md
│   ├── ifthenpay-pinpay.md     ├── eupago-split.md      └── sibs-marketplace.md
│   └── ifthenpay-callbacks.md  ├── eupago-pix.md
│                               ├── eupago-status.md
│                               └── eupago-webhooks.md   (1.0 e 2.0)
└── migration/
    ├── 00-setup.md · 01-boxwey-adopt.md · 02-boxwey-cleanup.md
    └── 03-bookwey-adopt.md · 04-bookwey-security.md · 05-sibs.md
```

Cada `providers/*.md` segue o mesmo molde: **(a)** endpoints, método, auth e base URLs por ambiente; **(b)** campos de request *verbatim* com tipos e limites (ex.: `descricao` ≤ 50, `id` ≤ 15 numéricos, `amount` com separador `.`); **(c)** campos de response *verbatim*; **(d)** vocabulários de estado, separando síncrono de callback; **(e)** formato de callback e mecanismo de verificação; **(f)** *"o que o projeto X faz hoje"* com `ficheiro:linha`; **(g)** *delta* entre os dois; **(h)** link ao documento oficial.

Cada `migration/*.md` segue: pré-condições · passos exatos e ordenados · ficheiros tocados · testes a acrescentar · comando de verificação · **como reverter**.

### Fase 0b — Verificar contra a sandbox tudo o que está ⚠️ (**antes de escrever providers**)

Com as credenciais de sandbox disponíveis, nenhuma dedução precisa de sobreviver até ao código. Script descartável em `tests/manual/`, respostas cruas gravadas em `docs/observed/` e promovidas a fixtures do transporte `FAKE` — o que fecha o ciclo: o que o nível 1 simula passa a ser o que o gateway realmente devolveu.

| A confirmar | Como |
|---|---|
| `/clientes/rest_api/multibanco/info` devolve `estado` ou `estado_referencia`? Que valores? | Criar referência MB WAY em sandbox e consultar antes e depois de pagar |
| A resposta de `/api/v1.02/mbway/create` traz `entity`? (`booking.py` lê `entity`/`reference`/`amount`, mas a spec só documenta `transactionStatus`/`transactionID`/`reference`) | Chamada real em sandbox |
| O split devolve mesmo `entity`+`reference`+`amount`? | Chamada real em sandbox |
| `successUrl`/`failUrl`/`backUrl` no PIX: aceites, ignorados ou erro? | Chamada real com e sem esses campos |
| Que parâmetros chegam de facto no callback 1.0, e `chave_api` vem preenchido? | Configurar o callback de sandbox para um túnel e pagar |
| ifthenpay: `descricao` > 50 chars é truncada, ignorada ou rejeitada? | Conta de teste (`ITP_MBWAY_KEY`) |
| Que valores textuais de `[ESTADO]` chegam ao callback? | **Webhook Tester** oficial da ifthenpay |

Regra: se a verificação **contradisser** o que o plano assume, ganha a observação — atualiza-se `docs/providers/*.md` e `docs/PROGRESS.md` e o plano passa a seguir o comportamento real, não o documentado.

### Fase 0c — Core + ifthenpay (`v0.1.0`)
- Core a partir de `boxwey/api/integrations/ifthenpay/client.py` + `sibs_sdk/client.py::_request`, mais `Environment` e o transporte `FAKE`. O `sibs-integration-project` fica onde está até à Fase 5; nada dele é copiado agora.
- `providers/ifthenpay/` com as duas tabelas de estado separadas (síncrona numérica / callback textual), `CallbackMapping` configurável e `descricao` truncada a 50.
- Os 11 testes de webhook em `boxwey/api/integrations/ifthenpay/tests.py:117-195` reescritos sem Django (com `responses`) → suite de conformidade do SDK, mais casos para cada código numérico oficial na resposta síncrona.
- Gates: `ruff`, `mypy --strict`, `pytest`, `tests/test_isolation.py`.

### Fase 1 — `boxwey` adota, sem alteração de comportamento
- `requirements.txt`: `weypay @ git+https://github.com/<org>/weypay-sdk@v0.1.0`.
- `integrations/ifthenpay/client.py` reduz-se a um shim (~20 linhas) que devolve o `MbwayPaymentResult` atual → `events/services/payments.py` e `public_api/tests/test_checkout.py` **não mudam**.
- `views.py:37-75` passa a usar `verify_and_parse`; o lookup da `Order`, a comparação de valor e o state machine em `events/services/orders.py` ficam onde estão.
- Verificação: `python manage.py test` verde **sem editar um único teste**.

### Fase 2 — `boxwey`: remover o shim, corrigir os bugs confirmados pelos docs, ganhar auditoria
- `initiate_payment` chama o SDK diretamente; apagar `client.py` e `MbwayPaymentResult`.
- **Deixar de devolver 400 a estados desconhecidos** no callback (hoje `views.py:91`) — passa a 200 + registo, cortando os 13 retries. Confirmar com a ifthenpay o conjunto real de valores textuais de `[ESTADO]` e só então mapear recusa/reembolso; até lá esses ramos ficam explicitamente marcados como não verificados, em vez de comparados contra códigos numéricos que não se aplicam ao callback.
- **Garantir `[VALOR]` no template de callback de todas as contas** (config no backoffice, não código) e tornar a verificação de montante obrigatória em vez de condicional.
- **Truncar `descricao` a 50 caracteres.**
- **Corrigir o bug do timeout**: `PaymentIndeterminate` deixa a order em `PENDING` (o `expire_orders` já a apanha) em vez do `FAILED` terminal de `public_api/views.py:150-155`.
- Modelo `GatewayCallLog` em `integrations/models.py` + admin read-only. É a definição de referência que a Fase 4 replica.
- Resolver `core/phone.py:27-31` (`pt_national_digits` é código morto): usar ou apagar.
- **Registar em backlog** (fora de âmbito aqui, mas agora documentado): migrar de MB WAY v1 para a v2 REST, que é a API suportada.

### Fase 3 — `bookwey` adota o transporte (`v0.2.0`)
- SDK ganha `providers/eupago/` e `providers/ifthenpay/pinpay.py`, escritos contra os docs oficiais.
- As 6 funções de `utils.py` ficam finas: comissão (`calculate_commission_amount`, mantém-se — coberta por `tests/test_commission.py`) + chamada ao SDK + `Payment.objects.create`. Saem: `requests` direto, `print()`, `float()`.
- `Environment` explícito (`sandbox.eupago.pt` ↔ `clientes.eupago.pt`) em vez do URL em texto livre por merchant; `FAKE` por default em desenvolvimento.
- Riscos a controlar com teste de tabela payload-antigo-vs-novo: `float()` → `Decimal` muda o valor no fio em arredondamentos; e confirmar se `successUrl`/`failUrl`/`backUrl` são de facto ignorados no PIX (não constam da spec) antes de os remover.

### Fase 4 — `bookwey`: fechar os buracos de segurança
Duas falhas abertas, ambas com o mesmo efeito — **marcações confirmadas sem pagamento**:
- `api/services/payments.py:11-19` — `GET /api/pagamento-callback/<schedule_uuid>/` é público, sem autenticação e **sem qualquer verificação junto do gateway**: confirma o pagamento a quem souber o UUID do `Schedule`.
- `api/services/payments.py:26-27` — `check_payment_status` confirma qualquer pagamento `pinpay` **sem contactar a ifthenpay**; a referência é `str(schedule.id.int)[-15:]` e é devolvida ao browser.

Correções, todas suportadas por mecanismo oficial:
- **EuPago**: verificar a `chave_api` do callback 1.0 contra `merchant.eupago_api_key` (segredo partilhado que já existe e hoje é ignorado), em tempo constante, **e** validar `valor`/`referencia`. Migrar para **Webhooks 2.0** com assinatura `X-Signature` HMAC-SHA256 assim que o canal estiver configurado no backoffice — é o único que também notifica reembolso/expiração.
- **PINPAY**: registar o callback anti-phishing no backoffice ifthenpay, **reutilizando os mesmos nomes de parâmetros do template do `boxwey`** (`chave`/`referencia`/`valor`/`estado`) — como os nomes são nossos, os dois projetos passam a partilhar um único parser. Remover o ramo `pinpay` de `check_payment_status`; até o callback estar registado, `pinpay` só confirma por callback verificado.
- Investigar `estado_referencia` vs `estado` no `/multibanco/info` e corrigir — pode estar a impedir toda a confirmação por polling.
- **Passar os callbacks a platform-wide** (`/api/v1/webhooks/eupago/`, `/api/v1/webhooks/ifthenpay/`), abandonando o `adminCallback` por-merchant com o id no path, e localizar o `Payment` pela referência do gateway como o `boxwey` faz.
- **Trocar a referência por um token aleatório** em vez de `str(schedule.id.int)[-15:]`, requisito da URL única — **15 dígitos aleatórios** (`secrets`), porque o PINPAY exige `id` numérico com ≤ 15 caracteres. Migração de dados: só afeta pagamentos `pending`; os históricos mantêm a referência antiga (a coluna não muda de tipo nem de tamanho).
- `select_for_update` + unique index de dedupe; `GatewayCallLog` copiado da Fase 2.
- Portar o padrão dos 11 testes de webhook do `boxwey` — o `bookwey` tem hoje **zero** testes de callback (lacuna já assumida em `booksys-be/docs/TESTS.md:275`).
- Corrigir `booksys-be/CLAUDE.md:145-154`, que documenta um `settings.EUPAGO_API_URL` inexistente.

### Fase 5 — SIBS (`v0.3.0`), escrita contra a especificação real
- Absorver o `sibs-integration-project`: o esboço entra reescrito, o `saas-example-fastapi/` como `examples/`.
- `providers/sibs/spg/`: checkout (`Bearer` → `transactionID` + `transactionSignature`), purchase MB WAY e geração de referência Multibanco (`Digest`), consulta de estado, e webhook AES-256-GCM com o ack `{"statusCode":"200","statusMsg":"Success","notificationID":…}`.
- `providers/sibs/marketplace/`: submerchant e split/payout.
- Testes contra payloads gravados dos docs; **não ligado a nenhum projeto** até haver contrato e credenciais QLY. `docs/OPEN-QUESTIONS.md` regista o que falta confirmar: qual host/prefixo aplicável ao contrato (`api.*.sibspayments.com` vs `spg.qly.site1.sibs.pt` vs `sandbox.sibspayments.com`, `/api/v2` vs `/sibs/spg/v1`), ciclo de vida do `AuthToken` e se há mTLS.

---

## Execução autónoma (fim de semana)

Modo: `/loop` auto-ritmado. Cada despertar retoma o plano na fase corrente, executa o próximo passo, testa, faz commit no SDK e reagenda. O estado vive em `docs/PROGRESS.md` no repo do SDK (fase, passo, o que ficou por fazer, o que falhou) — é ele que permite retomar sem contexto anterior.

Para reduzir custo, o passo 0a cria a skill `weypay-phase`, que carrega o protocolo abaixo em cada iteração em vez de o reconstituir do histórico.

### Restrições invioláveis

1. **Commits só no repo novo** `/home/chrisdo/projects/weypay-sdk`. Nunca `git commit` nem `git add` em `bookwey-serverless`, `boxwey-serverless` ou qualquer outro projeto.
2. **Nunca `git push`** — em lado nenhum, incluindo o SDK. O remote fica para quando estiveres presente.
3. **GCP e Cloudflare: sem escritas.** Só leitura, e apenas se for imprescindível e justificado no relatório. Em caso de dúvida, não acede — regista em `docs/PROGRESS.md` como bloqueio e segue para outra coisa.
4. **Não sair da WSL.** Nada de ferramentas do lado Windows.
5. **Ambiente limpo no fim.** Dependências só dentro de um `venv` do próprio SDK; nada instalado globalmente. Se algo global for mesmo necessário, é removido no fim e registado.
6. **Testar antes de avançar.** Nenhuma fase começa sem os gates da anterior verdes (`ruff`, `mypy --strict`, `pytest`). Falha → pára a fase, regista em `docs/PROGRESS.md`, e passa a trabalho que não dependa dela; nunca se contorna um teste a falhar.
6b. **Na dúvida, ler a documentação oficial; na dúvida persistente, observar a sandbox; nunca deduzir.** Se nenhuma das duas resolver, fica ⚠️ em `docs/OPEN-QUESTIONS.md` e o comportamento atual **mantém-se intacto** — os sistemas estão em produção, e a opção segura é sempre não mexer.
7. **Nada de malicioso ou suspeito, e nunca tocar em segredos.** Só dependências de origem conhecida e estritamente necessárias (`requests`, `pytest`, `responses`, `ruff`, `mypy`), fixadas por versão e registadas no relatório. Não ler, copiar, imprimir nem transportar credenciais: `.env`, `~/.config/gcloud`, `~/.aws`, chaves SSH, tokens de API, ou as colunas de credenciais na base de dados (`Merchant.eupago_*`, `Tenant.mbway_key`, …). O SDK é código de protocolo — não precisa de uma única credencial real para ser escrito nem testado, e as fixtures saem dos exemplos da documentação oficial, nunca de dados reais.
8. **Alternar modelos** só onde o trabalho é mecânico e bem delimitado. Um subagente arranca sem contexto e volta a derivá-lo — para tarefas de raciocínio sai mais caro, não mais barato.
9. **Âmbito**: Fases 0a → 0b → 1 → 2 → **3**. A Fase 3 entra porque o objetivo é ter os **dois** projetos a pagar pelo SDK ao regresso, e é preservadora de comportamento. Ficam de fora a Fase 4 (muda a semântica de confirmação e depende de configuração nos backoffices dos gateways, que só tu podes fazer) e a Fase 5.
10. **Relatório final** em `docs/REPORT.md`: o que foi feito por fase, commits, testes corridos e resultados, decisões tomadas sozinho, o que ficou por fazer e porquê, bloqueios, e qualquer coisa instalada/removida.

### Objetivo ao regresso: pagar localmente nos dois projetos

Entregável dedicado: **`docs/LOCAL-TESTING.md`**, com um guião por projeto (`bookwey-serverless` e `boxwey-serverless`) — comandos exatos, migrations, seed, que definições usar, que URL abrir, o que se deve ver em cada ecrã, e como inspecionar o `GatewayCallLog` para ver o pedido e a resposta redigidos.

Há três níveis, com garantias diferentes, e o documento separa-os explicitamente:

| Nível | O que exercita | Precisa de | Garantido ao regresso? |
|---|---|---|---|
| **1 — `FAKE`** | Fluxo completo: checkout → SDK → callback simulado → order/marcação confirmada → auditoria escrita. Sem rede | nada | **Sim** |
| **2 — sandbox EuPago** | Chamada real a `sandbox.eupago.pt` (MB WAY, split, PIX, consulta de estado) | credenciais que forneceste | **Sim** — a Fase 0b já as usa, portanto fica verificado por construção |
| **2 — conta de teste ifthenpay** | Pedido MB WAY real com `ITP_MBWAY_KEY` + callback via **Webhook Tester** oficial | credenciais que forneceste | **Sim** para o pedido e para o callback simulado |
| **3 — callback real de ponta a ponta** | O gateway a chamar a tua máquina após um pagamento verdadeiro | túnel público + registar o URL no backoffice do gateway | **Não** — precisa de ti |

O nível 3 é o único que fica de fora, por dois motivos que não consigo contornar sozinho: exige um túnel público para a tua máquina e exige registar esse URL no backoffice de cada gateway. Documento os dois passos (`cloudflared tunnel --url`, efémero, sem tocar na tua conta Cloudflare), mas não os executo. O **Webhook Tester** da ifthenpay cobre a maior parte dessa lacuna sem túnel nenhum.

As credenciais de sandbox vão para os `.env` dos projetos consumidores, **nunca** para o repo do SDK — que fica sem um único segredo, e é o que permite torná-lo público.

### Pressupostos confirmados

Computador ligado e sessão aberta durante o fim de semana; definições de consumo já parametrizadas na conta. Fica na mesma o limite que não controlo: se a sessão cair (crash, suspensão da WSL, reinício), o loop não recomeça sozinho — o `docs/PROGRESS.md` existe precisamente para que a retoma manual custe uma frase.

---

## Verificação

| Fase | Como se prova |
|---|---|
| 0a | `docs/` completo e revisto antes de existir código; cada `providers/*.md` marca ✅/⚠️ por afirmação, com link ao doc oficial e delta com `ficheiro:linha` dos projetos atuais |
| 0b | Respostas cruas da sandbox gravadas em `docs/observed/`; **zero ⚠️ por resolver** nos providers que vão ser escritos; contradições com o plano registadas e o plano corrigido |
| 0c | `pytest` + `mypy --strict` + `ruff`; `test_isolation.py` falha se um provider importar outro; teste de que `FAKE` não abre socket e de que `PRODUCTION` recusa chaves de teste |
| 1 | `cd boxwey-serverless/api && python manage.py test` verde **sem editar testes** — é este o critério de "sem alteração de comportamento" |
| 2 | Testes novos: `estado` desconhecido → HTTP **200** e order inalterada (não 400); callback sem `valor` → rejeitado; `descricao` > 50 chars é truncada; `requests.ReadTimeout` → order fica `PENDING`, não `FAILED`; `GatewayCallLog` criado e sem segredos (assert de que nenhum valor de chave aparece no registo) |
| 3 | Teste de tabela payload-antigo-vs-novo por gateway; `python manage.py test` do `booksys-be` verde |
| local | Nos **dois** projetos, com `Environment.FAKE`: percorrer o `docs/LOCAL-TESTING.md` de ponta a ponta e obter marcação/order confirmada e `GatewayCallLog` escrito sem segredos. É este o critério de "consigo pagar localmente" |
| 4 | Testes novos: callback sem `chave_api` válida → **não** confirma; valor divergente → não confirma; callback repetido → idempotente; dois callbacks concorrentes → uma só transição; `pinpay` não se confirma por polling |
| 5 | Testes de decifra AES-GCM contra o vetor dos docs; nenhum import de `sibs` a partir dos projetos |
| ponta-a-ponta | Uma compra real MB WAY em cada projeto antes de apagar o código antigo (o `boxwey` tem precedente em `docs/MIGRATION-REPORT.md:105`) |

Cada fase é um commit/PR independente e reversível: as Fases 1 e 3 não alteram comportamento observável; a 2, 4 e 5 alteram-no deliberadamente e trazem os testes que o comprovam.

---

## Fontes consultadas

- ifthenpay — [API MBWAY (deprecated) + tabela de Estado + callback](https://helpdesk.ifthenpay.com/en/support/solutions/articles/79000086376-api-mbway-deprecated-) · [API PayByLink & PINPAY](https://helpdesk.ifthenpay.com/en/support/solutions/articles/79000143271-api-paybylink-pinpay) · [Documentação técnica](https://helpdesk.ifthenpay.com/en/support/solutions/folders/79000059075) · [docs](https://www.ifthenpay.com/docs/en/) — sem sandbox própria: chaves de teste pedidas à ifthenpay, contra os endpoints de produção
- EuPago — [REST API](https://eupago.readme.io/reference/api-eupago) · [MB WAY](https://eupago.readme.io/reference/mbway) · [Split Payments](https://eupago.readme.io/reference/split-payments) · [EuroPix](https://eupago.readme.io/reference/europix) · [Reference Information](https://eupago.readme.io/reference/reference-information) · [Webhooks 1.0](https://eupago.readme.io/reference/webhooks) · [Realtime Webhooks 2.0](https://eupago.readme.io/reference/realtime-webhooks-20)
- SIBS — [SPG integration guide](https://www.docs.pay.sibs.com/portugal/sibs-gateway/integrations/api/integration-guide/) · [Webhooks](https://www.docs.pay.sibs.com/portugal/sibs-gateway/notifications/webhooks/) · [Webhook examples](https://www.docs.pay.sibs.com/portugal/sibs-gateway/notifications/webhooks/examples/) · [Marketplace Onboarding API](https://www.docs.pay.sibs.com/portugal/marketplace/integrations/marketplace-api/onboarding-api/) · [Marketplace Split API](https://www.docs.pay.sibs.com/portugal/marketplace/integrations/marketplace-api/split-api/) · [API Market sandbox: MB WAY](https://developer.sibsapimarket.com/sandbox/node/3088) · [CARD](https://developer.sibsapimarket.com/sandbox/node/3086)
