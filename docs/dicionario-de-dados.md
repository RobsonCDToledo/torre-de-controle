# Dicionário de dados

Catálogo de tabelas, campos e medidas — mantido por tabela e preparado para busca,
inclusive por agentes de IA.

> **Status:** completo — silver, gold, medidas e sinônimos documentados. A seção "Sinônimos
> para Q&A" abaixo fica só como referência: Q&A não é suportado em Direct Lake (`ADR-005`),
> então não há esquema linguístico do modelo pra aplicar esse mapeamento hoje.

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
| `titulo_comentario` | string | **87.658 nulos** — a maioria não escreve título |
| `comentario` | string | **58.274 nulos** — a maioria dá nota sem comentar |
| `data_avaliacao` | datetime | Diária na prática: apenas 2 horários distintos em 99.224 linhas |
| `data_resposta` | datetime | Resposta do vendedor. Timestamp real, 53.278 horários distintos |

**Regras conhecidas:** a relação entre avaliação e pedido é **muitos-para-muitos legítima**,
nos dois sentidos — **789 avaliações cobrem mais de um pedido** e **547 pedidos têm mais de
uma avaliação**. A chave composta foi medida como única.

Usar `id_avaliacao` sozinho descartaria 814 linhas **diferentes entre si**, com aparência de
limpeza. Nenhuma linha é rejeitada.

Os nulos nos comentários são esperados e não indicam falha de carga. A caixa do texto é
preservada como o cliente escreveu: comentário em maiúsculas carrega sinal.

**Os nulos da silver são maiores que os da origem, de propósito.** O CSV tem 87.656 títulos e
58.247 comentários vazios; a silver registra 87.658 e 58.274. A diferença são 2 títulos e 27
comentários que continham **apenas espaço, tabulação ou caractere de controle**. O
`Text.Clean` e o `Text.Trim` os esvaziam, e o passo seguinte converte vazio para nulo, porque
texto sem conteúdo visível não é texto. É regra da camada, não defeito de carga.

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
**Grão:** um pedido — 99.441 linhas, igual a `silver.pedidos`.
**Origem:** `silver.pedidos`, enriquecida por `silver.itens_pedido` e `silver.avaliacoes`.

| Campo | Tipo | Definição |
|---|---|---|
| `sk_pedido` | bigint | Chave substituta |
| `id_pedido` | string | Chave natural da origem, mantida para rastreio |
| `sk_cliente` | bigint | Junta com `dim_cliente`. Sem nulos |
| `sk_geografia_destino` | bigint | Junta com `dim_geografia`. É o endereço do cliente |
| `uf_destino` | string | UF do cliente. **Nulo em 279 pedidos** — mesmos casos de `sk_geografia_destino` nulo, zero divergência entre os dois |
| `uf_origem` | string | UF do vendedor do item de maior preço no pedido — ver ADR-003. **Nulo nos mesmos 775 pedidos sem item** |
| `rota` | string | `uf_origem` + " → " + `uf_destino`, pronta pra uso em visual. **Nulo em 1.050 pedidos** — união dos nulos de origem e destino (só 4 pedidos são nulos nos dois ao mesmo tempo) |
| `sk_data_compra` | int | `yyyyMMdd`. Marco zero do funil |
| `sk_data_prevista` | int | `yyyyMMdd`. Prazo prometido ao cliente |
| `sk_data_entrega` | int | `yyyyMMdd`. **Nulo em 2.965 pedidos** não entregues |
| `status_pedido` | string | Oito valores da origem |
| `dias_ate_aprovacao` | int | Compra até aprovação do pagamento |
| `dias_ate_coleta` | int | Compra até coleta pela transportadora |
| `lead_time_dias` | int | Compra até entrega ao cliente |
| `dias_de_atraso` | int | Entrega real menos prevista. Negativo indica entrega adiantada |
| `entregue_no_prazo` | boolean | Verdadeiro quando a entrega ocorreu até a data prevista. Base do OTD |
| `nota` | int | De 1 a 5. Avaliação mais recente do pedido — ver ADR-002. **Nulo em 768 pedidos** |
| `valor_itens` | decimal | Soma do preço dos itens. Total: **13.591.643,70** |
| `valor_frete` | decimal | Soma do frete dos itens. Total: **2.251.909,54** |
| `qtd_itens` | int | Contagem de linhas de item |

