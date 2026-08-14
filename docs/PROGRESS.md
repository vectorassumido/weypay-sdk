# Estado de execução

Lido no início de cada iteração pela skill `weypay-phase`. Formato: uma entrada por passo
concluído (mais recente no topo), mais o estado corrente.

## Estado corrente

- **Fase:** 0a **concluída**. Próxima: 0b (verificar contra a sandbox tudo o que está ⚠️ em
  `docs/OPEN-QUESTIONS.md`) — ver `docs/migration/00-setup.md`.
- **Próximo passo:** criar `venv`, instalar `.[dev,sibs]`, escrever os scripts de
  `tests/manual/` para as questões #1-7 de `docs/OPEN-QUESTIONS.md` e correr contra a
  sandbox EuPago / conta de teste ifthenpay com as credenciais já fornecidas.
- **Bloqueios abertos:** nenhum.
- **Modo:** trabalho interativo (não `/loop`) nesta sessão.

## Incidentes evitados

### 2026-08-14 — cwd persistido apontava para `boxwey-serverless/api`
Uma verificação de `seed.py` usou `cd /home/chrisdo/projects/boxwey-serverless/api && ...`
para inspecionar o comando `seed`. O `cd` persistiu no shell entre chamadas de Bash (o
comportamento documentado da ferramenta), e o `git add -A && git commit` seguinte correu
**nesse diretório**, não em `weypay-sdk`. Sem dano: `git add -A` ali não encontrou nada para
stage (`docs/LOCAL-TESTING.md` vive numa árvore completamente separada), o commit falhou com
"nothing to commit", e o `git log` do `boxwey-serverless` ficou idêntico ao `origin/main`.
**Correção de hábito, daqui em diante**: todo o comando `git` deste projeto leva
`cd /home/chrisdo/projects/weypay-sdk &&` explícito no mesmo comando — nunca depender do
diretório persistido entre chamadas de Bash quando a chamada envolve git.

## Log

### 2026-08-14 — Fase 0a, passo 1: esqueleto do repo
- `git init` em `/home/chrisdo/projects/weypay-sdk`, branch `main`.
- `pyproject.toml` (Python ≥3.12, `requests` base, extras `ifthenpay`/`eupago` vazios,
  `sibs` com `cryptography`, `dev` com `pytest`/`responses`/`ruff`/`mypy`/`types-requests`).
- `.gitignore` a excluir `.env*`, chaves, caches — sem exceções para segredos.
- `README.md`, `CHANGELOG.md`.
- Commit `e284c09`.
- Nada instalado no sistema; nenhum `venv` criado ainda.

### 2026-08-14 — Fase 0a, passo 2: skill `weypay-phase`
- Criada em `/home/chrisdo/.claude/skills/weypay-phase/SKILL.md`: protocolo de arranque por
  iteração, gates, as 9 restrições invioláveis, marcação ✅/⚠️, e critério de fecho (`REPORT.md`
  + parar antes da Fase 4).

### 2026-08-14 — Fase 0a, passos 3-9: documentação completa
- `docs/providers/`: `ifthenpay-mbway.md`, `ifthenpay-pinpay.md`, `ifthenpay-callbacks.md`,
  `eupago-mbway.md`, `eupago-pix.md`, `eupago-status.md`, `eupago-webhooks.md`,
  `sibs-spg.md`, `sibs-marketplace.md` — 9 ficheiros, cada afirmação marcada ✅/⚠️.
  Discrepâncias reais encontradas e registadas (não corrigidas ainda): endpoint EuPago legado
  `/clientes/rest_api/multibanco/info` vs o documentado `/multibanco/info`; `successUrl`/
  `failUrl`/`backUrl` enviados no PIX sem constarem da spec; três hosts SIBS incompatíveis
  entre fontes oficiais; vocabulário de estado do callback ifthenpay por confirmar.
- `docs/ARCHITECTURE.md`, `ENVIRONMENTS.md`, `SECURITY.md` (9 regras), `OPEN-QUESTIONS.md`
  (14 itens, priorizados por resolúvel-na-0b vs precisa-do-utilizador vs bloqueado-por-SIBS).
- `docs/LOCAL-TESTING.md`: 3 níveis por projeto, comandos exatos a partir dos README/CLAUDE.md
  reais (não inventados) de `bookwey-serverless` e `boxwey-serverless`.
- `docs/migration/00-setup.md` a `05-sibs.md`: 6 guiões, cada um com pré-condições, passos,
  testes a acrescentar, comando de verificação e reversão. `04` e `05` documentados mas
  explicitamente fora do âmbito autónomo.
- `docs/PLAN.md`: cópia do plano aprovado pelo utilizador.
- Commits: `084aee3` (providers), `47b76b6` (transversais), `fb76f54` (LOCAL-TESTING).
- Quase-incidente registado acima (cwd persistido) — sem dano, hábito corrigido.
- Nada instalado além do que já estava no sistema (Python 3.12.12, git 2.34.1, ambos
  pré-existentes). Nenhum `venv` criado ainda — fica para o primeiro passo da Fase 0b.

## Regras de retoma

1. Ler o "Estado corrente" acima antes de tudo.
2. Se `Bloqueios abertos` não estiver vazio, resolver ou contornar antes de avançar a fase.
3. Cada passo termina com: gates verdes (ou falha registada) → commit no SDK → esta entrada
   atualizada. Nunca avançar de passo sem as três coisas.
4. Se algo aqui contradisser `docs/PLAN.md`, o `PLAN.md` é que se corrige — este ficheiro é o
   registo do que aconteceu, não a fonte da decisão.
