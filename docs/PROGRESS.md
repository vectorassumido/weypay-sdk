# Estado de execução

Lido no início de cada iteração pela skill `weypay-phase`. Formato: uma entrada por passo
concluído (mais recente no topo), mais o estado corrente.

## Estado corrente

- **Fase:** 0a — repositório e documentação
- **Próximo passo:** escrever `docs/providers/ifthenpay-mbway.md`
- **Bloqueios abertos:** nenhum
- **Modo:** trabalho interativo (não `/loop`) nesta sessão

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

## Regras de retoma

1. Ler o "Estado corrente" acima antes de tudo.
2. Se `Bloqueios abertos` não estiver vazio, resolver ou contornar antes de avançar a fase.
3. Cada passo termina com: gates verdes (ou falha registada) → commit no SDK → esta entrada
   atualizada. Nunca avançar de passo sem as três coisas.
4. Se algo aqui contradisser `docs/PLAN.md`, o `PLAN.md` é que se corrige — este ficheiro é o
   registo do que aconteceu, não a fonte da decisão.
