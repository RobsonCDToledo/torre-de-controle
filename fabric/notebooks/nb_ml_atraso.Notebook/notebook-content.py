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
# META           "id": "54fe162c-166b-4a5e-b222-c896510adbe3"
# META         }
# META       ]
# META     }
# META   }
# META }

# MARKDOWN ********************

# # nb_ml_atraso
#
# Prevê, **no instante da compra**, se um pedido vai atrasar. Fase 6 do projeto.
#
# Lê só da gold (`lh_gold` como lakehouse padrão), treina, registra no MLflow e escreve as
# predições de volta na gold como `predicao_atraso`, para o modelo semântico consumir.
#
# ---
# ## O contrato do problema
#
# | | |
# |---|---|
# | **Pergunta** | Este pedido vai ser entregue depois da data prometida? |
# | **Alvo** | `atraso = 1` quando `entregue_no_prazo = false`. Só pedidos **entregues** têm alvo (96.476) |
# | **Instante da previsão** | A compra. Nada que aconteça depois pode entrar |
# | **Divisão** | **Temporal** pela data de compra: 70% mais antigos treinam, 15% validam e escolhem o limiar, 15% mais recentes testam. Embaralhar vazaria o futuro para o passado |
#
# ## A regra que define o projeto: sem vazamento temporal
#
# **Proibidos como atributo** — acontecem depois da compra: `dias_ate_aprovacao`,
# `dias_ate_coleta`, `lead_time_dias`, `dias_de_atraso`, `sk_data_entrega`, `nota`,
# `status_pedido`. Além deles, `order_approved_at` e `order_delivered_carrier_date` e qualquer
# derivado. Uma célula abaixo **falha** se algum deles aparecer na lista de atributos.
#
# **Permitidos** — conhecidos na compra: UF de origem e destino, distância entre centroides,
# prazo prometido (compra até data prevista, que o cliente já vê no checkout), peso, volume,
# frete, preço, categoria, mês e dia da semana, quantidade de itens e de vendedores, e a
# **pontualidade histórica do vendedor**.
#
# **A pontualidade do vendedor é o atributo perigoso.** Calculada sobre a base inteira, ela
# carregaria o resultado dos pedidos futuros do próprio vendedor para dentro do treino. Aqui, para
# cada pedido, só contam entregas do mesmo vendedor com **data de entrega estritamente anterior
# à data de compra** deste pedido — o que de fato se sabia naquele dia. Pedido sem histórico fica
# com atributo nulo, que o modelo trata nativamente; não se inventa taxa.
#
# ## Vendedor e UF de origem
#
# Vale a regra do `ADR-003`: o item de maior `preco`, `numero_item` como desempate. Vendedor,
# categoria e geografia de origem vêm desse mesmo item.

# CELL ********************

import numpy as np
import pandas as pd
import mlflow
import mlflow.sklearn
from mlflow.models import infer_signature
from pyspark.sql import functions as F
from pyspark.sql.window import Window

# Parametros do experimento ------------------------------------------------------------------
EXPERIMENTO = "exp_atraso_entrega"
NOME_MODELO = "modelo_atraso_entrega"
FRACAO_TREINO = 0.70
FRACAO_VALIDACAO = 0.15   # o restante (0.15) e teste
SEMENTE = 42

# Atributos que NAO podem entrar: acontecem depois da compra.
PROIBIDOS = {
    "dias_ate_aprovacao", "dias_ate_coleta", "lead_time_dias", "dias_de_atraso",
    "sk_data_entrega", "data_entrega", "nota", "status_pedido", "entregue_no_prazo",
    "order_approved_at", "order_delivered_carrier_date",
}
print("ok")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 1. Atributos conhecidos na compra
#
# Uma linha por pedido. O item principal sai de uma janela por pedido (maior `preco`, depois menor
# `numero_item`). A distância é haversine entre o centroide do CEP do vendedor e o do cliente.

# CELL ********************

def para_data(coluna):
    # sk_data_* e yyyyMMdd inteiro -> date
    return F.to_date(F.col(coluna).cast("string"), "yyyyMMdd")

def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = F.radians(lat1), F.radians(lat2)
    dphi, dlambda = p2 - p1, F.radians(lon2 - lon1)
    a = F.sin(dphi / 2) ** 2 + F.cos(p1) * F.cos(p2) * F.sin(dlambda / 2) ** 2
    return 2 * 6371.0 * F.asin(F.sqrt(a))

