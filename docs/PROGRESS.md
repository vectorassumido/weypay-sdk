# Estado de execução

Lido no início de cada iteração pela skill `weypay-phase`. Formato: uma entrada por passo
concluído (mais recente no topo), mais o estado corrente.

## Estado corrente

- **Fase:** 2 **concluída** — `client.py` apagado, `initiate_payment` chama o SDK
  diretamente, `estado` desconhecido no callback → 200 (não 400), `GatewayCallLog` novo
  (auditoria em criação e webhook), `core/phone.py` limpo. **209/209 testes, `OK`**.
- **Próximo passo:** Fase 3 — `docs/migration/03-bookwey-adopt.md`. Precisa primeiro de
  `providers/eupago/` (mbway, split, pix, status, callbacks) e
  `providers/ifthenpay/pinpay.py` já existe — só falta EuPago no SDK. Depois `bookwey-serverless`
  adota o transporte. Pré-condição do próprio guião: `docs/OPEN-QUESTIONS.md` #1-3
  já resolvidas na Fase 0b.
- **Bloqueios abertos:** nenhum para começar os providers EuPago no SDK (não tocam nenhum
  projeto consumidor). Reserva de número de teste real disponível (condições estritas — ver
  `docs/OPEN-QUESTIONS.md` §"Número de teste em reserva"), mas nenhuma fase autónoma depende
  dela hoje.
- **Modo:** `/loop` auto-ritmado, sessão contínua.

## Incidentes reais (não evitados — corrigidos depois de acontecerem)

### 2026-08-14 — credenciais de sandbox comitadas em claro em `docs/LOCAL-TESTING.md`
Na Fase 0a, ao escrever o guião de teste local, copiei os valores reais das credenciais que o
utilizador tinha colado na conversa (chave EuPago de sandbox, chaves de beneficiário,
`ITP_MBWAY_KEY`) diretamente para `docs/LOCAL-TESTING.md`, como "exemplo". Isso violou a regra
do próprio repositório ("O repo do SDK nunca contém uma credencial") e ficou commitado no
commit `fb76f54`. Um fragmento truncado da mesma chave também entrou em `docs/ENVIRONMENTS.md`
como exemplo de padrão (corrigido para um placeholder totalmente sintético).

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

### 2026-08-14 — crase na mensagem de commit interpretada pelo shell
Usei `` `responses` `` (Markdown, para destacar o nome de uma dependência) dentro de uma
mensagem de commit passada com `-m "..."`. O bash interpretou as crases como substituição de
comando (`responses` como comando inexistente), imprimiu `responses: command not found` no
stderr, e a palavra desapareceu do corpo do commit (`6a44613`): "sem Django, com . O
docstring..." em vez de "sem Django, com `responses`. O docstring...". Sem impacto em código,
segredos ou significado enganador — só uma palavra em falta numa frase. Não fiz `git commit
--amend` para corrigir, porque a regra de segurança geral é nunca reescrever commits sem
pedido explícito, mesmo por um motivo cosmético e mesmo num repo local sem remote.
**Hábito corrigido**: nunca usar crase nem `$()`/back-tick em mensagens de commit passadas
inline com `-m`; se precisar de destacar código na mensagem, usar aspas simples ou escrever a
mensagem para um ficheiro e usar `git commit -F`.

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

### 2026-08-14 — Fase 0c: core + provider ifthenpay completos (commits 5549857, e09383c, a7ba17d, 6a44613)
- **Core** (`5549857`): `money.py` (`Money`, rejeita `float`, quantize ROUND_HALF_UP,
  `to_gateway_string()`/`parse()`), `errors.py` (6 exceções), `types.py` (`PaymentStatus`,
  `Environment`, `GatewayCall`, `PaymentResult`, `WebhookEvent`), `redaction.py`. 17 testes.
- **Transporte** (`e09383c`, corrigido em `a7ba17d`): `http.py` — `perform_request()` nunca
  levanta por status code (o provider decide); `ConnectionError`→`GatewayUnavailable`,
  timeout→`PaymentIndeterminate` (nunca o inverso); `retry=True` só leitura, 2 tentativas,
  backoff+jitter, só ligação/5xx; `resolve_base_url()`/`GatewayEndpoints` com
  `acknowledge_no_sandbox`; `FakeResponseRegistry`/`Environment.FAKE` nunca abre socket
  (testado com monkeypatch). Correção **a7ba17d**: `redact_url_values` — encontrada ao
  desenhar o PINPAY, cujo segredo vai no path do URL, que `secret_keys` (só dicts) não apanhava.
