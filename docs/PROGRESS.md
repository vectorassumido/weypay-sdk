# Estado de execução

Lido no início de cada iteração pela skill `weypay-phase`. Formato: uma entrada por passo
concluído (mais recente no topo), mais o estado corrente.

## Estado corrente

- **Fase:** 3 **concluída** (passos 1-3; passo 4 deliberadamente adiado — ver Log).
  `bookwey-serverless` adota o transporte SDK para EuPago/PINPAY. **91/91 testes, `OK`**,
  idêntico à baseline.
- **Âmbito autónomo original (0a→3) terminado e revisto pelo utilizador ao regressar.**
- **2026-08-14 (regresso do utilizador) — política de commits nos consumidores mudou**: os
  diffs das Fases 1-2 (`boxwey-serverless`) e Fase 3 (`bookwey-serverless`), que tinham ficado
  por commitar (regra antiga), foram agora commitados numa branch dedicada
  `weypay-sdk-migration` em cada repo (`boxwey` commit `9da26b9`, `bookwey` commit `9815c84`),
  criada e commitada pelo utilizador interativamente — não pelo loop autónomo. `main` fica
  intocado em ambos. **Decisão explícita do utilizador**: doravante, o trabalho autónomo
  também pode commitar diretamente nesta branch (nunca em `main`, nunca `push`) — ver skill
  `weypay-phase` restrição 1, atualizada. Antes de continuar Fase 4/5 ou qualquer trabalho
  novo, confirmar sempre `git branch --show-current` é `weypay-sdk-migration` em cada
  consumidor antes de commitar.
- **Bloqueios abertos:** nenhum nas fases concluídas. Itens deliberadamente adiados, todos
  documentados: `providers/eupago/callback.py` (Fase 4), `Environment.FAKE` default em
  `bookwey`'s `development.py` (precisa de fixtures reais, quebraria testes existentes sem
  elas), Fase 4 (segurança `bookwey`) e Fase 5 (SIBS) por inteiro.
- **Modo:** interativo (utilizador presente). Ver `docs/REPORT.md` para o relatório completo
  da execução autónoma 0a→3.
- **2026-08-14 — pagamento sandbox real concluído com sucesso em `bookwey-serverless`**,
  incluindo confirmação como "paga" no backoffice EuPago. Pelo caminho, dois problemas reais
  encontrados e corrigidos (não hipotéticos — só apareceram com dinheiro/estado real):
  1. Bug no SDK: `status.py::ENDPOINTS` tinha `/api` a mais → toda consulta de estado 404.
     Corrigido (SDK commit `6740693`, `bookwey` commit `2782735` — `_eupago_status_base_url()`
     separado de `_eupago_base_url()`). Fecha a última ⚠️ real: `estado_referencia == "paga"`
     confirmado por observação direta.
  2. `adminCallback`/`eupago_api_callback` inalcançável (`localhost`) impede marcar a
     referência como paga no backoffice sandbox — não é bug de código, é requisito de
     configuração; documentado em `docs/LOCAL-TESTING.md` e `docs/providers/eupago-mbway.md`.
  Push real ao telemóvel nunca chega em sandbox — confirmado pelo utilizador como normal
  (mesmo no projeto pré-migração), não uma falha desta migração.
- **2026-08-14 — terceiro problema real, desta vez no EuroPix**: `verificar_pagamento` também
  404ava para pagamentos EuroPix, mesmo com o fix do `/api` acima. Causa diferente: `Payment.
  reference` guardava `numeric_id` (id local gerado antes da chamada à EuPago, necessário para
  `successUrl`), nunca substituído pela referência real que a EuPago devolve — bug presente
  também no `main` pré-migração, nunca detetado por falta de teste. Corrigido (`bookwey`
  commit `7ece22a`): `Payment.reference` passa a ser sempre a referência real; novo campo
  `Payment.client_reference` guarda o id local, usado só para `check_payment_status` encontrar
  o pagamento antes de a EuPago responder. Migration aditiva (`0002_payment_client_reference`,
  schema-only). 4 testes novos + suite completa (95/95) verde. Verificado com pagamento
  sandbox real: `Payment.reference="320787"` (EuPago), `client_reference="<id local>"`,
  `check_payment_status(client_reference)` resolve sem 404. Ver
  `docs/providers/eupago-pix.md`, `docs/OPEN-QUESTIONS.md` #19.
