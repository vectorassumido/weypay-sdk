# 01 — `boxwey` adota o SDK, sem alteração de comportamento

**Critério de aceitação único**: `python manage.py test` verde **sem editar um único teste
existente**. Se isso não for possível sem editar um teste, o passo está mal desenhado — parar
e reportar em `docs/PROGRESS.md`, não forçar.

## ✅ Executado em 2026-08-14 — âmbito ajustado por conflito real encontrado

O `client.py` do `boxwey` **não foi tocado nesta fase** — só `views.py`. Motivo, descoberto ao
implementar (não deduzido antecipadamente): `integrations/ifthenpay/tests.py::ClientTests`
faz `@patch("integrations.ifthenpay.client.requests.post")` — um detalhe de implementação. Um
shim que delegasse para `weypay.providers.ifthenpay.mbway` não precisaria de importar
`requests` dentro de `client.py`, e o alvo do mock deixaria de existir, quebrando 3 testes por
um motivo estrutural, não por mudança de comportamento. Regra do próprio plano ("se não for
possível sem editar um teste, o passo está mal desenhado — parar e reportar") aplicada: em vez
de editar esses 3 testes ou inventar uma solução híbrida que não adota de facto o transporte
do SDK, adiou-se o `client.py` inteiro para a Fase 2 — que já planeava **apagar** `client.py`
por completo (`initiate_payment` passa a chamar o SDK diretamente), altura em que
`ClientTests` também é removida, com a cobertura equivalente já a existir em
`weypay-sdk/tests/providers/test_ifthenpay_mbway.py` desde a Fase 0c. Não há shim intermédio
a criar e depois a apagar — simplificação genuína, não um adiamento por preguiça.

O que **foi** feito: `views.py` passou a usar `weypay.providers.ifthenpay.callback` — as
funções granulares `verify_key`/`verify_amount`/`parse_status` (não `verify_and_parse` de uma
vez só), porque o webhook devolve códigos HTTP diferentes por tipo de falha (403 chave
inválida, 400 valor divergente, 400 estado desconhecido) e um único
`WebhookVerificationError` genérico não os distingue sem parsing de mensagem — ver o commit
`7645f9b` no SDK, que expôs essas funções exatamente por causa disto.

**Resultado**: `python manage.py test` → **209 testes, `OK`**, idêntico ao baseline
pré-mudança (também 209, `OK`). Zero testes editados. `ruff`/`mypy` do projeto inteiro também
verdes. Ficheiro tocado em `boxwey-serverless`: só `integrations/ifthenpay/views.py`, não
commitado (regra 1).

## Pré-condições

- `docs/migration/00-setup.md` concluído, `weypay` com gates verdes.
- `boxwey-serverless/api` com suite de testes atual verde (`python manage.py test`), para ter
  uma baseline antes de mexer. **Baseline real registada**: 209 testes, `OK`.

## Ficheiros tocados (execução real)

- `boxwey-serverless/api/integrations/ifthenpay/views.py` — passa a usar
  `weypay.providers.ifthenpay.callback.verify_key`/`verify_amount`/`parse_status`.
- **`client.py` não tocado** — ver "✅ Executado" acima para o porquê. Fica para
  `02-boxwey-cleanup.md`, que já planeava apagá-lo por completo.
- `requirements.txt` **não tocado** — o SDK foi instalado só via
  `pip install -e /home/chrisdo/projects/weypay-sdk` no venv local, sem editar o ficheiro (uma
  entrada `-e <caminho local>` só funcionaria nesta máquina; melhor deixar `requirements.txt`
  limpo até haver uma tag/remote real a apontar, o que fica para quando o utilizador decidir
  publicar o SDK).

**Nada mais muda.** `events/services/payments.py`, `events/services/orders.py`, os modelos, os
testes — tudo fica exatamente como está (confirmado: 209/209, zero editados).

## Passos (como correu de facto)

1. `pip install -e /home/chrisdo/projects/weypay-sdk` no venv do `boxwey`.
2. Descoberto o conflito com `ClientTests` (ver acima) — decisão de não tocar `client.py`.
3. `views.py` reescrito com as funções granulares do SDK, preservando os códigos HTTP exatos
   por tipo de falha.
4. `mypy` do `boxwey` falhou com `import-untyped` para `weypay` — faltava o marcador
   `py.typed` (PEP 561) no SDK. Corrigido no SDK (`ce535f8`), sem precisar de reinstalar.
5. `ruff`, `mypy`, `python manage.py test` — todos verdes, 209/209.

## Testes a acrescentar

Nenhum do lado do `boxwey` — preservador de comportamento, confirmado (209/209, zero
editados). Do lado do SDK, 9 testes novos para `verify_key`/`verify_amount`/`parse_status`
(commit `7645f9b`), já contabilizados na Fase 0c/aqui.

## Comando de verificação

```bash
cd /home/chrisdo/projects/boxwey-serverless/api && source venv/bin/activate
python manage.py test
```
✅ Executado: **209 testes, `OK`** — idêntico à baseline.

## Reversão

`git diff` neste passo toca só `integrations/ifthenpay/views.py` em `boxwey-serverless/api` —
não commitado (regra 1). Reverter é `git checkout -- integrations/ifthenpay/views.py` dentro
de `boxwey-serverless` (confirmar `git status` antes — não há stash nem commit a perder,
porque nada foi commitado).
