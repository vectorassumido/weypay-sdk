# 00 — Setup do core (Fase 0b + 0c)

Fecha a Fase 0a e prepara o terreno antes de tocar em qualquer projeto consumidor.

## Pré-condições

- `docs/` completo (Fases 0a-1 a 0a-3 concluídas, `docs/PROGRESS.md` atualizado).
- Credenciais de sandbox EuPago + conta de teste ifthenpay disponíveis (fornecidas pelo
  utilizador, vivem nos `.env` dos projetos consumidores — nunca aqui).

## Passos — Fase 0b (observação)

1. `python3 -m venv venv && source venv/bin/activate && pip install -e ".[dev,sibs]"`.
2. Escrever scripts descartáveis em `tests/manual/` para cada item da tabela em
   `docs/OPEN-QUESTIONS.md` #1-7 — um script por chamada, sem lógica além de
   "chamar → imprimir a resposta crua → gravar em `docs/observed/<nome>.json`".
3. Correr cada script à mão, uma vez, contra a sandbox/conta de teste real.
4. Para cada resultado: atualizar o `docs/providers/*.md` correspondente (⚠️ → ✅, ou corrigir
   a afirmação se a observação contradisser o que estava escrito), remover a linha de
   `OPEN-QUESTIONS.md`, e copiar a resposta para `docs/observed/` como fixture candidata do
   transporte `FAKE`.
5. Se alguma observação contradisser uma decisão do `docs/PLAN.md` (não só de um `providers/*.md`),
   corrigir o `PLAN.md` também, com nota do porquê.

## Passos — Fase 0c (core + ifthenpay)

1. `src/weypay/money.py`, `errors.py`, `types.py`, `redaction.py` — ver `docs/ARCHITECTURE.md`
   para as assinaturas exatas.
2. `src/weypay/http.py` — transporte com timeout explícito, `Environment`, o modo `FAKE` a ler
   as fixtures de `docs/observed/` (mais os exemplos oficiais para o que a Fase 0b não cobriu).
3. `src/weypay/providers/ifthenpay/mbway.py` + `pinpay.py` + `callback.py`
   (`CallbackMapping` configurável — ver `docs/providers/ifthenpay-callbacks.md`).
4. `tests/test_money.py`, `test_http.py`, `test_redaction.py`, `test_isolation.py`
   (`providers/<x>/` nunca importa `providers/<y>/`).
5. `tests/providers/test_ifthenpay_mbway.py` — porta os 11 testes de webhook de
   `boxwey/api/integrations/ifthenpay/tests.py:117-195` para `responses`, sem Django. Mais um
   teste por código numérico oficial da tabela síncrona (`docs/providers/ifthenpay-mbway.md`).
6. Gates: `ruff check . && ruff format --check . && mypy . && pytest`.
7. Tag `v0.1.0.dev0` → quando os gates passarem de forma estável, `v0.1.0` (sem publicar
   remote — ver restrição 2).

## Testes a acrescentar (além dos portados)

- `Environment.FAKE` não abre socket (mock que falha se `socket.socket` for invocado).
- `Environment.PRODUCTION` recusa uma credencial com padrão de chave de teste conhecido.
- `Environment.SANDBOX` na ifthenpay levanta `ConfigurationError` sem
  `acknowledge_no_sandbox=True`.
- `redact()` não deixa nenhum valor de segredo sobreviver, mesmo em dict aninhado ou lista.

## Comando de verificação

```bash
cd /home/chrisdo/projects/weypay-sdk && source venv/bin/activate
ruff check . && ruff format --check . && mypy . && pytest -q
```
Todos verdes, `docs/OPEN-QUESTIONS.md` #1-7 fechadas ou explicitamente adiadas com razão.

## Reversão

Sem impacto fora do próprio repo do SDK — nenhum projeto consumidor foi tocado ainda. Reverter
é `git reset` dentro de `weypay-sdk` (nunca `--hard` sem stash prévio) ou simplesmente não
avançar para `01-boxwey-adopt.md`.