**Pedido não entregue não é pedido atrasado.** Os 2.965 sem `data_entrega_real` têm
`sk_data_entrega`, `dias_de_atraso` e `entregue_no_prazo` **nulos**, nunca falso e nunca zero.
Falso significaria "atrasou", e pedido em trânsito ainda não atrasou. É o que faz o
denominador do OTD ser **96.476** e não 99.441.

**A comparação de prazo é feita em data, não em timestamp.** `data_entrega_prevista` vem com
hora `00:00:00` e `data_entrega_real` com hora real. Comparar as duas cruas marcaria como
atrasada toda entrega feita no dia do prazo depois da meia-noite. O fato aplica `DATE()` nos
dois lados.

**775 pedidos não têm nenhum item**, então `valor_itens`, `valor_frete`, `qtd_itens` e
`uf_origem`/`rota` ficam nulos — nunca zero, que diria "pedido de R$ 0,00" e contaminaria
ticket médio e frete sobre faturamento. A quebra por status explica 767 deles: 603
`unavailable` e 164 `canceled`. Os outros 8 são anomalia da origem — 5 `created`, 2 `invoiced`
e **1 `shipped`**, este último sem explicação de negócio possível.

**`uf_origem` (e por extensão `rota`) é uma aproximação em ≈1,3% dos pedidos.** Não existe "o
vendedor do pedido" nesta base, pelo mesmo motivo de não existir "a nota do pedido": um pedido
pode ter itens de mais de um vendedor — **1.278 de 98.666 pedidos com item** (os que sobram
depois dos 775 sem item nenhum). A regra (`ADR-003`): o vendedor do item de maior `preco`,
`numero_item` como desempate secundário. Nesses 1.278 casos, `uf_origem` reflete só o vendedor
"principal", não uma junção fiel de todas as origens reais do pedido — a origem exata por item
continua em `fato_item_pedido[sk_geografia_origem]`, no grão certo pra isso.

---

### `fato_item_pedido`

**Propósito:** o item de um pedido, com preço e frete próprios. Grão do custo de frete por
rota.
**Grão:** um item de um pedido — 112.650 linhas, igual a `silver.itens_pedido`.
**Origem:** `silver.itens_pedido`.

| Campo | Tipo | Definição |
|---|---|---|
| `sk_item` | bigint | Chave substituta |
| `id_pedido`, `numero_item` | string, int | Chave natural composta, mantida para rastreio |
| `sk_pedido` | bigint | Junta com `fato_entrega`. **Sem nulos** — nulo aqui seria fato órfão |
| `sk_produto` | bigint | Junta com `dim_produto`. Sem nulos |
| `sk_vendedor` | bigint | Junta com `dim_vendedor`. Sem nulos |
| `sk_geografia_origem` | bigint | Junta com `dim_geografia`. É o endereço do vendedor. **Nulo em 253 linhas** |
| `sk_data_limite_envio` | int | `yyyyMMdd`. Prazo do vendedor para despachar |
| `preco` | decimal | Preço do item. Total: **13.591.643,70** |
| `valor_frete` | decimal | Frete rateado no item. Total: **2.251.909,54** |
| `peso_gramas`, `volume_cm3` | int | Materializados da `dim_produto` — ver abaixo |

**A chave natural é `id_pedido` + `numero_item`, nunca `id_pedido` + `id_produto`.** O mesmo
produto aparece várias vezes no mesmo pedido, que é como a origem representa quantidade;
deduplicar por produto apagaria 10.225 linhas, 9% da tabela.

**`peso_gramas` e `volume_cm3` são desnormalização deliberada.** Custo por quilo é medida de
linha de item, e buscá-los na dimensão custaria uma junção em toda consulta de frete. Ficam
nulos nas **18 linhas** dos 2 produtos sem dimensão física.

