# ifthenpay — MB WAY

Marcação: cada afirmação leva ✅ (documentação oficial ou código lido) ou ⚠️ (a confirmar —
ver `docs/OPEN-QUESTIONS.md`). Fonte primária: [API MBWAY (deprecated)](https://helpdesk.ifthenpay.com/en/support/solutions/articles/79000086376-api-mbway-deprecated-),
[índice de APIs](https://www.ifthenpay.com/docs/en/).

## (a) Endpoint, método, auth, ambientes

- ✅ **Versão em uso pelo `boxwey`: v1, marcada "API - MBWAY (Deprecated)"** pela própria ifthenpay.
- ✅ Endpoint: `POST https://mbway.ifthenpay.com/ifthenpaymbw.asmx/SetPedidoJson`
- ✅ Existe também `SetPedido` (SOAP) — não usado por nenhum dos dois projetos, não portar.
- ✅ Auth: `MbWayKey` vai **no corpo do pedido**, não em header. É a chave por-tenant/merchant.
- ✅ **Sem sandbox própria.** O isolamento vem só de pedir chaves de teste à ifthenpay
  (`ITP_MBWAY_KEY` nos `.env` legados) contra o **mesmo host de produção**. Ver
  `docs/ENVIRONMENTS.md`.
- ⚠️ **API v2 REST existe** (`api/mbway/` no índice atual) e é a via recomendada para
  integrações novas — fora de âmbito desta migração (que preserva comportamento), registada
  como item de backlog na Fase 2.

## (b) Request — `SetPedidoJson`, campos verbatim

| Campo | Obrigatório | Tipo/limite | Fonte |
|---|---|---|---|
| `MbWayKey` | ✅ sim | string, atribuída pela ifthenpay | ✅ |
| `canal` | ✅ sim | constante `"03"` | ✅ |
| `referencia` | ✅ sim | string, **máx. 15 caracteres** | ✅ |
| `valor` | ✅ sim | decimal | ✅ |
| `nrtlm` | ✅ sim | telefone do cliente | ✅ |
| `email` | opcional | string | ✅ |
| `descricao` | ✅ sim | string, **máx. 50 caracteres** | ✅ |

⚠️ Comportamento se `descricao` exceder 50 chars (trunca / ignora / rejeita) não está
documentado — `boxwey/api/events/services/payments.py:41` envia
`f"{event.name} — {n} bilhete(s)"` sem truncar. Confirmar na Fase 0b.

## (c) Response — campos verbatim

`IdPedido`, `Valor`, `CodigoMoeda` (✅ sempre `9782`), `Estado`, `DataHora`, `MsgDescricao`.

`boxwey/api/integrations/ifthenpay/client.py:75-83` lê `IdPedido` (obrigatório — ausência
→ `PaymentGatewayError`) e `Estado`; guarda o resto em `raw`.

## (d) Vocabulário de estado — **dois, não um**

✅ Esta é a distinção mais importante desta API, e o código atual já a documenta corretamente
em comentário (`client.py:18-27`), mesmo sem a citar:

**Síncrono** (resposta de `SetPedidoJson` / `EstadoPedidos`) — numérico:

| Código | Significado |
|---|---|
| `000` | Financial transaction completed successfully |
| `020` | Financial transaction cancelled by the user |
| `048` | Financial transaction cancelled by the Merchant |
| `100` | The operation could not be completed |
| `104` | Financial operation not allowed |
| `111` | The format of the mobile number was not in the correct format |
| `113` | The mobile number used as an identifier was not found |
| `122` | Operation refused to the user |
| `123` | Financial transaction not found |
| `125` | Operation refused to the user |

**Callback** — textual, ver `ifthenpay-callbacks.md`. `client.py:20-22` compara
`STATUS_REFUNDED="023"` e `STATUS_DECLINED={"020","101","113"}` contra o `estado` do
**callback** — ⚠️ mas o callback é textual (`PAGO`, ver abaixo), pelo que estes códigos
numéricos provavelmente não se aplicam a ele. `"101"` nem sequer consta da tabela síncrona
oficial acima. Não corrigir sem confirmar o vocabulário real do callback (Fase 0b) — a
correção segura e incondicional é: estado desconhecido no callback nunca devolve 4xx.

## (e) Consulta de estado — `EstadoPedidosJson`

✅ Existe, GET ou POST, devolve o estado de um ou mais pedidos pela `referencia`. **Nunca
portado** em nenhum dos dois projetos — é o endpoint de reconciliação que falta para um job
de "confirmar pagamentos pendentes há muito tempo" sem depender só do callback.

## (f) Estado atual do código

`boxwey/api/integrations/ifthenpay/client.py` — bom: timeout 15s (`TIMEOUT_SECONDS`),
`MbWayKey` redigido antes de persistir (`:83`), erro de rede/HTTP/JSON tratado
(`:66-77`). `descricao` não truncada. `EstadoPedidosJson` nunca usado — sem reconciliação.

`bookwey` não usa MB WAY v1 direto — usa EuPago para MB WAY (ver `eupago-mbway.md`) e
ifthenpay só via PINPAY (`ifthenpay-pinpay.md`).

## (g) Delta a corrigir

- Nada no v1 em si — está correto e em produção. Ver `ifthenpay-callbacks.md` para o delta
  real (vocabulário de estado do callback, resposta a estado desconhecido).
- `descricao` > 50 chars: truncar defensivamente no SDK independentemente do que a ifthenpay
  fizer — é grátis e elimina uma classe de falha.
- Backlog (fora desta migração): avaliar migração para MB WAY v2 REST.

## (h) Fonte

[API MBWAY (Deprecated)](https://helpdesk.ifthenpay.com/en/support/solutions/articles/79000086376-api-mbway-deprecated-) ·
[Documentação técnica (índice)](https://helpdesk.ifthenpay.com/en/support/solutions/folders/79000059075) ·
[docs.ifthenpay.com](https://www.ifthenpay.com/docs/en/)
