# Testar pagamentos localmente

Guião para pagar, na tua máquina, sem afetar produção, em `boxwey-serverless` e
`bookwey-serverless`, depois de as Fases 0c-3 estarem implementadas (`docs/PROGRESS.md` diz
até onde chegou). Três níveis, com garantias diferentes — ver `docs/PLAN.md` para o porquê.

| Nível | Exercita | Precisa de | Verificado pela execução autónoma? |
|---|---|---|---|
| **1 — `FAKE`** | Fluxo completo: checkout → SDK → callback simulado → confirmação → auditoria | nada | ✅ sim |
| **2 — sandbox real** | Chamada verdadeira a `sandbox.eupago.pt` / conta de teste ifthenpay | as credenciais abaixo | ✅ sim (a Fase 0b já as usa) |
| **3 — callback real de ponta a ponta** | O gateway a chamar a tua máquina depois de um pagamento verdadeiro | túnel público + registo no backoffice do gateway | ❌ não — precisa de ti |

## Credenciais de sandbox/teste

Vivem nos `.env` de cada projeto consumidor — **nunca** neste repositório. Valores fornecidos
pelo utilizador (sandbox EuPago legada e conta de teste ifthenpay):

```bash
# .env do bookwey-serverless/booksys-be — usadas pelo merchant seedado em desenvolvimento
EUPAGO_API_URL=https://sandbox.eupago.pt
EUPAGO_API_KEY=demo-REDACTED-eupago-api-key
EUPAGO_OWNER_KEY=REDACTED-eupago-owner-key
EUPAGO_SALON_KEY=REDACTED-eupago-salon-key

# .env do boxwey-serverless/api — para o Tenant.mbway_key local
ITP_MBWAY_KEY=REDACTED-itp-mbway-key
```

⚠️ Como o `EUPAGO_SALON_KEY` fornecido é diferente do `EUPAGO_OWNER_KEY`, o `bookwey` vai pelo
ramo de **split payments** em `criar_pagamento_com_split` (`utils.py:158`), não pelo MB WAY
simples — ver `docs/providers/eupago-mbway.md` (c).

---

## `boxwey-serverless`

### Nível 1 — `FAKE`, sem rede

```bash
cd /home/chrisdo/projects/boxwey-serverless/api
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pip install -e /home/chrisdo/projects/weypay-sdk         # editable, aponta para o SDK local
python manage.py migrate                                  # SQLite por omissão em dev
DJANGO_SUPERUSER_EMAIL=admin@local.test python manage.py seed --demo
```

- Tenant `demo` fica criado, sem `mbway_key`/`itp_callback_key` — define-os no shell:
  ```bash
  python manage.py shell -c "
  from core.models import Tenant
  t = Tenant.objects.get(slug='demo')
  t.mbway_key = 'FAKE-TEST-KEY'; t.itp_callback_key = 'fake-anti-phishing'; t.save()
  "
  ```
- `WEYPAY_ENVIRONMENT=fake python manage.py runserver` (a variável exata é definida na
  Fase 0c/2 — este documento é atualizado quando o nome ficar fixo em `settings/development.py`).
- Noutro terminal: `cd front && NUXT_PUBLIC_API_BASE=http://127.0.0.1:8000 NUXT_PLATFORM_KEY=dev-key npm run dev`
- Abrir `http://demo.boxwey.localhost:3000` (o subdomínio resolve o tenant pelo `Host`),
  escolher um evento, fazer checkout. O pedido a `initiate_payment` corre contra o transporte
  `FAKE` — resposta gravada, `Order.provider_payment_id` preenchido, sem qualquer chamada de
  rede.
- Para simular o callback: `POST /api/v1/webhooks/ifthenpay/?chave=fake-anti-phishing&referencia=<provider_reference>&valor=<total>&estado=PAGO`
  contra `localhost:8000`, com `curl` ou o cliente REST à escolha. A `provider_reference` está
  em `Order.provider_reference` (consultável via admin ou shell).
- Confirmar: `Order.status == "PAID"`, e em `/admin/` a nova tabela `GatewayCallLog` (Fase 2)
  mostra duas entradas — `initiate_payment` e o webhook — com o pedido/resposta redigidos
  (`MbWayKey` nunca aparece em claro).

### Nível 2 — conta de teste ifthenpay

- `.env`: `ITP_MBWAY_KEY=REDACTED-itp-mbway-key`; usar essa chave em vez de `FAKE-TEST-KEY` no
  `Tenant.mbway_key` acima, e `WEYPAY_ENVIRONMENT=sandbox` — que para ifthenpay resolve para o
  **mesmo host de produção** (não há sandbox separada, ver `docs/ENVIRONMENTS.md`); é a chave
  de teste que isola o pagamento, não o host.
