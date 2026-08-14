# Questões em aberto

Cada ⚠️ dos documentos em `docs/providers/` reunido aqui, com o que falta, como resolver, e o
que bloqueia. Nada nesta lista vira código sem passar a ✅ — ver a regra 7 em
`docs/PROGRESS.md`/`weypay-phase`: documentação oficial → sandbox → nunca dedução.

## Regra de segurança permanente, descoberta a aplicar durante a Fase 0b

**Nunca disparar uma criação de pagamento MB WAY (EuPago `mbway/create`,
`split-payments/mbway`, ou ifthenpay `SetPedidoJson`) com um número de telefone que não tenha
sido explicitamente fornecido pelo utilizador para este fim.** A chamada de *criação*, não só
a confirmação, é o que dispara a notificação push para o telefone indicado — ao contrário do
PIX (que só gera uma referência/QR, sem contactar ninguém). Adivinhar ou inventar um número
arriscaria notificar uma pessoa real e desconhecida sobre um pagamento que não pediu. Por isso
as questões #2, #5 e #15 abaixo **não foram resolvidas por chamada real com sucesso** — só o
que era seguro observar (respostas de erro com número deliberadamente inválido, ou mecanismos
que não envolvem MB WAY) foi executado. Esta regra aplica-se a todas as iterações futuras do
loop, não só a esta.

## Resolvidas na Fase 0b (2026-08-14, observação direta em sandbox)

| # | Questão | Resultado |
|---|---|---|
| ~~1~~ | `/clientes/rest_api/multibanco/info` devolve `estado` ou `estado_referencia`? | **Ambos.** `estado` (numérico) e `estado_referencia` (string, `"pendente"` observado) coexistem. `bookwey/api/services/payments.py:30,34` está correto. O endpoint `/multibanco/info` documentado publicamente devolve 404 nesta sandbox — é uma página de documentação para uma API diferente, não o path que o `bookwey` usa. Ver `docs/providers/eupago-status.md`, `docs/observed/eupago_status_*.json`. |
| ~~3~~ | `successUrl`/`failUrl`/`backUrl` no PIX: aceites, ignorados, ou erro? | **Aceites, sem erro** — `HTTP 201` idêntico com e sem os três campos. Ver `docs/providers/eupago-pix.md`, `docs/observed/eupago_pix_*.json`. |

## Parcialmente resolvida — limitada pela regra de segurança acima

| # | Questão | O que se sabe agora | O que falta |
|---|---|---|---|
| 2 | A resposta de `/api/v1.02/mbway/create` (sem split) traz `entity`? | Testado só com número inválido (seguro): `HTTP 400 CUSTOMERPHONE_INVALID`, forma de erro confirmada. Ver `docs/observed/eupago_mbway_create_invalid_phone.json`. | Uma criação com sucesso, que só é segura com um número de telefone de teste **fornecido pelo utilizador**. |

## Precisam de um número de telefone de teste do utilizador (não resolúveis pelo agente sozinho)

| # | Questão | Gateway/doc | Bloqueia |
|---|---|---|---|
| 5 | `descricao` > 50 chars na ifthenpay MB WAY: trunca, ignora ou rejeita? | `ifthenpay-mbway.md` | Fase 2 — testável só com `SetPedidoJson`, que dispara push real |
| 15 | A resposta de `split-payments/mbway` traz mesmo `entity`+`reference`+`amount`? | `eupago-mbway.md` | Fase 3 |

## Precisam de acesso ao backoffice do utilizador

| # | Questão | Gateway/doc | Como resolver | Bloqueia |
|---|---|---|---|---|
| 4 | `chave_api` do Webhook 1.0 é mesmo o mecanismo de verificação, ou só está documentado como "a chave usada para criar a referência"? | `eupago-webhooks.md` | Configurar callback de sandbox para um túnel, pagar, observar | Fase 4 (fora do âmbito autónomo, mas a resposta informa-a) |
| 6 | Que valores textuais de `[ESTADO]` chegam ao callback ifthenpay além de `PAGO`? Existe callback de recusa/cancelamento? | `ifthenpay-callbacks.md` | **Webhook Tester** oficial no backoffice ifthenpay | Fase 2 (mapear `STATUS_REFUNDED`/`STATUS_DECLINED` corretamente) |
| 7 | O `bookwey`/PINPAY já tem algum callback registado no backoffice? Com que nomes de parâmetro? | `ifthenpay-pinpay.md` | Ler o backoffice ifthenpay da conta `bookwey` | Fase 4 |

## Não resolúveis sem o utilizador (túnel público ou registo em backoffice)

| # | Questão | Bloqueia |
|---|---|---|
| 8 | Callback real de ponta a ponta (gateway → máquina local) — precisa de túnel público e URL registado no backoffice | Nível 3 de `LOCAL-TESTING.md`, explicitamente fora do que a execução autónoma garante |
| 9 | Garantir `[VALOR]` no template de callback ifthenpay de todas as contas — mudança de configuração, não de código | Fase 4 |

## SIBS — bloqueadas por falta de contrato (Fase 5, fora do âmbito autónomo)

| # | Questão |
|---|---|
| 10 | Qual host/versão de path se aplica ao contrato real: `api.qly.sibspayments.com` + `/api/v2`, `spg.qly.site1.sibs.pt` + `/api/v2`, ou `sandbox.sibspayments.com` + `/sibs/spg/v1`? Ver `docs/providers/sibs-spg.md` |
| 11 | Ciclo de vida do `AuthToken` (OAuth) — expiração, refresh |
| 12 | Existe mTLS no onboarding real, ou só `X-IBM-Client-Id` + Bearer/Digest? |
| 13 | Schema completo do request/response de `service-reference/generate` (Multibanco) — não capturado nas páginas consultadas |
| 14 | Base URL e auth da Marketplace API (onboarding/split) — não documentados na página consultada |

## Regra de resolução

Uma linha só sai desta tabela quando a coluna "Como resolver" tiver sido executada e o
resultado estiver refletido no `docs/providers/*.md` correspondente, com a marcação trocada
de ⚠️ para ✅ e a fonte da observação citada (`docs/observed/<ficheiro>` ou link da
documentação). Se a observação contradisser o que o `docs/PLAN.md` assumia, o `PLAN.md`
corrige-se também — nunca o inverso.
