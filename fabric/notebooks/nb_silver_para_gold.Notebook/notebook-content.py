# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "54fe162c-166b-4a5e-b222-c896510adbe3",
# META       "default_lakehouse_name": "lh_gold",
# META       "default_lakehouse_workspace_id": "528a4166-a694-4105-90bd-d6509fcc0536",
# META       "known_lakehouses": [
# META         {
# META           "id": "f6b1f2f6-b88e-4122-898d-b8fc04b30459"
# META         },
# META         {
# META           "id": "54fe162c-166b-4a5e-b222-c896510adbe3"
# META         }
# META       ]
# META     }
# META   }
# META }

# MARKDOWN ********************

# # nb_silver_para_gold
# 
# Constrói o esquema estrela da camada gold a partir das tabelas da silver.
# 
# É o terceiro e último passo do desenho de uma ferramenta por camada, registrado no
# [ADR-001](../../docs/decisoes/ADR-001-ferramenta-por-camada.md): o **pipeline** ingere,
# o **dataflow** padroniza, o **notebook** modela. Aqui é onde a regra de negócio entra —
# até a silver, o dado era fiel à origem em conteúdo.
# 
# ---
# ## Pré-requisitos
# 
# **Conecta com lh_gold**
#  
#  Anexar o lh_gold
#  No painel esquerdo do notebook, na seção Lakehouses (Explorer), clique em + Adicionar → Lakehouse existente → lh_gold.
#  Depois de conectado ao LakeHouse gold, tornar ele o default.  e usar o silver apenas para fazer call das tabelas silver. 
# 
# ---
# 
# ## O que este notebook constrói
# 
# **Cinco dimensões**
# 
# | Tabela | Grão | Origem | Linhas |
# |---|---|---|---|
# | `dim_calendario` | dia | gerada, 2016-01-01 a 2018-12-31 | 1.096 |
# | `dim_geografia` | prefixo de CEP | `silver.geografia` | 19.011 |
# | `dim_cliente` | pessoa (`id_cliente_unico`) | `silver.clientes` + `silver.pedidos` | 96.096 |
# | `dim_vendedor` | vendedor | `silver.vendedores` | 3.095 |
# | `dim_produto` | produto | `silver.produtos` | 32.951 |
# 
# **Dois fatos**
# 
# | Tabela | Grão | Origem | Linhas |
# |---|---|---|---|
# | `fato_entrega` | um pedido | `silver.pedidos` + agregação de itens + `silver.avaliacoes` | 99.441 |
# | `fato_item_pedido` | um item de um pedido | `silver.itens_pedido` | 112.650 |
# 
# **Por que dois grãos e não um:** OTD é atributo do pedido, não do item. Achatar tudo no
# grão de item multiplicaria cada pedido pelo número de itens e distorceria o indicador em
# favor dos pedidos grandes. É a decisão que mais protege a corretude dos números.
# 
# ---
# 
# ## Contrato de execução
# 
# **Lê apenas da silver.** Nenhuma célula toca a bronze — inclusive quando isso custa uma
# funcionalidade, como o alias de categoria em inglês, que exigiria pular uma camada.
# 
# **Reconstrói tudo, sempre.** Todas as escritas usam `mode("overwrite")`. A gold é derivada:
# reconstruir é mais simples de auditar que atualizar incrementalmente, e garante que os dois
# fatos apontem para a mesma geração de chaves das dimensões.
# 
# **A ordem das células importa.** As dimensões nascem antes dos fatos porque os fatos
# consomem as chaves substitutas delas. E `fato_entrega` vem antes de `fato_item_pedido`,
# porque é ela que gera o `sk_pedido` que o item busca. Executar o notebook fora de ordem
# produz fato órfão sem levantar erro — por isso é um notebook só, e não sete.
# 
# ---
# 
# ## Decisões que valem para todas as células
# 
# **Chave substituta por `row_number()` ordenado pela chave natural**, nunca
# `monotonically_increasing_id()`. O segundo produz chaves não contíguas e diferentes a cada
# execução; como a gold é reconstruída com o modelo semântico já publicado em cima dela, a
# chave precisa ser determinística.
# 
# A única exceção é `dim_calendario`, cujo `sk_data` é `yyyyMMdd`. Em dimensão de data essa
# chave inteligente é convenção consolidada, deixa o fato legível — `sk_data_compra = 20170315`
# — e nunca colide.
# 
# **Nulo é preservado.** Nenhum campo recebe valor padrão para preencher buraco: pedido sem
# data de entrega, produto sem categoria e pedido sem avaliação continuam nulos. A ausência
# do dado é informação, e substituí-la por zero contaminaria os indicadores.


