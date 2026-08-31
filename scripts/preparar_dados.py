"""
Prepara os arquivos de origem do Olist para o repositório.

Duas responsabilidades, deliberadamente pequenas:

1. Converter olist_geolocation_dataset.csv para Parquet. O CSV tem ~61 MB e cerca de
   1 milhão de linhas; o GitHub avisa acima de 50 MB e rejeita acima de 100 MB.
2. Validar que os nove arquivos esperados estão presentes e reportar o que há em cada um.

Nenhuma transformação de conteúdo acontece aqui. Limpeza, tipagem e agregação pertencem
à camada silver, dentro do Fabric, onde ficam visíveis e versionadas.

Por isso a conversão lê todas as colunas como texto: inferir tipo já é decidir sobre o
conteúdo, e a decisão seria da biblioteca, não do projeto. O Parquet resultante é um
recipiente do que o CSV continha, literalmente.

Uso:
    python scripts/preparar_dados.py
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import pandas as pd
    import pyarrow.parquet as pq
except ImportError:
    sys.exit("Falta o pandas ou o pyarrow. Instale com: pip install pandas pyarrow")

ORIGEM = Path(__file__).resolve().parent.parent / "dados" / "origem"

GEO_CSV = "olist_geolocation_dataset.csv"
GEO_PARQUET = "olist_geolocation_dataset.parquet"

ESPERADOS = [
    "olist_orders_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_customers_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "product_category_name_translation.csv",
    GEO_PARQUET,
]

LIMITE_AVISO_MB = 50


def mb(caminho: Path) -> float:
    return caminho.stat().st_size / (1024 * 1024)


def converter_geolocalizacao() -> None:
    csv = ORIGEM / GEO_CSV
    parquet = ORIGEM / GEO_PARQUET

    if parquet.exists() and not csv.exists():
        print(f"  ja convertido: {GEO_PARQUET} ({mb(parquet):.1f} MB)")
        return

    if not csv.exists():
        print(f"  AUSENTE: {GEO_CSV} — baixe o dataset antes de rodar este script")
        return

    print(f"  lendo {GEO_CSV} ({mb(csv):.1f} MB)...")
    # dtype=str desliga a inferencia de tipo do pandas. Sem isso, o prefixo de CEP
    # "01037" e lido como inteiro 1037, e 24,6% do arquivo perde o zero a esquerda —
    # o que quebra a juncao com clientes e vendedores tres camadas adiante.
    # A tipagem pertence a silver; aqui so muda o formato do arquivo.
    df = pd.read_csv(csv, dtype=str)
    df.to_parquet(parquet, engine="pyarrow", compression="snappy", index=False)

    reducao = (1 - mb(parquet) / mb(csv)) * 100
    print(
        f"  convertido: {GEO_PARQUET} ({mb(parquet):.1f} MB) "
        f"— reducao de {reducao:.0f}%, {len(df):,} linhas"
    )
    print(f"  ACAO: remova {GEO_CSV} antes do commit — so o Parquet vai para o Git")


def validar() -> bool:
    print("\nValidando arquivos de origem:\n")
    ok = True

    for nome in ESPERADOS:
        caminho = ORIGEM / nome
        if not caminho.exists():
            print(f"  [FALTA]  {nome}")
            ok = False
            continue

        tamanho = mb(caminho)
        alerta = "  <-- acima do limite de aviso do GitHub" if tamanho > LIMITE_AVISO_MB else ""

        try:
            if nome.endswith(".parquet"):
                # num_rows vem do rodape do arquivo: contagem exata, sem carregar os dados.
                # Ler com columns=[] devolve zero linhas no pandas 3, mascarando arquivo vazio.
                linhas = pq.ParquetFile(caminho).metadata.num_rows
            else:
                linhas = sum(1 for _ in caminho.open(encoding="utf-8")) - 1
        except Exception as exc:  # noqa: BLE001 - queremos reportar, nao interromper
            print(f"  [ERRO]   {nome}: {exc}")
            ok = False
            continue

        print(f"  [OK]     {nome:<45} {tamanho:>6.1f} MB  {linhas:>9,} linhas{alerta}")

    return ok


def main() -> int:
    if not ORIGEM.exists():
        sys.exit(f"Pasta nao encontrada: {ORIGEM}")

    print(f"Origem: {ORIGEM}\n")
    print("Convertendo geolocalizacao:")
    converter_geolocalizacao()

    if not validar():
        print("\nHa arquivos faltando ou ilegiveis. Veja dados/origem/README.md.")
        return 1

    print("\nTudo pronto para o commit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
