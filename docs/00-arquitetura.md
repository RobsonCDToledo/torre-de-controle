# Arquitetura

Desenho completo da plataforma, com o contrato de cada camada e o modelo dimensional.

---

## Contrato das camadas

Cada camada tem uma promessa. O que ela garante, e o que ela explicitamente não garante.

### Bronze — `lh_bronze`

**Promessa:** o arquivo como chegou, com rastro de quando chegou.

- Armazenado em `Files/`, não em tabelas — sem imposição de esquema
- Particionado por data de ingestão: `Files/olist/<data_ingestao>/<arquivo>`
- Nenhuma tipagem, nenhuma limpeza, nenhum descarte de linha
- Imutável: uma execução nunca sobrescreve a anterior

**Não garante:** tipos corretos, ausência de duplicatas, integridade referencial.

Se um dado parece errado na gold, a bronze é onde se prova se ele já veio errado da origem.
Essa é a única razão de a camada existir.

### Silver — `lh_silver`

**Promessa:** uma tabela Delta por origem, tipada, deduplicada e nomeada em português.

- Tipos explícitos, com datas como `timestamp` e valores como `decimal`
- Deduplicação pela chave natural de cada origem
- Nomes de coluna em português, legíveis por analista de negócio
- Colunas de qualidade: `_ingerido_em`, `_origem_arquivo`
- Registros que falham nas regras não são apagados — vão para tabelas `_rejeitados`

**Não garante:** modelo dimensional, agregações, regras de negócio.

A silver é fiel à origem em conteúdo, mas confiável em forma. É a camada onde a
agregação da geolocalização acontece — visível e reversível, não escondida na origem.

### Gold — `lh_gold`

**Promessa:** esquema estrela pronto para consumo, com regras de negócio aplicadas.

- Fatos e dimensões, com chaves substitutas
- Indicadores de negócio materializados (OTD, lead time por etapa, dias de atraso)
- Tabela de atributos para ML, com grão e recorte temporal próprios
- Documentada no dicionário de dados

**Não garante:** ser a única forma de ver o dado. Analistas com perguntas fora do modelo
usam o endpoint SQL sobre a silver.

---

## Modelo dimensional

### Fatos

**`fato_entrega`** — grão: um pedido.

O fato central da Torre de Controle. Cada linha é um pedido com sua história de entrega.

| Campo | Papel |
|---|---|
| `sk_pedido` | Chave substituta |
| `id_pedido` | Chave natural (degenerada, para rastreio) |
| `sk_cliente`, `sk_data_compra`, `sk_data_prevista`, `sk_data_entrega` | Chaves estrangeiras |
| `sk_geografia_destino` | Geografia do cliente |
| `status_pedido` | Dimensão degenerada — cardinalidade baixa demais para tabela própria |
| `dias_ate_aprovacao`, `dias_ate_coleta`, `dias_ate_entrega` | Lead time por etapa do funil |
| `dias_de_atraso` | Positivo se entregue depois do previsto, negativo se adiantado |
| `entregue_no_prazo` | Flag booleana — base do OTD |
| `valor_frete_total`, `valor_itens_total` | Somas do grão de item |
| `qtd_itens`, `qtd_vendedores` | Contagens |

**`fato_item_pedido`** — grão: um item de um pedido.

Existe porque preço, frete e vendedor variam por item — e um pedido pode ter itens de
vendedores diferentes. Sem esse grão, custo de frete por rota fica errado.

| Campo | Papel |
|---|---|
| `sk_item` | Chave substituta |
| `sk_pedido`, `sk_produto`, `sk_vendedor`, `sk_geografia_origem` | Chaves estrangeiras |
| `preco`, `valor_frete` | Medidas aditivas |
| `peso_gramas`, `volume_cm3` | Do produto, materializados para cálculo de custo por kg |

### Dimensões