# MARKDOWN ********************

# ## Configurações do Notebook

# CELL ********************

from pyspark.sql import functions as F
from pyspark.sql.window import Window
from datetime import date, datetime

SILVER = "`Torre-de-Controle`.lh_silver.dbo"

def silver(tabela):
    return spark.read.table(f"{SILVER}.{tabela}")


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# # dim_calendario
# 
# **Grão:** um dia. **Origem:** gerada, 2016-01-01 a 2018-12-31.
# **Alimenta:** `fato_entrega` em três papéis — compra, prevista e entrega.
# 
# **Decisões:** `sk_data` no formato `yyyyMMdd`, única exceção à regra de chave
# sequencial. Feriados calculados pelo cômputo da Páscoa em vez de lista fixa,
# para que a janela de datas possa mudar sem reescrever a célula.
# 
# **Validação:** 1.096 linhas — 366 de 2016, bissexto, mais 365 de cada outro ano.


# CELL ********************

# Parâmetros de período automaticos
#
# ano_atual  = date.today().year
# start = date(ano_atual -2, 1, 1)
# end   = date(ano_atual, 12, 31)
#
# ============================================================
# Parâmetros de período manual
#
# start = "2016-01-01"
# end = "2018-12-31"
#
# ============================================================

# Datas Manuais aplicadas para analise dos dados do projeto atual 

start = datetime.strptime('2016-01-01','%Y-%m-%d')
end   = datetime.strptime('2018-12-31','%Y-%m-%d')

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Criação do range de datas a partir da data inicial e data final

calendar_auto = spark.sql(f"""
    SELECT explode(
        sequence(
            to_date('{start}'),
            to_date('{end}'),
            interval 1 day
        )
    ) AS data
""")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Funções de feriados (equivalente à função de Gauss / EhFeriado / NomeFeriado)
# Em vez de UDF por linha, calculamos os feriados só para os anos do período
# e depois fazemos um join — é bem mais barato no Spark.

def calcular_pascoa(ano: int) -> date:
    a = ano % 19
    b = ano // 100
    c = ano % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = (h + l - 7 * m + 114) % 31 + 1
    return date(ano, mes, dia)

def feriados_do_ano(ano: int):
    pascoa = calcular_pascoa(ano)
    sexta_santa      = pascoa - pd_timedelta(2)
    segunda_carnaval = pascoa - pd_timedelta(48)
    terca_carnaval   = pascoa - pd_timedelta(47)
    corpus_christi   = pascoa + pd_timedelta(60)

    fixos = [
        (date(ano, 1, 1),   'Confraternização Universal'),
        (date(ano, 4, 21),  'Tiradentes'),
        (date(ano, 5, 1),   'Dia do Trabalhador'),
        (date(ano, 9, 7),   'Independência do Brasil'),
        (date(ano, 10, 12), 'Nossa Senhora Aparecida'),
        (date(ano, 11, 2),  'Finados'),
        (date(ano, 11, 15), 'Proclamação da República'),
        (date(ano, 12, 25), 'Natal'),
    ]
    moveis = [
        (sexta_santa,      'Sexta-feira Santa'),
        (pascoa,           'Páscoa'),
        (segunda_carnaval, 'Segunda-feira de Carnaval'),
        (terca_carnaval,   'Terça-feira de Carnaval'),
        (corpus_christi,   'Corpus Christi'),
    ]
    return fixos + moveis

# helper simples sem depender de pandas
from datetime import timedelta as pd_timedelta

anos = list(range(start.year, end.year + 1))
lista_feriados = [f for ano in anos for f in feriados_do_ano(ano)]

feriados_df = spark.createDataFrame(lista_feriados, ['data', 'nome_feriado'])


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Dicionario com meses e dias em PT-BR

meses_pt = {1:'Janeiro',2:'Fevereiro',3:'Março',4:'Abril',5:'Maio',6:'Junho',
            7:'Julho',8:'Agosto',9:'Setembro',10:'Outubro',11:'Novembro',12:'Dezembro'}

# dayofweek do Spark: 1=Domingo ... 7=Sábado
dias_pt = {1:'Domingo',2:'Segunda-feira',3:'Terça-feira',4:'Quarta-feira',
           5:'Quinta-feira',6:'Sexta-feira',7:'Sábado'}

