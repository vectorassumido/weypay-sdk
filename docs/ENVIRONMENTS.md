# Ambientes

Os três gateways **não oferecem a mesma coisa** — tratá-los como se oferecessem seria a
origem do próximo incidente, não uma simplificação.

## Por gateway

| Gateway | Sandbox real? | Como se separa de produção |
|---|---|---|
| **EuPago** | ✅ Sim, host próprio | `sandbox.eupago.pt` ↔ `clientes.eupago.pt` (troca-se a palavra) |
| **SIBS** | ✅ Sim, host próprio | QLY `api.qly.sibspayments.com` ↔ PRD `api.sibspayments.com` — mas ver a discrepância de host em `docs/providers/sibs-spg.md`, ainda por resolver |
| **ifthenpay** | ❌ **Não** | Mesmos endpoints de produção sempre; o isolamento vem só das **chaves de teste**, pedidas diretamente à ifthenpay |

O "Sandbox Mode" mencionado em plugins de terceiros da ifthenpay é uma flag que só suprime o
disparo de callbacks — não é um ambiente separado, e não deve ser tratado como tal no SDK.

## `Environment` no SDK

```python
class Environment(Enum):
    SANDBOX = "sandbox"
    PRODUCTION = "production"
    FAKE = "fake"
```

- `SANDBOX`/`PRODUCTION` resolvem a base URL por provider. Substitui o `merchant.eupago_api_url`
  em texto livre do `bookwey` — hoje o único indicador de ambiente, sem qualquer flag
  explícita, um erro de configuração de distância de um `sandbox.` a menos ou a mais.
- **ifthenpay + `SANDBOX` não é silencioso.** Como não há host de sandbox real, resolver
  `SANDBOX` para o host de produção sem avisar daria uma falsa sensação de segurança — um
  teste "em sandbox" estaria, de facto, a acontecer em produção. O SDK levanta
  `ConfigurationError` nesse caso, salvo passagem explícita de `acknowledge_no_sandbox=True`;
  quando essa flag é usada, o `GatewayCall` resultante fica marcado
  `outcome`-adjacente como tendo corrido contra produção, para que apareça de forma óbvia em
  qualquer auditoria de logs.

## `FAKE` — o terceiro modo, para desenvolvimento local

Transporte que **não abre socket nenhum**. Devolve respostas gravadas — os mesmos exemplos da
documentação oficial usados como fixtures na suite de conformidade (Fase 0c), promovidos a
partir das observações reais de sandbox da Fase 0b quando existirem (`docs/observed/`).

- É o default em `config.settings.development` / `booksys_be.settings.development` nos dois
  projetos.
- Fecha uma lacuna real: hoje o `boxwey` local nunca exercita o cliente de facto (os testes
  fazem `@patch` a `requests.post`, nunca correm o transporte real), e o `bookwey` bateria
  literalmente em produção da ifthenpay se alguém corresse o fluxo de checkout à mão em
  desenvolvimento, porque não há sandbox nem flag que o impeça.
- Um teste garante a propriedade central: `Environment.FAKE` nunca abre uma ligação de rede,
  verificável por mock que falha se `socket.socket` for chamado.

## Regras derivadas (testadas)

- `PRODUCTION` nunca aceita uma credencial que bata num padrão conhecido de chave de teste
  (ex.: prefixo `demo-` no EuPago, como em `EUPAGO_API_KEY=demo-xxxx-xxxx-xxxx-xxx`).
- `FAKE` nunca abre socket — se o teste tentar, falha alto, não silenciosamente.
- Nenhum provider lê `Environment` de uma variável de ambiente por si — recebe-o explícito na
  chamada. Quem decide o ambiente é a aplicação (via a sua própria configuração), nunca o SDK
  por adivinhação.

## Onde vivem as credenciais de teste

Nos `.env` de cada projeto consumidor — nunca no repo do SDK. As credenciais de sandbox
EuPago e a chave de teste MB WAY da ifthenpay foram fornecidas pelo utilizador e residem
localmente nos `.env` do `bookwey-serverless`/`boxwey-serverless`; ver `docs/LOCAL-TESTING.md`
para como usá-las sem as expor em lado nenhum deste repositório.
