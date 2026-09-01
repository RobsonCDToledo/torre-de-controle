# Dicionário de dados

Catálogo de tabelas, campos e medidas — mantido por tabela e preparado para busca,
inclusive por agentes de IA.

> **Status:** camada silver documentada e verificada. Gold e medidas do modelo semântico
> serão preenchidas nas fases 3 e 4. A fase 5 exige este documento completo: sem ele,
> self-service vira acesso a dado sem acesso a significado.

---

## Como usar

Cada tabela segue o mesmo bloco: propósito, grão, origem, campos, e regras conhecidas.
A padronização é o que torna o documento pesquisável — por pessoas e por máquinas.

Termos de negócio recebem a mesma definição aqui e no esquema linguístico do modelo
semântico, para que a resposta de uma pergunta em linguagem natural nunca contradiga a
documentação.

---

## Camada silver

Oito tabelas de negócio mais uma de rejeitados, em `lh_silver`. Nomes de coluna em
português, tipos explícitos, deduplicação pela chave natural declarada. **570.730 linhas
no total.**

### Colunas de rastro, presentes em todas

| Campo | Tipo | Definição |
|---|---|---|
| `_origem_arquivo` | string | Nome do arquivo da bronze que originou a linha |
| `_ingerido_em` | date | Data da **partição da bronze**, não da execução do Dataflow. Responde "de qual ingestão esta linha veio" — a silver se reconstrói muitas vezes sobre a mesma bronze |

### Convenções de tipo

**Identificador é sempre texto.** `prefixo_cep`, `id_pedido`, `id_produto` e afins não são
quantidades: não se somam, não têm magnitude, e perdem zero à esquerda se virarem número.

**Dinheiro é decimal fixo**, nunca ponto flutuante.

**Nulo é informação e é preservado.** Nenhum campo recebe valor padrão para "preencher
buraco" — a ausência do dado é o próprio dado.

---

### `clientes`

**Propósito:** um cliente e sua geografia de destino. Alimenta a `dim_cliente` da gold.
**Grão:** um `customer_id`.
**Origem:** `olist_customers_dataset.csv` — 99.441 linhas, 99.441 na silver.

| Campo | Tipo | Definição |
|---|---|---|
| `id_cliente` | string | Chave natural. Muda a cada pedido — **não** identifica a pessoa |
| `id_cliente_unico` | string | Identifica a pessoa. 96.096 distintos. É este que a `dim_cliente` usa |
| `prefixo_cep` | string | Cinco primeiros dígitos do CEP. Junta com `geografia` |
| `cidade` | string | Capitalizada na silver; sem acento na origem |
| `uf` | string | Sigla da unidade federativa, maiúscula |

**Regras conhecidas:** a origem tem **dois identificadores diferentes** e confundi-los quebra
a dimensão cliente — 99.441 `id_cliente` para 96.096 pessoas. Sem nulos e sem duplicata.
**23.995 prefixos começam com zero** e só sobrevivem porque o campo é texto ponta a ponta.

---

### `vendedores`

**Propósito:** um vendedor e sua geografia de origem. Alimenta a `dim_vendedor`.
**Grão:** um `seller_id`.
**Origem:** `olist_sellers_dataset.csv` — 3.095 linhas, 3.095 na silver.

| Campo | Tipo | Definição |
|---|---|---|
| `id_vendedor` | string | Chave natural |
| `prefixo_cep` | string | Junta com `geografia`. É a origem da rota |
| `cidade` | string | Capitalizada na silver |
| `uf` | string | UF de origem — metade do par que define uma rota |

**Regras conhecidas:** sem nulos, sem duplicata, sem número. A mais simples das oito.

---

### `produtos`

**Propósito:** atributos físicos e de categoria do produto. Alimenta a `dim_produto`.
**Grão:** um `product_id`.
**Origem:** `olist_products_dataset.csv` — 32.951 linhas, 32.951 na silver.