pedidos = (
    spark.table("fato_entrega")
    .select("sk_pedido", "uf_origem", "uf_destino", "sk_geografia_destino",
            "sk_data_compra", "sk_data_prevista", "sk_data_entrega",
            "entregue_no_prazo", "qtd_itens", "valor_itens", "valor_frete")
    .withColumn("data_compra", para_data("sk_data_compra"))
    .withColumn("data_prevista", para_data("sk_data_prevista"))
    .withColumn("data_entrega", para_data("sk_data_entrega"))
)

# Item principal por pedido: mesma regra do ADR-003
itens = spark.table("fato_item_pedido").join(
    spark.table("dim_produto").select("sk_produto", "categoria_rotulo"), "sk_produto", "left"
)
janela = Window.partitionBy("sk_pedido").orderBy(F.col("preco").desc(), F.col("numero_item").asc())
principal = (
    itens.withColumn("_r", F.row_number().over(janela)).where("_r = 1")
    .select("sk_pedido",
            F.col("sk_vendedor").alias("sk_vendedor_principal"),
            F.col("categoria_rotulo").alias("categoria_principal"),
            F.col("sk_geografia_origem").alias("sk_geografia_origem_principal"))
)
agregados = itens.groupBy("sk_pedido").agg(
    F.sum("peso_gramas").alias("peso_total_g"),
    F.sum("volume_cm3").alias("volume_total_cm3"),
    F.countDistinct("sk_vendedor").alias("qtd_vendedores"),
)

geo = spark.table("dim_geografia").select(
    "sk_geografia", F.col("latitude").cast("double").alias("lat"), F.col("longitude").cast("double").alias("lon"))
geo_o = geo.select(F.col("sk_geografia").alias("sk_geografia_origem_principal"),
                   F.col("lat").alias("lat_o"), F.col("lon").alias("lon_o"))
geo_d = geo.select(F.col("sk_geografia").alias("sk_geografia_destino"),
                   F.col("lat").alias("lat_d"), F.col("lon").alias("lon_d"))

base = (
    pedidos.join(principal, "sk_pedido", "left").join(agregados, "sk_pedido", "left")
    .join(geo_o, "sk_geografia_origem_principal", "left").join(geo_d, "sk_geografia_destino", "left")
    .withColumn("prazo_prometido_dias", F.datediff("data_prevista", "data_compra"))
    .withColumn("mes_compra", F.month("data_compra"))
    .withColumn("dia_semana_compra", F.dayofweek("data_compra"))
    .withColumn("mesma_uf", F.when(F.col("uf_origem").isNull() | F.col("uf_destino").isNull(), None)
                .otherwise((F.col("uf_origem") == F.col("uf_destino")).cast("int")))
    .withColumn("distancia_km", haversine_km(F.col("lat_o"), F.col("lon_o"), F.col("lat_d"), F.col("lon_d")))
    .withColumn("valor_itens", F.col("valor_itens").cast("double"))
    .withColumn("valor_frete", F.col("valor_frete").cast("double"))
    .withColumn("frete_sobre_valor", F.col("valor_frete") / F.col("valor_itens"))
)
print("pedidos:", base.count())

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 2. Pontualidade histórica do vendedor, sem olhar o futuro
#
# Para cada pedido, junta as entregas **do mesmo vendedor principal** cuja `data_entrega` é
# **estritamente anterior** à `data_compra` do pedido. É a única forma de saber, na compra, como
# aquele vendedor vinha entregando. Entrega no mesmo dia da compra fica de fora — conservador.

# CELL ********************

historico = (
    base.where(F.col("data_entrega").isNotNull() & F.col("sk_vendedor_principal").isNotNull())
    .select(F.col("sk_vendedor_principal").alias("h_vendedor"),
            F.col("data_entrega").alias("h_entrega"),
            F.col("entregue_no_prazo").cast("int").alias("h_no_prazo"))
)
alvo = base.select("sk_pedido", "sk_vendedor_principal", "data_compra")

