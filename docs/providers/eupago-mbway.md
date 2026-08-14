# EuPago — MB WAY (com e sem split)

Marcação: ✅ verificado / ⚠️ a confirmar. Fonte primária:
[MB WAY](https://eupago.readme.io/reference/mbway) ·
[Split Payments](https://eupago.readme.io/reference/split-payments) ·
[REST API overview](https://eupago.readme.io/reference/api-eupago).

Usado só pelo `bookwey`. Duas variantes na mesma função
(`utils.py:139-230::criar_pagamento_com_split`), escolhidas por `if merchant.eupago_salon_key
!= merchant.eupago_owner_key`.

## (a) Endpoints, método, auth, ambientes

- ✅ Sandbox: `https://sandbox.eupago.pt/api/`. Produção: troca-se `sandbox` por `clientes`
  (`clientes.eupago.pt`) — ✅ confirmado também no `ENVIRONMENTS.md` via doc de auth.
- ✅ Sem split: `POST /v1.02/mbway/create`
- ✅ Com split: `POST /v1/split-payments/mbway`
- ✅ Auth: header `Authorization: ApiKey xxxx-xxxx-xxxx-xxxx-xxxx`

## (b) Request — sem split, campos verbatim

```json
{
  "payment": {
    "identifier": "string",
    "amount": { "value": 20.00, "currency": "EUR" },
    "customerPhone": "string",
    "countryCode": "string"
  }
}
```
Opcional `customer{notify, failOver, name, email, phone}`, não usado pelo `bookwey`.

## (c) Request — split, campos verbatim

```json
{
  "amount": 4.68,
  "identifier": "string",
  "alias": "string (telefone, MB WAY apenas)",
  "adminCallback": "string",
  "lang": "PT",
  "beneficiaries": [
    { "externKey": "string", "amount": 3.50, "identifier": "string", "immediatePayment": false }
  ]
}
```
✅ Métodos suportados pelo split: `multibanco, mbway, pix, creditcard, applepay, googlepay`.

`utils.py:158-178`: usa exatamente este formato, com 2 beneficiários (salão + plataforma) e
`adminCallback` **por-merchant e com o id da marcação no path**
(`{merchant.eupago_api_callback}/{agendamento_id}`) — ver delta em (g) e
`docs/PLAN.md` §"Callbacks: uma URL comum?".

## (d) Response — verbatim

Sucesso (`201`/`200`): sem split `{"transactionStatus":"Success","transactionID":"...","reference":"..."}`;
com split `{"transactionStatus":"Success","entity":"82307","reference":"100502152","amount":"4.68"}`.
Erro `401`: `{"transactionStatus":"Rejected","code":"...","text":"..."}`.

⚠️ `booksys-be/api/services/booking.py` lê `entity`/`reference`/`amount` da resposta — a spec
documentada do endpoint **sem split** só promete `transactionID`/`reference`, não `entity`.
**Parcialmente investigado na Fase 0b, não resolvido**: uma criação bem-sucedida de MB WAY
dispara de imediato um push para o número indicado, sem esperar confirmação — testar isto
exigiria um número de telefone de teste real, que o agente não tem e não pode adivinhar sem
risco de notificar uma pessoa desconhecida (ver a regra de segurança em
`docs/OPEN-QUESTIONS.md`). O único teste seguro feito foi com um número deliberadamente
inválido: `HTTP 400 {"transactionStatus":"Rejected","code":"CUSTOMERPHONE_INVALID",...}`
(`docs/observed/eupago_mbway_create_invalid_phone.json`) — confirma a forma do erro, não
responde à pergunta sobre `entity`. Fica em `docs/OPEN-QUESTIONS.md` #2/#15, dependente de um
número de teste fornecido pelo utilizador.

## (e) Vocabulário de estado

`transactionStatus`: `Success` \| `Rejected`. Não é o estado do *pagamento* (que é assíncrono)
— é só o estado do *pedido de pagamento*. O estado do pagamento em si vem por consulta
(`eupago-status.md`) ou webhook (`eupago-webhooks.md`).

## (f) Limites

✅ Montante máximo `99 999€`. ✅ Janela de pagamento: "5 minutos" após a notificação MB WAY.

## (g) Estado atual e delta

- `utils.py:160,167,173,190`: `float(reservation_value)` etc. — dinheiro em `float`, não
  `Decimal`, num payload financeiro. Corrigir na Fase 3 (`Money` formata por gateway).
- `utils.py:210-211`: `print(payload)`/`print(data)` — despeja `externKey` (chaves de
  beneficiário) e a resposta completa para stdout. Corrigir na Fase 3 (redação de fronteira).
- Zero `timeout=` nas duas chamadas (`:180`, `:198`). Corrigir na Fase 3.
- `adminCallback` por-merchant, com o id da marcação no path — não é a URL platform-wide que
  o resto do plano assume; migração de callback é Fase 4, não Fase 3.

## (h) Fonte

[MB WAY](https://eupago.readme.io/reference/mbway) ·
[Split Payments](https://eupago.readme.io/reference/split-payments)