- **Provider ifthenpay** (`6a44613`): `mbway.py` (porto fiel do client.py do boxwey — status
  sempre `PENDING` numa criação aceite, nunca interpreta `Estado` síncrono como confirmação),
  `pinpay.py` (valida `id` numérico ≤15 chars, `description` ≤200, `GATEWAY_KEY` redigida do
  URL), `callback.py` (`extract_reference()`/`verify_and_parse()` em duas fases porque a
  chave é por-tenant; `CallbackMapping` explícito; estado desconhecido → `UNKNOWN` sem
  levantar — correção da Fase 2, aplicada já no SDK, documentada como divergência intencional
  face ao HTTP 400 do código atual).
- 24 testes portados de `boxwey/api/integrations/ifthenpay/tests.py`, com nota explícita do
  que NÃO foi portado (efeitos de app — email, anular bilhetes, state machine) e porquê.
- `tests/test_isolation.py`: prova que providers nunca se importam entre si (hoje vacuamente
  verdadeiro, só há um provider).
- **65 testes no total, gates verdes** (`ruff`, `mypy --strict`, `pytest`).
- Nada instalado além do já registado na Fase 0b (mesmo venv).
- Dois incidentes cosméticos, sem impacto real, registados acima (fragmento de credencial
  residual em PROGRESS.md; crase interpretada pelo shell numa mensagem de commit).

### 2026-08-14 — Fase 1: `boxwey` adota o SDK (commits 7645f9b, ce535f8 no SDK; `views.py` por commitar no `boxwey`)
- **Baseline estabelecida primeiro**: `python manage.py test` no `boxwey` limpo →
  **209 testes, `OK`**. Guardada antes de tocar em qualquer ficheiro.
- SDK instalado em editable mode no venv do `boxwey`
  (`pip install -e /home/chrisdo/projects/weypay-sdk`) — nada global.
- **Conflito real encontrado, não deduzido**: `integrations/ifthenpay/tests.py::ClientTests`
  faz `@patch("integrations.ifthenpay.client.requests.post")`. Um shim de `client.py` a
  delegar para o SDK deixaria de importar `requests`, quebrando o alvo do mock em 3 testes —
  não por mudança de comportamento, por um motivo estrutural. Segui a regra do próprio plano
  ("se não for possível sem editar um teste, o passo está mal desenhado — parar e reportar"):
  **não toquei em `client.py`**. Fase 2 já planeava apagá-lo por completo — a decisão foi
  adiar para lá em vez de criar um shim intermédio que seria apagado a seguir.
- **SDK ganhou 3 funções granulares** (`verify_key`/`verify_amount`/`parse_status`, commit
  `7645f9b`) — descoberto que `views.py` devolve códigos HTTP diferentes por tipo de falha
  (403/400/400), que um único `WebhookVerificationError` genérico não distingue sem parsing
  de mensagem. `verify_and_parse` continua a existir, agora compondo estas três. 9 testes
  novos (74 no total no SDK).
- **`views.py` reescrito** para usar essas 3 funções, preservando exatamente os mesmos códigos
  HTTP e mensagens de log — único ficheiro tocado em `boxwey-serverless`, não commitado.
- **Encontrado e corrigido**: `mypy` do `boxwey` falhava com `import-untyped` para `weypay` —
  faltava o marcador `py.typed` (PEP 561). Corrigido no SDK (commit `ce535f8`); não precisou
  de reinstalar o editable install.
- **Resultado**: `python manage.py test` → **209 testes, `OK`**, idêntico à baseline, **zero
  testes editados**. `ruff`/`mypy` do `boxwey` inteiro também verdes.
- `docs/migration/01-boxwey-adopt.md` e `02-boxwey-cleanup.md` atualizados para refletir o
  âmbito real (ver "✅ Executado" no `01`).