**253 linhas não têm geografia de origem** — 7 vendedores cujo prefixo de CEP **nunca esteve
no arquivo de geolocalização**. É lacuna de cobertura da origem, e não rejeição por regra
nossa: os 31 de `geografia_rejeitados` são população diferente, medida e descartada por
coordenada inválida. Os 7 estão em cinco UFs, sem concentração. A `dim_vendedor` mantém
cidade e UF deles, então análise de rota por par de estados não é afetada — só o mapa.

---

### Dimensões

| Tabela | Grão | Linhas | Chave natural | Observação |
|---|---|---|---|---|
| `dim_calendario` | um dia | 1.096 | `data` | Gerada, 2016-01-01 a 2018-12-31. `sk_data` é `yyyyMMdd` — única chave inteligente do modelo |
| `dim_cliente` | uma pessoa | 96.096 | `id_cliente_unico` | SCD tipo 1. A geografia é a do pedido mais recente |
| `dim_vendedor` | um vendedor | 3.095 | `id_vendedor` | Cidade, UF e prefixo de CEP |
| `dim_produto` | um produto | 32.951 | `id_produto` | 610 sem categoria, 2 sem dimensão física |
| `dim_geografia` | um prefixo de CEP | 19.011 | `prefixo_cep` | Centroide em mediana. Serve os dois fatos em papéis opostos |

**Todas as chaves substitutas vêm de `ROW_NUMBER()` ordenado pela chave natural**, nunca de
`monotonically_increasing_id()`. A gold é reconstruída inteira a cada execução, com o modelo
semântico publicado em cima dela, então a chave precisa ser determinística. Onde a escolha da
linha depende de ordenação — a `dim_cliente` e a nota da `fato_entrega` —, há sempre um
critério de desempate que nunca empata.

**`dim_calendario` é dimensão de papel duplo.** Compra, prazo prometido e entrega apontam
para ela através de `sk_data_compra`, `sk_data_prevista` e `sk_data_entrega`. É por isso que
o fato guarda a data como **chave** e não como data: `sk_data_compra = 20170315` se lê como
identificador e não convida ninguém a agregar por ele direto no fato.

**`dim_cliente` é tipo 1, e o histórico se perde.** 250 pessoas têm mais de um prefixo de CEP,
122 mais de uma cidade e 39 mais de uma UF ao longo dos pedidos. O risco é contido porque o
**fato guarda a geografia do próprio pedido** — `sk_geografia_destino` vem do CEP daquele
`id_cliente`, não do CEP atual da pessoa. Análise de rota usa o fato e continua correta; a
dimensão responde "onde esta pessoa está hoje".

**`categoria_rotulo` da `dim_produto` deriva do código da origem** por
`INITCAP(REPLACE(categoria, '_', ' '))`. O `product_category_name_translation.csv` foi
descartado: traduz do português para o inglês, direção oposta à do projeto, e não virou
tabela silver — usá-lo obrigaria o notebook da gold a ler da bronze, pulando uma camada. O
rótulo fica imperfeito (`Cama Mesa Banho`, não `Cama, Mesa e Banho`), e a limitação é
registrada aqui em vez de escondida.

---

## Medidas do modelo semântico

