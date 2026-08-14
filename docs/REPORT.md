# Relatório final — execução autónoma (Fases 0a → 3)

**Período**: 2026-08-14, sessão contínua em `/loop` auto-ritmado.
**Âmbito autorizado**: Fases 0a, 0b, 0c, 1, 2, 3. Fases 4 (segurança `bookwey`) e 5 (SIBS)
explicitamente fora do âmbito autónomo — exigem revisão presencial e configuração em
backoffices externos que só o utilizador pode fazer.
**Resultado**: âmbito cumprido por inteiro. `boxwey-serverless` (209/209 testes) e
`bookwey-serverless` (91/91 testes) adotam o SDK partilhado `weypay` para os fluxos de
pagamento ifthenpay/EuPago, com zero regressões medidas.

---

## O que foi feito, por fase

### Fase 0a — Repositório e documentação (commits `e284c09`…`44258bc`)
Repositório `weypay-sdk` criado do zero, com toda a documentação escrita **antes** de
qualquer código: especificação *verbatim* dos 3 gateways (ifthenpay, EuPago, SIBS) em
`docs/providers/`, arquitetura do core, modelo de ambientes, as regras de segurança
não-negociáveis, questões em aberto, guião de teste local, e um guião de migração por fase.
Skill `weypay-phase` criada para dar a cada iteração futura o protocolo de arranque e as
restrições invioláveis sem reconstituir contexto.

### Fase 0b — Verificação contra a sandbox real (commit `a5600e9`)
Com as credenciais fornecidas pelo utilizador, três scripts chamaram a sandbox EuPago real.
**Corrigiu uma suposição errada do plano**: o endpoint de consulta de estado que o `bookwey`
usa (`/clientes/rest_api/multibanco/info`, um path legado) devolve `estado_referencia` —
campo que eu tinha concluído (por dedução a partir da documentação pública, não observação)
que não existia. O código do `bookwey` estava correto; não havia bug nenhum aí.

**Descoberta de segurança permanente, registada como regra**: a criação de um pagamento
MB WAY dispara o push de imediato — não só a confirmação. Por isso nenhuma automação neste
projeto testou uma criação MB WAY com um número de telefone adivinhado; só o que era seguro
(PIX, respostas de erro com número deliberadamente inválido) foi exercitado.

### Fase 0c — Core do SDK + provider ifthenpay (commits `5549857`…`6a44613`, `71fdbcd`)
`Money`, hierarquia de erros, tipos (`PaymentStatus`, `Environment`, `GatewayCall`,
`PaymentResult`, `WebhookEvent`), transporte HTTP (timeout sempre explícito, retry só em
leitura, `Environment.FAKE` sem rede), e o provider ifthenpay completo (`mbway`, `pinpay`,
`callback`). 65 testes.

Correção encontrada a meio (`a7ba17d`): a `GATEWAY_KEY` da PINPAY vai no *path* do URL, que a
redação por chave de dicionário não apanhava — `redact_url_values` acrescentado.

### Fase 1 — `boxwey-serverless` adota o SDK (commits `7645f9b`, `ce535f8`, `f27b1cc`)
**Conflito real encontrado, não deduzido**: os testes existentes do `boxwey`
(`ClientTests`) espiavam `client.py`'s próprio `requests.post` — um shim delegando para o
SDK quebraria esse alvo de mock por um motivo estrutural, não por mudança de comportamento.
Segui a regra do próprio plano ("se não for possível sem editar um teste, o passo está mal
desenhado — parar e reportar"): reduzi o âmbito da Fase 1 a só `views.py` (usa
`verify_key`/`verify_amount`/`parse_status` do SDK), deixando `client.py` para a Fase 2, que
já planeava apagá-lo por completo.

Encontrado e corrigido: faltava o marcador `py.typed` (PEP 561) no SDK — o `mypy` do `boxwey`
tratava-o como *import-untyped*.

**Resultado: 209/209 testes, `OK`, zero testes editados** — idêntico à baseline.

