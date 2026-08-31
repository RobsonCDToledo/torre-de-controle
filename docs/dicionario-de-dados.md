# Dicionário de dados

Catálogo de tabelas, campos e medidas — mantido por tabela e preparado para busca,
inclusive por agentes de IA.

> **Status:** estrutura definida, conteúdo preenchido conforme cada camada é construída.
> A fase 5 exige este documento completo: sem ele, self-service vira acesso a dado sem
> acesso a significado.

---

## Como usar

Cada tabela segue o mesmo bloco: propósito, grão, origem, campos, e regras conhecidas.
A padronização é o que torna o documento pesquisável — por pessoas e por máquinas.

Termos de negócio recebem a mesma definição aqui e no esquema linguístico do modelo
semântico, para que a resposta de uma pergunta em linguagem natural nunca contradiga a
documentação.

---

## Camada gold

### `fato_entrega`

**Propósito:** um pedido e sua história de entrega. Base de todos os indicadores de prazo.
**Grão:** um pedido.
**Origem:** `silver.pedidos`, enriquecida por `silver.itens_pedido`.

| Campo | Tipo | Definição |
|---|---|---|
| `sk_pedido` | bigint | Chave substituta |
| `id_pedido` | string | Chave natural da origem, mantida para rastreio |
| `dias_de_atraso` | int | Dias entre entrega real e prevista. Negativo indica entrega adiantada |
| `entregue_no_prazo` | boolean | Verdadeiro quando a entrega ocorreu até a data prevista. Base do OTD |
| | | _(completar na fase 3)_ |

**Regras conhecidas:** pedidos sem `data_entrega_real` não entram no cálculo de OTD — são
pedidos em trânsito, cancelados ou indisponíveis. Contá-los como atrasados inflaria o
indicador.

### `fato_item_pedido`

_(preencher na fase 3)_

### Dimensões

_(preencher na fase 3)_

---

## Medidas do modelo semântico

| Medida | Definição de negócio | Cuidado |
|---|---|---|
| `OTD %` | Pedidos entregues até a data prevista sobre pedidos entregues | Denominador exclui pedidos não entregues |
| `Lead time médio` | Média de dias entre compra e entrega | Sensível a outliers — considerar mediana em paralelo |
| `Frete sobre faturamento` | Soma de frete sobre soma do valor dos itens | Razão de somas, nunca média de razões |
| | | _(completar na fase 4)_ |

---

## Glossário de termos

| Termo | Significado neste projeto |
|---|---|
| **OTD** | On-Time Delivery. Percentual de pedidos entregues dentro do prazo prometido ao cliente |
| **Lead time** | Tempo decorrido entre dois marcos do funil de entrega |
| **Rota** | Par UF de origem do vendedor → UF de destino do cliente |
| **Frete percentual** | Custo de frete como proporção do valor dos itens |
| **Prefixo de CEP** | Cinco primeiros dígitos, granularidade da geolocalização na origem |
