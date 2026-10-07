# Torre de Controle

**Plataforma de dados end-to-end em Microsoft Fabric para visibilidade logística.** Projeto concluído em outubro de 2026.

Da ingestão de arquivos brutos até painéis executivos, ambiente de self-service e um
modelo de predição de atraso de entrega — com arquitetura medalhão, modelo semântico em
Direct Lake e todo o workspace versionado em Git.

> **Por que "Torre de Controle":** é o nome que o setor dá à função de visibilidade
> logística — a mesa que enxerga onde cada carga está, o que vai atrasar e quanto custa.
> É exatamente o que esta plataforma entrega.

---

## O que este projeto demonstra

| Competência | Onde aparece |
|---|---|
| Orquestração de ingestão | Data Pipeline parametrizado, com ForEach sobre a lista de arquivos |
| Transformação low-code | Dataflow Gen2 na camada silver, legível por outro analista |
| Engenharia de dados | Notebook PySpark construindo o modelo dimensional na gold |
| Modelagem dimensional | Esquema estrela com dimensão calendário e chaves substitutas |
| Modelo semântico moderno | Direct Lake sobre o Lakehouse gold, sem processo de atualização |
| Governança de BI | Workspace versionado em Git, TMDL/PBIR legíveis, dicionário de dados |
| Self-service governado | Modelo compartilhado com permissão de build, RLS e endpoint SQL |
| Perguntas em linguagem natural | Avaliado e documentado: Q&A não é suportado em Direct Lake (`ADR-005`) |
| Machine learning | Predição de atraso no instante da compra, com MLflow, divisão temporal e trava anti-vazamento (`ADR-006`) |

**O repositório é o projeto.** Notebooks, modelo semântico e relatórios estão versionados
como texto — qualquer pessoa consegue auditar a arquitetura inteira aqui, sem precisar de
licença de Fabric.

---

## Arquitetura

```
GitHub (dados/origem/)
        │  arquivos brutos, versionados
        ▼
┌───────────────────────────────────────────────┐
│  Data Pipeline · Copy activity                │  ingestão, sem transformação
│  ForEach sobre lista parametrizada            │
└───────────────────┬───────────────────────────┘
                    ▼
              ╔═══════════╗
              ║  BRONZE   ║  Lakehouse · Files/  · como veio, imutável
              ╚═════╤═════╝
                    ▼
┌───────────────────────────────────────────────┐
│  Dataflow Gen2                                │  tipagem, limpeza, dedup,
│                                               │  nomes em português
└───────────────────┬───────────────────────────┘
                    ▼
              ╔═══════════╗
              ║  SILVER   ║  Lakehouse · Delta  · uma tabela por origem
              ╚═════╤═════╝
                    ▼
┌───────────────────────────────────────────────┐
│  Notebook PySpark                             │  esquema estrela, chaves,
│                                               │  dim_calendario, features
└───────────────────┬───────────────────────────┘
                    ▼
              ╔═══════════╗
              ║   GOLD    ║  Lakehouse · Delta  · fatos + dimensões + features
              ╚═════╤═════╝
                    │
        ┌───────────┼────────────┬──────────────┐
        ▼           ▼            ▼              ▼
  Modelo         Endpoint     Notebook      Perguntas
  semântico      SQL          de ML         nativas
  (Direct Lake)  (analistas)  (MLflow)      (Q&A)
        │
   ┌────┴─────┐
   ▼          ▼
 Painel     Painel de
 Executivo  Frete e Rotas
```

O raciocínio por trás da divisão de ferramentas está em
[docs/decisoes/ADR-001-ferramenta-por-camada.md](docs/decisoes/ADR-001-ferramenta-por-camada.md).

---

## Fonte de dados

**Brazilian E-Commerce Public Dataset by Olist** — cerca de 100 mil pedidos reais de
e-commerce brasileiro entre 2016 e 2018.

Foi escolhido porque carrega, em dado real e público, exatamente os indicadores da
operação logística:

- `order_estimated_delivery_date` vs `order_delivered_customer_date` → **OTD real**
- `freight_value` por item → **custo de frete** e frete sobre faturamento
- compra → aprovação → coleta → entrega → **lead time por etapa**
- UF do vendedor e UF do cliente → **análise por rota**
- `review_score` e `order_status` → proxy de qualidade de entrega e cancelamento

Instruções completas de obtenção e preparo em [dados/origem/README.md](dados/origem/README.md).

---

## Como replicar

O passo a passo completo — onde conseguir cada recurso, quanto custa, e **como refazer
este projeto sem Fabric**, caso você não tenha acesso — está em
[docs/01-como-replicar.md](docs/01-como-replicar.md).

Resumo do mínimo necessário:

1. **Conta Microsoft corporativa ou acadêmica** — o trial do Fabric não aceita conta pessoal
2. **Capacidade Fabric** — trial de 60 dias, ou uma capacidade F2 sob demanda
3. **Power BI Desktop** — gratuito, para o modelo semântico e os relatórios
4. **Python 3.10+** — apenas para o script de preparo dos arquivos de origem
5. **Conta no GitHub** — para hospedar os arquivos e integrar ao workspace

---

## Estrutura do repositório

