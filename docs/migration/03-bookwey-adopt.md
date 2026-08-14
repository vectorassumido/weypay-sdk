# 03 — `bookwey` adota o transporte

**Critério de aceitação**: `python manage.py test` verde, mais o teste de tabela
payload-antigo-vs-novo (abaixo) a provar que nenhum valor monetário muda por efeito da troca
`float`→`Decimal`. Diferente da 01/02 do `boxwey`, este passo aceita mudanças de comportamento
**pontuais e guardadas por teste** (a troca de tipo numérico, a remoção de `print()`), mas
**nunca** uma mudança de comportamento não coberta por um teste que a demonstre.

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
