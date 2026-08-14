# Estado de execução

Lido no início de cada iteração pela skill `weypay-phase`. Formato: uma entrada por passo
concluído (mais recente no topo), mais o estado corrente.

## Estado corrente

- **Fase:** 0b **concluída** (dentro do que é seguro fazer sozinho — ver regra de segurança
  nova abaixo). Próxima: 0c (core + ifthenpay) — ver `docs/migration/00-setup.md`.
- **Próximo passo:** `src/weypay/money.py`, `errors.py`, `types.py`, `redaction.py`, depois
  `http.py` com `Environment` e o transporte `FAKE` a ler `docs/observed/`.
- **Bloqueios abertos:** nenhum para a Fase 0c. Ficam em aberto (não bloqueiam) as questões
  #2/#5/#15 de `OPEN-QUESTIONS.md` — dependem de um número de telefone de teste do utilizador.
- **Modo:** `/loop` auto-ritmado, sessão contínua.

## Incidentes reais (não evitados — corrigidos depois de acontecerem)

### 2026-08-14 — credenciais de sandbox comitadas em claro em `docs/LOCAL-TESTING.md`
Na Fase 0a, ao escrever o guião de teste local, copiei os valores reais das credenciais que o
utilizador tinha colado na conversa (chave EuPago de sandbox, chaves de beneficiário,
`ITP_MBWAY_KEY`) diretamente para `docs/LOCAL-TESTING.md`, como "exemplo". Isso violou a regra
do próprio repositório ("O repo do SDK nunca contém uma credencial") e ficou commitado no
commit `fb76f54`. Um resto truncado (`demo-f2be-...`) também entrou em `docs/ENVIRONMENTS.md`
como exemplo de padrão.

**Descoberto e corrigido na Fase 0b**, ao fazer uma varredura (`grep`) antes de commitar os
scripts de observação — hábito que devia ter sido aplicado logo na Fase 0a. Correção: os dois
ficheiros passaram a usar placeholders (`<a tua chave de sandbox EuPago>`); os valores reais
vivem agora só em `.env.manual` (gitignored, nunca commitado, confirmado com
`git check-ignore`).

**O que fica por resolver, e não decidi sozinho**: os valores reais **continuam no histórico
git** dos commits `fb76f54` e `44258bc` (que reescrevia o mesmo ficheiro). Como o repo nunca
teve `git push` (regra 2) e não tem remote configurado, a exposição é local a esta máquina —
mas apagá-la do histórico exigiria reescrever commits (`rebase`/`filter-branch`), uma operação
destrutiva que as restrições invioláveis não cobrem explicitamente e que não vou fazer sem
pedido direto. **Recomendação para o utilizador**: antes de este repositório ganhar um remote
público, reescrever o histórico (`git rebase -i` ou recomeçar o repo do zero a partir do estado
atual) para que os commits antigos não sobrevivam — ou trocar as credenciais de sandbox por
precaução, já que passaram por git localmente. Sinalizado aqui com destaque para não passar
despercebido no relatório final.

**Hábito corrigido, daqui em diante**: antes de qualquer commit que toque `docs/`, correr
`grep` pelos valores conhecidos de credenciais (ver lista em `.env.manual`, nunca copiada para
aqui) sobre a árvore staged, não só confiar em nunca os ter escrito.

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

### 2026-08-14 — Fase 0b: venv + observação real contra a sandbox EuPago
- `venv` criado, `pip install -e ".[dev,sibs]"` — `requests 2.34.2`, `pytest 9.1.1`,
  `responses 0.26.2`, `ruff 0.16.3`, `mypy 2.3.0`, `types-requests`, `cryptography 50.0.0`.
  Tudo dentro do venv do projeto, nada global.
- **Descoberta nova, registada como regra permanente** (`SECURITY.md` #10, skill `weypay-phase`
  restrição 10): a criação de um pagamento MB WAY dispara o push de imediato, não só a
  confirmação — logo nunca testar isso com um número de telefone adivinhado. Limitou o que a
  Fase 0b conseguiu resolver sozinha.
- `.env.manual` criado (gitignored, confirmado com `git check-ignore`) com as credenciais de
  sandbox fornecidas pelo utilizador — nunca commitado.
- 3 scripts em `tests/manual/`, corridos uma vez cada contra `sandbox.eupago.pt`:
  - `observe_eupago_pix.py` — resolveu OPEN-QUESTIONS #3: `successUrl`/`failUrl`/`backUrl`
    aceites sem erro (`HTTP 201` idêntico com/sem).
  - `observe_eupago_status.py` — resolveu OPEN-QUESTIONS #1, **corrigindo uma suposição do
    `PLAN.md`**: o path legado que o `bookwey` usa devolve `estado` E `estado_referencia`; o
    endpoint documentado publicamente (`/multibanco/info`) devolve 404 nesta sandbox. O
    código do `bookwey` estava correto — não há bug de polling.
  - `observe_eupago_mbway_invalid_phone.py` — só testou número inválido por segurança (ver
    acima); confirma a forma do erro (`400 CUSTOMERPHONE_INVALID`), não resolve se `entity`
    vem numa criação bem-sucedida (fica ⚠️, dependente de número de teste do utilizador).
- Atualizados: `docs/providers/eupago-status.md`, `eupago-pix.md`, `eupago-mbway.md`,
  `docs/OPEN-QUESTIONS.md` (renumerado, 2 fechadas, 1 parcial, resto categorizado por
  dependência), `docs/PLAN.md` (3 correções onde a observação contrariou o texto original).
- **Incidente real corrigido** (ver secção acima): credenciais em claro em 2 ficheiros de
  Fase 0a, substituídas por placeholders; valores reais ficam só no histórico git local, sem
  remote — sinalizado ao utilizador, não resolvido sozinho (rescrever histórico é destrutivo).
- Gates: `ruff check` + `ruff format --check` + `mypy` verdes (após corrigir `pyproject.toml`
  — `ruff format` estava a tentar reformatar blocos de código dentro de `.md`, `extend-exclude
  = ["*.md"]` adicionado). `pytest` sem testes ainda (esperado — chegam na Fase 0c).
- Commit: ver `git log` — mensagem "Fase 0b: observação real contra a sandbox EuPago...".

## Regras de retoma

1. Ler o "Estado corrente" acima antes de tudo.
2. Se `Bloqueios abertos` não estiver vazio, resolver ou contornar antes de avançar a fase.
3. Cada passo termina com: gates verdes (ou falha registada) → commit no SDK → esta entrada
   atualizada. Nunca avançar de passo sem as três coisas.
4. Se algo aqui contradisser `docs/PLAN.md`, o `PLAN.md` é que se corrige — este ficheiro é o
   registo do que aconteceu, não a fonte da decisão.
