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

`utils.py:158-178` usava este formato, com 2 beneficiários (salão + plataforma) e
`adminCallback` **por-merchant e com o id da marcação no path**
(`{merchant.eupago_api_callback}/{agendamento_id}`) — ver delta em (g) e
`docs/PLAN.md` §"Callbacks: uma URL comum?". **Deixou de ser enviado (2026-08-19)**, ver
correção abaixo.

### ✅ `adminCallback` NÃO precisa de ser alcançável — corrigido em 2026-08-19, achado anterior estava errado

**Substitui a secção anterior desta data**, que concluía o oposto a partir de uma correlação
mal interpretada. Três fontes convergentes, nenhuma dedução:

1. **Documentação oficial** ([Split Payments](https://eupago.readme.io/reference/split-payments),
   spec verbatim extraída do schema OpenAPI embutido na página): `adminCallback` —
   `"desc": "Use this optional field to receive a communication when this reference is paid.",
   "required": false`. Um campo de notificação opcional, sem nenhuma menção a ser prerequisito
   de confirmação.
2. **Teste controlado isolado em sandbox** (2026-08-19, ver
   `docs/observed/eupago_split_admincallback_unreachable_is_cosmetic.json`): uma referência
   **sozinha** (nenhuma outra criada antes/depois — elimina qualquer efeito colateral entre
   referências), com `adminCallback` inalcançável, mostra o mesmo erro
   (`"Ocorreu um erro! O estado da referência não foi alterado."`) ao clicar em "marcar como
   paga" — **mas um simples refresh da lista (sem tocar na referência de novo) já a mostra
   "Paga"**. O erro é cosmético: a UI da sandbox tenta notificar `adminCallback`
   sincronamente como parte da própria ação de marcar como paga, e mostra o erro quando essa
   notificação falha — mas o estado do lado da EuPago já tinha mudado, independentemente.
3. **Confirmado que `adminCallback` É chamado quando alcançável**: com um túnel real, a
   EuPago fez mesmo um `GET` ao `adminCallback` exatamente no instante em que a referência
   foi marcada como paga — o mecanismo existe e funciona como a doc oficial descreve, só não
   é um prerequisito de confirmação.

**O achado de 2026-08-14** (referência com `adminCallback` inalcançável parecendo nunca
confirmar, enquanto uma segunda com URL real confirmava) nunca tinha testado um simples
refresh antes de concluir causalidade — a referência "presa" já estava paga, só a UI não
tinha sido re-consultada. Correção completa: `admin_callback` passou a opcional no SDK
(`v0.4.0`) e o `bookwey` deixou de o enviar — `eupago_api_callback` fica vestigial,
tal como Webhooks 2.0 já tinha tornado o Webhook 1.0/`chave_api`. Ver
`docs/OPEN-QUESTIONS.md`.

## (d) Response — verbatim

Sucesso (`201`/`200`): sem split `{"transactionStatus":"Success","transactionID":"...","reference":"..."}`;
com split `{"transactionStatus":"Success","entity":"82307","reference":"100502152","amount":"4.68"}`.
Erro `401`: `{"transactionStatus":"Rejected","code":"...","text":"..."}`.

⚠️ `booksys-be/api/services/booking.py` lê `entity`/`reference`/`amount` da resposta — a spec
documentada do endpoint **sem split** só promete `transactionID`/`reference`, não `entity`.
O único teste seguro feito na Fase 0b foi com um número deliberadamente inválido: `HTTP 400
{"transactionStatus":"Rejected","code":"CUSTOMERPHONE_INVALID",...}`
(`docs/observed/eupago_mbway_create_invalid_phone.json`) — confirma a forma do erro, não
respondia à pergunta sobre `entity`.

✅ **#15 resolvido (2026-08-14, teste local real** — `bookwey-serverless`, merchant
`salao-beleza-viva`, número de telefone real autorizado explicitamente pelo utilizador para
este teste): criação **com split** (`salon_key != owner_key` para este merchant) devolveu
`HTTP 200 {"entity": null, "reference": "320778", "amount": "15.00"}`. **`entity` existe na
resposta mas vem `null`** para um pagamento MB WAY (não `Multibanco`) — `reference` e `amount`
vêm sempre preenchidos. `booking.py`'s `pagamento.get("entity")` já lida com isto corretamente
(devolve `None`, não levanta erro). O booking/push foi criado com sucesso; a variante **sem**
split (`eupago_mbway.create_payment`) continua ⚠️ não observada com sucesso — este merchant usa
o caminho com split.

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
- ~~`adminCallback` por-merchant, com o id da marcação no path — não é a URL platform-wide que
  o resto do plano assume; migração de callback é Fase 4, não Fase 3.~~ **Resolvido
  (2026-08-19)**: confirmado vestigial (ver secção acima) — deixou de ser enviado.

## (h) Fonte

[MB WAY](https://eupago.readme.io/reference/mbway) ·
[Split Payments](https://eupago.readme.io/reference/split-payments)