| Medida | Definição de negócio | Cuidado |
|---|---|---|
| `Total de Pedidos` | Quantidade de pedidos — contagem de linhas de `fato_entrega` | — |
| `Pedidos Entregues` | Pedidos que chegaram ao destino | Filtra por `entregue_no_prazo` não nulo, não por `sk_data_entrega` — os dois ficam nulos juntos para pedido não entregue, mas o primeiro carrega o significado de negócio |
| `Pedidos no Prazo` | Pedidos entregues até a data prometida ao cliente | — |
| `Pedidos Cancelados` | Pedidos com status "canceled" | — |
| `OTD %` | Pedidos entregues até a data prevista sobre pedidos entregues | Denominador exclui pedidos não entregues |
| `Lead Time Médio` | Média de dias entre compra e entrega | Sensível a outliers — considerar mediana em paralelo |
| `Lead Time Mediano` | Mediana de dias entre compra e entrega | Complementa a média quando outliers distorcem o indicador |
| `Frete sobre Faturamento` | Soma de frete sobre soma do valor dos itens | Razão de somas, nunca média de razões — calcular por pedido e tirar a média distorce a favor de pedidos pequenos |
| `Valor de Itens` | Soma do valor dos itens do pedido | — |
| `Valor de Frete` | Soma do valor de frete do pedido | — |
| `Ticket Médio` | Valor médio de itens por pedido | — |
| `Dias até Aprovação (méd)` | Média de dias entre compra e aprovação do pagamento | — |
| `Dias até Coleta (méd)` | Média de dias entre aprovação e coleta pela transportadora | — |
| `Dias de Transporte (méd)` | Média de dias em trânsito, da coleta à entrega | Calculada por pedido antes de tirar a média — subtrair duas médias já prontas não dá o mesmo resultado (desigualdade de Jensen) |
| `Dias de Atraso (méd)` | Média de dias de atraso entre os pedidos atrasados | Filtra `dias_de_atraso > 0`, não apenas não-nulo — pedido adiantado não entra |
| `Nota Média` | Média da avaliação do cliente | Nula em 768 pedidos sem avaliação — `AVERAGE` já ignora nulos |
| `Pedidos Entregues (por Data de Entrega)` | `Pedidos Entregues` reagrupado pelo mês em que a entrega aconteceu, não pelo mês da compra | Usa o relacionamento inativo `sk_data_entrega`, via `USERELATIONSHIP` |
| `OTD % (por Data de Entrega)` | `OTD %` reagrupado pelo mês da entrega | Mesma técnica de `USERELATIONSHIP` — necessária para a evolução mensal fazer sentido pelo mês em que a entrega ocorreu |
| `Valor de Frete (Item)` | Soma do frete no grão de item, de `fato_item_pedido` | — |
| `Peso Total (kg)` | Soma do peso dos itens, convertido de gramas | — |
| `Custo por Quilo` | Valor de frete por quilo transportado | Escopo do Painel de Frete e Rotas (fase 5) — já existe no modelo, mas só passa a ser usada quando esse painel for construído |
| `Dias de Atraso (méd) por Vendedor` | `Dias de Atraso (méd)` filtrado pelo vendedor, mesmo sem relacionamento físico entre os fatos | Ponte virtual via `TREATAS` — evita reabrir a ambiguidade que motivou remover o relacionamento direto entre `fato_entrega` e `fato_item_pedido` |
| `Peso Total (kg) por Rota` | `Peso Total (kg)` filtrado por rota, mesma ponte virtual via `TREATAS`, direção oposta (de `fato_entrega` pra `fato_item_pedido`) | Escopo do Painel de Frete e Rotas (fase 5) — `rota` só existe em `fato_entrega`, peso só existe em `fato_item_pedido` |
| `Custo por Quilo (por Rota)` | `Valor de Frete` sobre `Peso Total (kg) por Rota` | Reaproveita `Valor de Frete` (já soma do frete dos itens) em vez de abrir uma segunda ponte só pro frete |
| `Rota Mais Cara por Kg` | Nome da rota (UF origem → UF destino) com o maior `Custo por Quilo (por Rota)` | Ignora rota em branco ou custo zero — ruído de pedido sem item completo |
| `Custo por Kg da Rota Mais Cara` | `Custo por Quilo (por Rota)` avaliado só pra rota de `Rota Mais Cara por Kg` | — |
| `Custo por Kg Médio (Top 10)` | Média de `Custo por Quilo (por Rota)` entre as 10 rotas de maior `Valor de Frete` | "Maior volume" = mesmo corte do treemap do Painel de Frete e Rotas |
| `Múltiplo Custo por Kg` | `Custo por Kg da Rota Mais Cara` sobre `Custo por Kg Médio (Top 10)` | Quantas vezes a rota mais cara por kg custa em relação à média das rotas de maior volume |
| `Insight Frete e Rotas` | Frase narrativa concatenando frete total, % sobre faturamento, rota mais cara por kg e o múltiplo | Medida de texto pro cartão de destaque do painel — mesmo padrão de `OTD % (Legend)` |
| `OTD % por Vendedor` | `OTD %` filtrado pelo vendedor, mesma ponte virtual via `TREATAS` de `Dias de Atraso (méd) por Vendedor` | Escopo do Painel de Atribuição de Causas (fase 5, item 5) — fecha lacuna encontrada no teste de aceite: não existia OTD por UF de origem, só por UF de destino |
| `Desvio OTD por Vendedor` | `OTD % por Vendedor` menos `OTD %` nacional, calculado por linha (por UF) | Usa o fato de `dim_vendedor` não ter relacionamento físico com `fato_entrega` — `[OTD %]` fica sempre no total nacional dentro de um visual com `dim_vendedor[uf]` no eixo, então a subtração já dá o desvio direto, sem precisar de `ALLSELECTED` |
| `Quantidade de Itens` | Contagem de linhas de `fato_item_pedido` | Medida de volume genérica — usada como critério de Top N nos visuais que cortam "as N categorias/rotas de maior volume" |
| `Pedidos Atrasados por Vendedor` | Contagem de pedidos com `dias_de_atraso > 0`, filtrada pelo vendedor via a mesma ponte `TREATAS` | Escopo do Painel de Atribuição de Causas — fecha a lacuna de contagem (existia só média de atraso por vendedor, não contagem) |
| `Nota Média por Categoria` | `Nota Média` filtrada pela categoria do produto, mesma ponte `TREATAS` — funciona porque a ponte propaga qualquer filtro que chegue em `fato_item_pedido`, não só o de vendedor | Escopo do Painel de Atribuição de Causas — fecha a lacuna de nota por categoria, que não existia em nenhum painel |
| `UF Mais Crítica (Vendedor)` | Nome da UF de origem (vendedor) com o menor `OTD % por Vendedor` | Ignora UF em branco ou OTD em branco — mesmo cuidado de `Rota Mais Cara por Kg` |
| `OTD % da UF Mais Crítica` | `OTD % por Vendedor` avaliado só pra UF de `UF Mais Crítica (Vendedor)` | Usa `MINX` sobre a tabela de ranking, não filtro por igualdade — evita o erro PLACEHOLDER já documentado |
| `Desvio OTD da UF Mais Crítica` | `OTD % da UF Mais Crítica` menos `OTD %` nacional | Negativo por definição — a UF mais crítica está sempre abaixo da média |
| `Pedidos Atrasados da UF Mais Crítica` | `Pedidos Atrasados por Vendedor` avaliado só pra UF de `UF Mais Crítica (Vendedor)` | Mesma técnica de ranking, coluna extra na mesma tabela em vez de nova ponte |
| `Categoria Mais Crítica (Nota)` | Nome da categoria com a menor `Nota Média por Categoria`, entre as 10 de maior volume (contagem de itens) | "Maior volume" aqui é contagem de itens, não valor de frete — corte análogo ao do Painel de Frete e Rotas, métrica diferente porque o contexto é outro |
| `Nota da Categoria Mais Crítica` | `Nota Média por Categoria` avaliada só pra categoria de `Categoria Mais Crítica (Nota)` | — |
| `Melhor Nota (Top 10 Categorias)` | Maior `Nota Média por Categoria` entre as 10 de maior volume | Base do comparativo "pior vs. melhor" no painel |
| `Diferença Nota vs Melhor Categoria` | `Melhor Nota (Top 10 Categorias)` menos `Nota da Categoria Mais Crítica` | — |
| `Insight Atribuição de Causas` | Frase narrativa concatenando UF mais crítica, seu OTD e desvio, pedidos atrasados, e a categoria com pior nota e sua diferença pra melhor | Medida de texto pro cartão de destaque do painel — mesmo padrão de `Insight Frete e Rotas` |

