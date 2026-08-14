# Segurança e auditoria

Nove regras. Cada uma corrige um defeito real e presente num dos dois projetos — nada aqui é
especulativo, e nada aqui é decorativo: cada regra tem um teste que a comprova.

**Contexto que enquadra tudo isto**: `bookwey-serverless` e `boxwey-serverless` estão em
produção, a receber pagamentos reais, hoje. Estas regras corrigem risco latente — não
significam que o sistema atual esteja avariado. Nenhuma delas se aplica sem teste que mostre
que o comportamento observável não piora.

## As nove regras

1. **Retry nunca numa operação de criação de pagamento.**
   `ConnectionError` (o pedido nunca saiu) → `GatewayUnavailable`, seguro reagir como falha.
   `ReadTimeout` (não se sabe se chegou) → `PaymentIndeterminate`, e a aplicação **não pode**
   tratar isso como pagamento falhado — hoje o `boxwey` marca `FAILED` (estado sem saída na
   sua state machine) num timeout em que o push MB WAY pode perfeitamente já ter disparado no
   telefone do comprador. Só operações de **leitura** (`get_status`) fazem retry: 2
   tentativas, backoff exponencial com jitter, só em erro de ligação e 5xx, nunca em 4xx.

2. **Timeouts sempre explícitos.** `(connect=5, read=15)` por omissão. O `bookwey` não tem
   nenhum timeout em nenhuma das 6 chamadas de `requests.post` em `utils.py` — um gateway
   pendurado segura o pedido HTTP até ao corte dos 60s do Cloud Run, gastando o tempo de
   resposta inteiro à espera de um socket que talvez nunca responda.

3. **Redação na fronteira do SDK, não na aplicação.** `GatewayCall.request`/`.response` saem
   já redigidos — a aplicação persiste às cegas, sem ter de saber quais campos são segredo em
   cada provider. Generaliza o `{**payload, "MbWayKey": "***"}` manual já existente no
   `boxwey`, e elimina o `print(payload)`/`print(data)` do `bookwey`
   (`utils.py:210-211,215,288,292,356,360,408,412,447,451`), que hoje despeja `externKey` de
   beneficiários de split e respostas completas do gateway para stdout sem qualquer filtro.

4. **`Decimal` ponta-a-ponta.** `Money` formata a string exata que cada gateway espera (a
   ifthenpay exige separador `.`); acabam os `float(reservation_value)` do `bookwey` num
   caminho onde um erro de arredondamento binário é dinheiro real, não um detalhe estético.

5. **Comparação em tempo constante** de toda chave/segredo de callback, sempre —
   `hmac.compare_digest` / `django.utils.crypto.constant_time_compare`. O `boxwey` já o faz
   para a `chave` ifthenpay; a regra generaliza-o a `chave_api` (EuPago) e `X-Signature`
   (EuPago 2.0) quando forem adotados.

6. **Um estado desconhecido no callback nunca devolve 4xx ao gateway.** Mapeia para
   `PaymentStatus.UNKNOWN`, regista em auditoria, responde 200. Devolver 400 (como o `boxwey`
   faz hoje em `views.py:91`) só desencadeia os "até 13" retries documentados da ifthenpay,
   sem que nada mude do lado da aplicação — é retrabalho puro, potencialmente perigoso se um
   estado de sucesso legítimo cair nesse ramo por um vocabulário mal mapeado (ver
   `docs/providers/ifthenpay-callbacks.md`).

7. **Verificar sempre assinatura/chave + referência + valor + moeda.** Onde o esquema de
   verificação do gateway for fraco ou a chave estiver a ser ignorada (caso do `bookwey`
   hoje — ver Fase 4), **reconciliar contra o gateway** antes de confirmar em vez de confiar
   cegamente no callback.