| Campo | Tipo | Definição |
|---|---|---|
| `id_produto` | string | Chave natural |
| `categoria` | string | Código de domínio da origem, ex. `cama_mesa_banho`. Rótulo legível é construído na gold |
| `tamanho_nome` | int | Caracteres no nome do produto |
| `tamanho_descricao` | int | Caracteres na descrição |
| `qtd_fotos` | int | Fotos no anúncio |
| `peso_gramas` | int | Peso. Base do custo por quilo |
| `comprimento_cm`, `altura_cm`, `largura_cm` | int | Dimensões. O volume é calculado na gold |

**Regras conhecidas:** **610 produtos não têm categoria**, tamanhos nem contagem de fotos, e
**2 não têm peso nem dimensões**. Nenhum é rejeitado: são produtos válidos, e removê-los
deixaria itens de pedido órfãos. Os 2 sem peso não entram no custo por quilo.

A origem escreve `product_name_lenght`, com o erro de digitação. O contrato de colunas
reproduz o erro exatamente, porque descreve o que a origem **é**, não o que deveria ser.

---

### `pedidos`

**Propósito:** um pedido e sua história de entrega. Base de todos os indicadores de prazo.
**Grão:** um `order_id`.
**Origem:** `olist_orders_dataset.csv` — 99.441 linhas, 99.441 na silver.

| Campo | Tipo | Definição |
|---|---|---|
| `id_pedido` | string | Chave natural |
| `id_cliente` | string | Junta com `clientes` |
| `status_pedido` | string | Oito valores: `delivered`, `shipped`, `canceled`, `unavailable`, `invoiced`, `processing`, `approved`, `created` |
| `data_compra` | datetime | Marco zero do funil. Sem nulos |
| `data_aprovacao` | datetime | Aprovação do pagamento. **160 nulos** |
| `data_coleta` | datetime | Coleta pela transportadora. **1.783 nulos** |
| `data_entrega_real` | datetime | Entrega ao cliente. **2.965 nulos** |
| `data_entrega_prevista` | datetime | Prazo prometido. Sem nulos |

**Regras conhecidas:** os nulos nas datas são **legítimos** — pedidos em trânsito, cancelados
ou indisponíveis. 96.478 dos 99.441 têm status `delivered`. Nenhuma data recebe valor padrão:
pedidos sem `data_entrega_real` **não entram no cálculo de OTD**, porque contá-los como
atrasados inflaria o indicador.

**1.359 pedidos têm coleta anterior à aprovação.** Não são rejeitados — é plausível na
operação real que a transportadora colete antes de o pagamento compensar. Fica registrado
como característica conhecida, não como erro.

---

### `itens_pedido`

**Propósito:** o item de um pedido, com preço e frete próprios. Alimenta `fato_item_pedido`.
**Grão:** **um item de um pedido.**
**Origem:** `olist_order_items_dataset.csv` — 112.650 linhas, 112.650 na silver.

| Campo | Tipo | Definição |
|---|---|---|
| `id_pedido` | string | Junta com `pedidos`. Metade da chave natural |
| `numero_item` | int | Contador posicional dentro do pedido, de 1 a 21. Outra metade da chave |
| `id_produto` | string | Junta com `produtos` |
| `id_vendedor` | string | Junta com `vendedores`. Origem da rota |
| `data_limite_envio` | datetime | Prazo que o vendedor tem para despachar |
| `preco` | decimal | Preço do item. Soma total: **13.591.643,70** |
| `valor_frete` | decimal | Frete rateado no item. Soma total: **2.251.909,54** |

**Regras conhecidas:** a chave natural é `id_pedido` + `numero_item`, **nunca**
`id_pedido` + `id_produto` — o mesmo produto aparece várias vezes no mesmo pedido, que é como
a origem representa quantidade. Deduplicar por produto apagaria 10.225 linhas, 9% da tabela.

Sem nulos em nenhuma coluna. Nenhum preço menor ou igual a zero, nenhum frete negativo.

