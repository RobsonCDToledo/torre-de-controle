# ADR-001 · Uma ferramenta diferente para cada camada

**Status:** aceito
**Contexto:** definição da arquitetura inicial

---

## Contexto

O Microsoft Fabric oferece pelo menos três formas de mover e transformar dados: Data
Pipelines, Dataflows Gen2 e notebooks Spark. Qualquer uma delas, sozinha, conseguiria
construir todo o caminho da origem à camada gold.

Precisávamos decidir se o projeto usaria uma ferramenta só, por coerência, ou distribuiria
o trabalho entre elas.

## Decisão

Cada camada usa a ferramenta em que ela é de fato superior:

| Trecho | Ferramenta | Motivo |
|---|---|---|
| Origem → Bronze | **Data Pipeline**, Copy activity | Ingestão quer orquestração, parametrização e resiliência — não transformação. Um ForEach sobre a lista de arquivos resolve os nove em uma atividade, com agendamento e retentativa nativos |
| Bronze → Silver | **Dataflow Gen2** | É a camada que outro analista precisa conseguir ler e ajustar. Power Query é legível sem saber Spark, e o perfilamento de dados acelera a descoberta de problemas de qualidade |
| Silver → Gold | **Notebook PySpark** | Chaves substitutas, geração de dimensão calendário e engenharia de atributos são trabalho de código. Fazer isso em Power Query seria possível e seria pior |

## Alternativas consideradas

**Tudo em Dataflow Gen2.** Mais rápido de construir e mais próximo do perfil de quem vem
de BI. Rejeitada porque a modelagem dimensional fica desconfortável em Power Query, e a
camada de ML não teria como existir com naturalidade.

**Tudo em notebooks.** Demonstra competência de engenharia e é a opção mais poderosa.
Rejeitada porque descarta o Dataflow Gen2 — que é justamente a ferramenta que conecta este
projeto ao trabalho real de BI — e porque produziria um projeto que nenhum analista de
negócio conseguiria abrir e entender.

## Consequências

**Positivas.** O projeto demonstra três competências distintas do Fabric em vez de uma. Há
uma resposta pronta e defensável para a pergunta de entrevista "por que não fez tudo em
Dataflow?". E a camada silver permanece acessível a quem não programa, o que sustenta a
promessa de self-service.

**Negativas.** Três ferramentas significam três lugares para depurar quando algo quebra, e
três conjuntos de convenções para documentar. A curva de manutenção é maior que a de uma
solução homogênea.

**Mitigação.** Cada camada tem contrato explícito em `00-arquitetura.md`. Quando um número
está errado, o contrato diz em qual camada procurar.
