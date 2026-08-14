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

## Correções, cada uma dependente de uma ação do utilizador primeiro

| Correção | Depende de |
|---|---|
| Verificar `chave_api` do callback EuPago 1.0 | `docs/OPEN-QUESTIONS.md` #4 confirmado (é mesmo o mecanismo de verificação?) |
| Migrar para Webhooks 2.0 (assinatura `X-Signature`) | Canal configurado no backoffice EuPago pelo utilizador |
| Registar callback anti-phishing do PINPAY | Ação no backoffice ifthenpay pelo utilizador; `docs/OPEN-QUESTIONS.md` #7 |
| Passar callbacks a platform-wide (`/api/v1/webhooks/eupago/`, `/api/v1/webhooks/ifthenpay/`) | Reconfigurar `adminCallback` no backoffice EuPago por-merchant → um só, platform-wide |
| Trocar a referência por 15 dígitos aleatórios | Migração de dados só em pagamentos `pending` — decisão sobre janela de corte é do utilizador |
| `select_for_update` + unique index de dedupe | Nenhuma dependência externa — pode ir junto quando o resto avançar |
| `GatewayCallLog` no `bookwey` | Cópia da definição de `02-boxwey-cleanup.md` — sem dependência externa |
| Portar os 11 testes de webhook do `boxwey` | Depende da rota existir primeiro |

## Porque não entra na execução autónoma

Registar o callback no backoffice ifthenpay e configurar o canal EuPago 2.0 são ações fora do
alcance de um agente sem acesso às contas externas — e mesmo que fossem tecnicamente
possíveis, mudar de onde vem a confirmação de um pagamento **antes** de essa confirmação estar
verificada contra o gateway é o tipo de mudança que precisa de olhos humanos antes de ir para
produção, não só de testes verdes.

## O que a execução autónoma pode preparar sem decidir por ninguém

- `GatewayCallLog` no `bookwey` (cópia de `02`).
- `select_for_update` + unique index de dedupe na tabela `Payment` — não muda a *fonte* da
  confirmação, só torna a aplicação de qualquer confirmação (correta ou não) atómica.
- Os testes que **provam a falha atual** (callback confirma sem verificação; `pinpay` confirma
  sem contactar a ifthenpay) — escritos como testes que hoje **falham** (`xfail` ou
  explicitamente marcados como demonstração da falha), para servirem de critério de aceitação
  claro quando a correção for aplicada.

Se a execução autónoma chegar aqui com tempo/orçamento sobrando, fazer só o acima e parar —
nunca a parte que exige configuração externa.

## Reversão

Idêntica aos passos anteriores: nada commitado em `bookwey-serverless`.
