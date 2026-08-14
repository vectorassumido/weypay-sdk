# ifthenpay — Callbacks (MB WAY e PINPAY)

Marcação: ✅ verificado / ⚠️ a confirmar.

## (a) O que é diferente aqui: o template é nosso, não da ifthenpay

✅ **Confirmado pelo utilizador, com o template real do `boxwey`:**

```
https://api.boxwey.com/api/v1/webhooks/ifthenpay/?chave=[ANTI_PHISHING_KEY]&referencia=[REFERENCIA]&valor=[VALOR]&estado=[ESTADO]
```

Este URL é registado **por conta**, no backoffice ifthenpay. Os nomes dos parâmetros
(`chave`, `referencia`, `valor`, `estado`) e a ordem são **escolha nossa** — a ifthenpay só
substitui os placeholders `[ANTI_PHISHING_KEY]`, `[REFERENCIA]`, `[VALOR]`, `[ESTADO]` pelos
valores reais. Logo: **não são protocolo**, são configuração, e podem ser diferentes por
conta e por produto (MB WAY vs PINPAY já usam nomes diferentes de fábrica — ver `(b)`).

Consequência de desenho: o parser do SDK não pode assumir nomes fixos. Recebe um
`CallbackMapping` (nomes dos parâmetros → papel semântico) com o default a corresponder ao
template atual do `boxwey`.

## (b) Nomes de fábrica por produto (o que a ifthenpay sugere se não se escolher outra coisa)

| Produto | Template |
|---|---|
| MB WAY (exemplo do helpdesk) | `chave=[ANTI_PHISHING_KEY]&referencia=[REFERENCIA]&idpedido=[ID_TRANSACAO]&valor=[VALOR]&datahorapag=[DATA_HORA_PAGAMENTO]&estado=[ESTADO]` |
| MB WAY (template real do `boxwey`) | `chave=[ANTI_PHISHING_KEY]&referencia=[REFERENCIA]&valor=[VALOR]&estado=[ESTADO]` (sem `idpedido`/`datahorapag`) |
| PINPAY | `key=[ANTI_PHISHING_KEY]&id=[ID]&amount=[AMOUNT]&payment_datetime=[PAYMENT_DATETIME]&payment_method=[PAYMENT_METHOD]` |

⚠️ Se a conta do `bookwey` já tem um template PINPAY registado, é preciso lê-lo no backoffice
antes de assumir o default acima — tarefa do utilizador, registada em `OPEN-QUESTIONS.md`.
**Recomendação** (ver `docs/PLAN.md`): ao registar o callback do PINPAY, usar os mesmos nomes
do MB WAY (`chave`/`referencia`/`valor`/`estado`) — como os nomes são nossos, os dois
projetos convergem para um único parser.

## (c) Vocabulário de `[ESTADO]`/`[estado]`

✅ O único valor confirmado pela documentação é `PAGO` — a ifthenpay só dispara o callback em
caso de sucesso (nota do helpdesk sobre o MB WAY: o callback "só é enviado se a referência for
paga"). ⚠️ Não documentado: se existe callback de recusa/cancelamento/reembolso, e que valor
textual traria. `boxwey/api/integrations/ifthenpay/client.py:20-27` assume que **não** há
(`CALLBACK_STATUS_PAID = "PAGO"` é o único valor tratado como sucesso; os códigos numéricos em
`STATUS_REFUNDED`/`STATUS_DECLINED` são comparados contra esse mesmo campo textual, o que é
⚠️ suspeito — ver `ifthenpay-mbway.md` (d)). A confirmar com o **Webhook Tester** oficial
(Fase 0b) antes de mexer nesse mapeamento.

## (d) Verificação — o que garante que o callback é legítimo

- ✅ `chave` = anti-phishing key, definida por nós no backoffice, uma por conta.
  `constant_time_compare` (`boxwey/api/integrations/ifthenpay/views.py:58`).
- ✅ `valor`, quando presente no template, permite validar o montante contra o registo local
  (`views.py:62-75`). ⚠️ Como o template é nosso, `valor` pode simplesmente não constar de
  alguma conta — nesse caso a verificação de montante é estruturalmente impossível até se
  corrigir o template, não um bug de parsing.
- Sem HMAC, sem assinatura, sem IP allowlist. A segurança do callback assenta inteiramente na
  `chave` (segredo partilhado) + verificação de montante.

## (e) Retry

✅ Sucesso = **HTTP 200**. Se não, a ifthenpay repete "até 13 vezes" (helpdesk). Consequência
direta: devolver 4xx a um `estado` desconhecido é ativamente prejudicial — gera até 13
notificações redundantes sem que nada mude no lado da aplicação. Regra do SDK: estado
desconhecido → `PaymentStatus.UNKNOWN`, registar, responder 200.

## (f) Ferramenta de teste oficial

✅ Existe um **Webhook Tester** no backoffice ifthenpay: "simula pedidos de webhook para cada
método de pagamento disponível, permitindo testar e validar integrações". É o mecanismo para
exercitar o callback localmente (via túnel) sem depender de um pagamento real — coberto em
`docs/LOCAL-TESTING.md`.

## (g) Estado atual do código, por projeto

| | `boxwey` (MB WAY) | `bookwey` (PINPAY) |
|---|---|---|
| Rota | `GET /api/v1/webhooks/ifthenpay/` | **inexistente** |
| Verificação de `chave` | ✅ tempo constante | — |
| Verificação de `valor` | ✅ condicional a estar presente | — |
| Estado desconhecido | ❌ HTTP 400 (dispara retries) | — |
| Referência | `uuid4().hex[:12]`, única, não adivinhável | `str(schedule.id.int)[-15:]`, previsível |
| Idempotência | ✅ state machine com transições early-return | ❌ nenhuma (confirma sem contactar a ifthenpay) |

## (h) Delta a corrigir

- **`boxwey`, Fase 2**: estado desconhecido passa a 200 + registo, nunca 400.
- **`bookwey`, Fase 4** (fora do âmbito autónomo): registar o callback no backoffice,
  implementar a rota, remover a confirmação sem verificação em `check_payment_status`, trocar
  a referência por um token de 15 dígitos aleatórios.

## Fonte

Confirmado em conversa pelo utilizador (template real do `boxwey`) +
[API - MBWAY (Deprecated)](https://helpdesk.ifthenpay.com/en/support/solutions/articles/79000086376-api-mbway-deprecated-) ·
[API - PayByLink & PINPAY](https://helpdesk.ifthenpay.com/en/support/solutions/articles/79000143271-api-paybylink-pinpay)
