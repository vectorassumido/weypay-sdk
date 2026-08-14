# 02 — `boxwey`: remover o shim, corrigir os bugs confirmados, ganhar auditoria

Ao contrário de `01`, este passo **muda comportamento deliberadamente** — cada mudança tem um
teste novo que a prova.

## Pré-condições

- `01-boxwey-adopt.md` concluído e verde — ✅ feito em 2026-08-14, 209/209 testes.
- `docs/OPEN-QUESTIONS.md` #5 e #6 (ifthenpay: `descricao` > 50 chars, vocabulário de
  `[ESTADO]`) resolvidas na Fase 0b — ou explicitamente adiadas com nota do porquê, se a Fase
  0b não conseguiu confirmá-las. **Ambas ficaram adiadas** — #5 não bloqueia (o SDK já trunca
  sempre, independentemente da resposta real da ifthenpay); #6 depende do backoffice do
  utilizador. Ver `docs/OPEN-QUESTIONS.md` §"Número de teste em reserva".

**Nota herdada de `01`**: o `client.py` do `boxwey` não foi tocado na Fase 1 (conflito real
com `ClientTests`, que faz `@patch("integrations.ifthenpay.client.requests.post")`) — fica
todo para aqui. Quando `client.py` for apagado, **`ClientTests` (3 testes) também é apagada**
— não editada, apagada por completo, porque o seu sujeito (a chamada `requests.post` dentro de
`client.py`) deixa de existir. A cobertura equivalente já existe em
`weypay-sdk/tests/providers/test_ifthenpay_mbway.py` desde a Fase 0c — isto é uma remoção
justificada de teste redundante, não uma perda de cobertura.

## Ficheiros tocados

- `boxwey-serverless/api/events/services/payments.py` — `initiate_payment` chama o SDK
  diretamente.
- `boxwey-serverless/api/integrations/ifthenpay/client.py` — **apagado**.
- `boxwey-serverless/api/integrations/ifthenpay/views.py` — resposta a estado desconhecido.
- `boxwey-serverless/api/public_api/views.py:150-155` — tratamento de timeout.
- `boxwey-serverless/api/integrations/models.py` — **novo**, `GatewayCallLog`.
- `boxwey-serverless/api/integrations/admin.py` — **novo**, read-only.
- `boxwey-serverless/api/core/phone.py:27-31` — resolver `pt_national_digits` morto.
- Migration nova para `GatewayCallLog`.

## Passos

1. `initiate_payment` (`events/services/payments.py`) passa a chamar
   `weypay.providers.ifthenpay.mbway.request_payment(...)` diretamente; apagar `client.py` e
   `MbwayPaymentResult`.
2. `views.py:91` — estado desconhecido no callback deixa de devolver `HTTP 400`: passa a
   `PaymentStatus.UNKNOWN`, regista via `GatewayCallLog`, responde `200`. **Não** mapear
   `STATUS_REFUNDED`/`STATUS_DECLINED` para além do que a Fase 0b confirmou — se ficou por
   confirmar, esses ramos ficam marcados "não verificado" no código (comentário + log), não
   silenciosamente ativos.
3. `PaymentIndeterminate` (do SDK, em `ReadTimeout`) faz `initiate_payment` devolver a order
   em `PENDING`, não `FAILED` — `public_api/views.py:150-155` deixa de tratar timeout como
   falha terminal. `expire_orders` já cobre o caso de nunca se resolver.
4. `descricao` truncada a 50 caracteres antes de sair (`f"{event.name} — {n} bilhete(s)"[:50]`)
   — defensivo, independente do que a Fase 0b tiver confirmado sobre o comportamento da
   ifthenpay.
5. `GatewayCallLog`: ~10 colunas espelhando `weypay.types.GatewayCall` (`correlation_id`,
   `provider`, `operation`, `url`, `http_status`, `duration_ms`, `request` JSON, `response`
   JSON, `outcome`, `occurred_at`), escrito em `initiate_payment` e no webhook. Admin
   `readonly_fields = "__all__"`.
6. `core/phone.py:27-31` — `pt_national_digits` não tem nenhuma chamada no repo (confirmado
   por `grep`). Usar (se `nrtlm` precisar de formato nacional em vez de E.164 — confirmar
   contra `docs/providers/ifthenpay-mbway.md`, que não documenta o formato esperado) ou apagar.

## Testes a acrescentar

- `estado` desconhecido no callback → `HTTP 200`, order inalterada, `GatewayCallLog` criado
  com `outcome="unknown_status"`.
- `requests.ReadTimeout` na criação → order fica `PENDING`; `expire_orders` a apanha depois de
  `PENDING_ORDER_TTL`.
- `descricao` de 80 caracteres → o payload enviado tem exatamente 50.
- `GatewayCallLog.request`/`.response` nunca contêm o valor de `MbWayKey`/`itp_callback_key`
  em claro — assert de string sobre o JSON persistido.

## Comando de verificação

```bash
cd /home/chrisdo/projects/boxwey-serverless/api && source venv/bin/activate
python manage.py makemigrations --check --dry-run   # confere que a migration foi gerada
python manage.py test
```

## Reversão

`git status` em `boxwey-serverless` (nada commitado — regra 1). `git checkout --` nos
ficheiros existentes tocados; apagar `integrations/models.py`, `integrations/admin.py` e a
migration nova (ficheiros não rastreados, `git clean -n` primeiro para confirmar a lista antes
de qualquer remoção).