### Fase 2 — `boxwey-serverless`: limpeza e auditoria (commits `8454b50`, `5a7faa9`)
`client.py` apagado por completo; `ClientTests` removida (cobertura equivalente já existia no
SDK). `initiate_payment` chama o SDK diretamente, com uma correção **além do que o guião
pedia**: a referência do pagamento passa a ser gravada **antes** da chamada ao gateway, não
depois — sem isto, um timeout perderia a referência e o objetivo de "deixar `PENDING` em vez
de `FAILED`" ficaria sem efeito prático (nenhum webhook tardio conseguiria encontrar a
marcação). Estado desconhecido no callback deixa de devolver `HTTP 400` (passa a `200` +
registo — evita os "até 13" retries da ifthenpay). `GatewayCallLog` novo (modelo + migration +
admin read-only), escrito na criação e no webhook.

**Encontrado por varredura, fora do plano original**: `public_api/tests/test_checkout.py`
tinha mais 2 testes a espiar `client.py`, não detetados na Fase 1.

**Resultado: 209/209 testes, `OK`**.

### Fase 3 — `bookwey-serverless` adota o transporte (commits `1c0d423`…`3974693`)
Providers EuPago escritos no SDK (`mbway`, `split`, `pix`, `status`) — vários testes espelham
literalmente as respostas reais observadas em sandbox na Fase 0b, não payloads inventados.
`Money.to_gateway_number()` acrescentado como exceção estreita e documentada a "nunca float"
(a EuPago exige número JSON, não string; a conversão é só na fronteira de serialização, nunca
em aritmética, provada sem perdas por teste).

**Encontrado ao desenhar o rewrite**: os providers resolviam sempre para o host canónico fixo
da EuPago, mas o `bookwey` guarda o URL exato por-merchant em dados reais de produção que
podem divergir — `base_url` opcional acrescentado a todos os providers EuPago para preservar
exatamente o host que cada merchant já tinha configurado.

Teste de tabela payload-antigo-vs-novo (obrigatório antes de trocar `float`→`Money`) corrido
como verificação: byte-a-byte idêntico para todos os valores que podem ocorrer de facto neste
codebase. As 5 funções de `integrations/payments/utils.py` reescritas para chamar o SDK,
preservando as mensagens de erro originais byte-a-byte. `Merchant.eupago_environment`
acrescentado (aditivo, com migration de dados que faz backfill sem mudar comportamento de
nenhum merchant existente).

**Encontrado por varredura sistemática, aplicada logo à partida desta vez** (hábito das duas
fases anteriores): `api/tests/test_booking_client_phone_sync.py` tinha 2 testes a espiar
`requests.post` dentro de `utils.py` — adaptados, não apagados (testam um bug real de
negócio, não um detalhe de implementação).

**Resultado: 91/91 testes, `OK`**, idêntico à baseline.

---

## Decisões tomadas sem supervisão

Cada uma abaixo é uma decisão de engenharia real, não uma escolha arbitrária — todas
documentadas em detalhe no `docs/PROGRESS.md`/`docs/migration/*.md` correspondente no
momento em que foram tomadas.

1. **Fase 1 do `boxwey` reduzida de âmbito** (não tocar `client.py`) por conflito real com
   `ClientTests`. Ver `docs/migration/01-boxwey-adopt.md`.
2. **`provider_reference` gravada antes da chamada ao gateway** em `initiate_payment`
   (`boxwey`), para o timeout→`PENDING` ter efeito prático real. Não estava explicitado no
   guião original, mas é necessário para o objetivo declarado funcionar.
3. **`GatewayRejected` passou a levar o `GatewayCall` completo** — extensão pequena ao SDK,
   necessária para auditar também pedidos rejeitados.
4. **`redact_url_values`** acrescentado ao transporte — segredos embutidos no path do URL
   (PINPAY) não eram apanhados pela redação por chave de dicionário.
5. **`base_url` opcional** acrescentado a todos os providers EuPago — preserva o URL exato
   por-merchant do `bookwey` em vez de forçar o host canónico fixo sobre dados reais de
   produção.
6. **`Money.to_gateway_number()`** — exceção estreita e documentada à regra "nunca float",
   necessária porque a EuPago exige número JSON e `json` da biblioteca padrão não serializa
   `Decimal`. Registada explicitamente em `docs/SECURITY.md` como não-reabertura da regra.
7. **`providers/eupago/callback.py` adiado para a Fase 4** — não é consumido por nada em
   Fase 3 (o `bookwey` não tem hoje um handler de webhook EuPago real).
8. **`Environment.FAKE` default em `bookwey`'s `development.py` adiado** — forçá-lo sem
   fixtures reais quebraria os próprios testes existentes (FAKE nunca chega a
   `requests.request`, os mocks ficam sem efeito).