```
torre-de-controle/
├── dados/origem/          arquivos brutos servidos ao pipeline via raw.githubusercontent
├── design/                design system do Painel Executivo — paleta, tema PBI, mockup
│   ├── theme/             theme_torre_de_controle.json, pronto pra importar no Desktop
│   ├── mockups/           mockup do painel (Design Components, 16x9)
│   ├── design-system.html          referência navegável (paleta, tipografia, componentes)
│   └── paleta-e-uso.md    raciocínio e validação de cor por trás do tema
├── docs/
│   ├── 00-arquitetura.md          desenho completo e contrato de cada camada
│   ├── 01-como-replicar.md        passo a passo de recursos e alternativas
│   ├── 02-replicar-funcoes-dax.md catálogo de medidas DAX do modelo semântico
│   ├── 03-design-visual.md        processo de design visual, do zero ao Figma
│   ├── dicionario-de-dados.md     catálogo de tabelas, campos e medidas
│   └── decisoes/                  registros de decisão de arquitetura (ADR)
├── fabric/                espelha a hierarquia de pastas do workspace via integração Git
│   ├── lakehouses/        lh_bronze, lh_silver e lh_gold
│   ├── pipelines/         definição do pipeline de ingestão
│   ├── dataflows/         Dataflow Gen2 (bronze → silver)
│   ├── notebooks/         gold e machine learning
│   ├── modelos-semanticos/  modelo Direct Lake em TMDL
│   └── relatorios/        4 relatórios em PBIR: Executivo, Frete e Rotas, Atribuição de Causas, Previsão de Atraso
├── scripts/               utilitários locais de preparo de dados
└── planejamento/          cronograma e escopo por fase
```

---

## Estado do projeto

Construído em seis fases, cada uma com entrega publicável. Acompanhe em
[planejamento/cronograma.md](planejamento/cronograma.md).

- [x] **Fase 1** · Fundação — repositório, dados de origem, workspace, integração Git, ingestão para bronze
- [x] **Fase 2** · Silver — Dataflow Gen2, tipagem, limpeza, regras de qualidade
- [x] **Fase 3** · Gold — notebook, esquema estrela, dimensão calendário
- [x] **Fase 4** · Semântica — Direct Lake, medidas DAX, Painel Executivo
- [x] **Fase 5** · Self-service — RLS, endosso, dicionário, Q&A avaliado (ADR-005), painéis de Frete e de Atribuição de Causas
- [x] **Fase 6** · ML — atributos sem vazamento, modelo no MLflow, `predicao_atraso` na gold e painel de previsto × realizado

---

## Resultados

- **Modelo dimensional:** 2 fatos (pedido e item de pedido) e 5 dimensões, 99.441 pedidos, validado contra a origem.
- **Um modelo semântico, quatro relatórios:** Direct Lake sobre a gold, com RLS por UF de origem do vendedor.
- **Predição de atraso no instante da compra:** ROC-AUC 0,716 no teste contra 0,622 do baseline; o top 10% de
  risco captura 22,9% dos atrasos (2,3× o acaso). É um modelo **modesto**, e o repositório diz isso:
  precisão de 10% no limiar, e a probabilidade serve para ordenar pedidos, não como risco absoluto.
  Detalhes e leitura completa no [ADR-006](docs/decisoes/ADR-006-ml-sem-vazamento-e-divisao-temporal.md).

## Decisões de arquitetura

| ADR | Decisão |
|---|---|
| [001](docs/decisoes/ADR-001-ferramenta-por-camada.md) | Uma ferramenta por camada |
| [002](docs/decisoes/ADR-002-nota-do-pedido.md) | A nota do pedido é a avaliação mais recente |
| [003](docs/decisoes/ADR-003-uf-de-origem-do-pedido.md) | UF de origem construída na gold |
| [004](docs/decisoes/ADR-004-rls-por-uf-de-origem.md) | RLS por UF de origem, não de destino |
| [005](docs/decisoes/ADR-005-qa-nao-suportado-em-direct-lake.md) | Q&A não é suportado em Direct Lake |
| [006](docs/decisoes/ADR-006-ml-sem-vazamento-e-divisao-temporal.md) | Modelo de atraso sem vazamento, com divisão temporal |

## Limitações conhecidas

- **Sem Q&A nativo.** Não suportado em Direct Lake; o vocabulário fica no dicionário de dados (`ADR-005`).
- **Os dados e os relatórios vivem no workspace do Fabric.** O repositório guarda o código e as definições;
  reconstruir exige executar de novo o pipeline, o dataflow e os notebooks em um workspace com capacidade.
- **"UF mais crítica" não tem volume mínimo**, então aponta para UFs de poucos pedidos (ver
  `planejamento/fase-5-inicio.md`).
- **Lead time por mês** não tem visual de tendência.
- **O modelo de ML foi testado num período de menor atraso** (4,3%) que o de treino (7,8%).

---

## Licença e créditos

O código deste repositório é de uso livre. **O conjunto de dados Olist não é** — ele é
publicado sob licença Creative Commons e possui cláusula não comercial. Verifique os
termos na página do dataset antes de qualquer uso além de estudo e portfólio, e mantenha
a atribuição à Olist.

---

Construído por Robson Carlos de Toledo · [LinkedIn](https://www.linkedin.com/in/robsoncarlos-rc) · [Portfólio](https://robsoncdtoledo.github.io/portfolio/)
