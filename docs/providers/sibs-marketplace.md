# SIBS — Marketplace API (Onboarding + Split)

Marcação: ✅ verificado / ⚠️ a confirmar. Fonte primária:
[Marketplace Onboarding API](https://www.docs.pay.sibs.com/portugal/marketplace/integrations/marketplace-api/onboarding-api/) ·
[Marketplace Split API](https://www.docs.pay.sibs.com/portugal/marketplace/integrations/marketplace-api/split-api/).

**Família de API separada do SPG** (`sibs-spg.md`) — onboarding de submerchants e
partilha/payout de transações, não processamento de pagamento em si. Só faz sentido se algum
projeto consumidor vier a precisar de um modelo marketplace/multi-vendor — hoje nenhum
precisa. Não ligado a nenhum projeto (Fase 5, e mesmo dentro dela é o extra menos prioritário).

## Onboarding API

### (a) Endpoints — verbatim

| Operação | Método | Path |
|---|---|---|
| Adicionar submerchant | POST | `/sibs/v2/submerchant` |
| Adicionar acordo/comissão | POST | `/sibs/v2/submerchant/{submerchant-id}/commission` |
| Modificar submerchant | PUT | `/sibs/v2/submerchant/{submerchant-id}` |
| Alterar acordo | PUT | `/sibs/v2/submerchant/{submerchant-id}/commission` |
| Alterar estado | PUT | `/sibs/v2/submerchant/{submerchant-id}` |
| Detalhes | GET | `/sibs/v2/submerchant/{submerchant-id}` |
| Consultar acordo | GET | `/sibs/v2/submerchant/{submerchant-id}/commission` |
| Remover submerchant | DELETE | `/sibs/v2/submerchant/{submerchant-id}` |
| Listar submerchants | GET | `/sibs/v2/submerchant` |

⚠️ Base URL e headers de autenticação não capturados na página consultada — presumivelmente
o mesmo `Bearer` + `X-IBM-Client-Id` do SPG, mas **não confirmado**, não presumir.

### (b) Campos do submerchant — verbatim

NIF, nome da empresa, nome abreviado, código de atividade, descrição, tipo de liquidação,
teto de reembolso, tipo de arranjo de payout, intervalos de payout diferido. Financeiros:
IBAN, BIC. Morada (opcional): rua, código postal, localidade, localidade postal, país
(ISO-3166 numérico). Contacto (opcional): email, telefone, telemóvel. Comissão: componente
fixa, componente percentual, limiar mínimo, limiar máximo.

### (c) Ciclo de vida de estado

`ACT` (Ativo), `PND` (Pendente), `SUS` (Suspenso), com janelas de progressão de 30 dias.

## Split API

### (a) Endpoints — verbatim

| Operação | Método | Path |
|---|---|---|
| Publicar split/payout | POST | `/sibs/v1/split/{split-type}` — `split-type` = `Purchase` ou `Refund` |
| Alterar agendamento de payout | PUT | `/sibs/v1/split` |
| Listar transações por submerchant | GET | `/sibs/v1/split/transactions` |
| Consultar split | GET | `/sibs/v1/spli/transaction` *(sic — a documentação oficial escreve `spli`, não `split`; citado verbatim, não é erro de transcrição nossa)* |

### (b) Campos — verbatim

Código do submerchant (**8 dígitos numéricos**), ID de transação externo, montante do split,
código de moeda `"968"` (**EUR** — código numérico ISO 4217, não `"EUR"` texto como no SPG).

### (c) Nota de fiabilidade citada no doc oficial

> "Se o utilizador não receber resposta a esta API, deve chamar a API 'Inquire Split' para
> validar que a informação foi publicada com sucesso."

Padrão de reconciliação explícito da própria SIBS — reforça a regra 1 de `SECURITY.md`
(nunca retry automático numa escrita; ler o estado antes de repetir).

## Fonte

[Marketplace Onboarding API](https://www.docs.pay.sibs.com/portugal/marketplace/integrations/marketplace-api/onboarding-api/) ·
[Marketplace Split API](https://www.docs.pay.sibs.com/portugal/marketplace/integrations/marketplace-api/split-api/)