---

## Sinônimos para Q&A

> **Não aplicado no modelo.** Q&A e esquema linguístico não são suportados em modelo Direct
> Lake — testado e descartado em três contextos diferentes, ver `ADR-005`. A tabela abaixo
> fica como referência de intenção: se o Direct Lake ganhar suporte a Q&A no futuro, o
> mapeamento já está pronto pra virar configuração real sem trabalho de redescoberta.

### Tabelas

| Tabela | Sinônimos |
|---|---|
| `fato_entrega` | pedidos, entregas |
| `fato_item_pedido` | itens, itens de pedido, itens do pedido |
| `dim_cliente` | clientes, compradores |
| `dim_vendedor` | vendedores, lojistas, sellers |
| `dim_produto` | produtos, itens do catálogo |
| `dim_geografia` | geografia, localização, cidades, estados |
| `dim_calendario` | calendário, datas |

### Campos

| Campo | Tabela | Sinônimos | Por quê |
|---|---|---|---|
| `uf_origem` | `fato_entrega` | UF do vendedor, estado de origem, estado do vendedor, de onde saiu | "origem" sozinho é ambíguo com `uf_destino` — a pergunta precisa distinguir vendedor de cliente |
| `uf_destino` | `fato_entrega` | UF do cliente, estado de destino, estado do cliente, para onde foi | mesmo motivo, lado oposto |
| `rota` | `fato_entrega` | trajeto, trecho, caminho | variações comuns do termo já fechado no glossário |
| `dias_de_atraso` | `fato_entrega` | atraso, dias atrasado, quanto atrasou | — |
| `entregue_no_prazo` | `fato_entrega` | no prazo, pontual, dentro do prazo | — |
| `lead_time_dias` | `fato_entrega` | tempo de entrega, prazo de entrega, tempo até entregar | — |
| `nota` | `fato_entrega` | avaliação, satisfação, review, estrelas | escala 1–5; "estrelas" é o termo visual usado no painel |
| `status_pedido` | `fato_entrega` | situação do pedido, status | — |
| `uf` | `dim_vendedor`, `dim_cliente`, `dim_geografia` | estado, unidade federativa | mesmo papel semântico em três tabelas — cadastrar nas três, não só numa |
| `cidade` | `dim_geografia` | município | — |
| `categoria_rotulo` | `dim_produto` | categoria do produto, tipo de produto | — |
| `peso_gramas` | `dim_produto`, `fato_item_pedido` | peso | — |

