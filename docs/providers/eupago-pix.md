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

⚠️ **Discrepância real, não dedução — confirmada por leitura do código**:
`bookwey/booksys-be/integrations/payments/utils.py:255-266` envia, dentro de `payment{}`,
`successUrl`, `failUrl` e `backUrl`, nenhum dos quais consta da especificação documentada
acima. Três hipóteses, nenhuma decidível sem observar a sandbox: (1) são aceites e apenas não
documentados; (2) são silenciosamente ignorados; (3) causam erro de schema e a chamada falha
hoje sempre que a EuPago validar estritamente. Item central da Fase 0b — se (3) fosse
verdade já teria quebrado produção, o que torna (1) ou (2) mais prováveis, mas não é
suficiente para decidir sem observar.

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

[EuroPix](https://eupago.readme.io/reference/europix)
