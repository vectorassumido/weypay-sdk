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
| ~~15~~ | A resposta de `split-payments/mbway` traz mesmo `entity`+`reference`+`amount`? | **Teste local real, 2026-08-14** (utilizador presente, número próprio autorizado): `{"entity": null, "reference": "320778", "amount": "15.00"}`. `entity` vem `null` para MB WAY (não é erro), `reference`/`amount` sempre presentes. Ver `docs/providers/eupago-mbway.md`. |

## Parcialmente resolvida — limitada pela regra de segurança acima

| # | Questão | O que se sabe agora | O que falta |
|---|---|---|---|
| 2 | A resposta de `/api/v1.02/mbway/create` (sem split) traz `entity`? | Testado só com número inválido (seguro): `HTTP 400 CUSTOMERPHONE_INVALID`, forma de erro confirmada. Ver `docs/observed/eupago_mbway_create_invalid_phone.json`. | Uma criação com sucesso — ver "Número de teste em reserva" abaixo. |

## Número de teste em reserva — usar só se genuinamente bloqueante

**2026-08-14**: o utilizador forneceu um número de telefone pessoal real (guardado só em
`.env.manual`, nunca neste ficheiro nem em nenhum ficheiro rastreado) como reserva de
emergência para desbloquear #5/#15 abaixo, com condições estritas:

- O utilizador **não pode reagir a nenhum push** neste número até regressar (fim de semana) —
  qualquer push enviado fica por confirmar até expirar.
- Usar **só se uma fase autónoma ficar genuinamente bloqueada** sem isto — nunca por
  curiosidade nem para "completar" uma questão que já tem um comportamento seguro assumido.
- **No máximo uma chamada**, nunca repetida.

**Avaliação, 2026-08-14**: nenhuma das Fases 1/2/3 (âmbito autónomo atual) depende de facto de
#5 ou #15 — ambas são confirmatórias, não bloqueantes (o SDK já trunca `descricao`
defensivamente independentemente do que a ifthenpay fizer; o código que lê `entity` não é
tocado antes da Fase 3, e mesmo aí o comportamento atual pode ser preservado sem confirmação).
**Decisão: não usar o número agora.** Só reconsiderar se uma fase autónoma ficar
verdadeiramente parada sem esta informação — registar aqui e em `PROGRESS.md` antes de usar.

| # | Questão | Gateway/doc | Bloqueia de facto? |
|---|---|---|---|
| 5 | `descricao` > 50 chars na ifthenpay MB WAY: trunca, ignora ou rejeita? | `ifthenpay-mbway.md` | Não — o SDK já trunca sempre, independentemente da resposta |

## Resolvidas em teste local real (2026-08-14, fora da Fase 0b — pagamento sandbox verdadeiro)

