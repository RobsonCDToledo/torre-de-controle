# Torre de Controle

**Plataforma de dados end-to-end em Microsoft Fabric para visibilidade logística.**

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
| Perguntas em linguagem natural | Sinônimos, descrições de campo e esquema linguístico configurados |
| Machine learning | Predição de atraso de entrega, com MLflow e sem vazamento temporal |

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
├── docs/
│   ├── 00-arquitetura.md          desenho completo e contrato de cada camada
│   ├── 01-como-replicar.md        passo a passo de recursos e alternativas
│   ├── dicionario-de-dados.md     catálogo de tabelas, campos e medidas
│   └── decisoes/                  registros de decisão de arquitetura (ADR)
├── fabric/                sincronizado com o workspace via integração Git
│   ├── pipelines/         definição do pipeline de ingestão
│   ├── dataflows/         Dataflow Gen2 (bronze → silver)
│   ├── notebooks/         gold e machine learning
│   ├── modelos-semanticos/  modelo Direct Lake em TMDL
│   └── relatorios/        relatórios em PBIR
├── scripts/               utilitários locais de preparo de dados
└── planejamento/          cronograma e escopo por fase
```

---

## Estado do projeto

Construído em seis fases, cada uma com entrega publicável. Acompanhe em
[planejamento/cronograma.md](planejamento/cronograma.md).

- [ ] **Fase 1** · Fundação — repositório, dados de origem, workspace, integração Git, ingestão para bronze
- [ ] **Fase 2** · Silver — Dataflow Gen2, tipagem, limpeza, regras de qualidade
- [ ] **Fase 3** · Gold — notebook, esquema estrela, dimensão calendário
- [ ] **Fase 4** · Semântica — Direct Lake, medidas DAX, Painel Executivo
- [ ] **Fase 5** · Self-service — RLS, endosso, dicionário, perguntas nativas, Painel de Frete
- [ ] **Fase 6** · ML — engenharia de atributos, modelo, MLflow, escrita na gold

---

## Licença e créditos

O código deste repositório é de uso livre. **O conjunto de dados Olist não é** — ele é
publicado sob licença Creative Commons e possui cláusula não comercial. Verifique os
termos na página do dataset antes de qualquer uso além de estudo e portfólio, e mantenha
a atribuição à Olist.

---

Construído por Robson Carlos de Toledo · [LinkedIn](https://www.linkedin.com/in/robsoncarlos-rc) · [Portfólio](https://robsoncdtoledo.github.io/portfolio/)
