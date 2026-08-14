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

✅ `"pendente"` e `"paga"` confirmados (observados — ver c', c'''). `estado` numérico (`0` nos
dois casos observados, pendente e paga) — vocabulário completo não documentado nem observado
para outros valores (`estado_referencia` é o campo fiável, não `estado`).

## (e) Estado atual e delta

- Zero `timeout=` nas duas chamadas (`utils.py:396`, `:434`).
- `print()` em vez de log estruturado (`:408`, `:412`, `:447`, `:451`).
- Cada função (`verificar_pagamento`, `verificar_pagamento_mbway`) duplica quase o mesmo
  corpo — candidatas naturais a ficarem finas sobre um único `get_reference_status()` do SDK.
- ~~O código não estava errado~~ **Corrigido abaixo (c'') — o SDK tinha mesmo um bug real,
  descoberto só num teste local com um pagamento sandbox verdadeiro.**

## (c'') Bug real encontrado e corrigido (2026-08-14): `status.py` tinha `/api` a mais

✅ **Observado, teste local real** (`bookwey-serverless`, merchant `salao-beleza-viva`, booking
real via `create_booking()`, telefone autorizado explicitamente pelo utilizador): uma
referência criada momentos antes por `split-payments/mbway` (`reference="320778"`) consultada
via `verificar_pagamento_mbway()` devolvia **HTTP 404, corpo `"Page Not Found"`** — diferente
do 200 observado em (c') para a referência `320653`. Ver
`docs/observed/eupago_status_mbway_split_reference_404.json`.

**Causa raiz identificada (não é dedução — confirmada corrigindo e reobservando)**:
`weypay/providers/eupago/status.py::ENDPOINTS` tinha `/api` no host canónico
(`https://sandbox.eupago.pt/api`), copiado por engano de `mbway.py`/`split.py`/`pix.py` —
esses **precisam** de `/api` porque os seus sufixos (`/v1/split-payments/mbway`,
`/v1.02/mbway/create`) sempre levaram `/api` a meio no código original. O path legado deste
ficheiro (`/clientes/rest_api/multibanco/info`) **nunca** levou `/api` no código original —
`f"{merchant.eupago_api_url}/clientes/rest_api/multibanco/info"`, confirmado em
`git show main:.../utils.py`. Resultado: toda consulta de estado ia para
`.../api/clientes/rest_api/multibanco/info` (404) em vez de
`.../clientes/rest_api/multibanco/info` (200). **A observação de 200 em (c') não detetou isto
porque o script manual da Fase 0b usava o URL correto diretamente — o bug só entrou quando o
provider do SDK foi escrito na Fase 0c com `ENDPOINTS` errado, e o próprio teste do provider
(`tests/providers/test_eupago_status.py`) foi escrito com o mesmo engano no URL esperado, por
isso passava.**

**Correção**: `ENDPOINTS` sem `/api` (`https://sandbox.eupago.pt`, `https://clientes.eupago.pt`);
`bookwey-serverless` ganhou `_eupago_status_base_url()` (sem `/api`), separado de
`_eupago_base_url()` (com `/api`, só para criação). Teste do provider corrigido para o URL
real. **Não é uma regressão da Fase 3 nem comportamento herdado do `bookwey`** — é um bug
introduzido na Fase 0c/3 do próprio SDK, nunca antes exercitado com um pagamento real.

## (c''') `estado_referencia` de sucesso — resolvido (2026-08-14, pagamento sandbox real)

✅ **Confirmado, não mais ⚠️.** Referência `320780`, criada com `adminCallback` real e
alcançável (ver `docs/providers/eupago-mbway.md` §"adminCallback deve ser alcançável"),
marcada como paga manualmente no backoffice sandbox pelo utilizador, consultada com o
`status.py` já corrigido:

```json
{
  "estado_referencia": "paga",
  "pagamentos": [{"trid": 29751801, "estado": "paga", "valor": "15.00000", ...}]
}
```

`STATUS_PAID = "paga"` **confirmado exatamente como o código sempre assumiu** — não muda
nada, só deixa de ser inferência. Ver `docs/observed/eupago_status_mbway_paid_confirmed.json`.
Note-se também o campo adicional `pagamentos` (lista), não documentado nem usado hoje pelo
`bookwey` — fica registado, sem ação associada.

## (f) Fonte

[Reference Information](https://eupago.readme.io/reference/reference-information) ·
[Reference Information (OAuth)](https://eupago.readme.io/reference/reference-information-oauth) ·
Observação direta em sandbox, 2026-08-14: `docs/observed/eupago_status_legacy_path.json`,
`docs/observed/eupago_status_documented_path.json`.