# mapear Meses e dias para acrescentar na tabela

mapa_mes = F.create_map([F.lit(x) for kv in meses_pt.items() for x in kv])
mapa_dia = F.create_map([F.lit(x) for kv in dias_pt.items() for x in kv])

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Dataset com acrescimo das colunas principais de analise
calendar_auto = (calendar_auto
    .withColumn('sk_data', F.date_format('data', 'yyyyMMdd').cast('int'))
    .withColumn('ano', F.year('data'))
    .withColumn('mes', F.month('data'))
    .withColumn('anomes', (F.col('ano') * 100 + F.col('mes')).cast('int'))
    .withColumn('nome_do_mes', mapa_mes[F.col('mes')])
    .withColumn('_num_trimestre', F.quarter('data'))
    .withColumn('anotrimestre', (F.col('ano') * 100 + F.col('_num_trimestre')).cast('int'))
    .withColumn('semana_ano',
        F.ceil((F.dayofyear('data') + F.dayofweek(F.trunc('data', 'year')) -1)/ 7))
    .withColumn('semana_mes',
        F.ceil((F.dayofmonth('data') + F.dayofweek(F.trunc('data', 'month')) -1)/ 7))
    .withColumn('dia', F.dayofmonth('data'))
    .withColumn('nome_do_dia', mapa_dia[F.dayofweek('data')])
)

# Coluna abreviada de trimestre (add 'Sufixo º Tri')
calendar_auto = (calendar_auto
    .withColumn('trimestre', F.concat(F.col('_num_trimestre'), F.lit('ºTri'))))

# Coluna abreviada com 3 caracteres para nome do mês e nome do dia
calendar_auto = (calendar_auto
    .withColumn('mes_abreviado', F.substring('nome_do_mes', 1, 3))
    .withColumn('dia_semana_abreviado', F.substring('nome_do_dia',1 ,3)))

# trimestre_do_ano no padrão '1ºTri-26'
calendar_auto = (calendar_auto
    .withColumn('trimestre_do_ano',
    F.concat(F.col('trimestre'), F.lit('-'), F.substring(F.col('ano').cast('string'), 3, 2)))
)
# Nome da semana do mês ('1º - Sem' ... '6º - Sem')
calendar_auto = (calendar_auto
.withColumn('semana_do_mes',
    F.concat(F.col('semana_mes').cast('string'), F.lit('º - Sem')))
)

# Remover coluna de trimestre inutilizavel

calendar_auto = calendar_auto.drop('_num_trimestre')



# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Join da tabela calendário criada acima com as colunas de feriado e dia util. 

calendar_auto = (calendar_auto
    .join(feriados_df, on='data', how='left')
    .withColumn('feriado', F.col('nome_feriado').isNotNull())
    .withColumn('nome_feriado', F.coalesce(F.col('nome_feriado'), F.lit('')))
    .withColumn('fim_de_semana', F.dayofweek('data').isin(1, 7))
    .withColumn('tipo_dia',
        F.when(F.col('feriado'), 'Feriado')
        .when(F.col('fim_de_semana'), 'Fim de Semana')
        .otherwise('Dia Útil'))
    .withColumn('dia_util', F.col('tipo_dia') == 'Dia Útil')
)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# ordenar as colunas e deixa a chave na frente e renomeia para dim_calendario de fato
dim_calendario = calendar_auto.select(
    "sk_data", "data",
    "ano", "anotrimestre", "trimestre", "trimestre_do_ano",
    "mes", "anomes", "nome_do_mes", "mes_abreviado",
    "semana_ano", "semana_mes", "semana_do_mes",
    "dia", "nome_do_dia", "dia_semana_abreviado",
    "feriado", "nome_feriado", "fim_de_semana", "tipo_dia", "dia_util",
)

# Escreve a tabela no banco
dim_calendario.write.mode('overwrite').option('overwriteSchema', 'true').saveAsTable('dim_calendario')


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# # dim_vendedor
# 
# **Grão:** Um vendedor por linha.  
# **Origem:** silver.vendedores - 3.095 linhas   
# **Chave natural:** id_vendedor  
# **Alimenta:** `fato_item_pedido` via `sk_vendedor`. A UF daqui é a **origem** da rota;
# o destino vem de `dim_cliente` através de `fato_entrega`.  
# **Validação:** 3.095 linhas, `sk_vendedor` de 1 a 3.095 sem buraco.
# 


