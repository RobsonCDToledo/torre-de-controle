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

# # Comentarios tabelas 
# 


# CELL ********************

# ═══════════════════════════════════════════════════════════════════
# Documentação das tabelas
#
# As descrições ficam na tabela Delta, não só no notebook — assim elas
# viajam para o endpoint SQL e para o modelo semântico. É a promessa de
# self-service da Fase 5 começando aqui.
# ═══════════════════════════════════════════════════════════════════
comentarios = {
    "dim_calendario": "Um dia por linha, 2016 a 2018. Gerada. Dimensao de papel duplo: compra, previsao e entrega.",
    "dim_vendedor": "Um vendedor por linha, contendo dados de Cidade, Uf e Prefixo do CEP.",
    "dim_geografia": "Um centroide por prefixo de CEP. Serve destino do cliente e origem do vendedor."
    #"dim_cliente":    "Uma pessoa por linha (id_cliente_unico), nao um id_cliente. Geografia do pedido mais recente.",
    # ...
}
for tabela, texto in comentarios.items():
    spark.sql(f"COMMENT ON TABLE {tabela} IS '{texto}'")


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
