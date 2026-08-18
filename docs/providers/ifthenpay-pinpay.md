# ifthenpay — Pay by Link / PINPAY (Gateway)

Marcação: ✅ verificado / ⚠️ a confirmar. Fonte primária:
[API - PayByLink & PINPAY](https://helpdesk.ifthenpay.com/en/support/solutions/articles/79000143271-api-paybylink-pinpay).

Produto **distinto** do MB WAY direto: é uma página de checkout hospedada pela ifthenpay que
agrega vários métodos (MB WAY, cartão, Apple Pay, Google Pay) atrás de um único link. Só o
`bookwey` usa este produto — o `boxwey` usa MB WAY direto.

## (a) Endpoint, método, auth

- ✅ `POST https://api.ifthenpay.com/gateway/pinpay/{GATEWAY_KEY}`
- ✅ Auth: a `GATEWAY_KEY` vai **no path**, não em header nem body.
- ✅ Sem sandbox própria (igual ao MB WAY — ver `ifthenpay-mbway.md` e `ENVIRONMENTS.md`).

## (b) Request — campos verbatim

| Campo | Obrigatório | Tipo/limite |
|---|---|---|
| `id` | ✅ sim | string, **máx. 15 caracteres numéricos** |
| `amount` | ✅ sim | decimal, separador `.` (ex.: `"21.50"`) |
| `description` | não | string, **máx. 200 caracteres** — note: limite diferente do MB WAY (50) |
| `lang` | não | `pt`\|`en`\|`es`\|`fr`, default `pt` |
| `expiredate` | não | `YYYYMMDD` |
| `accounts` | não | string `"MBWAY\|chave;CCARD\|chave;APPLE\|chave;GOOGLE\|chave"` |
| `success_url` | não | URL de redirect em sucesso |
| `error_url` | não | URL de redirect em erro |
| `cancel_url` | não | URL de redirect em cancelamento |

`bookwey/booksys-be/integrations/payments/utils.py:325-343` usa `id`, `amount`, `description`
(truncado a 200 — ✅ correto), `lang`, `success_url`, `accounts`. **Não usa** `error_url` nem
`cancel_url` — o utilizador que cancela ou falha não é redirecionado para lado nenhum
explícito; ficar `error_url`/`cancel_url` = `success_url` com um query param de estado é uma
melhoria de UX a considerar na Fase 3, não uma correção de bug.

## (c) Response — campos verbatim

`PinCode`, `RedirectUrl`. `utils.py:359` lê a resposta completa mas o único uso a jusante
(`booking.py:446`) é `RedirectUrl`.

## (d) Vocabulário de estado

Não há estado síncrono nesta chamada — só se sabe se o checkout foi criado. O estado do
pagamento chega **apenas pelo callback** (ver `ifthenpay-callbacks.md`).

✅ **Confirmado (2026-08-15, releitura da documentação oficial, motivada pela descoberta do
mesmo dia de que `EstadoPedidosJson`/`EstadoPedidosJSON` do MB WAY não estava documentado
corretamente): a página oficial do PINPAY não lista nenhum endpoint de consulta de estado.**
Só o endpoint de criação está documentado — nada equivalente ao `EstadoPedidosJSON` do MB
WAY. Isto **não foi verificado por chamada real** (ao contrário do MB WAY hoje) — falta uma
conta de teste com `GATEWAY_KEY`/`ifthenpay_apple_key` real (ver
`docs/OPEN-QUESTIONS.md`, item pendente de credenciais de teste PINPAY). Fica ⚠️ a
possibilidade de existir um endpoint não documentado nesta página mas real (como aconteceu
com o MB WAY), a confirmar quando houver conta de teste PINPAY disponível — **não assumir que
não existe só por não estar na documentação**, foi exatamente esse erro que o teste real do
MB WAY corrigiu.

## (e) Callback

✅ Formato oficial: `key=[ANTI_PHISHING_KEY]&id=[ID]&amount=[AMOUNT]&payment_datetime=[PAYMENT_DATETIME]&payment_method=[PAYMENT_METHOD]`

**Nomes diferentes dos do MB WAY** (`chave`/`referencia`/`valor`/`estado`) — mas, tal como no
MB WAY, o **template é configurado por nós** no backoffice ifthenpay, não fixado pelo
protocolo. Ver decisão em `docs/PLAN.md` §"Callbacks: uma URL comum?": registar o callback do
PINPAY com os mesmos nomes do MB WAY para os dois projetos partilharem um único parser.

## (f) Estado atual do código

`bookwey`: **nenhum callback registado para PINPAY.** `check_payment_status`
(`api/services/payments.py:26-27`) confirma qualquer pagamento `pinpay` sem contactar a
ifthenpay — falha de segurança tratada em `docs/migration/04-bookwey-security.md`, fora do
âmbito autónomo (Fase 4).

✅ **Confirmado com um pagamento real (2026-08-18)**: checkout PINPAY criado com sucesso
(`RedirectUrl` funcional, `accounts=APPLE|...;GOOGLE|...` com as chaves reais de produção do
utilizador — `ifthenpay_mbway_key`/`ifthenpay_ccard_key` não configuradas, por isso só Apple
Pay e Google Pay disponíveis nesta conta), **Apple Pay e Google Pay confirmados a funcionar**
(pagamento de €0,01 completado pelo utilizador em ambos).

⚠️→✅ **Achado inicial corrigido, não deixar a versão errada.** Logo a seguir ao pagamento,
`Payment.status` continuava `"pending"` — a primeira leitura foi "confirma o gap de segurança
do `check_payment_status`". **Errado, e corrigido pelo próprio utilizador**: o teste real foi
feito noutro dispositivo, e `success_url`/`front_domain` do merchant local aponta para
`http://salao-beleza-viva.localhost:3000/aguardar-pagamento?reference=...` —
**inalcançável fora da máquina de dev** (mesma classe de problema já encontrada com o
`adminCallback` da EuPago). É essa página (`booksys-fe/app/pages/aguardar-pagamento.vue`) que
faz *polling* a `/api/pagamento-status/<reference>/` (`check_payment_status`) — nunca chegou a
carregar, por isso nunca chamou nada. **Confirmado invocando `check_payment_status()`
manualmente para esta mesma referência**: `status` passa a `"confirmed"` imediatamente,
`schedule.is_active=True`. O mecanismo de atualização funciona quando é de facto chamado — o
que faltou foi só o browser conseguir chegar lá, uma limitação de teste local, não um bug.

O gap de segurança em si (`check_payment_status` confirma `pinpay` **sem verificar nada junto
da ifthenpay** — só confia em quem quer que chame o endpoint) continua real e por corrigir,
mas **não foi isto que este teste demonstrou** — é conhecido desde a leitura do código
original, antes de qualquer migração. Ver (d) acima para a pergunta em aberto sobre se existe
mesmo um callback/endpoint de estado do lado da ifthenpay.

## (i) O callback é registado por-CONTA, não por-produto (2026-08-18, backoffice real)

✅ **Descoberta estrutural, confirmada visualmente no backoffice ifthenpay do utilizador**
(`Administração → Contrato/Contas`): o callback anti-phishing **não** é uma configuração
única do produto PINPAY/Gateway. Cada "Conta" (sub-conta por método de pagamento — `APPLE`,
`CCARD`, `DD`, `GOOGLE`, `MB`, `MBWAY`, `PAYSHOP`) tem o seu **próprio** ícone de "Ativação de
Callback", com o seu próprio URL + Chave Anti-phishing. Quando o PINPAY processa um pagamento
através de, por exemplo, `APPLE|<key>`, é o callback registado **nessa conta `APPLE`** que
dispara — não existe um callback "do PINPAY" separado. Confirmado também que o menu "Pay By
Link & PINPAY" da barra lateral (`Novo`/`Histórico`) é só para gerar links/formulários
manualmente — **não tem nenhuma configuração de callback própria**.

Estado observado nesta conta: a conta `MBWAY | LML-691666` já tem um callback real
configurado — `https://api.boxwey.com/api/v1/webhooks/ifthenpay/?chave=[ANTI_PHISHING_KEY]&
referencia=[REFERENCIA]&valor=[VALOR]&estado=[ESTADO]` — mas essa é a conta usada
**diretamente** pelo `boxwey` (MB WAY, não PINPAY), já em produção. As contas `APPLE` e
`GOOGLE` (as que o `bookwey` usa via `accounts=` no PINPAY, ver (c) acima) **não tinham
nenhum callback configurado** — confirmado pelo utilizador clicando no ícone de cada uma.

**Consequência para a Fase 4**: para o `bookwey` receber confirmações de PINPAY (Apple
Pay/Google Pay), é preciso registar um callback em **cada conta usada** (`APPLE`, `GOOGLE`,
e `CCARD` se/quando ativado) — não um único registo. O URL de callback do `bookwey` foi
implementado (`bookwey-serverless` commit `0c813cb`, `/api/webhooks/ifthenpay/`, ver
`docs/migration/04-bookwey-security.md`), com o mesmo `CallbackMapping` do MB WAY
(`chave`/`referencia`/`valor`/`estado`) — a mesma convergência que o `docs/PLAN.md` já
recomendava. Falta só: (1) uma URL alcançável para colar no campo "URL de Callback" (túnel ou
deploy real — não local), e (2) escolher uma chave anti-phishing (≥15 caracteres) e colá-la
também em `Merchant.ifthenpay_callback_key` no admin do `bookwey`.

## (j) Consulta de estado / fallback de reconciliação — "List of Payments REST" (2026-08-19)

✅ **Confirmado via a documentação oficial** (URLs partilhados pelo utilizador:
`ifthenpay.com/docs/en/api/list-of-payments-rest/` e `.../api/pbl/`, ambos SPAs em React —
o conteúdo real só ficou acessível via `openapi.yaml`, referenciado no HTML bruto da página
mas não pelo `WebFetch`). A ifthenpay documenta explicitamente esta API como resposta à
pergunta #23: *"As an alternative or complement to the callback (webhook), you can retrieve
completed payments using a web service."*

**Endpoint**: `POST https://api.ifthenpay.com/v2/payments/read`. Cobre a conta inteira —
`entity` aceita `MB`/`MBWAY`/`PAYSHOP`/`CCARD`/`COFIDIS`/`GOOGLE`/`APPLE`/`PIX`/`TPA` — não é
específico do PINPAY, mas `orderId` no pedido e na resposta corresponde exatamente ao `id`
que `create_payment` (acima) envia — mesmo limite de 15 caracteres — o que o torna
diretamente utilizável para reconciliar pagamentos PINPAY (`APPLE`/`GOOGLE`) por `id`.

**Pedido** (todos os campos opcionais exceto `boKey`; sem filtros devolve os 1000 pagamentos
mais recentes): `boKey`, `entity`, `subEntity` (ex. `"APPLE KEY"`), `reference`, `orderId`,
`amount`, `requestId`, `dateStart`/`dateEnd` (`dd-MM-yyyy HH:mm:ss`), `procDateStart`/
`procDateEnd` (`yyyyMMdd`).

**Resposta**: `message`, `status` (`200` ou `403` — "Invalid boKey" — campo do corpo, não
necessariamente o HTTP status), `payments[]` com `amount`, `entity`, `fee`, `netAmount`,
`orderId`, `paymentDate`, `procDate`, `reference`, `requestId`, `subEntity`, `terminal`. **Sem
campo de estado por pagamento** — o endpoint só lista pagamentos **concluídos**
("retrieve completed payments"), portanto a presença de um item com o `orderId` pedido já
significa pago; a ausência não distingue "ainda pendente" de "`orderId` nunca existiu" (a
própria API não faz essa distinção).

**Bloqueio real, não resolvido**: exige `boKey` — "key provided by ifthenpay when signing the
contract" / "Backoffice key that identifies the merchant account" (visto também como campo
obrigatório da API de ativação de callback por API, `POST /callback/activation`, não usada
esta sessão porque o callback já foi ativado manualmente no backoffice — ver (i) acima). É
uma credencial **distinta** da `gateway_key` (cria o pagamento) e da chave anti-phishing
(valida o callback). ⚠️ Onde/como obtê-la não foi confirmado — possivelmente o campo "Chave
de Backoffice" visto mascarado no modal "Ativação de Callback" do backoffice, nunca preenchido
nem lido esta sessão (nunca se lê nem transporta uma credencial real — ver regra 6 da skill
`weypay-phase`). Ver `docs/OPEN-QUESTIONS.md` #26.

**Implementado e testado** (fixtures a partir do schema documentado, sem credencial real —
mesmo padrão usado para todo o SDK antes de validação em sandbox/produção real):
`weypay/providers/ifthenpay/pinpay.py::get_order_status(*, bo_key, order_id, ...)`, `v0.3.0`.
**Não ligado a nenhum consumidor em modo ativo** — `bookwey` ganhou o campo aditivo
`Merchant.ifthenpay_bo_key` (em branco por omissão) e uma chamada condicional em
`check_payment_status` que só corre se o campo estiver preenchido; com o campo vazio (estado
atual, em todos os merchants), o comportamento fica exatamente como estava — sem regressão.

## (g) Delta a corrigir

- Nada no protocolo — a chamada de criação está correta.
- A falha real é operacional/segurança (callback nunca registado), não de protocolo: ver
  Fase 4.

## (h) Fonte

[API - PayByLink & PINPAY](https://helpdesk.ifthenpay.com/en/support/solutions/articles/79000143271-api-paybylink-pinpay) ·
[What is PINPAY?](https://helpdesk.ifthenpay.com/en/support/solutions/articles/79000142861-what-is-pinpay-)