# CELL ********************

# Chama e monta a tabela com a chave sk_vendedor

dim_vendedor = spark.sql(f"""
    SELECT ROW_NUMBER() OVER (ORDER BY id_vendedor) AS sk_vendedor,
    id_vendedor,
    prefixo_cep,
    cidade,
    uf
    FROM {SILVER}.vendedores
""")

# Escreve a tabela no banco
dim_vendedor.write.mode('overwrite').option('overwriteSchema', 'true').saveAsTable('dim_vendedor')

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# # dim_geografia
# 
# - **Grão:** um prefixo de CEP
# - **Origem:** `silver.geografia` — 19.011 linhas
# - **Chave natural:** `prefixo_cep`
# 
# **Alimenta os dois fatos, em papéis opostos:** `fato_entrega` pelo `sk_geografia_destino`,
# que é o endereço do cliente, e `fato_item_pedido` pelo `sk_geografia_origem`, que é o do
# vendedor. O par das duas UFs é o que define uma rota.
# 
# **Decisões desta célula**
# 
# `regiao` não existe na origem — deriva da UF por `CASE`. É o agrupamento que a análise usa
# antes de descer ao par de estados.
# 
# O `CASE` vai **sem `ELSE`**. As 27 UFs estão completas hoje, então qualquer valor que caia
# fora é genuinamente desconhecido, e nulo o torna visível. `ELSE uf` colocaria "SP" na coluna
# `regiao` sem que ninguém percebesse — falha disfarçada de dado.
# 
# **Herdado da silver, não decidido aqui**
# 
# O centroide é mediana e não média, e cidade e UF são o valor mais frequente do prefixo.
# As duas regras e os números que as sustentam estão no
# [dicionário](../../docs/dicionario-de-dados.md).
# 
# **Quatro prefixos não existem nesta dimensão** — `18243`, `78131`, `83252` e `95130` —
# porque todas as coordenadas deles são inválidas na origem. Junção nula ali é limite do
# dataset, não falha do pipeline. Afeta 1 cliente e 0 vendedores.
# 
# **Validação:** 19.011 linhas e **nenhuma `regiao` nula**. Nulo ali significa UF fora das 27,
# e o `CASE` sem `ELSE` devolve isso em silêncio — vale um `WHERE regiao IS NULL` depois de
# gravar.


# CELL ********************

# Chama e monta a tabela com a chave sk_geografia

dim_geografia = spark.sql(f"""
    SELECT ROW_NUMBER() OVER (ORDER BY prefixo_cep) AS sk_geografia,
    prefixo_cep,
    latitude,
    longitude,
    cidade,
    uf,
    CASE
        WHEN uf IN ('AC','AP','AM','PA','RO','RR','TO') THEN 'Norte'
        WHEN uf IN ('AL','BA','CE','MA','PB','PE','PI','RN','SE') THEN 'Nordeste'
        WHEN uf IN ('DF','GO','MT','MS') THEN 'Centro-Oeste'
        WHEN uf IN ('ES','MG','RJ','SP') THEN 'Sudeste'
        WHEN uf IN ('PR','RS','SC') THEN 'Sul'
    END AS regiao
    FROM {SILVER}.geografia
""")
# Escreve a tabela no banco
dim_geografia.write.mode('overwrite').option('overwriteSchema', 'true').saveAsTable('dim_geografia')

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# # dim_produto
# 
# - **Grão:** um produto
# - **Origem:** `silver.produtos` — 32.951 linhas
# - **Chave natural:** `id_produto`
# 
# **Alimenta:** `fato_item_pedido` via `sk_produto`. É a única dimensão que também entrega
# **medida** ao fato — `peso_gramas` e `volume_cm3` são materializados lá para o custo por
# quilo não precisar atravessar a dimensão.
# 
# **Decisões desta célula**
# 
# `categoria_rotulo` não existe na origem — deriva do próprio código por
# `INITCAP(REPLACE(categoria, '_', ' '))`, que transforma `cama_mesa_banho` em
# `Cama Mesa Banho`. O dataset traz um `product_category_name_translation.csv`, e ele foi
# **descartado**: traduz do português para o **inglês**, direção oposta à que o projeto usa, e
# não virou tabela silver — ficou em `Files/` na bronze. Usá-lo obrigaria este notebook a ler
# da bronze, pulando uma camada. O rótulo fica imperfeito (`Cama Mesa Banho`, não
# `Cama, Mesa e Banho`) e a limitação está registrada no dicionário em vez de escondida.
# 
# `volume_cm3` é `comprimento_cm * altura_cm * largura_cm`. Calculado aqui e não no fato
# porque é atributo do produto, não da venda.
# 
# **As colunas de anúncio ficam** — `tamanho_nome`, `tamanho_descricao` e `qtd_fotos` não
# descrevem o produto físico, descrevem como ele foi anunciado. Entram porque a **fase 6 lê da
# gold**: deixá-las fora obrigaria o notebook de ML a buscar na silver, que é a mesma violação
# de camada que descartou o arquivo de tradução.
# 
# **Nulo propaga sozinho, e é por isso que não há `COALESCE` aqui.** Qualquer expressão que
# toca nulo devolve nulo: os **610 produtos sem categoria** saem com `categoria_rotulo` nulo e
# os **2 sem dimensão** saem com `volume_cm3` nulo. Nenhum é descartado — são produtos válidos,
# e removê-los deixaria item de pedido órfão. Os 2 sem peso simplesmente não entram no custo
# por quilo.
# 
# **Validação:** 32.951 linhas, `sk_produto` de 1 a 32.951 sem buraco, **exatamente 610**
# `categoria_rotulo` nulos e **exatamente 2** `volume_cm3` nulos. Os dois últimos números são
# a prova de que a propagação funcionou — se vierem zerados, algum `COALESCE` entrou sem ser
# convidado.


