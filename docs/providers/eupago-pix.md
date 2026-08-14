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

- `utils.py:259`: `float(reservation_value)` — mesmo problema de `Decimal` que o MB WAY.
- `utils.py:288,292`: `print()` em vez de log estruturado.
- Zero `timeout=` (`:276`).
- A referência interna usada por este fluxo é `numeric_id = str(schedule.id.int)[-15:]`
  (`:237`), **derivada do UUID do `Schedule`** e devolvida ao browser em `success_url`
  (`:247`) — mesma falha de previsibilidade documentada em `ifthenpay-callbacks.md` e
  corrigida na Fase 4, não na 3 (a Fase 3 preserva comportamento).

## (f) Fonte

[EuroPix](https://eupago.readme.io/reference/europix) · Observação direta em sandbox,
2026-08-14: `docs/observed/eupago_pix_with_urls.json`, `eupago_pix_without_urls.json`.
