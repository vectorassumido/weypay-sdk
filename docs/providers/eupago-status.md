# EuPago — Consulta de estado (Reference Information)

Marcação: ✅ verificado / ⚠️ a confirmar. Fonte primária:
[Reference Information](https://eupago.readme.io/reference/reference-information).

## (a) Endpoint documentado vs endpoint usado

- ✅ Endpoint **documentado atual**: `POST /multibanco/info` (mesma base sandbox/produção).
- ⚠️ **O `bookwey` chama um path diferente**: `{merchant.eupago_api_url}/clientes/rest_api/multibanco/info`
  (`utils.py:397`, `:432`) — `/clientes/rest_api/` é um prefixo que não aparece na
  documentação atual e tem cheiro de API legada. Pode ser um alias válido ainda suportado, ou
  pode estar a bater num endpoint diferente com schema diferente. **Não presumir que devolve
  a mesma coisa** que a spec abaixo até se observar a sandbox (Fase 0b).

## (b) Request — campos verbatim (endpoint documentado)

| Campo | Obrigatório |
|---|---|
| `chave` | ✅ sim — API Key |
| `referencia` | ✅ sim |
| `entidade` | não — "nem todos os serviços têm entidade" |

`utils.py:386-389` (PIX) envia `referencia`+`chave`; `utils.py:424-428` (MB WAY) envia
`entidade`+`referencia`+`chave`. Ambos consistentes com o schema documentado.

## (c) Response — verbatim

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

✅ **O campo é `estado`, não `estado_referencia`.** Nem `estado_referencia` nem `valor` nem
`data_pagamento` constam da resposta documentada.

⚠️ `bookwey/api/services/payments.py:30,34` testa `data.get("estado_referencia") == "paga"`
— um campo que não existe nesta especificação. **Não concluir daqui que o polling está morto**:
o path chamado é o legado descrito em (a), que pode ter um schema diferente do documentado
aqui. É preciso observar a resposta real do path legado antes de decidir se o código está
errado ou se a documentação atual simplesmente não cobre o endpoint legado.

## (d) Vocabulário de `estado`

Não documentado exaustivamente — só o exemplo `"pendente"` aparece na spec. Valores como
`"paga"` (usado pelo código) não são citados nem negados pela documentação disponível.
Confirmar o conjunto completo na Fase 0b, criando uma referência em sandbox e consultando
antes e depois do pagamento.

## (e) Estado atual e delta

- Zero `timeout=` nas duas chamadas (`utils.py:396`, `:434`).
- `print()` em vez de log estruturado (`:408`, `:412`, `:447`, `:451`).
- Cada função (`verificar_pagamento`, `verificar_pagamento_mbway`) duplica quase o mesmo
  corpo — candidatas naturais a ficarem finas sobre um único `get_reference_status()` do SDK.

## (f) Fonte

[Reference Information](https://eupago.readme.io/reference/reference-information) ·
[Reference Information (OAuth)](https://eupago.readme.io/reference/reference-information-oauth)
