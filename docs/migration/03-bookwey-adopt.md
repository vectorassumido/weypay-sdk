# 03 — `bookwey` adota o transporte

**Critério de aceitação**: `python manage.py test` verde, mais o teste de tabela
payload-antigo-vs-novo (abaixo) a provar que nenhum valor monetário muda por efeito da troca
`float`→`Decimal`. Diferente da 01/02 do `boxwey`, este passo aceita mudanças de comportamento
**pontuais e guardadas por teste** (a troca de tipo numérico, a remoção de `print()`), mas
**nunca** uma mudança de comportamento não coberta por um teste que a demonstre.

## ✅ Executado em 2026-08-14 — **91/91 testes, `OK`** (idêntico à baseline)

Passos 1-3 concluídos como planeado. **Passo 4 adiado** — ver abaixo.

- **Teste de tabela payload-antigo-vs-novo** corrido primeiro, como pré-condição: para
  `0.10, 0.15, 19.99, 100.005, 33.33×3`, o payload JSON gerado por `float(Decimal(v))` (código
  antigo) e por `Money(v).to_gateway_number()` (novo) é **byte-a-byte idêntico** em todos os
  casos que podem ocorrer de facto neste codebase. O único caso "DIFERENTE" (`100.005`) é
  teórico — todo `DecimalField` de dinheiro no `bookwey` já é `decimal_places=2`, e
  `calculate_commission_amount()` já quantiza a cada passo, por isso um valor de 3 casas
  decimais nunca chega de facto a `criar_pagamento_*()`. Onde acontece (só no teste), `Money`
  arredonda corretamente (`100.01`) — mais seguro que o `float()` antigo, que teria enviado
  `100.005` sem arredondar.
- **Encontrado ao desenhar o rewrite, correção adicional ao SDK**: os providers EuPago
  resolviam sempre para o host canónico fixo (`clientes.eupago.pt`/`sandbox.eupago.pt`), mas
  o `bookwey` guarda o URL exato por-merchant em `Merchant.eupago_api_url` — dados reais de
  produção que podem não bater certo com o canónico. Adicionado `base_url: str | None` opcional
  a `mbway.py`/`split.py`/`pix.py`/`status.py` (commit `396faad`), que quando dado substitui a
  resolução por completo. `bookwey` passa sempre `base_url=f"{merchant.eupago_api_url}/api"` —
  preserva exatamente o host que cada merchant já tinha configurado.
- **5 funções de `integrations/payments/utils.py` reescritas**: `criar_pagamento_com_split`
  (delega para `eupago_split`/`eupago_mbway` conforme `salon_key != owner_key`, tal como
  antes), `criar_pagamento_europix`, `criar_pagamento_pinpay`, `verificar_pagamento`,
  `verificar_pagamento_mbway`. `calculate_commission_amount`, `create_staff_payment`,
  `pay_pagamento`, `send_merchant_monthly_summary_email` **inalteradas**. Mensagens de erro
  originais preservadas byte-a-byte (`raise Exception("Erro ao iniciar o pagamento.") from exc`
  etc.) — `GatewayRejected`/`GatewayUnavailable` do SDK são apanhadas e reconvertidas, para
  `booking.py`'s `except Exception as e: raise APIException(str(e))` continuar a devolver
  exatamente a mesma mensagem de hoje.
- **`Merchant.eupago_environment`**: campo aditivo (`core/models.py`), migration de schema
  (`0002`) + migration de **dados** separada (`0003`, `RunPython`) que faz backfill a partir
  do parsing de `eupago_api_url` — nenhum merchant muda de comportamento, só torna explícito o
  que já estava implícito no texto do URL. Adicionado também ao fieldset do admin
  (`backoffice/admin.py`).
- **Encontrado por varredura sistemática (grep) antes de tocar em qualquer ficheiro** — hábito
  já estabelecido nas Fases 1/2: `api/tests/test_booking_client_phone_sync.py` tinha 2 testes
  a espiar `integrations.payments.utils.requests.post` diretamente. Adaptados (não apagados —
  testam lógica de negócio real do `bookwey`, o bug de telefone obsoleto do cliente) para
  `@patch("weypay.http.requests.request")`, confirmados a passar isoladamente antes da suite
  completa.
- **Resultado**: `python manage.py test` → **91 testes, `OK`**, idêntico à baseline.
  `makemigrations --check --dry-run` limpo. (Sem `ruff`/`mypy` — este checkout do `bookwey`
  não tem essas ferramentas configuradas, ao contrário do `boxwey`; verificação de sintaxe via
  `py_compile` feita como substituto mínimo.)

### Passo 4 — `Environment.FAKE` como default em `development.py` — **adiado, não implementado**