pontualidade = (
    alvo.join(historico,
              (alvo.sk_vendedor_principal == historico.h_vendedor) & (historico.h_entrega < alvo.data_compra),
              "left")
    .groupBy("sk_pedido")
    .agg(F.count("h_no_prazo").alias("qtd_entregas_anteriores_vendedor"),
         F.avg("h_no_prazo").alias("taxa_pontualidade_vendedor"))
)

base = base.join(pontualidade, "sk_pedido", "left")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 3. Lista de atributos e trava anti-vazamento
#
# Se qualquer atributo proibido entrar na lista, a célula falha e o treino não acontece.

# CELL ********************

ATRIBUTOS_CAT = ["uf_origem", "uf_destino", "categoria_principal"]
ATRIBUTOS_NUM = [
    "prazo_prometido_dias", "distancia_km", "mesma_uf", "mes_compra", "dia_semana_compra",
    "qtd_itens", "qtd_vendedores", "valor_itens", "valor_frete", "frete_sobre_valor",
    "peso_total_g", "volume_total_cm3",
    "taxa_pontualidade_vendedor", "qtd_entregas_anteriores_vendedor",
]
ATRIBUTOS = ATRIBUTOS_CAT + ATRIBUTOS_NUM

vazados = PROIBIDOS.intersection(ATRIBUTOS)
assert not vazados, f"VAZAMENTO TEMPORAL: atributos proibidos na lista: {sorted(vazados)}"
print(f"{len(ATRIBUTOS)} atributos, nenhum proibido")

# Apenas pedidos com item (sem item nao ha o que prever)
colunas = ["sk_pedido", "data_compra", "entregue_no_prazo"] + ATRIBUTOS
pdf = base.where("qtd_itens IS NOT NULL").select(*colunas).toPandas()
pdf["data_compra"] = pd.to_datetime(pdf["data_compra"])
pdf["atraso"] = np.where(pdf["entregue_no_prazo"].isna(), np.nan, 1 - pdf["entregue_no_prazo"].astype(float))
for c in ATRIBUTOS_NUM:
    pdf[c] = pd.to_numeric(pdf[c], errors="coerce")
print("pedidos com item:", len(pdf), "| entregues (com alvo):", int(pdf["atraso"].notna().sum()))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 4. Divisão temporal
#
# Os cortes são **datas de compra**, calculadas sobre os pedidos entregues. Treino é o passado,
# teste é o futuro mais recente — como seria usar o modelo de verdade.

# CELL ********************

ent = pdf[pdf["atraso"].notna()].copy()
corte_treino = ent["data_compra"].quantile(FRACAO_TREINO)
corte_valid = ent["data_compra"].quantile(FRACAO_TREINO + FRACAO_VALIDACAO)

def conjunto(linha_data, tem_alvo):
    if not tem_alvo:
        return "nao_entregue"
    if linha_data < corte_treino:
        return "treino"
    if linha_data < corte_valid:
        return "validacao"
    return "teste"

pdf["conjunto"] = [conjunto(d, a) for d, a in zip(pdf["data_compra"], pdf["atraso"].notna())]

resumo = (pdf[pdf["atraso"].notna()].groupby("conjunto")
          .agg(pedidos=("sk_pedido", "size"), inicio=("data_compra", "min"), fim=("data_compra", "max"),
               taxa_atraso=("atraso", "mean")).loc[["treino", "validacao", "teste"]])
display(resumo)

# Sanidade: os conjuntos nao se sobrepoem no tempo
assert pdf[pdf.conjunto == "treino"]["data_compra"].max() < pdf[pdf.conjunto == "validacao"]["data_compra"].min()
assert pdf[pdf.conjunto == "validacao"]["data_compra"].max() < pdf[pdf.conjunto == "teste"]["data_compra"].min()

tr, va, te = (pdf[pdf.conjunto == c] for c in ("treino", "validacao", "teste"))
X_tr, y_tr = tr[ATRIBUTOS], tr["atraso"].astype(int)
X_va, y_va = va[ATRIBUTOS], va["atraso"].astype(int)
X_te, y_te = te[ATRIBUTOS], te["atraso"].astype(int)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 5. Modelo, baseline e métricas
#
# **Modelo:** gradiente com histogramas (`HistGradientBoostingClassifier`), que aceita nulo nativamente e
# trata UF e categoria como categóricas. **Baseline:** o mesmo modelo só com `prazo_prometido_dias` e
# `distancia_km` — mostra o quanto os demais atributos acrescentam. Atraso é raro, então a métrica principal é
# **PR-AUC** (precisão e revocação), ao lado do ROC-AUC.
#
# O **limiar** de decisão é escolhido na validação (maior F1) e só então aplicado ao teste.