### Medidas

| Medida | Sinônimos |
|---|---|
| `OTD %` | taxa de entrega no prazo, percentual on time, índice de pontualidade |
| `Lead Time Médio` | tempo médio de entrega, prazo médio de entrega |
| `Frete sobre Faturamento` | frete percentual, proporção de frete, frete sobre vendas |
| `Ticket Médio` | valor médio do pedido, ticket médio de venda |
| `Dias de Atraso (méd)` | atraso médio, média de atraso |
| `Custo por Quilo` | frete por quilo, custo de frete por peso |
| `Nota Média` | satisfação média, avaliação média |

### Campos a esconder do Q&A

Chaves substitutas (`sk_*`) e colunas de rastro (`id_pedido`, `numero_item` e afins) já estão
ocultas no modelo — Q&A não deveria sugeri-las como resposta padrão. Ao configurar o esquema
linguístico, confirmar que continuam ocultas: campo oculto não vira candidato de resposta
automática, mas ainda pode ser usado se alguém perguntar por ele explicitamente pelo nome.

### Perguntas de exemplo

Sem Q&A pra testar contra, essas perguntas viram diretamente o material do teste de aceite da
fase (item 5 do plano) — respondidas navegando o relatório e o dicionário, não digitadas numa
caixa de busca.

- "Qual o OTD por UF de origem?"
- "Quantos pedidos atrasados por estado do vendedor?"
- "Qual o lead time médio por mês?"
- "Qual a nota média por categoria de produto?"
- "Qual o frete sobre faturamento por rota?"

---

## Glossário de termos

| Termo | Significado neste projeto |
|---|---|
| **OTD** | On-Time Delivery. Percentual de pedidos entregues dentro do prazo prometido ao cliente |
| **Lead time** | Tempo decorrido entre dois marcos do funil de entrega |
| **Rota** | Par UF de origem do vendedor → UF de destino do cliente |
| **Frete percentual** | Custo de frete como proporção do valor dos itens |
| **Prefixo de CEP** | Cinco primeiros dígitos, granularidade da geolocalização na origem |
