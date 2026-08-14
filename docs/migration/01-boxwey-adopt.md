# 01 — `boxwey` adota o SDK, sem alteração de comportamento

**Critério de aceitação único**: `python manage.py test` verde **sem editar um único teste
existente**. Se isso não for possível sem editar um teste, o passo está mal desenhado — parar
e reportar em `docs/PROGRESS.md`, não forçar.

## Pré-condições

- `docs/migration/00-setup.md` concluído, `weypay` com gates verdes.
- `boxwey-serverless/api` com suite de testes atual verde (`python manage.py test`), para ter
  uma baseline antes de mexer.

## Ficheiros tocados

- `boxwey-serverless/api/requirements.txt` — acrescentar
  `weypay @ git+https://github.com/<org>/weypay-sdk@v0.1.0` (ou, enquanto não há remote
  público, `-e /home/chrisdo/projects/weypay-sdk` para desenvolvimento local — nunca commitar
  esse caminho local, só usar localmente).
- `boxwey-serverless/api/integrations/ifthenpay/client.py` — reduz-se a um shim.
- `boxwey-serverless/api/integrations/ifthenpay/views.py` — passa a usar `verify_and_parse`.

**Nada mais muda.** `events/services/payments.py`, `events/services/orders.py`, os modelos, os
testes — tudo fica exatamente como está.

## Passos

1. Instalar o SDK (editable, local, para já).
2. Reescrever `client.py` como shim: a assinatura pública `request_mbway_payment(...)` e o
   dataclass `MbwayPaymentResult` mantêm-se idênticos por fora; por dentro, chamam
   `weypay.providers.ifthenpay.mbway.request_payment` e traduzem `PaymentResult` de volta para
   `MbwayPaymentResult`. `PaymentGatewayError` continua a ser levantado nos mesmos casos.
3. Em `views.py:37-75`, substituir a leitura manual de `chave`/`referencia`/`estado`/`valor` e
   a comparação `constant_time_compare` por uma chamada a
   `weypay.providers.ifthenpay.callback.verify_and_parse(...)`, com o `CallbackMapping` default
   (que corresponde ao template real do `boxwey` — ver `docs/providers/ifthenpay-callbacks.md`).
   O resultado (`WebhookEvent`) alimenta a mesma lógica de dispatch que já existe
   (`order_service.mark_paid`/`mark_failed`/`refund_order`) — **sem mudar o que cada ramo faz**.
4. Correr `ruff`, `mypy`, e `python manage.py test`.

## Testes a acrescentar

Nenhum — este passo é preservador de comportamento por definição. Se surgir necessidade de um
teste novo para cobrir o shim, é sinal de que o shim não está a preservar comportamento e o
passo deve ser revisto, não avançado.

## Comando de verificação

```bash
cd /home/chrisdo/projects/boxwey-serverless/api && source venv/bin/activate
python manage.py test
```
Comparar a contagem de testes/falhas com a baseline da pré-condição — tem de ser idêntica.

## Reversão

`git diff` neste passo toca só 3 ficheiros em `boxwey-serverless/api` — não commitado (regra
1: sem commits em projetos consumidores). Reverter é `git checkout -- <os 3 ficheiros>` dentro
de `boxwey-serverless` (confirmar `git status` antes — não há stash nem commit a perder aqui,
porque nada foi commitado).