- **2026-08-15 — ifthenpay MB WAY validado no `boxwey-serverless` com um pagamento real de
  €0,01** (ifthenpay não tem sandbox — número do utilizador, autorizado e aceite por ele no
  telemóvel; ver `docs/SECURITY.md` regra 10). `initiate_payment()` funcionou sem alterações.
  Pelo caminho, implementada `get_order_status()` (`EstadoPedidosJSON`) — endpoint de
  reconciliação que nunca tinha sido portado em nenhum dos dois projetos. Três correções só
  descobertas por chamada real (a documentação estava errada nos três pontos): precisa de GET
  com querystring (não POST/JSON); o nome do método é `EstadoPedidosJSON`, todo maiúsculas
  (`EstadoPedidosJson` dá 500, o próprio erro revelou a grafia certa); a resposta tem dois
  `Estado` (o de topo é do pedido HTTP, o que importa é `EstadoPedidos[0].Estado`). Exigiu
  adicionar suporte a `params=` (query string) a `perform_request()` — única chamada do SDK
  que não vai no corpo. Confirmado `PaymentStatus.PAID` para o pagamento real. 4 testes novos
  (111/111 SDK verde). Ver `docs/providers/ifthenpay-mbway.md`, `docs/OPEN-QUESTIONS.md` #20.
- **2026-08-15 — caminho de recusa validado com uma recusa real**: segundo pagamento de
  €0,01, desta vez recusado deliberadamente no telemóvel. `EstadoPedidos[0].Estado == "020"`
  confirmado, mapeado para `PaymentStatus.DECLINED` em `get_order_status()` (antes caía em
  `UNKNOWN` como qualquer código não-"000"). Restantes códigos da tabela síncrona continuam
  ⚠️ não observados neste endpoint — não generalizado por dedução. 1 teste novo (112/112 SDK
  verde). Ver `docs/providers/ifthenpay-mbway.md`.