9. **Número de telefone de teste real, fornecido pelo utilizador em conversa, nunca usado** —
   avaliação explícita de que nenhuma fase autónoma dependia dele de facto; guardado só em
   `.env.manual`, fora do git.
10. **Mensagens de erro originais preservadas byte-a-byte** em ambos os projetos, mesmo onde
    o SDK oferecia mensagens mais informativas — para não mudar o texto que chega a clientes
    de API sem um teste dedicado a justificar a mudança.

---

## O que ficou por fazer, e porquê

| Item | Porquê ficou de fora |
|---|---|
| Fase 4 (`boxwey`/`bookwey` — segurança) | Explicitamente fora do âmbito autónomo. Depende de configuração em backoffices (registar callbacks, migrar para EuPago Webhooks 2.0) que só o utilizador pode fazer. Guião completo em `docs/migration/04-bookwey-security.md`. |
| Fase 5 (SIBS) | Explicitamente fora do âmbito autónomo. Bloqueada por uma discrepância de host entre 3 fontes oficiais (`docs/providers/sibs-spg.md`) e falta de contrato/credenciais reais — escrever código contra qualquer hipótese seria repetir o erro do esboço original que este SDK substitui. |
| `providers/eupago/callback.py` | Não consumido por nada até à Fase 4. |
| `Environment.FAKE` default em `bookwey`'s `development.py` | Precisa de fixtures reais gravadas (mesmo trabalho pendente em `docs/LOCAL-TESTING.md`); construir agora quebraria testes existentes. |
| `docs/LOCAL-TESTING.md` nível 1 (FAKE, sem rede) verificado ponta-a-ponta | O guião foi escrito na Fase 0a como alvo, mas nunca corrido manualmente nesta sessão — as fixtures reais que o sustentariam também ficaram por construir (ver item acima). |
| Nível 3 de `LOCAL-TESTING.md` (callback real via túnel) | Precisa de um túnel público e de registar o URL em backoffices externos — fora do que a execução autónoma pode fazer sozinha. |
| `requirements.txt` de `boxwey`/`bookwey` | Nunca editados — o SDK foi instalado só via `pip install -e` local nos dois venvs. Apontar para uma tag real (`git+https://...`) só faz sentido quando o repo tiver um remote público, decisão do utilizador. |
| `git remote`/publicação do SDK | O repo `weypay-sdk` continua 100% local, sem remote configurado — nunca houve `git push` (regra 2). |

---

## Bloqueios

Nenhum bloqueio impediu o âmbito autónomo de ser concluído. Os únicos itens genuinamente
bloqueados (não apenas adiados por escolha) são as pré-condições da Fase 5 (host SIBS
ambíguo, sem contrato) e as ações da Fase 4 que dependem de acesso a backoffices externos —
ambos já fora do âmbito pedido, portanto não impediram nada.

---

## Incidentes — todos com transparência total no `docs/PROGRESS.md`

Nenhum teve impacto real (nenhuma credencial exposta a terceiros, nenhum código de produção
quebrado). Listados aqui por completude — os detalhes completos, incluindo o texto exato do
que aconteceu, estão em `docs/PROGRESS.md`.

1. **Credenciais em claro em 2 ficheiros de documentação** (Fase 0a), copiadas da conversa
   como "exemplo". Descoberto e corrigido na Fase 0b via `grep` sistemático antes de cada
   commit — hábito adotado a partir daí. Os valores reais continuam no histórico git local
   (nunca publicado, sem remote) — sinalizado ao utilizador para decidir se quer reescrever o
   histórico antes de este repositório alguma vez ganhar um remote público.
2. **`cd` persistido apontou um commit para o diretório errado** (Fase 0a) — sem dano (nada
   para stage nesse diretório), mas levou à disciplina de sempre usar `cd` explícito ao repo
   certo em qualquer comando `git`, nunca depender do diretório persistido entre chamadas.
3. **Crase interpretada pelo shell numa mensagem de commit** (Fase 0c) — comeu uma palavra do
   texto (cosmético, sem impacto em código ou segredos). Não corrigido via `amend` (regra
   geral: nunca reescrever commits sem pedido explícito, mesmo por motivo cosmético).

---

## O que foi instalado — e o que não foi tocado