| # | Questão | Resultado |
|---|---|---|
| ~~16~~ | `verificar_pagamento_mbway()` devolvia 404 para uma referência MB WAY real. Bug ou comportamento herdado? | **Bug real no SDK** (não herdado): `status.py::ENDPOINTS` tinha `/api` a mais, copiado por engano de `mbway.py`/`split.py`. Corrigido (`weypay-sdk` commit local + `bookwey-serverless` `_eupago_status_base_url()` separado de `_eupago_base_url()`). Reconfirmado com a mesma referência: `estado_referencia="paga"`, HTTP 200. Ver `docs/providers/eupago-status.md` (c''). |
| ~~17~~ | `estado_referencia` de sucesso é mesmo `"paga"`? | **Confirmado, observação direta**: referência `320780`, marcada paga no backoffice sandbox pelo utilizador, consultada com sucesso — `estado_referencia: "paga"`. Ver `docs/providers/eupago-status.md` (c'''), `docs/observed/eupago_status_mbway_paid_confirmed.json`. |
| ~~18~~ | `split-payments/mbway` com `adminCallback` inalcançável (`localhost`) — a EuPago aceita a criação mas bloqueia a confirmação? | **Sim, confirmado por comparação direta**: mesma criação, só o `adminCallback` trocado por uma URL real e alcançável, e a referência resultante passou a poder ser marcada como paga no backoffice sandbox (antes: `"O estado da referência não foi alterado."`). Ver `docs/providers/eupago-mbway.md` §"adminCallback tem de ser uma URL alcançável". Push real ao telemóvel continua nunca observado em sandbox — confirmado pelo utilizador como normal, não regressão. |
| ~~19~~ | EuroPix: `Payment.reference` guarda o id local (`numeric_id`) ou a referência real da EuPago? | **Guardava o id local — bug real, não só "falta de previsibilidade" como esta lista descrevia antes.** Toda consulta de estado EuroPix 404ava, no `bookwey` pré- e pós-migração. Corrigido: `Payment.reference` = referência real da EuPago (como já acontecia em MB WAY/split); novo campo `Payment.client_reference` para o id local. Verificado com pagamento sandbox real — `check_payment_status` já não 404. Ver `docs/providers/eupago-pix.md`. |
| ~~20~~ | ifthenpay `EstadoPedidosJson`/`EstadoPedidosJSON`: método HTTP, grafia certa, nome do campo da chave, estrutura da resposta? | **Confirmado com uma chamada real** (pagamento MB WAY de €0,01 no `boxwey`, número do utilizador, autorizado e aceite por ele): exige **GET com querystring** (POST/JSON dá 500 sem detalhe); método é **`EstadoPedidosJSON`** (todo maiúsculas — o próprio erro 500 ao tentar `EstadoPedidosJson` revelou a grafia certa); campo da chave é `MbWayKey` (igual a `SetPedidoJson`). Resposta tem **dois `Estado`**: o de topo é do pedido HTTP, o que importa é `EstadoPedidos[0].Estado`. Implementado em `weypay/providers/ifthenpay/mbway.py::get_order_status()`. Ver `docs/providers/ifthenpay-mbway.md` (e). |
| ~~21~~ | Código de recusa/cancelamento em `EstadoPedidosJSON` — a tabela síncrona (`020`, `048`, `100`, ...) aplica-se aqui também? | **`"020"` confirmado com uma recusa real** (utilizador recusou o push deliberadamente): `MsgDescricao: "Operação financeira cancelada pelo utilizador"`, bate certo com a tabela. `get_order_status()` mapeia `"020"` → `PaymentStatus.DECLINED`. Os restantes códigos da tabela continuam por confirmar especificamente neste endpoint — não generalizados por dedução. Ver `docs/providers/ifthenpay-mbway.md`. |
| ~~22~~ | Existe um código dedicado a "pagamento expirado" (janela de tempo passada sem resposta)? | **Não — confirmado com DOIS testes reais de expiração deliberada, que devolveram códigos DIFERENTES conforme o timing da consulta.** Consultado logo a seguir à janela fechar (~4 min): `"123"` ("Financial transaction not found"). Consultado com mais margem (~5 min completos, sem interação): `"101"` ("Operação financeira expirada", texto literal — não consta da tabela documentada, mas já estava no `STATUS_DECLINED` do `boxwey` pré-migração). Hipótese ⚠️ não totalmente confirmada: "123" é transitório logo a seguir ao corte, "101" é o estado estável. `get_order_status()` mapeia ambos → `PaymentStatus.EXPIRED`. O utilizador recebeu uma notificação push de expiração da própria app MB WAY pouco depois dos ~4 min. Ver `docs/providers/ifthenpay-mbway.md`. |

## Precisam de acesso ao backoffice do utilizador

| # | Questão | Gateway/doc | Como resolver | Bloqueia |
|---|---|---|---|---|
| 4 | `chave_api` do Webhook 1.0 é mesmo o mecanismo de verificação, ou só está documentado como "a chave usada para criar a referência"? | `eupago-webhooks.md` | Configurar callback de sandbox para um túnel, pagar, observar | Fase 4 (fora do âmbito autónomo, mas a resposta informa-a) |
| 6 | Que valores textuais de `[ESTADO]` chegam ao callback ifthenpay além de `PAGO`? Existe callback de recusa/cancelamento? | `ifthenpay-callbacks.md` | **Webhook Tester** oficial no backoffice ifthenpay | Fase 2 (mapear `STATUS_REFUNDED`/`STATUS_DECLINED` corretamente) |
| 7 | O `bookwey`/PINPAY já tem algum callback registado no backoffice? Com que nomes de parâmetro? | `ifthenpay-pinpay.md` | Ler o backoffice ifthenpay da conta `bookwey` | Fase 4 |
| 23 | Existe um endpoint de consulta de estado para PINPAY (equivalente ao `EstadoPedidosJSON` do MB WAY, confirmado hoje só por chamada real, não pela documentação)? A documentação oficial não lista nenhum — mas a documentação também estava errada/incompleta sobre `EstadoPedidosJSON`. | `ifthenpay-pinpay.md` | Testar chamadas candidatas com as credenciais de produção já disponíveis (item 24 abaixo) | Fase 4 — é exatamente o mecanismo que fecharia a falha de segurança do `check_payment_status` para `pinpay` (item 7 acima) |
| ~~24~~ | **Resolvida (2026-08-18), corrigido um achado inicial errado**: pagamento PINPAY real (Apple Pay e Google Pay, €0,01) confirmado pago do lado da ifthenpay; `Payment` local ficou `"pending"` — mas **não por falta de mecanismo**. Causa real: `success_url`/`front_domain` aponta para `http://salao-beleza-viva.localhost:3000`, inalcançável do dispositivo do teste (mesma classe do `adminCallback` EuPago) — a página que faz *polling* de `check_payment_status` nunca carregou. Invocado manualmente para a mesma referência: `status` passa a `"confirmed"` de imediato. **O mecanismo funciona quando chamado**; não diz nada de novo sobre #7/#23, que continuam genuinamente em aberto. | `ifthenpay-pinpay.md` (f) | — | — |

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