- Repetir o checkout — desta vez o pedido MB WAY sai de verdade para a ifthenpay, com um
  telemóvel de teste. `GatewayCallLog` mostra a chamada real, `http_status=200`.
- Para o callback: usar o **Webhook Tester** oficial no backoffice ifthenpay
  (`docs/providers/ifthenpay-callbacks.md` (f)) para simular a notificação sem precisar de um
  telefone real a confirmar o pagamento.

### Nível 3 — callback real de ponta a ponta (fora do garantido)

Precisa de um túnel público (`cloudflared tunnel --url http://localhost:8000`, efémero, sem
tocar na tua conta Cloudflare) e de registar esse URL temporário no backoffice ifthenpay como
callback da conta de teste. Não executado pela execução autónoma — ver `docs/PLAN.md`.

---

## `bookwey-serverless`

### Nível 1 — `FAKE`, sem rede

```bash
cd /home/chrisdo/projects/bookwey-serverless/booksys-be
source venv/bin/activate
pip install -e /home/chrisdo/projects/weypay-sdk
DJANGO_SETTINGS_MODULE=booksys_be.settings.development python manage.py migrate
DJANGO_SETTINGS_MODULE=booksys_be.settings.development python manage.py seed
```

- `seed` cria o merchant "Salão Beleza Viva" e o manager `manager1`/`manager123` em
  `merchant.localhost`. Definir as chaves de pagamento no admin (`/admin/`, login
  `admin`/`admin123` por omissão) em vez de shell — o `bookwey` já expõe esses campos no
  `ModelAdmin` de `Merchant` (fieldsets "Payment Gateway"):
  - `eupago_api_url = https://sandbox.eupago.pt` (ou deixar em branco e usar
    `WEYPAY_ENVIRONMENT=fake`, quando a Fase 3 substituir o campo de texto livre pelo
    `Environment` explícito)
  - `ifthenpay_mbway_key` / `ifthenpay_gateway_key` = valores fictícios para `FAKE`
- `DJANGO_SETTINGS_MODULE=booksys_be.settings.development PLATFORM_SSR_KEY=dev-key python manage.py runserver`
- Noutro terminal: `cd booksys-fe && NUXT_PUBLIC_API_BASE=http://127.0.0.1:8000 NUXT_PLATFORM_KEY=dev-key npm run dev`
- Abrir `http://salao-beleza-viva.localhost:3000`, fazer uma marcação com pagamento. Em
  `FAKE`, a chamada EuPago/PINPAY corre contra o transporte gravado — `Payment.status`
  atualiza sem rede.
- Simular o callback conforme o mecanismo que a Fase 4 tiver deixado pronto (platform-wide
  `/api/v1/webhooks/eupago/` e `/api/v1/webhooks/ifthenpay/`) **ou**, se a Fase 4 ainda não
  tiver corrido, o mecanismo atual (`GET /api/pagamento-callback/<schedule_uuid>/`) — este
  documento é atualizado assim que se souber qual dos dois está ativo (ver `PROGRESS.md`).
- Confirmar: `GatewayCallLog` no admin, `Payment.status == "confirmed"`.

### Nível 2 — sandbox real EuPago

```bash
# .env do booksys-be
EUPAGO_API_URL=https://sandbox.eupago.pt
EUPAGO_API_KEY=demo-REDACTED-eupago-api-key
EUPAGO_OWNER_KEY=REDACTED-eupago-owner-key
EUPAGO_SALON_KEY=REDACTED-eupago-salon-key
```
Colocar os mesmos valores nos campos correspondentes de `Merchant` no admin (são por-merchant,
não globais — `docs/providers/eupago-mbway.md`). Repetir a marcação: o pedido de split MB WAY
sai de verdade contra `sandbox.eupago.pt`. Consultar o estado via
`docs/providers/eupago-status.md` (endpoint de reconciliação) para confirmar sem depender do
callback.

### Nível 3 — callback real de ponta a ponta (fora do garantido)

Mesma limitação do `boxwey`: precisa de túnel público + `adminCallback`/webhook registado no
backoffice EuPago. Fora do que a execução autónoma garante.

---

## O que fica por atualizar

Este documento assume nomes de variável (`WEYPAY_ENVIRONMENT`) e comandos exatos que só ficam
fixos durante as Fases 0c-3. Cada fase que mude um comando aqui referido **deve atualizar este
ficheiro no mesmo commit** — é o critério de aceitação do nível "local" em
`docs/PLAN.md` §Verificação, e é a razão de existir deste documento: garantir que, ao regresso,
os comandos acima funcionam tal como escritos, não só "em espírito".