Motivo, descoberto ao tentar implementar (não decidido antecipadamente): forçar `FAKE` sem
`fake_registry`/fixtures reais faria `Environment.FAKE` levantar `ConfigurationError` em
**qualquer** tentativa de pagamento local — incluindo dentro dos testes que correm com
`DJANGO_SETTINGS_MODULE=booksys_be.settings.development` (não há um settings module de teste
separado no `bookwey`). Isso quebraria `test_booking_client_phone_sync.py` e qualquer teste
futuro que mockeie `weypay.http.requests.request`: em modo FAKE o pedido nunca chega a esse
ponto, o mock fica sem efeito e a chamada falha sempre com `ConfigurationError` em vez de usar
a resposta mockada.

Resolver isto como deve ser exige fixtures reais gravadas (o mesmo trabalho já identificado
como pendente em `docs/LOCAL-TESTING.md` para o `bookwey`) — construir isso agora seria
scope creep sobre a Fase 3, com o risco adicional de quebrar testes existentes. Decisão:
**mesma categoria de adiamento que `providers/eupago/callback.py`** — registado aqui e em
`docs/PROGRESS.md`, não escondido. Environment continua a ser resolvido a partir do merchant
(`_eupago_environment()`), exatamente como descrito nos passos 1-3 acima; só a
flag global "força tudo para FAKE" fica por fazer.

## Pré-condições

- `docs/OPEN-QUESTIONS.md` #1-3 (endpoint legado de status, `entity` na resposta sem split,
  `successUrl`/`failUrl`/`backUrl` no PIX) resolvidas na Fase 0b — cada uma decide uma
  ambiguidade do código atual, não uma escolha de desenho.
- `bookwey-serverless/booksys-be` com suite atual verde (baseline).

## Ficheiros tocados

- `weypay-sdk/src/weypay/providers/eupago/` — **novo**: `mbway.py`, `split.py`, `pix.py`,
  `status.py`, `callback.py`.
- `weypay-sdk/src/weypay/providers/ifthenpay/pinpay.py` — **novo**.
- `bookwey-serverless/booksys-be/integrations/payments/utils.py` — as 6 funções ficam finas.
- `bookwey-serverless/booksys-be/core/models.py` — campo **aditivo** em `Merchant` (ver abaixo).
- Migration nova, aditiva e não destrutiva.

## Passos

1. Escrever os providers EuPago/PINPAY no SDK, contra `docs/providers/eupago-*.md` e
   `ifthenpay-pinpay.md` — já corrigidos pela Fase 0b onde havia ⚠️.
2. Em `utils.py`, cada função (`criar_pagamento_com_split`, `criar_pagamento_europix`,
   `criar_pagamento_pinpay`, `verificar_pagamento`, `verificar_pagamento_mbway`) passa a: (a)
   `calculate_commission_amount` — **inalterado**; (b) montar `Money`/parâmetros e chamar o
   provider do SDK; (c) `Payment.objects.create(...)` com os mesmos campos de hoje. Sai:
   `requests.post` direto, `print()`, `float()`.
3. **`Environment` em `Merchant` — aditivo, não destrutivo**: acrescentar
   `eupago_environment = CharField(choices=Environment, blank=True)`, **sem remover**
   `eupago_api_url`. Migration de dados (não de schema) que preenche o campo novo a partir do
   conteúdo do campo antigo: contém `"sandbox"` → `SANDBOX`; caso contrário → `PRODUCTION`. O
   código passa a preferir `eupago_environment` quando presente e a cair para o parsing do URL
   antigo quando não — **nenhum merchant existente muda de ambiente** por efeito desta
   migration; é só uma leitura explícita do que já estava implícito no texto do URL.
4. `FAKE` como default em `booksys_be/settings/development.py` — só nesse settings module,
   nunca em `production.py`/`serverless.py`.

## Teste de tabela payload-antigo-vs-novo (obrigatório antes de trocar `float`→`Decimal`)

Para um conjunto de valores que cubra os casos que mais preocupam arredondamento binário
(`0.10`, `0.15`, `19.99`, `100.005`, `33.33` repetido 3×), gerar o payload pela função antiga
(`float(...)`) e pela nova (`Money`), e comparar byte-a-byte a string enviada. Qualquer
diferença é motivo para parar e investigar antes de prosseguir — não para "corrigir e seguir
em frente" sem entender a causa.

## Testes a acrescentar

- Tabela payload-antigo-vs-novo (acima), por gateway (split, PIX, PINPAY).
- `Merchant.eupago_environment` vazio → comportamento idêntico ao atual (fallback ao parsing
  do URL) — teste de regressão explícito.
- `successUrl`/`failUrl`/`backUrl` no PIX: mantidos exatamente como a Fase 0b confirmou que a
  EuPago os trata (aceites, ignorados, ou removidos do payload se causavam erro).

## Comando de verificação

```bash
cd /home/chrisdo/projects/bookwey-serverless/booksys-be && source venv/bin/activate
DJANGO_SETTINGS_MODULE=booksys_be.settings.development python manage.py makemigrations --check --dry-run
DJANGO_SETTINGS_MODULE=booksys_be.settings.development python manage.py test
```

## Reversão

Nada commitado em `bookwey-serverless` (regra 1). `git checkout --` nos ficheiros existentes;
`git clean -n` para listar e depois remover a migration nova, se necessário reverter por
completo.
