# 04 — `bookwey`: fechar os buracos de segurança

**Fora do âmbito da execução autónoma** (`weypay-phase` regra 9). Este documento existe para
que a Fase 3 não precise de decidir nada aqui — fica escrito e pronto para revisão presencial.
Muda a semântica de confirmação de pagamento de um sistema em produção e depende de
configuração nos backoffices dos gateways, que só o utilizador pode fazer.

## As duas falhas (uma continua aberta, ver estado de cada uma abaixo)

1. `api/services/payments.py:11-19` — `GET /api/pagamento-callback/<schedule_uuid>/` é
   público, sem autenticação, e **confirma o pagamento sem contactar o gateway**. Basta
   conhecer o UUID de um `Schedule`.
2. ~~`api/services/payments.py:26-27` — `check_payment_status` confirma qualquer pagamento
   `pinpay` sem contactar a ifthenpay~~ — **✅ CORRIGIDA (2026-08-18, `bookwey` commit
   `e253ec2`).**

   **Achado crítico que motivou corrigir imediatamente, antes do deploy**, ao verificar com o
   utilizador se era seguro avançar para produção: `reconcile_pending_payments` (job
   agendado, cada 5 min, presente desde o "Initial commit" de `bookwey-serverless` — **não**
   introduzido por esta migração) chama `check_payment_status()` para todo o `Payment`
   `pending` há mais de 15 minutos. Combinado com a falha #2, isto significa que **qualquer
   pagamento PINPAY pendente há mais de ~15-20 min era automaticamente marcado como pago em
   produção, com ou sem pagamento real** — confirmado lendo `main` diretamente, não por
   dedução. Falha ativa, silenciosa, já em produção antes de qualquer trabalho desta migração.

   Sequência que tornou a correção segura: registar o callback nas contas `APPLE`/`GOOGLE` do
   backoffice ifthenpay → confirmar a funcionar de ponta a ponta com um pagamento real de
   €0,01 via túnel `cloudflared` (`GatewayCallLog(outcome="paid", http_status=200)`,
   `Payment.status` passou a `"confirmed"` sozinho, sem chamada manual) → só então remover o
   ramo inseguro. `check_payment_status` para `pinpay` deixa de fazer qualquer coisa — a
   confirmação é exclusiva do webhook verificado; a função só reflete o que ele já confirmou.
   2 testes de regressão substituem o teste que provava a falha.

## Correções, cada uma dependente de uma ação do utilizador primeiro

| Correção | Depende de |
|---|---|
| Verificar `chave_api` do callback EuPago 1.0 | `docs/OPEN-QUESTIONS.md` #4 confirmado (é mesmo o mecanismo de verificação?) |
| Migrar para Webhooks 2.0 (assinatura `X-Signature`) | ✅ canal disponível no backoffice EuPago (verificado 2026-08-18), mas por configurar — falta URL alcançável + gerar a chave criptográfica; `providers/eupago/callback.py` ainda não escrito no SDK |
| ~~Registar callback anti-phishing do PINPAY~~ | ✅ **Rota implementada** (`bookwey` commit `0c813cb`, `/api/webhooks/ifthenpay/`) — falta só o utilizador colar uma URL alcançável + chave nas contas `APPLE`/`GOOGLE` do backoffice ifthenpay (descoberta: é por-conta, não por-produto — ver `docs/OPEN-QUESTIONS.md` #7) |
| Passar callbacks a platform-wide (`/api/v1/webhooks/eupago/`, `/api/v1/webhooks/ifthenpay/`) | ✅ `/api/webhooks/ifthenpay/` já é platform-wide (uma rota, `Payment` localizado pela `reference`, mesmo padrão do `boxwey`) — falta a parte EuPago, e reconfigurar `adminCallback` por-merchant → um só |
| Trocar a referência por 15 dígitos aleatórios | Migração de dados só em pagamentos `pending` — decisão sobre janela de corte é do utilizador |
| ~~`select_for_update` + unique index de dedupe~~ | ✅ Feito (`bookwey` commit `37bca3a`) |
| ~~`GatewayCallLog` no `bookwey`~~ | ✅ Feito (`bookwey` commit `37bca3a`, escrito também no webhook desde `0c813cb`) |
| ~~Portar os 11 testes de webhook do `boxwey`~~ | ✅ Feito — 14 testes (`bookwey` commit `0c813cb`, `integrations/payments/tests/test_ifthenpay_webhook.py`) |

## Porque não entra na execução autónoma

Registar o callback no backoffice ifthenpay e configurar o canal EuPago 2.0 são ações fora do
alcance de um agente sem acesso às contas externas — e mesmo que fossem tecnicamente
possíveis, mudar de onde vem a confirmação de um pagamento **antes** de essa confirmação estar
verificada contra o gateway é o tipo de mudança que precisa de olhos humanos antes de ir para
produção, não só de testes verdes.

## O que a execução autónoma pode preparar sem decidir por ninguém

✅ **Feito (2026-08-18, `bookwey-serverless` commit `37bca3a`)** — a parte sem dependência
externa está completa:

- `GatewayCallLog` no `bookwey` (`integrations/payments/models.py`, cópia exata do modelo de
  `02`) — escrito na iniciação de `criar_pagamento_com_split`/`_europix`/`_pinpay`
  (`_log_call()`, tanto no sucesso como em `GatewayRejected`). **Não** escrito em
  `verificar_pagamento`/`verificar_pagamento_mbway` (consulta de estado) — `weypay.providers.
  eupago.status.get_reference_status()` não expõe `GatewayCall` no caminho de sucesso (só
  `data`), ao contrário dos providers de criação (`PaymentResult.call`). Alargar isso é uma
  mudança de desenho do SDK, não uma tarefa mecânica — ficou por fazer de propósito, registado
  como item de backlog, não escondido.
- `select_for_update()` em `pay_pagamento()` — toda a secção crítica (verificação de status →
  confirmação) passa a correr dentro de `transaction.atomic()` com o `Payment` bloqueado,
  fechando uma condição de corrida real (duas confirmações concorrentes — ex.: webhook e
  polling do frontend a chegar quase ao mesmo tempo — podiam ambas passar a verificação antes
  de qualquer uma escrever, duplicando o email/push de confirmação). `Payment.reference`
  (já `unique=True`) serve de dedupe key — não foi preciso campo novo.
- Testes que **provavam a falha atual** (`api/tests/test_payment_security_gaps.py`): o
  callback público confirma sem qualquer verificação (continua a provar isto — falha #1 ainda
  aberta), e `check_payment_status` confirmava `pinpay` sem contactar a ifthenpay (falha #2 —
  **corrigida a seguir, 2026-08-18, ver acima**; o teste passou a provar a correção).

97/97 testes nesta etapa (112/112 depois da correção da falha #2, ver acima). **Falha #1
(callback público) continua aberta e exploráveis** — depende de configuração externa
(assinatura EuPago 2.0 / callback ifthenpay verificado platform-wide) para fechar
definitivamente. Falha #2 fechada.

Falta a parte que precisa de ação do utilizador para a falha #1 (tabela acima) — ver
"Correções" no topo deste documento.

## Reversão

Idêntica aos passos anteriores: nada commitado em `bookwey-serverless`.