- **2026-08-15 — caminho de expiração validado deixando um pagamento expirar**: terceiro
  pagamento de €0,01, deixado passar sem aceitar nem recusar (janela real da app MB WAY do
  utilizador: ~4 min). `EstadoPedidos[0].Estado == "123"` ("Operação financeira não
  encontrada") — não há código dedicado a "expirado", a ifthenpay trata como transação
  inexistente. Mapeado para `PaymentStatus.EXPIRED`, com ressalva documentada sobre a
  ambiguidade teórica com um `IdPedido` inválido (não aplicável ao contrato de uso real desta
  função). 1 teste novo (113/113 SDK verde). Ver `docs/providers/ifthenpay-mbway.md`.

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

### 2026-08-14 — Fase 3 (parcial): providers EuPago no SDK (commits `1c0d423`, `baf76bb`)
- **`money.py`**: `to_gateway_number()` — exceção estreita e documentada a "nunca float"
  (a EuPago exige número JSON, não string; `json` da biblioteca padrão não serializa
  `Decimal`). Conversão só na fronteira de serialização, provada sem perdas por teste
  parametrizado até ao limite documentado da EuPago (99 999€). `docs/SECURITY.md` regra 4
  atualizada para deixar esta exceção explícita, não implícita.
- **`providers/eupago/`**: `mbway.py` (sem split — `entity` não preenchido, não confirmado
  nesta variante), `split.py` (`Beneficiary` dataclass, `externKey` redigido — corrige o bug
  original de `print(payload)` a despejar chaves de beneficiário), `pix.py`
  (`successUrl`/`failUrl`/`backUrl` aceites, confirmado em sandbox), `status.py` (path legado
  `/clientes/rest_api/multibanco/info`, `retry=True` por ser leitura).
- **Decisão de âmbito**: `providers/eupago/callback.py` **adiado para a Fase 4** — não é
  consumido por nada em Fase 3 (o `bookwey` não tem hoje um handler de webhook EuPago real, só
  o endpoint inseguro que a Fase 4 corrige), e escrevê-lo agora seria código não exercitado.
  A lista original em `docs/migration/03-bookwey-adopt.md` incluía-o; ajustado.
- 29 testes novos no SDK (103 no total), vários espelhando literalmente as respostas
  observadas em sandbox na Fase 0b (`docs/observed/eupago_*.json`) em vez de payloads
  inventados. `test_isolation.py` confirmado com 2 providers reais (antes só vacuamente
  verdadeiro com 1).
- **`bookwey-serverless` — preparação, nada tocado ainda**: SDK instalado em editable mode no
  venv. **Baseline estabelecida**: `python manage.py test` → **91 testes, `OK`**. Próximo
  passo real: o teste de tabela payload-antigo-vs-novo, depois a reescrita de
  `integrations/payments/utils.py`.
- Parei aqui deliberadamente — a reescrita de `utils.py` toca lógica de comissão e um modelo
  de produção real (`Merchant`) num terceiro codebase ainda não tocado nesta sessão; prefiro
  começá-la com orçamento fresco na próxima iteração, tal como fiz nas fronteiras 1→2 e 2→3.

### 2026-08-14 — Fase 3 fecha: `bookwey` adota o transporte (commit `396faad` no SDK; `bookwey` por commitar)
- **SDK, commit `396faad`**: `base_url: str | None` opcional acrescentado a
  `mbway.py`/`split.py`/`pix.py`/`status.py` — encontrado ao desenhar o rewrite: os providers
  resolviam sempre para o host canónico fixo, mas o `bookwey` guarda o URL exato por-merchant
  em dados reais de produção que podem divergir. 4 testes novos (107 no total).
- **Teste de tabela payload-antigo-vs-novo** corrido como script de verificação (não um teste
  permanente — compara código que ia ser apagado) antes de tocar em `utils.py`: para
  `0.10, 0.15, 19.99, 100.005, 33.33×3`, byte-a-byte idêntico em todos os casos que podem
  ocorrer de facto (todo `DecimalField` de dinheiro no `bookwey` já é 2dp,
  `calculate_commission_amount` já quantiza a cada passo). O único "diferente" (`100.005`) é
  teórico, e nesse caso `Money` é mais seguro (arredonda) que o `float()` antigo.
  Output completo em `docs/migration/03-bookwey-adopt.md`.
- **`bookwey`, ficheiros tocados** (nenhum commitado, regra 1):
  - `integrations/payments/utils.py`: as 5 funções (`criar_pagamento_com_split`,
    `criar_pagamento_europix`, `criar_pagamento_pinpay`, `verificar_pagamento`,
    `verificar_pagamento_mbway`) chamam o SDK; `calculate_commission_amount`,
    `create_staff_payment`, `pay_pagamento`, `send_merchant_monthly_summary_email`
    inalteradas. Mensagens de erro preservadas byte-a-byte
    (`GatewayRejected`/`GatewayUnavailable` reconvertidas para `Exception(...)` com o mesmo
    texto de sempre, para `booking.py` continuar a devolver a mesma `APIException`).
  - `core/models.py` + `backoffice/admin.py`: `Merchant.eupago_environment` aditivo.
  - `core/migrations/0002_...` (schema) + `0003_backfill_eupago_environment.py` (dados,
    `RunPython`, preenche a partir do parsing de `eupago_api_url`).
  - **Encontrado por varredura sistemática antes de tocar em qualquer ficheiro** (hábito das
    Fases 1/2, aplicado logo à partida desta vez): `api/tests/test_booking_client_phone_sync.py`
    tinha 2 testes a espiar `integrations.payments.utils.requests.post`. Adaptados (não
    apagados — testam um bug real de negócio, não implementação) para
    `@patch("weypay.http.requests.request")`.
- **Passo 4 do guião (`Environment.FAKE` default em `development.py`) — adiado, não
  implementado.** Motivo descoberto ao tentar: sem `fake_registry`/fixtures reais, FAKE
  levantaria `ConfigurationError` em qualquer tentativa de pagamento local, incluindo dentro
  dos próprios testes (o `bookwey` não tem settings module de teste separado — os testes
  correm sob `development.py`). Isso quebraria `test_booking_client_phone_sync.py` e qualquer
  teste futuro com `weypay.http.requests.request` mockado, já que em FAKE o pedido nunca
  chega a esse ponto. Construir fixtures reais agora seria scope creep (é o mesmo trabalho já
  pendente em `docs/LOCAL-TESTING.md`) — mesma categoria de adiamento que
  `providers/eupago/callback.py`.
- **`bookwey` não tem `ruff`/`mypy` configurados** neste checkout (sem `requirements-dev.txt`,
  ao contrário do `boxwey`) — `py_compile` usado como verificação de sintaxe mínima em
  substituição, já que instalar ferramentas novas seria fora do âmbito pedido.
- **Resultado**: `python manage.py test` → **91/91, `OK`**, idêntico à baseline.
  `makemigrations --check --dry-run` limpo.
- `docs/migration/03-bookwey-adopt.md` atualizado com "✅ Executado" e a nota do adiamento.
- Sem incidentes de segurança nesta fase — sweep de credenciais e do número de telefone
  limpo em ambos os repos antes do commit.
- **Fase 3 concluída. Âmbito autónomo (Fases 0a→3) cumprido — ver `docs/REPORT.md`.**

## Regras de retoma

1. Ler o "Estado corrente" acima antes de tudo.
2. Se `Bloqueios abertos` não estiver vazio, resolver ou contornar antes de avançar a fase.
3. Cada passo termina com: gates verdes (ou falha registada) → commit no SDK → esta entrada
   atualizada. Nunca avançar de passo sem as três coisas.
4. Se algo aqui contradisser `docs/PLAN.md`, o `PLAN.md` é que se corrige — este ficheiro é o
   registo do que aconteceu, não a fonte da decisão.
