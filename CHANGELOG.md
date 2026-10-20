# Changelog

Formato: [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).
Versionamento semântico. Os projetos consumidores fixam sempre uma tag exata.

## [Não lançado]

### v0.5.0 — ifthenpay: referências com prefixo de sistema
- Novo `providers/ifthenpay/reference.py`: `SYSTEM_PREFIXES` (`71` bookwey, `72` p8a, `73`
  boxwey), `new_reference(system)` (15 dígitos: prefixo + aleatórios via `secrets`),
  `has_prefix(reference, system)`. Decidido em backlog-ideias#25, depois de a ifthenpay
  confirmar por escrito que não há fan-out de callback (uma conta só tem um endereço) — cada
  sistema passa a ter a sua própria conta ifthenpay, e o prefixo fica como defesa adicional de
  baixo custo, não como mecanismo de pertença entre contas partilhadas.
- `providers/ifthenpay/mbway.request_payment()`: valida que `reference` não é vazia e tem no
  máximo 15 caracteres (`ValueError` caso contrário); lê `IdPedido` **ou** `idPedido` na
  resposta. `channel`/`canal` fica fixo em `"03"` — decisão explícita do Product Triage de não
  o expor como argumento variável por chamada, documentada em
  `docs/providers/ifthenpay-mbway.md` (i).
- `providers/ifthenpay/pinpay.create_payment()`: aceita os opcionais `btn_close_url`,
  `btn_close_label`, `otp` e `selected_method`, confirmados na especificação OpenAPI oficial do
  PINPAY — já usados hoje pelo `p8a` na sua chamada direta.
- Mudança aditiva: os testes existentes passam sem alterações.
- Ver `docs/providers/ifthenpay-callbacks.md` (i)/(j) para o modelo "uma conta ifthenpay por
  sistema, um callback por conta" e os dois templates de callback (legado vs. novo).

### v0.4.0 — EuPago: `admin_callback` do split passa a opcional
- `providers/eupago/split.create_split_payment()`: `admin_callback` deixa de ser
  obrigatório (default `""`, só enviado se dado). Confirmado com um teste controlado real em
  sandbox que a EuPago não exige que seja alcançável para a referência ficar confirmável —
  corrige um achado errado de 2026-08-14. Ver `docs/providers/eupago-mbway.md`,
  `docs/observed/eupago_split_admincallback_unreachable_is_cosmetic.json`.
- `docs/providers/eupago-pix.md`: confirmado (schema OpenAPI oficial completo) que
  `successUrl`/`failUrl`/`backUrl` não existem em nenhum endpoint documentado da EuPago —
  nunca tiveram efeito nenhum.

### v0.3.0 — ifthenpay: fallback de reconciliação para PINPAY
- `providers/ifthenpay/pinpay.get_order_status()` — usa a API oficial "List of Payments REST"
  (`POST /v2/payments/read`), documentada pela ifthenpay como alternativa/complemento ao
  callback. Cobre a conta inteira (não só PINPAY), mas `orderId` corresponde exatamente ao
  `id` usado em `create_payment`.
- Requer uma credencial nova, `bo_key` ("Backoffice key that identifies the merchant
  account"), distinta da `gateway_key` e da chave anti-phishing — ⚠️ ainda não confirmado como
  obter; ver `docs/OPEN-QUESTIONS.md`.

### Fase 0a — repositório e documentação
- Esqueleto do repositório e documentação completa escrita antes de qualquer implementação.
- Especificação *verbatim* de cada API dos três gateways, com marcação ✅ verificado / ⚠️ a confirmar.
- Guiões de migração por fase e guião de teste local para os dois projetos consumidores.