- **`weypay-sdk`**: `venv` próprio, com `requests`, `pytest`, `responses`, `ruff`, `mypy`,
  `types-requests`, `cryptography` (só para o extra `sibs`) — todas as dependências
  declaradas em `pyproject.toml`, fixadas por versão mínima.
- **`boxwey-serverless`**: `weypay` instalado em modo editable no `venv` já existente. Nada
  mais instalado.
- **`bookwey-serverless`**: `weypay` instalado em modo editable no `venv` já existente. Nada
  mais instalado — em particular, `ruff`/`mypy` **não** foram instalados aqui, porque este
  checkout não os tinha configurados; `py_compile` foi usado como verificação de sintaxe
  mínima em substituição, para não introduzir ferramentas novas fora do pedido.
- **Nada instalado globalmente**, em nenhum dos três repositórios.
- **Nenhuma escrita em GCP ou Cloudflare.** Nunca foi necessário sequer ler nada lá.
- **Nenhum `git push`**, em nenhum dos três repositórios.
- **Nenhum commit em `boxwey-serverless` nem `bookwey-serverless`** — ambos ficam com o diff
  completo das Fases 1-3 no working tree, por commitar, para revisão presencial.

---

## Estado final dos três repositórios

| Repositório | Estado |
|---|---|
| `weypay-sdk` | 21 commits locais, sem remote. Gates verdes (`ruff`, `mypy --strict`, `pytest` — 107 testes). |
| `boxwey-serverless` | `integrations/ifthenpay/views.py` modificado, `client.py` apagado, `integrations/{models,admin,apps}.py` novos + migration. Nada commitado. 209/209 testes locais, `OK`. |
| `bookwey-serverless` | `integrations/payments/utils.py`, `core/models.py`, `backoffice/admin.py`, `api/tests/test_booking_client_phone_sync.py` modificados; 2 migrations novas. Nada commitado. 91/91 testes locais, `OK`. |

## Para reveres ao regressares

1. `docs/PROGRESS.md` tem o registo cronológico completo, fase a fase, com todos os `git diff`
   relevantes descritos.
2. `git -C /home/chrisdo/projects/boxwey-serverless diff` e
   `git -C /home/chrisdo/projects/bookwey-serverless diff` mostram exatamente o que mudou em
   cada um, pronto para revisão e commit manual quando estiveres satisfeito.
3. O quase-incidente de credenciais no histórico do SDK (item 1 acima) é o único ponto que
   pede uma decisão tua antes deste repo alguma vez ganhar um remote público.
4. Nenhuma ação sua é necessária para nada mais — tudo o resto está em estado consistente e
   testado.

---

## Adendo — validação interativa com pagamentos reais (2026-08-14/15)

**Contexto**: o relatório acima cobre a execução autónoma (Fases 0a→3). Esta secção cobre o
trabalho **interativo**, feito depois do regresso do utilizador, que passou a autorizar
commits diretos em `boxwey-serverless`/`bookwey-serverless` na branch `weypay-sdk-migration`
(decisão registada em `docs/PROGRESS.md`, 2026-08-14). Ao contrário da fase autónoma, esta
sessão executou **pagamentos reais** (com montantes mínimos — €0,01 a €15,00 — e sempre com
autorização explícita do utilizador para cada chamada que contactasse o telefone dele),
porque era a única forma de confirmar comportamento que a documentação oficial não descrevia
ou descrevia mal. Todos os testes seguiram a mesma regra de segurança já registada:
**nunca disparar uma criação MB WAY com um número não fornecido explicitamente para esse
fim.**

### O que foi validado, gateway a gateway

| Gateway | Produto | Projeto | Desfecho testado | Resultado |
|---|---|---|---|---|
| EuPago | MB WAY (split) | `bookwey` | Criação + confirmação manual no backoffice sandbox + consulta de estado | ✅ `estado_referencia == "paga"` |
| EuPago | EuroPix | `bookwey` | Criação + confirmação + consulta de estado | ✅ idem, após corrigir bug (ver abaixo) |
| ifthenpay | MB WAY | `boxwey` | Aceite pelo utilizador | ✅ `Estado == "000"` |
| ifthenpay | MB WAY | `boxwey` | Recusado deliberadamente | ✅ `Estado == "020"` |
| ifthenpay | MB WAY | `boxwey` | Deixado expirar (~4 min, consulta imediata) | ✅ `Estado == "123"` |
| ifthenpay | MB WAY | `boxwey` | Deixado expirar (~5 min completos, consulta com margem) | ✅ `Estado == "101"` |
| ifthenpay | PINPAY/Apple Pay | `bookwey` | — | ⏸️ Adiado — utilizador precisa de pedir conta de teste à ifthenpay primeiro |

