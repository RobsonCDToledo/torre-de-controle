# Replicar funções DAX

Catálogo de toda medida do modelo semântico `sm_torre_de_controle` — nome, código, formato e o
cuidado de negócio por trás de cada uma. Serve a dois propósitos: reconstruir o modelo se o
trial do Fabric expirar antes de tudo estar publicado, e documentar a razão de cada fórmula não
ser a óbvia.

As três primeiras (`OTD %`, `Lead Time Médio`, `Frete sobre Faturamento`) também aparecem em
`dicionario-de-dados.md`, seção "Medidas do modelo semântico" — este arquivo é a versão
completa, com o código.

---

## Onde aplicar: Web Modeling, nunca o Power BI Desktop

**O relatório conecta no `sm_torre_de_controle` por Live Connection.** Live Connection é
somente leitura para o modelo — o Desktop não mostra Model view nem "Nova medida" contra ele.
Se o Desktop oferecer isso mesmo assim, a medida criada fica **local ao relatório**, não vai
pro modelo publicado, e quebra "um modelo, muitos relatórios": o próximo relatório que
conectar no mesmo modelo não a enxerga. Toda medida deste catálogo é criada **no portal do
Fabric, editor do modelo semântico (Web Modeling)** — nunca no Desktop.

Toda medida mora em **`_medidas`**, tabela de cálculo vazia (zero linhas, sem coluna) já criada
lá — não nas tabelas de fato. Centralizar medidas fora das tabelas de dado é o que o Best
Practice Analyzer cobra, e evita que `fato_entrega`/`fato_item_pedido` misturem coluna física
com cálculo.

1. Portal do Fabric → workspace → `sm_torre_de_controle` → **Editar** (Web Modeling).
2. Selecione a tabela `_medidas`, **Nova medida**, cole o código de cada fórmula abaixo,
   confirme. A fórmula referencia coluna de `fato_entrega`/`fato_item_pedido` normalmente — só
   a *home table* da medida é `_medidas`.
3. No painel de propriedades, aplique o formato indicado.
4. Organize por **pasta de exibição** (`Display folder`): `Contadores`, `Financeiro`,
   `Atraso`, `Avaliação` — facilita achar a medida certa depois.
5. **Commit** no painel de Controle de código-fonte do workspace, pra medida sair do modelo
   ao vivo e virar TMDL versionado no Git. Sem esse passo ela existe só no serviço.
6. No Desktop, **Refresh** do relatório pra sincronizar o painel de campos com o modelo
   publicado e usar as medidas novas nos visuais — o Desktop só *consome* a partir daqui.

As seções abaixo indicam de qual tabela cada medida **lê as colunas** (para saber onde estão
`SUM`, `AVERAGE` etc.) — não é onde a medida é criada; todas vivem em `_medidas`.

Medidas em português, com espaço, exatamente como aparecem aqui — é o nome que o usuário do
painel vê.

---

## `fato_entrega` — grão do pedido

### Contadores base

```dax
Total de Pedidos = COUNTROWS(fato_entrega)
```
Formato: `0`

```dax
Pedidos Entregues =
CALCULATE([Total de Pedidos], NOT ISBLANK(fato_entrega[entregue_no_prazo]))
```
Formato: `0`
**Por quê `entregue_no_prazo` e não `sk_data_entrega`:** os dois ficam nulos juntos para pedido
não entregue (ver `dicionario-de-dados.md`), mas `entregue_no_prazo` é o campo com significado
de negócio explícito.

```dax
Pedidos no Prazo =
CALCULATE([Total de Pedidos], fato_entrega[entregue_no_prazo] = TRUE)
```
Formato: `0`

```dax
Pedidos Cancelados =
CALCULATE([Total de Pedidos], fato_entrega[status_pedido] = "canceled")
```
Formato: `0`

### As três medidas centrais

```dax
OTD % = DIVIDE([Pedidos no Prazo], [Pedidos Entregues])
```
Formato: `0.0%`
**Cuidado:** denominador exclui pedidos não entregues — já embutido em `[Pedidos Entregues]`.
Contar não entregues como "atrasados" infla o indicador.

```dax
Lead Time Médio = AVERAGE(fato_entrega[lead_time_dias])
```
Formato: `0.0" dias"`

```dax
Lead Time Mediano = MEDIAN(fato_entrega[lead_time_dias])
```
Formato: `0.0" dias"`
Complementa a média — o próprio dicionário avisa que lead time é sensível a outliers.

```dax
Frete sobre Faturamento = DIVIDE([Valor de Frete], [Valor de Itens])
```
Formato: `0.0%`
**Cuidado:** razão de somas, nunca média de razões — calcular por pedido e tirar a média
distorce a favor de pedidos pequenos.

### Financeiro

```dax
Valor de Itens = SUM(fato_entrega[valor_itens])
Valor de Frete = SUM(fato_entrega[valor_frete])
```
Formato: Currency (R$)

```dax
Ticket Médio = DIVIDE([Valor de Itens], [Total de Pedidos])
```
Formato: Currency (R$)