---

### `pagamentos`

**Propósito:** como o pedido foi pago. Alimenta análises de forma e parcelamento.
**Grão:** um pagamento de um pedido.
**Origem:** `olist_order_payments_dataset.csv` — 103.886 linhas, 103.886 na silver.

| Campo | Tipo | Definição |
|---|---|---|
| `id_pedido` | string | Junta com `pedidos`. Metade da chave natural |
| `sequencial_pagamento` | int | Distingue as formas quando o pedido é dividido. Outra metade da chave |
| `tipo_pagamento` | string | Cinco valores: `credit_card`, `boleto`, `voucher`, `debit_card`, `not_defined` |
| `qtd_parcelas` | int | Parcelas do pagamento |
| `valor` | decimal | Valor pago. Soma total: **16.008.872,12** |

**Regras conhecidas:** um pedido pode ser pago de mais de uma forma, e o sequencial é o que
distingue — por isso a chave é composta. **9 pagamentos têm valor zero** e **2 têm zero
parcelas**; nenhum é rejeitado, porque há explicação de negócio plausível, como voucher
cobrindo o pedido inteiro. Nenhum valor negativo.

---

### `avaliacoes`

**Propósito:** a nota que o cliente deu. Proxy de qualidade percebida da entrega.
**Grão:** uma avaliação de um pedido.
**Origem:** `olist_order_reviews_dataset.csv` — 99.224 linhas, 99.224 na silver.

| Campo | Tipo | Definição |
|---|---|---|
| `id_avaliacao` | string | Metade da chave natural. **Sozinho não é chave** — 98.410 distintos para 99.224 linhas |
| `id_pedido` | string | Outra metade da chave. Junta com `pedidos` |
| `nota` | int | De 1 a 5, sem valores fora da faixa |
| `titulo_comentario` | string | **87.656 nulos** — a maioria não escreve título |
| `comentario` | string | **58.247 nulos** — a maioria dá nota sem comentar |
| `data_avaliacao` | datetime | Diária na prática: apenas 2 horários distintos em 99.224 linhas |
| `data_resposta` | datetime | Resposta do vendedor. Timestamp real, 53.278 horários distintos |

**Regras conhecidas:** a relação entre avaliação e pedido é **muitos-para-muitos legítima**,
nos dois sentidos — **789 avaliações cobrem mais de um pedido** e **547 pedidos têm mais de
uma avaliação**. A chave composta foi medida como única.

Usar `id_avaliacao` sozinho descartaria 814 linhas **diferentes entre si**, com aparência de
limpeza. Nenhuma linha é rejeitada.

Os nulos nos comentários são esperados e não indicam falha de carga. A caixa do texto é
preservada como o cliente escreveu: comentário em maiúsculas carrega sinal.

> **Consequência para a fase 3:** com 547 pedidos tendo mais de uma nota, não existe "a nota
> do pedido". A `fato_entrega`, que é por pedido, precisará de uma regra declarada — média,
> mais recente ou menor — e a escolha muda o indicador de qualidade percebida.

---

### `geografia`

**Propósito:** o centroide de cada prefixo de CEP. Alimenta a `dim_geografia` e a distância
entre origem e destino usada pelo modelo de ML.
**Grão:** um prefixo de CEP.
**Origem:** `olist_geolocation_dataset.parquet` — **1.000.163 linhas viram 19.011 centroides.**

| Campo | Tipo | Definição |
|---|---|---|
| `prefixo_cep` | string | Chave natural. Cinco primeiros dígitos do CEP |
| `latitude` | number | **Mediana** das latitudes válidas do prefixo |
| `longitude` | number | **Mediana** das longitudes válidas |
| `cidade` | string | Cidade **mais frequente** do prefixo, sem acento e capitalizada |
| `uf` | string | UF mais frequente do prefixo |

**Regras conhecidas:**