| Dimensão | Grão | Observação |
|---|---|---|
| `dim_calendario` | Dia | Gerada, não derivada da origem. Cobre 2016–2018 com folga. Colunas em português, com ano, trimestre, mês, semana, dia da semana, feriado e flag de dia útil |
| `dim_cliente` | `customer_unique_id` | Note: a origem tem dois identificadores. `customer_id` muda a cada pedido; `customer_unique_id` é a pessoa. A dimensão usa o segundo |
| `dim_vendedor` | `seller_id` | Cidade, UF e prefixo de CEP |
| `dim_produto` | `product_id` | Categoria traduzida para português, peso, dimensões e volume calculado |
| `dim_geografia` | Prefixo de CEP | Centroide de latitude e longitude, cidade, UF e região. É aqui que o milhão de linhas de geolocalização vira cerca de 19 mil |

### Por que duas tabelas de fato e não uma

Seria possível achatar tudo no grão de item. Não fizemos porque OTD é atributo do pedido,
não do item: contar OTD sobre uma tabela no grão de item multiplica cada pedido pelo número
de itens e distorce o indicador em favor de pedidos grandes.

Manter os dois grãos e ligar por `sk_pedido` mantém cada indicador no nível em que ele é
verdadeiro. É a decisão que mais protege a corretude dos números.

---

## Indicadores

Materializados na gold ou calculados em DAX no modelo semântico, conforme o custo.

| Indicador | Definição |
|---|---|
| **OTD** | Pedidos entregues até a data prevista ÷ pedidos entregues |
| **Lead time médio** | Média de dias entre compra e entrega ao cliente |
| **Lead time por etapa** | Decomposição em aprovação, coleta e transporte |
| **Dias de atraso médio** | Média de `dias_de_atraso` entre os pedidos atrasados |
| **Custo de frete** | Soma de `valor_frete` |
| **Frete sobre faturamento** | Frete ÷ valor dos itens — o "frete percentual" da operação |
| **Custo por quilo** | Frete ÷ peso, por rota |
| **Taxa de cancelamento** | Pedidos cancelados ÷ total |
| **Nota média de avaliação** | Proxy de qualidade percebida, correlacionável com atraso |

---

## Camada de consumo

**Modelo semântico em Direct Lake** sobre `lh_gold`. Um único modelo alimenta os dois
relatórios — requisito do projeto e boa prática: um modelo, muitos relatórios.

**Painel Executivo de Entregas** — OTD, lead time, evolução mensal, mapa por UF de destino,
decomposição de atraso por etapa e por rota.

**Painel de Frete e Rotas** — custo de frete por rota UF origem → UF destino, frete sobre
faturamento, custo por quilo, dispersão e outliers, top rotas por custo.

**Self-service** — o modelo publicado com permissão de build, endosso aplicado, RLS por UF,
mais o endpoint SQL da gold para quem prefere consultar direto. Detalhado em
`05-self-service.md`.

**Perguntas nativas** — sinônimos, descrições de campo e esquema linguístico configurados
no modelo. Detalhado em `06-perguntas-nativas.md`.

---

## Machine learning

**Problema:** prever se um pedido vai atrasar, no momento da compra.

**Alvo:** `entregue_no_prazo`, binário.

**A restrição que define o projeto:** só entram atributos conhecidos **no instante da
compra**. Isso exclui `order_approved_at`, `order_delivered_carrier_date` e qualquer
derivado deles — eventos que acontecem depois e que, se usados, produziriam um modelo
excelente e completamente inútil.

Atributos candidatos: UF de origem e destino, flag de mesma UF, distância entre centroides,
peso e volume do produto, valor do frete, preço, categoria, mês e dia da semana da compra,
quantidade de itens, e taxa histórica de pontualidade do vendedor calculada com janela
temporal anterior à compra.

Essa última exige cuidado: calcular a taxa do vendedor sobre o conjunto inteiro vazaria
informação do futuro para o passado. A janela precisa ser estritamente anterior a cada
pedido.

**Registro:** MLflow, nativo no Fabric. Métricas, parâmetros e importância de atributos
ficam versionados junto ao experimento.

**Saída:** predições escritas de volta na gold, disponíveis ao modelo semântico — de modo
que o painel possa comparar atraso previsto e atraso realizado.