# CELL ********************

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import (average_precision_score, brier_score_loss, f1_score,
                             precision_score, recall_score, roc_auc_score, precision_recall_curve)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder

def montar_pipeline(cat, num, **params):
    pre = ColumnTransformer(
        [("cat", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1,
                                encoded_missing_value=-1), cat)],
        remainder="passthrough")
    modelo = HistGradientBoostingClassifier(
        categorical_features=list(range(len(cat))), random_state=SEMENTE, **params)
    return Pipeline([("pre", pre), ("modelo", modelo)])

PARAMS = dict(max_iter=300, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=50, l2_regularization=1.0)

def avaliar(y, p, limiar):
    pred = (p >= limiar).astype(int)
    topo = np.argsort(-p)[: max(1, int(len(p) * 0.10))]
    return {
        "roc_auc": roc_auc_score(y, p),
        "pr_auc": average_precision_score(y, p),
        "brier": brier_score_loss(y, p),
        "precisao": precision_score(y, pred, zero_division=0),
        "revocacao": recall_score(y, pred, zero_division=0),
        "f1": f1_score(y, pred, zero_division=0),
        "revocacao_top10pct": float(y.iloc[topo].sum() / max(1, y.sum())),
        "taxa_atraso_real": float(y.mean()),
    }

def melhor_limiar(y, p):
    prec, rev, lim = precision_recall_curve(y, p)
    f1 = 2 * prec[:-1] * rev[:-1] / np.clip(prec[:-1] + rev[:-1], 1e-9, None)
    return float(lim[int(np.argmax(f1))])

# Baseline
base_cols = ["prazo_prometido_dias", "distancia_km"]
pipe_base = montar_pipeline([], base_cols, **PARAMS)
pipe_base.fit(X_tr[base_cols], y_tr)
p_va_b = pipe_base.predict_proba(X_va[base_cols])[:, 1]
lim_b = melhor_limiar(y_va, p_va_b)
m_base = avaliar(y_te, pd.Series(pipe_base.predict_proba(X_te[base_cols])[:, 1], index=y_te.index).values, lim_b)

# Modelo completo
pipe = montar_pipeline(ATRIBUTOS_CAT, ATRIBUTOS_NUM, **PARAMS)
pipe.fit(X_tr, y_tr)
p_va = pipe.predict_proba(X_va)[:, 1]
limiar = melhor_limiar(y_va, p_va)
p_te = pipe.predict_proba(X_te)[:, 1]
m_val = avaliar(y_va, p_va, limiar)
m_te = avaliar(y_te, p_te, limiar)

comparativo = pd.DataFrame({"baseline_teste": m_base, "modelo_validacao": m_val, "modelo_teste": m_te}).round(4)
print("limiar escolhido na validacao:", round(limiar, 4))
display(comparativo)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 6. Importância dos atributos
#
# Importância por **permutação no teste**: quanto o ROC-AUC cai quando o atributo é embaralhado. Mede o que
# o modelo usa de fato em dado que ele não viu.

# CELL ********************

imp = permutation_importance(pipe, X_te, y_te, scoring="roc_auc", n_repeats=5, random_state=SEMENTE, n_jobs=-1)
importancia = (pd.DataFrame({"atributo": ATRIBUTOS, "queda_roc_auc": imp.importances_mean,
                             "desvio": imp.importances_std})
               .sort_values("queda_roc_auc", ascending=False).reset_index(drop=True))
display(importancia)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 7. Registro no MLflow
#
# Parâmetros, métricas, importância e o modelo, registrado com o nome `modelo_atraso_entrega`. Cada execução
# cria uma versão nova.

# CELL ********************

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

