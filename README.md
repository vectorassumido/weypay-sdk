# weypay

Cliente partilhado para gateways de pagamento portugueses — **ifthenpay**, **EuPago** e **SIBS** —
usado por `bookwey-serverless` e `boxwey-serverless`.

## O que é

Uma camada fina de *protocolo*: transporte HTTP com timeouts e política de retry, formatação de
payloads, normalização de estados, verificação criptográfica de callbacks, redação de segredos e
produção de um registo de auditoria por chamada.

**Sem estado.** O SDK não conhece bases de dados, ORMs, tenants nem máquinas de estados. As
credenciais são injetadas em cada chamada — vivem na base de dados de cada aplicação, nunca aqui.
A única dependência base é `requests`.

```python
from decimal import Decimal
from weypay import Environment, Money
from weypay.providers.ifthenpay import mbway

result = mbway.request_payment(
    mbway_key=tenant.mbway_key,          # vem da BD da aplicação
    reference="a1b2c3d4e5f6",
    amount=Money(Decimal("20.00"), "EUR"),
    phone="+351912345678",
    email="comprador@exemplo.pt",
    description="2 bilhetes",
    environment=Environment.SANDBOX,
)

result.status              # PaymentStatus.PENDING
result.raw_status          # "000" — o código do gateway, tal e qual
result.call.request        # o que foi enviado, já com as chaves redigidas
```

## Não faz

Base de dados · ORM · máquina de estados · idempotência · resolução de tenant · encriptação de
credenciais em repouso. Tudo isso pertence à aplicação, e é onde os dois projetos consumidores
divergem legitimamente.

## Documentação

| | |
|---|---|
| [`docs/PLAN.md`](docs/PLAN.md) | O plano completo: porquê um SDK, porquê junto, e o caminho de migração |
| [`docs/LOCAL-TESTING.md`](docs/LOCAL-TESTING.md) | Como pagar localmente nos dois projetos, passo a passo |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | O core: `Money`, erros, tipos, transporte, redação |
| [`docs/ENVIRONMENTS.md`](docs/ENVIRONMENTS.md) | Sandbox vs produção vs `FAKE`, por gateway |
| [`docs/SECURITY.md`](docs/SECURITY.md) | As regras não-negociáveis e o modelo de ameaça dos callbacks |
| [`docs/OPEN-QUESTIONS.md`](docs/OPEN-QUESTIONS.md) | O que ainda falta confirmar, por gateway |
| [`docs/providers/`](docs/providers/) | Um documento por API, com a spec oficial *verbatim* |
| [`docs/migration/`](docs/migration/) | Um guião por fase, com passos, testes e reversão |

Cada afirmação na documentação está marcada **✅ verificado** (citado da documentação oficial ou
lido no código) ou **⚠️ a confirmar**. Nenhum ⚠️ vira código sem ser observado contra a sandbox.

## Desenvolvimento

```bash
python3 -m venv venv && source venv/bin/activate
pip install -e ".[dev,sibs]"

ruff check . && ruff format --check .
mypy .
pytest
```

## Segredos

Este repositório **não contém credenciais** e não pode passar a conter. As chaves de sandbox e de
produção vivem nos `.env` e nas bases de dados dos projetos consumidores. As fixtures de teste são
respostas dos exemplos da documentação oficial e observações de sandbox — nunca dados reais.
