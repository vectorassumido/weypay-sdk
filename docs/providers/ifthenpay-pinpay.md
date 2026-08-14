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

## (g) Delta a corrigir

- Nada no protocolo — a chamada de criação está correta.
- A falha real é operacional/segurança (callback nunca registado), não de protocolo: ver
  Fase 4.

## (h) Fonte

[API - PayByLink & PINPAY](https://helpdesk.ifthenpay.com/en/support/solutions/articles/79000143271-api-paybylink-pinpay) ·
[What is PINPAY?](https://helpdesk.ifthenpay.com/en/support/solutions/articles/79000142861-what-is-pinpay-)
