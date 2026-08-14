# EuPago — EuroPix (PIX)

Marcação: ✅ verificado / ⚠️ a confirmar. Fonte primária:
[EuroPix](https://eupago.readme.io/reference/europix).

## (a) Endpoint, método, auth

- ✅ `POST /v1.02/pix/create`, mesma base sandbox/produção que MB WAY.
- ✅ Auth: `Authorization: ApiKey xxxx-xxxx-xxxx-xxxx-xxxx`.

## (b) Request — campos documentados verbatim

```json
{
  "payment": {
    "amount": { "value": 20.00, "currency": "EUR" },
    "identifier": "string"
  },
  "customer": {
    "name": "string", "vat": "string", "email": "string",
    "countryCode": "string", "phoneNumber": "string",
    "address": { "street": "...", "zipCode": "...", "city": "...", "state": "..." },
    "notify": false
  }
}
```

✅ **Resolvido (Fase 0b, observação direta em sandbox, 2026-08-14)**:
`bookwey/booksys-be/integrations/payments/utils.py:255-266` envia, dentro de `payment{}`,
`successUrl`, `failUrl` e `backUrl`, nenhum dos quais consta da especificação documentada
publicamente. Testado com um pedido idêntico com e sem esses três campos
(`docs/observed/eupago_pix_with_urls.json` / `eupago_pix_without_urls.json`): **ambos
devolvem `HTTP 201` com exatamente a mesma forma de resposta** (`transactionStatus`,
`transactionID`, `reference`, `pixCode`, `pixImage`) — os campos são **aceites, sem erro**,
hipótese (1) confirmada. Não há confirmação de que sejam *usados* (não são ecoados na
resposta), só de que não quebram o pedido — comportamento suficiente para a Fase 3 manter o
código como está.

## (c) Response — verbatim

Sucesso `201`: `{"transactionStatus":"Success","transactionID":"...","reference":"..."}`.
Erro `401`: `{"transactionStatus":"Rejected","code":"APIKEY_MISSING","text":"..."}`.

## (d) Limites

✅ Montante máximo `99 999€`.

## (e) Estado atual e delta

- ~~`utils.py:259`: `float(reservation_value)` — mesmo problema de `Decimal` que o MB WAY.~~
  Corrigido na Fase 3 (`Money`).
- ~~`utils.py:288,292`: `print()` em vez de log estruturado.~~ Corrigido na Fase 3.
- ~~Zero `timeout=` (`:276`).~~ Corrigido na Fase 3 (transporte do SDK).

### Bug real encontrado e corrigido (2026-08-14, pagamento sandbox real) — `Payment.reference` guardava o id local, não a referência da EuPago

O que esta secção descrevia como "falha de previsibilidade, Fase 4" era na verdade um **bug
funcional confirmado**, não só um problema de formato: `criar_pagamento_europix` guardava
`numeric_id = str(schedule.id.int)[-15:]` em `Payment.reference` — precisa de existir **antes**
da chamada à EuPago, para construir `successUrl`, mas nunca era substituído pela referência
real que a EuPago devolve (`data.get("reference")`, ex. `"320651"`). Toda consulta de estado
subsequente (`verificar_pagamento`, e `reconcile_pending_payments` em produção) interrogava a
EuPago com o id local, que a EuPago nunca viu → **HTTP 404, sempre**, tanto no `bookwey`
pré-migração como no pós-migração (não é regressão). Confirmado com um pagamento sandbox real:
`Payment.reference` antigo (`"283649437471407"`) não batia com a referência real da EuPago
(`"320651"`/`"320787"` observadas).

**Corrigido** (`bookwey-serverless` commit `7ece22a`): `Payment.reference` passa a guardar
sempre a referência real da EuPago (`data.get("reference")`), como já acontecia em MB
WAY/split; o id local ganhou um campo próprio, `Payment.client_reference`, usado só para
`check_payment_status()` encontrar o pagamento antes de a EuPago responder.
`check_payment_status` passou a procurar por `reference` OU `client_reference`, e a consultar a
EuPago sempre com `payment.reference` (nunca com o valor recebido do chamador). Reverificado
com um pagamento sandbox real: `client_reference` encontra o `Payment`, a consulta de estado à
EuPago já não 404. Ver `weypay-sdk/docs/OPEN-QUESTIONS.md`.

## (f) Fonte

[EuroPix](https://eupago.readme.io/reference/europix) · Observação direta em sandbox,
2026-08-14: `docs/observed/eupago_pix_with_urls.json`, `eupago_pix_without_urls.json`.
