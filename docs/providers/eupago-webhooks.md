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
✅ `POST`. Corpo:
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

## Fonte

[Webhooks 1.0](https://eupago.readme.io/reference/webhooks) ·
[Realtime Webhooks 2.0](https://eupago.readme.io/reference/realtime-webhooks-20)
