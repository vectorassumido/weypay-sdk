# 04 — `bookwey`: fechar os buracos de segurança

**Fora do âmbito da execução autónoma** (`weypay-phase` regra 9). Este documento existe para
que a Fase 3 não precise de decidir nada aqui — fica escrito e pronto para revisão presencial.
Muda a semântica de confirmação de pagamento de um sistema em produção e depende de
configuração nos backoffices dos gateways, que só o utilizador pode fazer.

## As duas falhas

1. `api/services/payments.py:11-19` — `GET /api/pagamento-callback/<schedule_uuid>/` é
   público, sem autenticação, e **confirma o pagamento sem contactar o gateway**. Basta
   conhecer o UUID de um `Schedule`.
2. `api/services/payments.py:26-27` — `check_payment_status` confirma qualquer pagamento
   `pinpay` sem contactar a ifthenpay; a referência (`str(schedule.id.int)[-15:]`) é
   devolvida ao browser.

   ⚠️ **Continua aberta de propósito** (2026-08-18): o webhook `/api/webhooks/ifthenpay/` já
   existe (ver Correções abaixo), mas removê-la agora — antes de o callback estar registado e
   testado ao vivo no backoffice ifthenpay — deixaria o PINPAY sem NENHUMA forma de confirmar
   localmente. Ordem correta: registar o callback → confirmar que funciona de ponta a ponta →
   só então remover este ramo. Não inverter a ordem.

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
- Testes que **provam a falha atual** (`api/tests/test_payment_security_gaps.py`): o callback
  público confirma sem qualquer verificação, e `check_payment_status` confirma `pinpay` sem
  contactar a ifthenpay. Passam hoje **porque a falha existe** — não são `xfail` — e servem de
  critério de aceitação explícito para quando cada uma for corrigida.

97/97 testes, `makemigrations --check --dry-run` limpo. **Nada disto muda a fonte da
confirmação de pagamento hoje** — as duas falhas continuam abertas e exploráveis; só ficou
mais fácil de auditar e mais seguro sob concorrência.

Falta a parte que precisa de ação do utilizador (tabela acima) — ver "Correções" no topo
deste documento.

## Reversão

Idêntica aos passos anteriores: nada commitado em `bookwey-serverless`.