### Decomposição de atraso por etapa

Item explícito do Painel Executivo em `00-arquitetura.md`.

```dax
Dias até Aprovação (méd) = AVERAGE(fato_entrega[dias_ate_aprovacao])
Dias até Coleta (méd) = AVERAGE(fato_entrega[dias_ate_coleta])
```
Formato: `0.0" dias"`

```dax
Dias de Transporte (méd) =
CALCULATE(
    AVERAGEX(fato_entrega, fato_entrega[lead_time_dias] - fato_entrega[dias_ate_coleta]),
    NOT ISBLANK(fato_entrega[entregue_no_prazo])
)
```
Formato: `0.0" dias"`
**Cuidado:** `AVERAGEX` calcula a diferença por pedido e depois tira a média — subtrair duas
médias já prontas não dá o mesmo resultado (desigualdade de Jensen). O filtro `NOT ISBLANK`
evita que pedido não entregue vire `0 - dias_ate_coleta`, porque `BLANK` se comporta como `0`
em aritmética do DAX.

```dax
Dias de Atraso (méd) =
CALCULATE(AVERAGE(fato_entrega[dias_de_atraso]), fato_entrega[dias_de_atraso] > 0)
```
Formato: `0.0" dias"`
A definição em `00-arquitetura.md` é "média entre os **pedidos atrasados**" — por isso o
filtro `> 0`, não apenas não-nulo. Pedido adiantado (`dias_de_atraso` negativo) não entra.

### Avaliação

```dax
Nota Média = AVERAGE(fato_entrega[nota])
```
Formato: `0.00`
Nula em 768 pedidos (ver dicionário) — `AVERAGE` já ignora nulos, nenhum tratamento extra.

### Trocando o eixo de tempo — relacionamentos inativos

`sk_data_prevista` e `sk_data_entrega` se ligam a `dim_calendario` como relacionamento
**inativo** (o ativo é `sk_data_compra`). O Best Practice Analyzer já sinalizou: relacionamento
inativo sem medida `USERELATIONSHIP` correspondente vira defeito, não intenção.

```dax
Pedidos Entregues (por Data de Entrega) =
CALCULATE(
    [Pedidos Entregues],
    USERELATIONSHIP(fato_entrega[sk_data_entrega], dim_calendario[sk_data])
)

OTD % (por Data de Entrega) =
CALCULATE(
    [OTD %],
    USERELATIONSHIP(fato_entrega[sk_data_entrega], dim_calendario[sk_data])
)
```
Formato: `0` e `0.0%`
Necessárias para a "evolução mensal" do Painel Executivo fazer sentido por mês em que a
entrega **aconteceu** — sem isso, todo gráfico de tempo só enxerga o mês de compra.

---

## `fato_item_pedido` — grão do item

### Financeiro e frete

```dax
Valor de Frete (Item) = SUM(fato_item_pedido[valor_frete])
Peso Total (kg) = SUM(fato_item_pedido[peso_gramas]) / 1000
```
Formato: Currency (R$) / `0.0" kg"`

```dax
Custo por Quilo = DIVIDE([Valor de Frete (Item)], [Peso Total (kg)])
```
Formato: Currency (R$)
Pertence ao escopo do Painel de Frete e Rotas (fase 5), mas a medida já pode existir no modelo
sem custo — só passa a ser usada quando esse painel for construído.

### Decomposição de atraso por rota — a ponte virtual

`00-arquitetura.md` pede "decomposição de atraso por etapa **e por rota**" no Painel
Executivo. O problema: `dim_vendedor[uf]` (origem da rota) só existe em `fato_item_pedido`;
`dias_de_atraso` só existe em `fato_entrega`. Não há relacionamento direto entre os dois
fatos — foi removido de propósito, registrado no diário de construção, porque criava caminho
ambíguo com `dim_geografia` e `dim_calendario`.

A ponte certa é uma relação **virtual**, via `TREATAS` — não uma medida de soma direta, e não
um relacionamento físico novo (isso reabriria a ambiguidade):

```dax
Dias de Atraso (méd) por Vendedor =
CALCULATE(
    [Dias de Atraso (méd)],
    TREATAS(VALUES(fato_item_pedido[sk_pedido]), fato_entrega[sk_pedido])
)
```
Formato: `0.0" dias"`
**Por que funciona:** num visual filtrado por `dim_vendedor`, `VALUES(fato_item_pedido[sk_pedido])`
já devolve só os pedidos que têm item daquele vendedor. `TREATAS` empurra esse conjunto para
dentro de `fato_entrega` sem relacionamento físico — a mesma técnica se replica para
`OTD %` e qualquer outra medida de `fato_entrega`, trocando `[Dias de Atraso (méd)]` pela
medida desejada dentro do `CALCULATE`.

---

## Pendências fora do escopo deste documento

- **Hierarquia de calendário** (`Ano` → `Trimestre` → `Mês` → `Dia`) — construída visualmente
  no Desktop, não é medida DAX, não entra aqui.
- **Descrições de medida** — entregável da fase 5 (self-service e perguntas nativas).