### Três bugs reais encontrados e corrigidos (nenhum hipotético — todos só apareceram ao pagar a sério)

1. **`weypay/providers/eupago/status.py` tinha `/api` a mais no host canónico.** Copiado por
   engano dos providers de criação (que precisam do `/api`); o path legado de consulta de
   estado nunca o levou no código original. Toda consulta de estado devolvia 404 — e o
   próprio teste do provider tinha o mesmo engano embutido no URL esperado, por isso passava
   sem detetar nada. Corrigido; fechou também a última incerteza real do projeto
   (`estado_referencia == "paga"` confirmado, não só assumido).
2. **`bookwey`'s EuroPix guardava o id local em `Payment.reference`, não a referência real da
   EuPago.** `criar_pagamento_europix` precisa de um id *antes* de chamar a EuPago (para
   `successUrl`), mas nunca substituía esse id pela referência real devolvida na resposta —
   bug presente também no código pré-migração, nunca detetado por falta de teste. Corrigido
   com um campo novo, `Payment.client_reference`, para o id local; `Payment.reference` passa a
   ser sempre a referência real (como já era no MB WAY/split).
3. **A documentação oficial da ifthenpay para `EstadoPedidosJSON` estava errada em três
   pontos** — método (exige GET, não POST), grafia (`EstadoPedidosJSON`, não
   `EstadoPedidosJson` — o próprio erro 500 revelou isto), e estrutura da resposta (dois
   níveis de `Estado`, só o de dentro de `EstadoPedidos[0]` importa). Este endpoint nunca
   tinha sido portado por nenhum dos dois projetos — implementado agora, com o vocabulário de
   estados descoberto por observação real: `"000"` pago, `"020"` recusado,
   `"101"`/`"123"` expirado (dois códigos diferentes consoante o timing da consulta — ver
   `docs/providers/ifthenpay-mbway.md` para a hipótese sobre porquê).

### Commits desta sessão

- `weypay-sdk`: 31 commits locais no total (branch `main`), sem remote. Gates verdes — 114
  testes (`pytest`), `ruff`, `mypy --strict`.
- `boxwey-serverless`: 25 commits na branch `weypay-sdk-migration` (inclui as Fases 1-2 já
  commitadas pelo utilizador ao regressar, mais o trabalho desta sessão). `main` intocado.
- `bookwey-serverless`: 19 commits na branch `weypay-sdk-migration` (idem, Fase 3 + os dois
  fixes de EuroPix/status). `main` intocado.
- Nenhum `git push` em lado nenhum. Nenhuma escrita em GCP/Cloudflare.

### O que ficou por fazer, e porquê

- **PINPAY/Apple Pay no `bookwey`**: precisa de uma conta de teste real da ifthenpay
  (`ifthenpay_apple_key` — o merchant local só tem `gateway_key`). Decisão do utilizador:
  pedir a conta primeiro, retomar depois.
- **Endpoint de consulta de estado para PINPAY**: a documentação oficial não lista nenhum
  (ao contrário do MB WAY, cuja documentação também estava incompleta mas o endpoint existe
  na mesma) — não verificado por chamada real, precisa da mesma conta de teste acima. Ver
  `docs/OPEN-QUESTIONS.md` #23.
- **`Environment.FAKE` como default em `bookwey`'s `development.py`**: continua adiado. Havia
  agora fixtures reais suficientes para o fazer (`docs/observed/*.json` cobre EuPago
  mbway/split/status/pix e ifthenpay mbway/status, incluindo os 4 desfechos de estado), mas
  `FakeResponseRegistry` só regista uma resposta por `(method, url)` — não distingue pedidos
  ao mesmo endpoint por corpo/query — por isso não dá para pré-carregar "pago" vs "recusado"
  vs "expirado" para o mesmo endpoint sem alargar o design do registo. Isso é uma decisão de
  desenho do SDK, não uma tarefa mecânica — fica para quando puderes confirmar a abordagem.
- **Fase 4 (segurança `bookwey`) e Fase 5 (SIBS)**: inalteradas, continuam fora do âmbito até
  decidires avançar — exigem configuração em backoffices externos.
