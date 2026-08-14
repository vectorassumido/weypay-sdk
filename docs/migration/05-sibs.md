# 05 — SIBS, escrita contra a especificação real

**Fora do âmbito da execução autónoma** (`weypay-phase` regra 9). Registado para quando houver
contrato e credenciais QLY — hoje nenhum projeto precisa de SIBS.

## Pré-condições (nenhuma satisfeita hoje)

- `docs/OPEN-QUESTIONS.md` #10-14 resolvidas: host/versão de path real do contrato, ciclo de
  vida do `AuthToken`, existência de mTLS, schema de `service-reference/generate`, base
  URL/auth da Marketplace API.
- Credenciais de sandbox SIBS (QLY) — não fornecidas; nada a testar sem elas.

## Ficheiros a criar, quando desbloqueado

- `weypay-sdk/src/weypay/providers/sibs/spg/` — `checkout.py`, `mbway.py`, `reference.py`
  (Multibanco), `status.py`, `webhook.py` (decifra AES-256-GCM + ack).
- `weypay-sdk/src/weypay/providers/sibs/marketplace/` — `submerchant.py`, `split.py`.
- `weypay-sdk/tests/providers/test_sibs_*.py` — contra payloads gravados dos exemplos oficiais
  (nunca contra a API real sem credenciais).

## Porque não entra na execução autónoma

Todas as pré-condições dependem de informação que só existe depois de um contrato SIBS ser
assinado e uma conta de sandbox QLY ser aprovisionada — nenhuma quantidade de leitura adicional
da documentação pública resolve a discrepância de host descrita em
`docs/providers/sibs-spg.md`. Escrever código contra qualquer uma das três hipóteses de host
sem confirmação seria repetir o erro do esboço original (`sibs-integration-project`), que este
SDK existe precisamente para corrigir.

## O que a execução autónoma pode preparar sem decidir por ninguém

Nada de código — o risco de codificar a hipótese errada de host/schema é maior que o benefício
de ter algo escrito. O único trabalho seguro é documental: manter
`docs/providers/sibs-spg.md` e `docs/OPEN-QUESTIONS.md` atualizados se surgir nova informação
pública (ex.: uma atualização da documentação oficial da SIBS), sem nunca converter uma
hipótese em código.

## Reversão

N/A — nada é criado até este passo ser desbloqueado.