# CELL ********************

# Chama e monta a tabela com a chave sk_produto

dim_produto = spark.sql(f"""
    SELECT ROW_NUMBER() OVER (ORDER BY id_produto) AS sk_produto,
    id_produto,
    categoria,
    INITCAP(REPLACE(categoria, '_', ' ')) AS categoria_rotulo,
    tamanho_nome,
    tamanho_descricao,
    qtd_fotos,
    peso_gramas,
    comprimento_cm,
    altura_cm,
    largura_cm,
    (comprimento_cm * altura_cm * largura_cm) AS volume_cm3
    FROM {SILVER}.produtos
""")
# Escreve a tabela no banco
dim_produto.write.mode('overwrite').option('overwriteSchema', 'true').saveAsTable('dim_produto')

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# # dim_cliente
# 
# - **Grão:** uma pessoa
# - **Origem:** `silver.clientes` — 99.441 linhas — cruzada com `silver.pedidos`
# - **Chave natural:** `id_cliente_unico` — 96.096 distintos
# 
# **Alimenta:** `fato_entrega` via `sk_cliente`. A UF daqui é o **destino** da rota; a origem
# vem de `dim_vendedor` através de `fato_item_pedido`.
# 
# **Decisões desta célula**
# 
# **A origem tem dois identificadores, e confundi-los quebra a dimensão.** `id_cliente` muda a
# cada pedido — são 99.441 deles para 96.096 pessoas. `id_cliente_unico` é a pessoa. A
# dimensão usa o segundo, e é por isso que ela tem 3.345 linhas a menos que a tabela de origem.
# O fato continua chegando pelo `id_cliente`, que é o que o pedido carrega, e a tradução de um
# para o outro acontece nesta célula.
# 
# **A geografia vem do pedido mais recente.** Como `id_cliente` é por pedido, a mesma pessoa
# pode aparecer com endereços diferentes ao longo do tempo: **250 pessoas com mais de um
# prefixo de CEP**, 122 com mais de uma cidade, 39 com mais de uma UF. A dimensão é
# **SCD tipo 1** — guarda o estado atual e não o histórico —, e "atual" aqui é o endereço do
# pedido de `data_compra` mais recente, resolvido por `ROW_NUMBER()` particionado pela pessoa.
# É por isso que esta célula precisa de `silver.pedidos`: sem a data não há como saber qual dos
# endereços é o último.
# 
# **O que se perde com o tipo 1, e por que aceitar.** Uma análise que filtrasse por UF do
# cliente atribuiria à UF atual pedidos entregues no endereço antigo. O risco é contido porque
# **o fato guarda a geografia do próprio pedido** — `fato_entrega` monta o
# `sk_geografia_destino` a partir do CEP daquele `id_cliente`, não do CEP atual da pessoa.
# Análise de rota usa o fato e continua correta; a dimensão responde "onde esta pessoa está
# hoje". Guardar o histórico exigiria SCD tipo 2, com vigência por linha, e o ganho não paga a
# complexidade num dataset de 24 meses.
# 
# **Validação:** 96.096 linhas, `sk_cliente` de 1 a 96.096 sem buraco, e **nenhum
# `id_cliente_unico` repetido** — o número que prova que a deduplicação por pessoa aconteceu.
# Se vier 99.441, a dimensão está no grão errado e todo indicador por cliente vai contar
# pedido, não gente.


