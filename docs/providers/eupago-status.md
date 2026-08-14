# EuPago — Consulta de estado (Reference Information)

Marcação: ✅ verificado / ⚠️ a confirmar. Fonte primária:
[Reference Information](https://eupago.readme.io/reference/reference-information).

## (a) Endpoint documentado vs endpoint usado

- ✅ Endpoint **documentado atual**: `POST /multibanco/info` — **observado em sandbox
  (Fase 0b, 2026-08-14) e devolve HTTP 404** em `sandbox.eupago.pt`. Não existe neste host,
  pelo menos com este método de auth (`ApiKey` no corpo) — pode exigir OAuth Bearer, ou não
  estar disponível nesta versão de sandbox. Não usar sem confirmar de novo.
- ✅ **O `bookwey` chama o path legado**: `{merchant.eupago_api_url}/clientes/rest_api/multibanco/info`
  (`utils.py:397`, `:432`) — **observado em sandbox: funciona, HTTP 200**, e é o único dos
  dois que responde. Ver `docs/observed/eupago_status_legacy_path.json` e
  `eupago_status_documented_path.json` para as respostas cruas completas.

## (b) Request — campos verbatim (endpoint documentado)

| Campo | Obrigatório |
|---|---|
| `chave` | ✅ sim — API Key |
| `referencia` | ✅ sim |
| `entidade` | não — "nem todos os serviços têm entidade" |

`utils.py:386-389` (PIX) envia `referencia`+`chave`; `utils.py:424-428` (MB WAY) envia
`entidade`+`referencia`+`chave`. Ambos consistentes com o schema documentado.

## (c) Response — verbatim, do endpoint **documentado** (`/multibanco/info`, hipotética — 404 na prática)

```json
{
  "entidade": "12345",
  "referencia": "123456789",
  "identificador": "Exemplo-em-JSON",
  "estado": "pendente",
  "data_criacao": "2021-10-28",
  "hora_criacao": "14:37:23",
  "arquivada": false,
  "sucesso": true,
  "resposta": "OK"
}
```

## (c') Response — verbatim, **observada em sandbox** no path legado real (`/clientes/rest_api/multibanco/info`)

```json
{
  "entidade": null,
  "referencia": "320653",
  "identificador": "weypay-obs-status-b7fb3550",
  "estado": 0,
  "data_criacao": "2026-08-14",
  "hora_criacao": "13:26:39",
  "estado_referencia": "pendente",
  "arquivada": false,
  "sucesso": true,
  "resposta": "OK"
}
```

✅ **Resolvido (Fase 0b, observação direta, não dedução): o endpoint real tem AMBOS os
campos** — `estado` (numérico, `0` no caso pendente observado) **e** `estado_referencia`
(string, `"pendente"` no caso observado). A documentação pública em readme.io descreve um
endpoint diferente (`/multibanco/info`, que não existe neste host) e por isso só lista
`estado`; não é uma inconsistência do código, é a *page* errada de referência.

✅ `bookwey/api/services/payments.py:30,34` (`data.get("estado_referencia") == "paga"`) está
**correto** — o campo existe mesmo, com esse nome exato. O que ficou por observar (limitação
de segurança deliberada, não técnica — ver `docs/OPEN-QUESTIONS.md`): o valor de
`estado_referencia` **depois** de um pagamento confirmado. Só se sabe que o valor pendente é
`"pendente"`; que o valor de sucesso seja exatamente `"paga"` continua ⚠️ até se observar uma
referência paga — não testável sem um pagamento real (PIX não se confirma sozinho em sandbox).

## (d) Vocabulário de `estado_referencia`

✅ `"pendente"` confirmado (observado). ⚠️ Valor de sucesso — o código assume `"paga"`, ainda
não observado. `estado` numérico (`0` no caso pendente) — vocabulário completo não
documentado nem observado para outros valores.

## (e) Estado atual e delta

- Zero `timeout=` nas duas chamadas (`utils.py:396`, `:434`).
- `print()` em vez de log estruturado (`:408`, `:412`, `:447`, `:451`).
- Cada função (`verificar_pagamento`, `verificar_pagamento_mbway`) duplica quase o mesmo
  corpo — candidatas naturais a ficarem finas sobre um único `get_reference_status()` do SDK.
- **O código não estava errado** — retirar isto do backlog de "possível bug" da Fase 3; o SDK
  só precisa de replicar o path legado (`/clientes/rest_api/multibanco/info`), não o
  documentado publicamente, que 404 nesta sandbox.

## (f) Fonte

[Reference Information](https://eupago.readme.io/reference/reference-information) ·
[Reference Information (OAuth)](https://eupago.readme.io/reference/reference-information-oauth) ·
Observação direta em sandbox, 2026-08-14: `docs/observed/eupago_status_legacy_path.json`,
`docs/observed/eupago_status_documented_path.json`.