- **Número de teste real recebido do utilizador**, em conversa, com condições estritas (não
  reagir até regressar; usar só se genuinamente bloqueante; no máximo uma chamada). Guardado
  só em `.env.manual` (nunca em ficheiro rastreado). Avaliação feita: **não usado** — nenhuma
  fase autónoma depende dele hoje. Ver `docs/OPEN-QUESTIONS.md` §"Número de teste em reserva",
  `docs/SECURITY.md` regra 10, e a skill `weypay-phase` restrição 10 (atualizadas as três).

### 2026-08-14 — Fase 2: `client.py` apagado, auditoria ganha (commit `8454b50` no SDK; `boxwey` por commitar)
- **SDK, commit `8454b50`**: `GatewayRejected` passou a levar o `GatewayCall` completo
  (`errors.py`), com `mbway.py`/`pinpay.py` a anexá-lo — necessário para o `GatewayCallLog`
  conseguir auditar também pedidos rejeitados, não só bem-sucedidos. 2 testes atualizados
  (74 no SDK, contagem inalterada — só passaram a verificar `.call`).
- **`boxwey`, ficheiros tocados** (nenhum commitado, regra 1):
  - `integrations/apps.py`, `integrations/models.py` (`GatewayCallLog`), `integrations/admin.py`
    (read-only), migration nova, `"integrations"` acrescentado a `INSTALLED_APPS` (não estava
    registada). Passo aditivo isolado, verificado com 209/209 antes de continuar.
  - `events/services/payments.py`: `initiate_payment` chama `weypay.providers.ifthenpay.mbway`
    diretamente. **Correção além do plano original**: `provider_reference`/`provider` gravados
    **antes** da chamada ao gateway — sem isto, um timeout perderia a referência e o objetivo
    de "PENDING sobrevive a timeout" ficaria sem efeito prático (nenhum webhook futuro
    conseguiria encontrar a order). `PaymentIndeterminate` apanhado aqui, nunca propaga.
  - `integrations/ifthenpay/views.py`: estado desconhecido → 200 (era 400); todo o callback
    (chave inválida, valor divergente, ou processado) escreve `GatewayCallLog`.
  - `public_api/views.py`: `except PaymentGatewayError` → `except (GatewayUnavailable,
    GatewayRejected)` — `PaymentIndeterminate` não aparece aqui porque nunca propaga.
  - `core/phone.py`: `pt_national_digits` apagada (zero chamadores). Formato de `nrtlm`
    **não alterado** — incerto qual o formato exato esperado, sem evidência de que o E.164
    atual esteja errado (funciona em produção), decisão de não mexer.
  - `integrations/ifthenpay/client.py` **apagado**. `ClientTests` (3 testes) removida —
    cobertura equivalente já existe no SDK desde a Fase 0c.
  - **Encontrado ao verificar, fora do plano original**: `public_api/tests/test_checkout.py`
    também tinha 2 testes a espiar `integrations.ifthenpay.client.requests.post` — não
    detetado na Fase 1 porque a procura por referências a `client.py` só foi feita
    sistematicamente agora. Corrigidos da mesma forma (alvo do patch →
    `weypay.http.requests.request`).
- **Resultado**: `ruff`/`mypy`/`makemigrations --check` limpos no `boxwey` inteiro;
  `python manage.py test` → **209/209, `OK`** (as 3 remoções de `ClientTests` e as 3 adições
  de testes de auditoria do webhook cancelam-se exatamente no total).
- `docs/migration/02-boxwey-cleanup.md` atualizado com "✅ Executado".
- Sem incidentes de segurança nesta fase — sweep de credenciais e do número de telefone
  limpo em ambos os repos antes do commit.

## Regras de retoma

1. Ler o "Estado corrente" acima antes de tudo.
2. Se `Bloqueios abertos` não estiver vazio, resolver ou contornar antes de avançar a fase.
3. Cada passo termina com: gates verdes (ou falha registada) → commit no SDK → esta entrada
   atualizada. Nunca avançar de passo sem as três coisas.
4. Se algo aqui contradisser `docs/PLAN.md`, o `PLAN.md` é que se corrige — este ficheiro é o
   registo do que aconteceu, não a fonte da decisão.