**Mediana, não média.** 309 prefixos têm ponto a mais de 100 km do próprio centroide —
coordenadas dentro do Brasil, mas erradas para o CEP. A média é arrastada por elas: 223
prefixos deslocariam mais de 10 km, e o pior caso 1.118 km. A mediana de latitude e de
longitude em separado não é a mediana geométrica verdadeira, mas para nuvem compacta de
pontos é boa aproximação e muito mais robusta.

**Moda para cidade e UF.** 8.554 prefixos declaram mais de uma cidade e 8 declaram mais de
uma UF. A mais frequente é escolha declarada, não "a primeira que aparecer".

**Acento removido antes da agregação.** A origem traz a mesma cidade em duas grafias — 2.042
nomes distintos são a mesma cidade escrita de duas formas. Normalizar depois do agrupamento
faria a grafia dividir o voto e a cidade minoritária vencer em 12 prefixos.

**Quatro prefixos não existem aqui:** `18243`, `78131` (Várzea Grande, MT), `83252` (Ilha dos
Valadares, PR) e `95130`. Todas as coordenadas deles são inválidas, então não há centroide a
calcular. **Isso é ausência de dado, não dado sujo** — o lugar existe, o CEP existe, e a
origem não tem coordenada boa. Junção nula ali é limite da origem, não falha do pipeline.
Impacto: 1 cliente e 0 vendedores.

---

### `geografia_rejeitados`

**Propósito:** as coordenadas descartadas da `geografia`, com o motivo. Auditoria.
**Grão:** uma coordenada rejeitada.
**Origem:** `olist_geolocation_dataset.parquet` — 31 linhas.

Mesmos campos da `geografia`, sem agregação, mais:

| Campo | Tipo | Definição |
|---|---|---|
| `_motivo_rejeicao` | string | Por que a linha saiu. Hoje há uma regra só: coordenada fora dos limites do território brasileiro |

**Regras conhecidas:** os limites usados são latitude entre **-33,75 e 5,27** e longitude
entre **-73,99 e -28,80**. O limite leste é -28,80 e não -34,79 de propósito: o segundo é o
extremo *continental* e descartaria Fernando de Noronha, prefixo 53990, que tem coordenada
correta.

O valor da cidade é preservado como veio, sem remoção de acento nem capitalização — auditoria
quer o original.

**O defeito é sistemático, não aleatório:** é falha de geocodificação por homônimo. 19 das 31
caem na Península Ibérica, 4 na Argentina, 3 na Itália, 3 entre México e Estados Unidos e 1
nas Filipinas. "Porto Trombetas" virou Porto, "Santo Antônio" virou San Antonio, "Santa Rosa"
caiu em Santa Rosa de La Pampa.

---

## Regras de qualidade verificadas

Regra que passa não vira tabela vazia: vira número medido. Tabela vazia não distingue "nada
falhou" de "a regra nunca rodou".

| Regra | Tabela | Ocorrências |
|---|---|---|
| Chave natural nula | todas as oito | **0** |
| Duplicata pela chave natural declarada | todas as oito | **0** |
| Entrega ou aprovação anterior à compra | `pedidos` | **0** |
| Preço ≤ 0 ou frete negativo | `itens_pedido` | **0** |
| Valor de pagamento negativo | `pagamentos` | **0** |
| Nota fora da faixa de 1 a 5 | `avaliacoes` | **0** |
| Item apontando para pedido inexistente | `itens_pedido` | **0** |
| Pagamento apontando para pedido inexistente | `pagamentos` | **0** |
| Avaliação apontando para pedido inexistente | `avaliacoes` | **0** |
| Item apontando para produto inexistente | `itens_pedido` | **0** |
| **Coordenada fora do território brasileiro** | `geografia` | **31** → rejeitados |

A integridade referencial da origem é perfeita nas quatro relações verificadas. Os defeitos
deste dataset não são de validade — são de **modelagem**: a chave natural das avaliações e a
qualidade das coordenadas.

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