# CELL ********************

# Chama e monta a tabela com a chave sk_cliente
dim_cliente = spark.sql(f"""

WITH 

ranqueados AS (
    SELECT 
        c.id_cliente_unico,
        c.prefixo_cep,
        c.cidade,
        c.uf,
        ROW_NUMBER() OVER (PARTITION BY c.id_cliente_unico ORDER BY p.data_compra DESC, p.id_pedido DESC) AS ordem
    FROM {SILVER}.clientes AS c
    LEFT JOIN {SILVER}.pedidos AS p
    ON p.id_cliente = c.id_cliente
)
SELECT 
    ROW_NUMBER() OVER (ORDER BY id_cliente_unico) AS sk_cliente,
    id_cliente_unico,
    prefixo_cep,
    cidade,
    uf
FROM ranqueados
WHERE ordem = 1
""")

# Escreve a tabela no banco
dim_cliente.write.mode('overwrite').option('overwriteSchema', 'true').saveAsTable('dim_cliente')

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# # fato_entrega
# 
# - **Grão:** um pedido
# - **Origem:** `silver.pedidos` — 99.441 linhas — enriquecida por `silver.itens_pedido` e
#   `silver.avaliacoes`
# - **Chave natural:** `id_pedido`
# 
# **É a tabela central do projeto.** OTD, lead time e atraso saem daqui, e o `sk_pedido` que
# ela gera é o que `fato_item_pedido` consome — por isso esta célula roda antes daquela.
# 
# **Decisões desta célula**
# 
# **Pedido não entregue não é pedido atrasado.** 2.965 pedidos não têm `data_entrega_real` —
# estão em trânsito, cancelados ou indisponíveis. `dias_de_atraso` e `entregue_no_prazo` ficam
# **nulos** para eles, nunca falso e nunca zero. Falso significaria "atrasou", e um pedido em
# trânsito ainda não atrasou. É essa escolha que faz o denominador do OTD ser **96.476** e não
# 99.441 — contá-los como atrasados inflaria o indicador contra a operação.
# 
# **`dias_de_atraso` é `data_entrega_real - data_entrega_prevista`**, em dias. Negativo
# significa entrega adiantada, e o sinal é deliberado: a distribuição inteira interessa, não só
# o lado ruim.
# 
# **A nota da avaliação: a mais recente.** Não existe "a nota do pedido" nesta origem — 547
# pedidos têm mais de uma avaliação, e 768 não têm nenhuma. Os sem avaliação ficam **nulos**,
# jamais zero: zero seria lido como nota péssima e afundaria a média de qualidade percebida.
# Para os com mais de uma, vale a de `data_avaliacao` mais recente, que é a opinião final do
# cliente. Média e menor nota foram consideradas; o registro da escolha e das alternativas está
# no ADR desta decisão.
# 
# **As datas viram chave, não ficam como data.** `sk_data_compra` e `sk_data_entrega` são
# `date_format(data, 'yyyyMMdd')` convertido para inteiro, para casar com o `sk_data` da
# `dim_calendario`. É trabalho extra e é deliberado: com três papéis de data no mesmo fato,
# uma coluna visivelmente **chave** impede que alguém agregue pela data crua e quebre o papel
# duplo da dimensão no modelo semântico.
# 
# **Os valores vêm agregados dos itens.** `valor_itens`, `valor_frete` e `qtd_itens` são somas
# de `silver.itens_pedido` reduzidas ao grão de pedido. Somar frete aqui é legítimo porque a
# origem já entrega o frete **rateado por item** — não é o frete do pedido repetido em cada
# linha, que é o erro clássico dessa agregação.
# 
# **Validação, em três números que precisam bater juntos:**
# - **99.441 linhas** — igual a `silver.pedidos`. Qualquer número maior significa que a junção
#   com itens ou avaliações multiplicou o pedido, e é o defeito mais provável desta célula.
# - **96.476** com `data_entrega_real` preenchida.
# - `SUM(valor_itens)` = **13.591.643,70** e `SUM(valor_frete)` = **2.251.909,54** — os mesmos
#   totais medidos na silver. Iguais, provam que a agregação não duplicou nem perdeu linha.