8. **Auditoria: uma tabela `GatewayCallLog` por projeto**, escrita tanto na iniciação do
   pagamento como na receção do webhook, read-only no admin. Persiste o `GatewayCall` do SDK
   tal e qual — já redigido, nada a filtrar do lado da aplicação. Hoje o `bookwey` não tem
   nada disto; o `boxwey` tem só `simple_history` na `Order`, que regista mudanças de estado
   mas não as chamadas HTTP em si.

9. **Idempotência é responsabilidade da aplicação, com trava explícita.** `dedupe_key`
   estável (a referência do gateway) + unique index + `select_for_update` ao aplicar a
   transição. Nenhum dos dois projetos tranca a linha da order/payment hoje — dois callbacks
   simultâneos para a mesma referência podem aplicar-se duas vezes antes que o primeiro
   `save()` complete.

10. **Nunca disparar uma notificação push a um número de telefone não fornecido
    explicitamente para esse fim.** Descoberta durante a Fase 0b: a chamada de *criação* de um
    pagamento MB WAY (EuPago `mbway/create`/`split-payments/mbway`, ifthenpay `SetPedidoJson`)
    dispara o push de imediato, sem esperar confirmação — ao contrário do PIX, que só gera uma
    referência/QR sem contactar ninguém. Adivinhar ou inventar um número arrisca notificar uma
    pessoa real e desconhecida. Regra permanente para qualquer teste automatizado contra estes
    gateways: só números fornecidos pelo utilizador para esse fim exato; na falta deles, testar
    só o que é seguro (respostas de erro com número deliberadamente inválido, ou métodos que não
    envolvem push — PIX, Multibanco, consulta de estado).

    **2026-08-14**: existe um número de teste real, fornecido pelo utilizador, guardado só em
    `.env.manual` (nunca em ficheiro rastreado). Condições estritas do próprio utilizador: não
    pode reagir a nenhum push até regressar, usar só se uma fase ficar genuinamente bloqueada
    sem isso, no máximo uma chamada, nunca repetida. Ver `docs/OPEN-QUESTIONS.md` §"Número de
    teste em reserva" para a avaliação de quando (não) usar.

## O que fica deliberadamente de fora

Registry de plugins, cliente async, pydantic, ABCs de provider (um `Protocol` de tipagem
chega), outbox/event bus, encriptação de credenciais dentro do SDK (é responsabilidade de
cada aplicação, com a sua própria política de secrets), circuit breaker. Cada um destes
resolveria um problema que nenhum dos dois consumidores tem hoje.

## Modelo de ameaça dos callbacks — o resumo por gateway

| Gateway | Mecanismo de verificação | Estado real (antes desta migração) |
|---|---|---|
| ifthenpay | Chave anti-phishing (segredo partilhado, tempo constante) + verificação de valor | `boxwey`: correto. `bookwey`/PINPAY: **inexistente** — confirma sem verificar nada |
| EuPago 1.0 | `chave_api` (⚠️ inferido, não documentado como mecanismo de segurança — ver `providers/eupago-webhooks.md`) | `bookwey`: **ignorado por completo** |
| EuPago 2.0 | HMAC-SHA256 em `X-Signature`, verificável de facto | Não adotado por nenhum projeto ainda |
| SIBS | AES-256-GCM (confidencialidade + integridade via tag de autenticação) | Não implementado — Fase 5 |

A falha mais grave hoje em produção não está no protocolo de nenhum gateway — está em dois
pontos do `bookwey` que **não usam** o mecanismo de verificação disponível:
`api/services/payments.py:11-19` (callback público sem nenhuma verificação, confirma pela
existência de um UUID de `Schedule`) e `:26-27` (`check_payment_status` confirma qualquer
pagamento `pinpay` sem contactar a ifthenpay). Ambas corrigidas na Fase 4 — fora do âmbito
autónomo, porque mudam a semântica de confirmação de um sistema em produção e dependem de
configuração no backoffice da ifthenpay que só o utilizador pode fazer.
