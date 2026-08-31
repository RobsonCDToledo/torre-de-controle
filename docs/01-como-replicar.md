# Como replicar este projeto

Passo a passo dos recursos necessários, onde consegui-los, quanto custam — e como
reconstruir a mesma arquitetura **sem Microsoft Fabric**, se você não tiver acesso.

---

## 1. Conta Microsoft

O trial do Fabric **não funciona com conta pessoal** (`@outlook.com`, `@gmail.com`,
`@hotmail.com`). É preciso uma conta corporativa ou acadêmica — um domínio próprio no
Microsoft Entra ID.

Se você não tem uma:

- **Conta de estudante** — se estiver matriculado, sua instituição provavelmente fornece
  um e-mail Microsoft com acesso ao Power BI e ao Fabric.
- **Microsoft 365 Developer Program** — historicamente oferecia um tenant de
  desenvolvimento gratuito e renovável. As condições de elegibilidade mudaram ao longo
  do tempo; consulte a página oficial do programa para ver o que vale hoje.
- **Domínio próprio + Microsoft 365 Business Basic** — o caminho mais confiável e o mais
  caro. Envolve custo mensal por usuário.

> Se você chegou aqui e não consegue uma conta corporativa, pule para a
> [seção 8](#8-replicando-sem-fabric) — dá para construir a mesma arquitetura em
> ferramentas gratuitas.

---

## 2. Capacidade Fabric

O Fabric precisa de capacidade computacional atribuída ao workspace. Sem isso, o Lakehouse,
os notebooks e o Direct Lake simplesmente não existem no menu.

**Opção A — Trial do Fabric.** Sessenta dias de capacidade de avaliação, ativado no portal
do Fabric pelo próprio usuário quando o tenant permite. É o caminho recomendado para
replicar este projeto: cabe folgado nas seis fases.

**Opção B — Capacidade F sob demanda no Azure.** Uma capacidade F2 criada pelo portal do
Azure, cobrada por hora de atividade. O ponto crítico: **ela pode ser pausada**, e capacidade
pausada não gera custo. Se você trabalha algumas horas por semana e pausa ao terminar, o
gasto mensal fica baixo. Exige uma assinatura Azure com forma de pagamento.

**Opção C — Capacidade Premium existente.** Se sua empresa já tem P SKU ou F SKU, os
recursos do Fabric provavelmente já estão disponíveis para você.

> **Antes de o trial expirar:** exporte tudo. Notebooks, definições de pipeline, o modelo
> semântico em TMDL e os relatórios em PBIR. Se o workspace estiver integrado ao Git
> (fase 1), isso já acontece sozinho — que é justamente por que a integração é a primeira
> coisa a fazer.

---

## 3. Power BI Desktop

Gratuito, apenas para Windows. Baixe da Microsoft Store — essa via se mantém atualizada
sozinha, o que evita incompatibilidade de formato com o serviço.

Duas configurações precisam ser ligadas em **Arquivo → Opções → Recursos de visualização**
antes de começar:

- **Salvar como projeto (`.pbip`)** — sem isso, o relatório é um binário e não há
  versionamento legível
- **Formato TMDL para o modelo semântico** — é o que produz diffs por medida no Git

Sem essas duas, o pilar de governança do projeto não existe.

---

## 4. Python

Necessário apenas para o script local que prepara os arquivos de origem
(`scripts/preparar_dados.py`). Python 3.10 ou superior, com `pandas` e `pyarrow`.

```bash
pip install pandas pyarrow
```

Não é usado em nenhuma etapa dentro do Fabric — lá, os notebooks rodam PySpark no próprio
ambiente.

---

## 5. Conta no GitHub

Gratuita. Serve a dois propósitos neste projeto:

1. **Hospedar os arquivos de origem.** O pipeline lê os arquivos por URL pública via
   `raw.githubusercontent.com`, simulando um sistema de origem externo.
2. **Versionar o workspace.** O Fabric integra o workspace a um repositório, sincronizando
   notebooks, pipelines, modelo semântico e relatórios como texto.

> **Sobre a integração Git:** o Fabric suporta Azure DevOps e GitHub. A disponibilidade de
> cada provedor varia conforme região, tipo de tenant e o momento em que você lê isto —
> confirme no seu ambiente antes de assumir. Se o GitHub não estiver disponível para você,
> use Azure DevOps para a sincronização do workspace e mantenha o GitHub apenas como
> hospedagem dos arquivos de origem e da documentação. A arquitetura não muda.

Repositório **público**, se a ideia é servir de portfólio. Arquivos em repositório privado
não são acessíveis por URL bruta sem autenticação, o que quebraria a ingestão.

---

## 6. O conjunto de dados

**Brazilian E-Commerce Public Dataset by Olist**, publicado no Kaggle sob o identificador
`olistbr/brazilian-ecommerce`.

Baixe pela interface do Kaggle (requer conta gratuita) ou pela CLI:

```bash
pip install kaggle
kaggle datasets download -d olistbr/brazilian-ecommerce
unzip brazilian-ecommerce.zip -d dados/origem/
```

A CLI exige um token de API, gerado nas configurações da sua conta Kaggle e salvo como
`~/.kaggle/kaggle.json`.

**Licença:** o dataset é publicado sob Creative Commons com cláusula não comercial. Uso em
estudo e portfólio está coberto; uso comercial não. Mantenha a atribuição à Olist e
confira os termos na página do dataset, porque licenças mudam.

O preparo dos arquivos — inclusive por que `olist_geolocation_dataset.csv` precisa virar
Parquet antes de ir para o Git — está em [../dados/origem/README.md](../dados/origem/README.md).

---

## 7. Ordem de execução

Fazer nesta ordem economiza retrabalho:

1. **Criar o repositório e subir os dados de origem.** Antes de tocar no Fabric — o
   pipeline vai precisar das URLs prontas.
2. **Criar o workspace e atribuir a capacidade.** Um workspace novo, não o "Meu workspace":
   integração Git e Direct Lake não funcionam no workspace pessoal.
3. **Conectar a integração Git imediatamente.** Antes de criar qualquer artefato. Assim
   tudo nasce versionado, e você não precisa reconciliar depois.
4. **Criar os três Lakehouses** — bronze, silver e gold. Separados, não schemas de um só:
   a fronteira entre camadas fica explícita e as permissões ficam simples.
5. **Construir na ordem das camadas.** Pipeline, depois Dataflow, depois notebook. Cada um
   depende do anterior estar populado.
6. **Modelo semântico e relatórios por último.** Direct Lake exige as tabelas Delta da gold
   já existindo.

---

## 8. Replicando sem Fabric

A arquitetura medalhão não pertence ao Fabric — ela é um padrão. Toda a lógica deste
projeto se transporta. O que muda é a ferramenta de cada camada.

### Equivalências

| Camada | Fabric | Alternativa gratuita |
|---|---|---|
| Armazenamento | Lakehouse (Delta) | DuckDB local, ou Parquet em disco |
| Ingestão | Data Pipeline | Python + `requests`, ou Airflow/Dagster |
| Bronze → Silver | Dataflow Gen2 | dbt, ou pandas/Polars em notebook |
| Silver → Gold | Notebook PySpark | dbt models, ou pandas/Polars |
| Modelo semântico | Direct Lake | Power BI Desktop em Import sobre DuckDB/Postgres |
| Self-service | Endpoint SQL | Postgres, ou Metabase sobre DuckDB |
| Perguntas nativas | Q&A do Power BI | Q&A do Power BI Desktop (funciona local) |
| ML | Notebook + MLflow | Jupyter + scikit-learn + MLflow local |

### Três caminhos que funcionam bem

**DuckDB + dbt + Power BI Desktop** — o mais próximo em espírito e totalmente gratuito.
DuckDB faz o papel do warehouse, dbt organiza as camadas com testes e documentação, o Power
BI Desktop entrega os relatórios. O `dbt docs` até substitui bem o dicionário de dados.
A lógica SQL migra quase sem alteração.

**Databricks Community Edition** — ambiente Spark gratuito, com Delta Lake nativo. É o mais
fiel tecnicamente às camadas bronze/silver/gold, e os notebooks PySpark deste projeto rodam
praticamente sem mudança. Não tem a camada de BI integrada.

**PostgreSQL + dbt + Metabase** — se o objetivo é demonstrar um stack mais tradicional e
autossuficiente. Roda inteiro em Docker na sua máquina.

### O que você perde

Sendo honesto sobre o que não se replica: **Direct Lake não tem equivalente fora do Fabric.**
Consultar arquivos Delta com desempenho de modelo importado, sem processo de atualização, é
específico da plataforma. Em qualquer alternativa você volta para Import ou DirectQuery, com
os compromissos conhecidos de cada um.

Também se perde a integração nativa entre orquestração, transformação, armazenamento e BI
dentro de um mesmo workspace — que é justamente o argumento comercial do Fabric. Nas
alternativas, essa costura é sua.

---

## 9. Custo total

| Recurso | Custo |
|---|---|
| Conta Microsoft corporativa | Variável — gratuito se estudante, mensal se domínio próprio |
| Capacidade Fabric | Zero no trial de 60 dias; por hora de atividade numa F2 pausável |
| Power BI Desktop | Gratuito |
| Publicar no serviço | Exige licença Power BI Pro por usuário |
| Python, GitHub, dataset | Gratuitos |

O caminho de custo zero: conta acadêmica, trial de 60 dias, e as seis fases concluídas
dentro da janela.