# CELL ********************

# Monta o fato de entrega no grao de pedido, com a chave sk_pedido

fato_entrega = spark.sql(f"""
    WITH itens AS (
        SELECT id_pedido,
               SUM(preco)       AS valor_itens,
               SUM(valor_frete) AS valor_frete,
               COUNT(*)         AS qtd_itens
        FROM {SILVER}.itens_pedido
        GROUP BY id_pedido
    ),
    avaliacao AS (
        SELECT id_pedido, nota FROM (
            SELECT id_pedido, nota,
                   ROW_NUMBER() OVER (PARTITION BY id_pedido
                                      ORDER BY data_avaliacao DESC, id_avaliacao DESC) AS ordem
            FROM {SILVER}.avaliacoes
        ) WHERE ordem = 1
    )
    SELECT ROW_NUMBER() OVER (ORDER BY p.id_pedido) AS sk_pedido,
           p.id_pedido,
           dc.sk_cliente,
           dg.sk_geografia AS sk_geografia_destino,
           CAST(DATE_FORMAT(p.data_compra,           'yyyyMMdd') AS INT) AS sk_data_compra,
           CAST(DATE_FORMAT(p.data_entrega_prevista, 'yyyyMMdd') AS INT) AS sk_data_prevista,
           CAST(DATE_FORMAT(p.data_entrega_real,     'yyyyMMdd') AS INT) AS sk_data_entrega,
           p.status_pedido,
           DATEDIFF(p.data_aprovacao,    p.data_compra)           AS dias_ate_aprovacao,
           DATEDIFF(p.data_coleta,       p.data_compra)           AS dias_ate_coleta,
           DATEDIFF(p.data_entrega_real, p.data_compra)           AS lead_time_dias,
           DATEDIFF(p.data_entrega_real, p.data_entrega_prevista) AS dias_de_atraso,
           DATE(p.data_entrega_real) <= DATE(p.data_entrega_prevista) AS entregue_no_prazo,
           a.nota,
           i.valor_itens,
           i.valor_frete,
           i.qtd_itens
    FROM {SILVER}.pedidos p
    LEFT JOIN itens             i  ON i.id_pedido        = p.id_pedido
    LEFT JOIN avaliacao         a  ON a.id_pedido        = p.id_pedido
    LEFT JOIN {SILVER}.clientes c  ON c.id_cliente       = p.id_cliente
    LEFT JOIN dim_cliente       dc ON dc.id_cliente_unico = c.id_cliente_unico
    LEFT JOIN dim_geografia     dg ON dg.prefixo_cep      = c.prefixo_cep
""")

# Escreve a tabela no banco
fato_entrega.write.mode('overwrite').option('overwriteSchema', 'true').saveAsTable('fato_entrega')

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# # fato_item_pedido
# 
# - **Grão:** um item de um pedido
# - **Origem:** `silver.itens_pedido` — 112.650 linhas
# - **Chave natural:** `id_pedido` + `numero_item`
# 
# **Última célula do esquema estrela.** Depende de `fato_entrega`, de onde busca o `sk_pedido`,
# e de `dim_produto` e `dim_vendedor`.
# 
# **Decisões desta célula**
# 
# **A chave natural é composta, e a alternativa óbvia está errada.** É `id_pedido` +
# `numero_item`, **nunca** `id_pedido` + `id_produto`: o mesmo produto aparece várias vezes no
# mesmo pedido, que é como esta origem representa quantidade. Deduplicar por produto apagaria
# **10.225 linhas — 9% da tabela** — em silêncio e com aparência de limpeza.
# 
# **Existe por causa do grão, não por conveniência.** `preco` e `valor_frete` são do item, e
# `sk_vendedor` também — um pedido pode ter itens de vendedores diferentes, e sem esta tabela
# o custo de frete por rota fica errado. Achatar os dois fatos em um só distorceria o OTD em
# favor dos pedidos grandes.
# 
# **`peso_gramas` e `volume_cm3` são materializados aqui.** É desnormalização deliberada: o
# custo por quilo é medida de linha de item, e trazer o peso da `dim_produto` a cada cálculo
# custaria uma junção em toda consulta de frete. Os **2 produtos sem dimensão** chegam nulos e
# simplesmente não entram no cálculo.
# 
# **A geografia daqui é a origem da rota** — `sk_geografia_origem` vem do CEP do vendedor. O
# destino mora em `fato_entrega`, porque é atributo do pedido. O par das duas UFs é o que
# define uma rota, e é a razão de a `dim_geografia` se ligar aos dois fatos em papéis opostos.
# 
# **Validação:**
# - **112.650 linhas** — igual a `silver.itens_pedido`. Junção com dimensão não pode alterar a
#   contagem de um fato; se alterar, alguma chave natural tem duplicata.
# - `SUM(preco)` = **13.591.643,70** e `SUM(valor_frete)` = **2.251.909,54**.
# - **Nenhum `sk_pedido` nulo.** Nulo ali significa item cujo pedido não existe em
#   `fato_entrega` — fato órfão, o defeito que a ordem das células existe para evitar e que não
#   levanta erro sozinho.


