# SIBS — Payment Gateway (SPG)

Marcação: ✅ verificado / ⚠️ a confirmar. Fonte primária:
[SPG integration guide](https://www.docs.pay.sibs.com/portugal/sibs-gateway/integrations/api/integration-guide/) ·
[Webhooks](https://www.docs.pay.sibs.com/portugal/sibs-gateway/notifications/webhooks/) ·
[Webhook examples](https://www.docs.pay.sibs.com/portugal/sibs-gateway/notifications/webhooks/examples/) ·
[API Market sandbox: MB WAY](https://developer.sibsapimarket.com/sandbox/node/3088) ·
[API Market sandbox: CARD](https://developer.sibsapimarket.com/sandbox/node/3086).

Não usado por nenhum dos dois projetos hoje. Escrito para substituir o esboço de
`sibs-integration-project`, que tinha o host, os paths, o schema e o webhook **todos
inventados** — ver comparação em `docs/PLAN.md`. Não ligado a nenhum projeto (Fase 5).

## ⚠️ Discrepância de host não resolvida — não escolher sem confirmar

A documentação oficial dá **três convenções de host diferentes** consoante a fonte:

| Fonte | Host/prefixo |
|---|---|
| Integration guide, secção "Base URLs" | `api.qly.sibspayments.com` (QLY/sandbox) / `api.sibspayments.com` (produção) |
| Integration guide, exemplos de endpoint | `spg.qly.site1.sibs.pt`, path `/api/v2/payments/...` |
| API Market sandbox (developer.sibsapimarket.com) | `sandbox.sibspayments.com`, path `/sibs/spg/v1/payments/...` |

Podem ser gerações diferentes da API (v1 vs v2), ambientes diferentes dentro do sandbox, ou
documentação desatualizada num dos dois portais. **Não decidir por dedução** — confirmar com
o contrato/onboarding real qual host e qual versão de path aplicam. Registado em
`docs/OPEN-QUESTIONS.md`. Os endpoints abaixo seguem a versão **v2** (integration guide, mais
recente e mais detalhada); o SDK parametriza o host e a versão do path, nunca os fixa.

## (a) Fluxo — 2 passos, dois esquemas de auth

1. **Checkout** — `Authorization: Bearer {AuthToken}` (token OAuth de longa duração,
   ⚠️ ciclo de vida/refresh não documentado nas páginas consultadas).
2. **Purchase específico do método** — `Authorization: Digest {transactionSignature}`, onde
   `transactionSignature` é devolvido pelo checkout. **Nunca `Bearer` nos passos seguintes.**

Header comum aos dois: `X-IBM-Client-Id: {clientId}` — API Gateway IBM, confirma o padrão já
visto no esboço original (esse ponto do esboço estava certo).

## (b) Checkout — `POST /api/v2/payments`

Request:
```json
{
  "merchant": { "terminalId": "...", "channel": "...", "merchantTransactionId": "..." },
  "transaction": {
    "transactionTimestamp": "...", "description": "...", "moto": false,
    "paymentType": "PURS",
    "amount": { "value": 20.00, "currency": "EUR" },
    "paymentMethod": ["CARD", "MBWAY", "REFERENCE"]
  }
}
```
Response: `transactionID`, `transactionSignature`, `paymentMethodList`,
`returnStatus{statusCode, statusMsg, statusDescription}`.

## (c) MB WAY purchase — `POST /api/v2/payments/{transactionID}/mbway-id/purchase`

Auth: `Digest {transactionSignature}`. Request: `{"customerPhone": "351#919999999"}` — note o
formato `351#nnnnnnnnn`, **diferente** do E.164 (`+351...`) usado pelo `boxwey` para a
ifthenpay. Conversão obrigatória no provider, não deixar para o consumidor.

## (d) Multibanco — `POST /api/v2/payments/{transactionID}/service-reference/generate`

Mesma auth `Digest`. ⚠️ Schema de request/response não capturado nas páginas consultadas —
por completar antes de implementar.

## (e) Consulta de estado — `GET /api/v2/payments/{transactionID}/status`

Auth: volta a `Bearer {AuthToken}` (não `Digest`). Response: `paymentStatus`, `returnStatus`.

## (f) Webhook — AES-256-GCM, não HMAC

✅ Headers: `X-Initialization-Vector` (IV, base64) + `X-Authentication-Tag` (tag GCM, base64).
Corpo: ciphertext base64. Algoritmo: **AES-256-GCM, sem padding**. Chave: `webhookSecret`,
gerada ou introduzida no **SIBS Gateway V2 Backoffice**.

Exemplo de decifra (PHP, do doc oficial):
```php
$result = openssl_decrypt($data, 'AES-256-GCM', $key, OPENSSL_RAW_DATA, $iv, $auth);
```
Em Python: `cryptography.hazmat.primitives.ciphers.aead.AESGCM` — daí o extra `weypay[sibs]`
depender de `cryptography` e não só de `requests`.

Payload decifrado (campos observados no exemplo oficial): `transactionID`,
`transactionDateTime`, `amount`, `merchant`, `paymentStatus`, `paymentType`, `notificationID`.

**Ack obrigatório**, formato exato:
```json
{"statusCode": "200", "statusMsg": "Success", "notificationID": "93b9b3a6-602f-4769-8158-48ae9c380ed5"}
```
Sem este corpo (não basta HTTP 200 nu), o "Webhook Retry System" da SIBS reenvia — e a
documentação avisa que a **ordem de entrega não é garantida** entre notificações.

## (g) Comparação com o esboço original (`sibs-integration-project`)

| | Esboço | Real |
|---|---|---|
| Host | `api.sibsapi.com` (inventado, não existe) | ver discrepância em (⚠️) acima — nenhum dos reais coincide com o inventado |
| Fluxo | 1 passo | 2 passos, checkout → purchase |
| Auth | `Bearer` sempre | `Bearer` no checkout, `Digest {transactionSignature}` depois |
| Webhook | HMAC-SHA256 hex, header `X-SIBS-Signature` (inventado) | AES-256-GCM, `X-Initialization-Vector`+`X-Authentication-Tag` |
| Ack | nenhum | corpo JSON obrigatório com `notificationID` |
| `transactionID`/`transactionSignature` | ausentes | centrais ao fluxo |

O que o esboço acertou e o SDK deve preservar: **stateless, credenciais injetadas por
chamada**, exceções em hierarquia (`SibsError`→`SibsAPIError`/`SibsSignatureError`), e o
`_request()` genérico de tratamento de erro — são a base do transporte partilhado
(`weypay.http`), não específicos da SIBS.

## Fonte

[SPG integration guide](https://www.docs.pay.sibs.com/portugal/sibs-gateway/integrations/api/integration-guide/) ·
[Webhooks](https://www.docs.pay.sibs.com/portugal/sibs-gateway/notifications/webhooks/) ·
[Webhook examples](https://www.docs.pay.sibs.com/portugal/sibs-gateway/notifications/webhooks/examples/) ·
[MB WAY (API Market sandbox)](https://developer.sibsapimarket.com/sandbox/node/3088) ·
[CARD (API Market sandbox)](https://developer.sibsapimarket.com/sandbox/node/3086)
