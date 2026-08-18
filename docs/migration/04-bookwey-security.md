# 04 — `bookwey`: fechar os buracos de segurança

**Estado: ambas as falhas corrigidas (2026-08-18).** Este documento começou como um guião para
"fora do âmbito da execução autónoma" (`weypay-phase` regra 9) — a parte que dependia de
configuração em backoffices externos só podia avançar com o utilizador presente. Ficou como
está por completude histórica; ver "Cronologia" abaixo para o que mudou depois.

## As duas falhas originais

1. `GET /api/pagamento-callback/<schedule_uuid>/` — público, sem autenticação, **confirmava
   o pagamento sem contactar o gateway**. Bastava conhecer o UUID de um `Schedule`.
2. `check_payment_status` confirmava qualquer pagamento `pinpay` sem contactar a ifthenpay.

## Cronologia da correção

### Falha #2 (PINPAY) — corrigida primeiro (`bookwey` commit `e253ec2`)

**Achado crítico que motivou corrigir antes do deploy**, ao confirmar com o utilizador se era
seguro avançar para produção: `reconcile_pending_payments` (job agendado, cada 5 min,
presente desde o "Initial commit" de `bookwey-serverless` — **não** introduzido por esta
migração) chama `check_payment_status()` para todo o `Payment` `pending` há mais de 15
minutos. Combinado com a falha #2, isto significa que **qualquer pagamento PINPAY pendente há
mais de ~15-20 min era automaticamente marcado como pago em produção, com ou sem pagamento
real** — confirmado lendo `main` diretamente, não por dedução. Falha ativa, silenciosa, já em
produção antes de qualquer trabalho desta migração.

Sequência que tornou a correção segura: registar o callback nas contas `APPLE`/`GOOGLE` do
backoffice ifthenpay → confirmar a funcionar de ponta a ponta com um pagamento real de €0,01
via túnel `cloudflared` (`GatewayCallLog(outcome="paid", http_status=200)`, `Payment.status`
passou a `"confirmed"` sozinho, sem chamada manual) → só então remover o ramo inseguro.
`check_payment_status` para `pinpay` deixa de fazer qualquer coisa — a confirmação é exclusiva
do webhook verificado; a função só reflete o que ele já confirmou.

### Falha #1 (callback público) — corrigida a seguir (`bookwey` commit `064101e`)

Removida por completo, não "consertada" — o único propósito do endpoint era esse blind
confirm, e não tinha nenhum caller legítimo (`grep` sistemático em `booksys-be`/`booksys-fe`
antes de tocar, confirmado vazio). A confirmação passa a ser exclusiva de:
- `/api/webhooks/eupago/` (novo — ver abaixo), assinatura HMAC-SHA256 verificada.
- `/api/webhooks/ifthenpay/` (já existia, ver adendo anterior), chave anti-phishing + valor
  verificados.
- Polling (`check_payment_status` para MB WAY/EuroPix) — consulta mesmo o gateway, sempre
  fez isto corretamente, nunca foi parte do problema.

Isto exigiu escrever `providers/eupago/callback.py` no SDK primeiro — nunca tinha sido feito
(deferido desde a Fase 0c/3). Implementa `verify_and_parse()` contra o protocolo documentado
(Webhooks 2.0): assinatura `X-Signature` (HMAC-SHA256 sobre o corpo bruto) verificada **antes**
de qualquer parsing do JSON — um corpo malformado com assinatura errada falha pela assinatura,
nunca revela se "parece" JSON válido. Vocabulário mapeado: `Paid`→confirma, `Cancel`/
`Expired`→`"failed"` (nunca rebaixando um `Payment` já `"confirmed"`), `Refund`→registado mas
não aplicado (`Payment` não tem estado "refunded" próprio — rebaixar silenciosamente
esconderia uma decisão de negócio que não é só técnica), `Error`→`UNKNOWN` deliberadamente (a
documentação não esclarece se é falha definitiva ou erro transitório do lado da EuPago).

Problema de desenho resolvido a meio: a chave de assinatura é por-merchant
(`Merchant.eupago_webhook_signing_key`), só se sabe depois de resolver o merchant a partir da
referência — mas a referência só é de confiar depois de verificar a assinatura. Resolvido
como o `ifthenpay.callback` já resolvia isto: `extract_reference()` separado, não verificado,
só para escolher a chave; a verificação real acontece a seguir em `verify_and_parse()`. Um
pedido forjado com a referência de outro merchant continua a falhar, porque a assinatura não
bate certo com a chave desse merchant.

⚠️ **O corpo/vocabulário do Webhooks 2.0 ainda não foi confirmado por um payload real** — os
35 testes (19 no SDK + 16 no `bookwey`) usam o exemplo documentado e o algoritmo HMAC
documentado (esse é protocolo verificável independentemente de um payload real). Falta:
configurar o canal no backoffice EuPago, gerar a chave criptográfica, e receber um pagamento
real — mesma disciplina que corrigiu três pontos errados na documentação do
`EstadoPedidosJSON` do MB WAY antes de uma chamada real.

## O que ficou feito, no total

- `GatewayCallLog` no `bookwey` (cópia do `boxwey`), escrito na iniciação de
  split/EuroPix/PinPay e em ambos os webhooks.
- `select_for_update()` em `pay_pagamento()` — fecha uma condição de corrida real entre
  confirmações concorrentes.
- `/api/webhooks/ifthenpay/` (PINPAY) — implementado, validado ao vivo com um pagamento real.
- `/api/webhooks/eupago/` (Webhooks 2.0) — implementado, testado contra o protocolo
  documentado, **por validar ao vivo** (ver `docs/OPEN-QUESTIONS.md`).
- `GET /api/pagamento-callback/<uuid>/` — removido.
- `check_payment_status` para `pinpay` — já não confirma sozinho.
- 128 testes no `bookwey` (91 baseline + 37 desta fase), `makemigrations --check` limpo.

## Ainda por fazer (não bloqueia produção, mas fica registado)

| Item | Porquê não está feito |
|---|---|
| Validar `/api/webhooks/eupago/` ao vivo (túnel + pagamento real) | Falta configurar o canal no backoffice EuPago — próximo passo natural |
| `chave_api` do Webhook 1.0 (EuPago) | Deprioritizado — o `bookwey` vai direto para 2.0 |
| Trocar a referência do `bookwey` por 15 dígitos aleatórios | Não é uma falha de segurança per se (a referência de EuroPix/PINPAY já não é a única forma de confirmar), decisão de janela de corte fica para quando o utilizador quiser |
| Cifra opcional do Webhooks 2.0 (AES-256-CBC) | Deliberadamente fora — a assinatura já garante integridade/autenticidade, cifrar é sobre confidencialidade em trânsito, redundante com HTTPS |

## Reversão

Nada commitado sem gates verdes primeiro, em nenhum passo desta fase.