# CELL ********************

# Monta o fato no grao de item, com a chave sk_item

fato_item_pedido = spark.sql(f"""
    SELECT ROW_NUMBER() OVER (ORDER BY i.id_pedido, i.numero_item) AS sk_item,
           i.id_pedido,
           i.numero_item,
           fe.sk_pedido,
           dp.sk_produto,
           dv.sk_vendedor,
           dg.sk_geografia AS sk_geografia_origem,
           CAST(DATE_FORMAT(i.data_limite_envio, 'yyyyMMdd') AS INT) AS sk_data_limite_envio,
           i.preco,
           i.valor_frete,
           dp.peso_gramas,
           dp.volume_cm3
    FROM {SILVER}.itens_pedido i
    LEFT JOIN fato_entrega  fe ON fe.id_pedido   = i.id_pedido
    LEFT JOIN dim_produto   dp ON dp.id_produto  = i.id_produto
    LEFT JOIN dim_vendedor  dv ON dv.id_vendedor = i.id_vendedor
    LEFT JOIN dim_geografia dg ON dg.prefixo_cep = dv.prefixo_cep
""")

# Escreve a tabela no banco
fato_item_pedido.write.mode('overwrite').option('overwriteSchema', 'true').saveAsTable('fato_item_pedido')


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# # Comentarios tabelas 
# 


# CELL ********************

# ═══════════════════════════════════════════════════════════════════
# Documentação das tabelas
#
# As descrições ficam na tabela Delta, não só no notebook — assim elas
# viajam para o endpoint SQL e para o modelo semântico. É a promessa de
# self-service da Fase 5 começando aqui.
#
# Roda por último: COMMENT ON em tabela inexistente falha.
# ═══════════════════════════════════════════════════════════════════

comentarios = {
    "dim_calendario":   "Um dia por linha, de 2016-01-01 a 2018-12-31 (1.096). Gerada, não derivada da origem. sk_data é yyyyMMdd. Dimensão de papel duplo: compra, previsão e entrega apontam para ela.",
    "dim_cliente":      "Uma pessoa por linha, identificada por id_cliente_unico (96.096) — não confundir com id_cliente, que muda a cada pedido. SCD tipo 1: a geografia é a do pedido mais recente. É o destino da rota.",
    "dim_vendedor":     "Um vendedor por linha (3.095), com cidade, UF e prefixo de CEP. É a origem da rota.",
    "dim_produto":      "Um produto por linha (32.951). categoria_rotulo deriva do código da origem; 610 produtos não têm categoria e 2 não têm dimensão física.",
    "dim_geografia":    "Um centroide por prefixo de CEP (19.011), em mediana de latitude e longitude. Serve os dois fatos: destino do cliente e origem do vendedor.",
    "fato_entrega":     "Um pedido por linha (99.441). Base de OTD, lead time e atraso. Pedido não entregue tem data, atraso e prazo no prazo nulos — 2.965 casos. A nota é a avaliação mais recente, conforme ADR-002.",
    "fato_item_pedido": "Um item de pedido por linha (112.650). É o grão do preço e do frete. Chave natural id_pedido + numero_item, nunca id_pedido + id_produto.",
}

for tabela, texto in comentarios.items():
    # Aspa simples no texto encerraria a string do SQL. Duplicar é como o
    # padrão escapa, e evita que uma descrição futura quebre a célula.
    seguro = texto.replace("'", "''")
    spark.sql(f"COMMENT ON TABLE {tabela} IS '{seguro}'")

print(f"{len(comentarios)} tabelas comentadas.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