mlflow.set_experiment(EXPERIMENTO)
with mlflow.start_run(run_name="hgb_atraso_v1") as run:
    mlflow.log_params({**PARAMS, "limiar": round(limiar, 4), "n_atributos": len(ATRIBUTOS),
                       "fracao_treino": FRACAO_TREINO, "fracao_validacao": FRACAO_VALIDACAO,
                       "corte_treino": str(corte_treino.date()), "corte_validacao": str(corte_valid.date())})
    mlflow.log_metrics({f"teste_{k}": v for k, v in m_te.items()})
    mlflow.log_metrics({f"validacao_{k}": v for k, v in m_val.items()})
    mlflow.log_metrics({f"baseline_{k}": v for k, v in m_base.items()})
    mlflow.log_dict(importancia.round(6).to_dict(orient="records"), "importancia_atributos.json")

    fig, ax = plt.subplots(figsize=(7, 5))
    top = importancia.head(12).iloc[::-1]
    ax.barh(top["atributo"], top["queda_roc_auc"], color="#4F46E5")
    ax.set_xlabel("queda do ROC-AUC ao embaralhar (teste)")
    ax.set_title("Importância dos atributos")
    fig.tight_layout()
    mlflow.log_figure(fig, "importancia_atributos.png")

    assinatura = infer_signature(X_va.head(50), pipe.predict_proba(X_va.head(50))[:, 1])
    info = mlflow.sklearn.log_model(pipe, "modelo", signature=assinatura, registered_model_name=NOME_MODELO)
    VERSAO = str(getattr(info, "registered_model_version", "") or "")
    ID_EXECUCAO = run.info.run_id

print("run:", ID_EXECUCAO, "| versao registrada:", VERSAO or "(ver no registro)")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 8. Predições de volta na gold
#
# `predicao_atraso`, um registro por pedido com item. **Atenção ao `conjunto`:** nas linhas `treino` e
# `validacao` a predição é *dentro da amostra* e parece melhor do que é. Para comparar previsto e realizado
# com honestidade, o painel deve filtrar `conjunto = 'teste'`. `nao_entregue` são pedidos ainda sem desfecho —
# a predição existe, mas não há realizado para comparar.

# CELL ********************

alvo_pred = pdf.copy()
alvo_pred["probabilidade_atraso"] = pipe.predict_proba(alvo_pred[ATRIBUTOS])[:, 1]
alvo_pred["previsao_atraso"] = (alvo_pred["probabilidade_atraso"] >= limiar).astype(int)

saida = alvo_pred[["sk_pedido", "probabilidade_atraso", "previsao_atraso", "conjunto", "atraso"]].rename(
    columns={"atraso": "atraso_real"})
saida["atraso_real"] = saida["atraso_real"].astype("float64")
saida["sk_pedido"] = saida["sk_pedido"].astype("int64")

predicao = (
    spark.createDataFrame(saida)
    .withColumn("atraso_real", F.when(F.isnan("atraso_real"), F.lit(None).cast("int"))
                .otherwise(F.col("atraso_real").cast("int")))
    .withColumn("limiar", F.lit(float(limiar)))
    .withColumn("modelo", F.lit(NOME_MODELO))
    .withColumn("versao_modelo", F.lit(VERSAO))
    .withColumn("gerado_em", F.current_timestamp())
)
predicao.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable("predicao_atraso")
print("predicao_atraso gravada")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 9. Validação do que foi gravado

# CELL ********************

p = spark.table("predicao_atraso")
n_esperado = spark.table("fato_entrega").where("qtd_itens IS NOT NULL").count()
n = p.count()
assert n == n_esperado, f"linhas {n} != pedidos com item {n_esperado}"
assert p.select("sk_pedido").distinct().count() == n, "sk_pedido duplicado"
lim = p.agg(F.min("probabilidade_atraso"), F.max("probabilidade_atraso")).first()
assert 0.0 <= lim[0] and lim[1] <= 1.0, "probabilidade fora de [0,1]"
orfaos = p.join(spark.table("fato_entrega"), "sk_pedido", "left_anti").count()
assert orfaos == 0, f"{orfaos} predicoes sem pedido correspondente"
print(f"{n} linhas, sk_pedido unico, probabilidade em [{lim[0]:.4f}, {lim[1]:.4f}], 0 orfaos")
display(p.groupBy("conjunto").agg(F.count("*").alias("pedidos"),
                                  F.round(F.avg("probabilidade_atraso"), 4).alias("prob_media"),
                                  F.round(F.avg("atraso_real"), 4).alias("taxa_atraso_real")).orderBy("conjunto"))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
