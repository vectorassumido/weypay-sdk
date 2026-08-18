# EuPago — Webhooks 1.0 e 2.0

Marcação: ✅ verificado / ⚠️ a confirmar. Fonte primária:
[Webhooks 1.0](https://eupago.readme.io/reference/webhooks) ·
[Realtime Webhooks 2.0](https://eupago.readme.io/reference/realtime-webhooks-20).

**Duas gerações de callback, muito diferentes** — nomes, transporte e verificação. O `bookwey`
não usa nenhuma das duas diretamente: usa `adminCallback` por-pagamento (ver
`eupago-mbway.md`), que é o mecanismo de split payments, não os webhooks gerais descritos aqui.
Este documento cobre as duas para a Fase 4, onde a migração para 2.0 é recomendada.

## 1.0

### (a) Configuração e transporte
- ✅ Configurado no backoffice: **Channels → Channel Listing → editar o canal → marcar
  "Receive notification for a URL"**, colar o endpoint.
- ⚠️ Método HTTP não especificado na documentação disponível.

### (b) Parâmetros — verbatim
`valor`, `canal`, `referencia`, `transacao`, `identificador`, `mp` (código do método:
`PC:PT, PS:PT, MW:PT, CC:PT, PF:PT, DD:PT, CP:PT, GP:PT, PA:PT, PX:PT, FP:PT`), `chave_api`
("API Key used to create the reference"), `data` (`YYYY-MM-DD:hh:mm`), `entidade`,
`comissao`, `local`.

### (c) Verificação
⚠️ Não documentado explicitamente como mecanismo de segurança. `chave_api` é a **mesma
API Key** usada para criar a referência — comparar contra `merchant.eupago_api_key` é
inferência razoável (é um segredo partilhado do lado do merchant), mas a documentação não
afirma que serve para validar o callback. Tratar como ⚠️ até confirmar — a decisão de usá-la
assim é da Fase 4, com teste que a comprove.

### (d) Cobertura de eventos e limite
✅ "A notificação só é enviada se a referência for paga" — sem cancelamento/reembolso/expiração.

## 2.0 (Realtime Webhooks)

### (a) Transporte
✅ `POST`. Corpo, **conforme a documentação** (⚠️ tem um erro real — ver "Confirmado com um
payload real" mais abaixo: o campo principal é `transaction`, singular, não `transactions`):
```json
{
  "transactions": {
    "entity": 0, "reference": 0, "identifier": "string",
    "method": "Multibanco|Mbway|CreditCard|Pix|GooglePay|ApplePay",
    "amount": {"value": 0, "currency": "EUR"},
    "fees": {"amount": 0, "currency": "EUR"},
    "date": "2026-01-01T00:00:00Z", "trid": 0,
    "status": "Paid|Refund|Error|Cancel|Expired"
  },
  "channel": { "name": "string" },
  "data": "string (presente e cifrado só se encrypt=true)"
}
```

### (b) Verificação — assinatura, **distinta** da cifra
✅ Header `X-Signature`: HMAC-SHA256 sobre o corpo, com a chave de encriptação gerada no
backoffice. Verificação:
```php
function verifySignature($data, $signature, $key) {
    $generatedSignature = hash_hmac('sha256', $data, $key, true);
    return hash_equals($generatedSignature, base64_decode($signature));
}
```
✅ `X-Initialization-Vector` **não é o mecanismo de autenticação** — só existe quando a cifra
opcional (`encrypt=true`, AES-256-CBC) está ativa, e carrega o IV em base64. Não confundir os
dois: assinatura sempre presente e obrigatória; cifra opcional e separada.

### (c) Estados e retry
✅ Estados: `Paid, Refund, Error, Cancel, Expired` — cobre reembolso e cancelamento, que o 1.0
não notifica. ✅ Retry: a cada 2 min até 3 tentativas, depois horário durante 24h. Resposta
esperada: `HTTP 200`.

## Delta e recomendação (Fase 4)

Migrar o `bookwey` para 2.0 assim que o canal estiver configurado: ganha assinatura
verificável de facto (não inferida), estados de reembolso/cancelamento/expiração, e retry
com backoff em vez de "melhor esforço". Até lá, `chave_api` do 1.0 é melhor do que nada —
está hoje completamente por verificar.

## Implementado (2026-08-18)

✅ `weypay/providers/eupago/callback.py::verify_and_parse()` — assinatura `X-Signature`
verificada **antes** de qualquer parsing do corpo (um corpo malformado com assinatura errada
falha por causa da assinatura, nunca revela se "parece" JSON válido). Cifra opcional
(`encrypt=true`, AES-256-CBC) **não implementada** — decisão deliberada, ver docstring do
módulo: a assinatura já garante integridade/autenticidade, cifrar é sobre confidencialidade
em trânsito, redundante com HTTPS (anti-overengineering, `docs/PLAN.md`).

**Vocabulário mapeado**: `Paid`→`PAID`, `Refund`→`REFUNDED`, `Cancel`→`DECLINED`,
`Expired`→`EXPIRED`. `Error` fica deliberadamente `UNKNOWN` — a documentação não esclarece se
é falha definitiva do pagamento ou um erro transitório do lado da EuPago; nunca assumir sem
observar um `Error` real primeiro (regra 6, docs/SECURITY.md).

## Confirmado com um payload real — a documentação errava o nome do campo principal (2026-08-18)

✅ **Validado de ponta a ponta em produção real**: canal Webhooks 2.0 configurado no
backoffice (URL + chave criptográfica gerada por eles), pagamento MB WAY real de €1,00
(mínimo real da EuPago para MB WAY em produção — €0,50 é rejeitado com `AMOUNT_INVALID`; o
valor exato entre os dois não foi isolado). A EuPago tentou entregar o webhook 3 vezes
(retries documentados, 2 em 2 min) e todas as 3 falharam — o código original só registava um
aviso genérico, sem guardar o corpo recebido, por isso a causa ficou invisível até se corrigir
isso e reobservar.

**Corpo real capturado** (`docs/observed/eupago_webhook_paid.json`):
```json
{
  "channel": {"account": "VECTORASSUMIDO", "name": "VECTORASSUMIDO"},
  "transaction": {
    "entity": "10076", "reference": "76856709",
    "identifier": "Salao-...", "method": "MW:PT",
    "amount": {"value": "1", "currency": "EUR"},
    "fees": {"value": 0.1476, "currency": "EUR"},
    "date": "2026-08-18T23:56:58", "trid": "118845709",
    "status": "Paid", "local": "Sem Informação"
  }
}
```

**Erro real na documentação, agora corrigido**: o campo principal chama-se **`transaction`**
(singular) — a documentação oficial (topo desta secção, (a)) diz `transactions` (plural). Era
exatamente essa a causa das 3 falhas de entrega. Diferenças adicionais, nenhuma delas exigiu
mudar o código (não usávamos esses campos, ou já eram tolerantes ao tipo):
`amount.value`/`trid` vêm como **string**, não número; `fees` usa a chave `value`, não
`amount`; `date` não tem sufixo `Z`; `method` usa o vocabulário `MW:PT` (estilo Webhooks 1.0),
não `Mbway`; há um campo extra `local` e `channel.account` não documentados.

**`status: "Paid"` confirmado exatamente como documentado** — essa parte da documentação
estava certa. Mesma categoria de erro que o `EstadoPedidosJSON` do MB WAY: a documentação
pública tinha um erro concreto, só visível numa chamada real, nunca por leitura atenta.

## Fonte

[Webhooks 1.0](https://eupago.readme.io/reference/webhooks) ·
[Realtime Webhooks 2.0](https://eupago.readme.io/reference/realtime-webhooks-20)
