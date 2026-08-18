# Changelog

Formato: [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).
Versionamento semântico. Os projetos consumidores fixam sempre uma tag exata.

## [Não lançado]

### v0.3.0 — ifthenpay: fallback de reconciliação para PINPAY
- `providers/ifthenpay/pinpay.get_order_status()` — usa a API oficial "List of Payments REST"
  (`POST /v2/payments/read`), documentada pela ifthenpay como alternativa/complemento ao
  callback. Cobre a conta inteira (não só PINPAY), mas `orderId` corresponde exatamente ao
  `id` usado em `create_payment`.
- Requer uma credencial nova, `bo_key` ("Backoffice key that identifies the merchant
  account"), distinta da `gateway_key` e da chave anti-phishing — ⚠️ ainda não confirmado como
  obter; ver `docs/OPEN-QUESTIONS.md`.

### Fase 0a — repositório e documentação
- Esqueleto do repositório e documentação completa escrita antes de qualquer implementação.
- Especificação *verbatim* de cada API dos três gateways, com marcação ✅ verificado / ⚠️ a confirmar.
- Guiões de migração por fase e guião de teste local para os dois projetos consumidores.
