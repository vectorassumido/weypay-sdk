# Questões em aberto

Cada ⚠️ dos documentos em `docs/providers/` reunido aqui, com o que falta, como resolver, e o
que bloqueia. Nada nesta lista vira código sem passar a ✅ — ver a regra 7 em
`docs/PROGRESS.md`/`weypay-phase`: documentação oficial → sandbox → nunca dedução.

## Resolúveis na Fase 0b (com as credenciais de sandbox já disponíveis)

| # | Questão | Gateway/doc | Como resolver | Bloqueia |
|---|---|---|---|---|
| 1 | `/clientes/rest_api/multibanco/info` (path legado usado pelo `bookwey`) devolve `estado` ou `estado_referencia`? Que valores? | `eupago-status.md` | Criar referência MB WAY em sandbox, consultar antes/depois de pagar | Fase 3 (se o polling estiver de facto morto, é um bug a corrigir, não a preservar) |
| 2 | A resposta de `/api/v1.02/mbway/create` (sem split) traz `entity`? | `eupago-mbway.md` | Chamada real em sandbox | Fase 3 |
| 3 | `successUrl`/`failUrl`/`backUrl` no PIX: aceites, ignorados, ou erro de schema? | `eupago-pix.md` | Chamada real com e sem esses campos | Fase 3 |
| 4 | `chave_api` do Webhook 1.0 é mesmo o mecanismo de verificação, ou só está documentado como "a chave usada para criar a referência"? | `eupago-webhooks.md` | Configurar callback de sandbox para um túnel, pagar, observar | Fase 4 (fora do âmbito autónomo, mas a resposta informa-a) |
| 5 | `descricao` > 50 chars na ifthenpay MB WAY: trunca, ignora ou rejeita? | `ifthenpay-mbway.md` | Conta de teste (`ITP_MBWAY_KEY`) | Fase 2 (decide se a correção do SDK é suficiente por si, ou se há de facto um bug ativo hoje) |
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
