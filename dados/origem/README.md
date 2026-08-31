# Dados de origem

Esta pasta é o **sistema de origem simulado** do projeto. Os arquivos aqui são servidos ao
pipeline de ingestão do Fabric por URL pública, exatamente como um sistema externo entregaria.

> Atenção à separação conceitual: esta pasta **não é a camada bronze**. A bronze vive no
> Lakehouse do Fabric. Aqui é o que existe *antes* — o equivalente ao SFTP, ao endpoint de
> API ou ao drop de arquivos que uma operação real teria.

---

## Obtendo os arquivos

Dataset: **Brazilian E-Commerce Public Dataset by Olist**, no Kaggle
(`olistbr/brazilian-ecommerce`).

```bash
pip install kaggle
kaggle datasets download -d olistbr/brazilian-ecommerce
unzip brazilian-ecommerce.zip -d dados/origem/
```

Ou baixe manualmente pela interface do Kaggle e extraia nesta pasta.

---

## Os nove arquivos

| Arquivo | Aprox. | Papel no modelo |
|---|---|---|
| `olist_orders_dataset.csv` | 17 MB | Fato principal — datas do funil de entrega |
| `olist_order_items_dataset.csv` | 15 MB | Grão de item — preço e frete |
| `olist_order_reviews_dataset.csv` | 14 MB | Satisfação, proxy de qualidade de entrega |
| `olist_customers_dataset.csv` | 9 MB | Dimensão cliente e geografia de destino |
| `olist_order_payments_dataset.csv` | 6 MB | Forma e parcelamento de pagamento |
| `olist_products_dataset.csv` | 2,4 MB | Dimensão produto — peso e dimensões |
| `olist_sellers_dataset.csv` | 0,2 MB | Dimensão vendedor e geografia de origem |
| `product_category_name_translation.csv` | < 0,1 MB | Tradução de categoria |
| `olist_geolocation_dataset.csv` | **61 MB** | Coordenadas por prefixo de CEP — ver abaixo |

---

## O problema do arquivo de geolocalização

`olist_geolocation_dataset.csv` tem cerca de **1 milhão de linhas e 61 MB**. O GitHub emite
aviso acima de 50 MB e **rejeita arquivos acima de 100 MB**. Ele passaria, mas raspando o
limite — e deixaria o clone do repositório lento sem necessidade.

**Decisão tomada:** converter para Parquet antes de commitar, o que derruba o arquivo para
algo em torno de 10 MB com compressão Snappy. Os outros oito arquivos vão como CSV, sem
alteração.

**Por que Parquet e não Git LFS:** o LFS resolveria o tamanho, mas exige que quem clona o
repositório tenha o LFS instalado e configurado — atrito desnecessário num projeto que
existe para ser inspecionado por terceiros. O Parquet resolve o mesmo problema sem
dependência nenhuma, e o conector Web do Fabric lê Parquet nativamente.

**Por que não agregar antes:** seria tentador reduzir o arquivo ao centroide por prefixo de
CEP, de 1 milhão de linhas para cerca de 19 mil. Mas isso é transformação, e transformação
não pertence à origem. A agregação acontece na camada silver, onde fica visível, versionada
e reversível. A origem permanece fiel ao que o sistema entregou.

Rode o script de preparo antes do primeiro commit:

```bash
python scripts/preparar_dados.py
```

Ele converte o arquivo de geolocalização, valida a presença dos nove arquivos e reporta
contagem de linhas de cada um.

---

## URLs de ingestão

Depois do push, cada arquivo fica acessível no padrão:

```
https://raw.githubusercontent.com/<usuario>/torre-de-controle/main/dados/origem/<arquivo>
```

Essas são as URLs que o pipeline consome. A lista parametrizada fica na definição do
pipeline, em `fabric/pipelines/`.

> **Cuidado com o cache.** O `raw.githubusercontent.com` serve conteúdo com cache de alguns
> minutos. Se você atualizar um arquivo de origem e reexecutar o pipeline imediatamente,
> pode ingerir a versão anterior. Ao testar mudança de origem, espere alguns minutos ou
> confirme pelo tamanho do arquivo ingerido.

---

## Nota de licença

O dataset é publicado sob licença Creative Commons com cláusula **não comercial**. Uso em
estudo e portfólio está coberto. Mantenha a atribuição à Olist e verifique os termos
vigentes na página do dataset — licenças mudam, e a deste repositório não substitui a de lá.
