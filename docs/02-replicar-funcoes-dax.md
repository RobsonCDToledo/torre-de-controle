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

## Painel de Frete e Rotas — ponte por rota e insight narrativo

`rota` (UF origem → UF destino) só existe em `fato_entrega` — peso e custo por quilo só
existem em `fato_item_pedido`. Mesmo problema de fundo do `Dias de Atraso (méd) por Vendedor`
acima, direção oposta: aqui a ponte parte de `fato_entrega` para `fato_item_pedido`.

```dax
Peso Total (kg) por Rota =
CALCULATE(
    [Peso Total (kg)],
    TREATAS(VALUES(fato_entrega[sk_pedido]), fato_item_pedido[sk_pedido])
)
```
Formato: `0.00`

```dax
Custo por Quilo (por Rota) = DIVIDE([Valor de Frete], [Peso Total (kg) por Rota])
```
Formato: Currency (R$)
**Por que `Valor de Frete` e não `Valor de Frete (Item)`:** os dois somam pro mesmo total —
`fato_entrega[valor_frete]` já é soma do frete dos itens (ver dicionário) — então só o peso
precisa de ponte. Abrir uma segunda ponte só pro frete seria trabalho sem ganho.

### Cartão de insight — quem é a rota mais cara por quilo

```dax
Rota Mais Cara por Kg =
VAR Ranking =
    ADDCOLUMNS(
        SUMMARIZE(fato_entrega, fato_entrega[rota]),
        "@CustoKg", [Custo por Quilo (por Rota)]
    )
VAR RotaTop =
    TOPN(1, FILTER(Ranking, NOT ISBLANK(fato_entrega[rota]) && [@CustoKg] > 0), [@CustoKg], DESC)
RETURN
    MAXX(RotaTop, fato_entrega[rota])
```
Formato: texto. Ignora rota em branco ou custo zero — ruído de pedido sem item completo, não
uma rota real disputando o topo do ranking.

```dax
Custo por Kg da Rota Mais Cara =
VAR Ranking =
    ADDCOLUMNS(
        SUMMARIZE(fato_entrega, fato_entrega[rota]),
        "@CustoKg", [Custo por Quilo (por Rota)]
    )
VAR Filtrado =
    FILTER(Ranking, NOT ISBLANK(fato_entrega[rota]) && [@CustoKg] > 0)
RETURN
    MAXX(Filtrado, [@CustoKg])
```
Formato: Currency (R$)
**Por que não `CALCULATE([Custo por Quilo (por Rota)], fato_entrega[rota] = [Rota Mais Cara
por Kg])`:** foi a primeira tentativa, e quebrou em produção com "A function 'PLACEHOLDER' has
been used in a True/False expression that is used as a table filter expression" — o mesmo
erro-classe já visto em `OTD % (por Data de Entrega) — Rótulo Final` acima. `Coluna = [Medida
complexa]` dentro de `CALCULATE` nem sempre vira filtro de tabela simples quando a medida do
lado direito já tem `CALCULATE`/`TOPN` por trás — o motor não consegue linearizar. A correção é
a mesma receita das duas vezes: parar de tentar transformar a comparação num filtro de
`CALCULATE`, e calcular o valor direto dentro de uma tabela intermediária (`FILTER`/`MAXX`).

```dax
Custo por Kg Médio (Top 10) =
VAR Top10 = TOPN(10, SUMMARIZE(fato_entrega, fato_entrega[rota]), [Valor de Frete], DESC)
RETURN AVERAGEX(Top10, [Custo por Quilo (por Rota)])
```
Formato: Currency (R$)
"Maior volume" = Top 10 rotas por `Valor de Frete` — o mesmo corte usado no treemap do painel,
pra a frase de insight e o visual contarem a mesma história com o mesmo recorte.

```dax
Múltiplo Custo por Kg = DIVIDE([Custo por Kg da Rota Mais Cara], [Custo por Kg Médio (Top 10)])
```
Formato: `0.0"×"`

```dax
Insight Frete e Rotas =
"R$ " & FORMAT(DIVIDE([Valor de Frete], 1000000), "#,0.00") & "M em frete no período (" &
FORMAT([Frete sobre Faturamento], "0,0%") & " do faturamento). A rota " &
[Rota Mais Cara por Kg] & " é a mais cara por quilo — " &
FORMAT([Custo por Kg da Rota Mais Cara], "\R\$ 0,00") & ", quase " &
FORMAT([Múltiplo Custo por Kg], "0,0") & "× o custo das rotas de maior volume."
```
Formato: texto. Concatena as quatro medidas acima numa frase só, mostrada num cartão sem
título — mesmo padrão de "medida devolve texto pronto" das medidas de formatação visual, só
que pra consumo direto do leitor do painel, não pra formatação condicional de outro visual.

---

## Medidas de formatação visual

Diferente de tudo acima, estas sete medidas não calculam indicador de negócio novo — geram um
valor de apoio (cor, texto, rótulo condicional) que um visual consome via formatação
condicional ou vinculação direta. Necessárias pro funcionamento da UI do painel, não pra
análise: por isso ficam **ocultas** (`isHidden`) do painel de campos — um analista não tem
motivo pra arrastar `OTD % (Text Color)` solta num visual. Moram em `_medidas`, pasta de
exibição `Formatações`.

### Régua de cor do OTD

Três medidas implementam a régua de status documentada em `design/paleta-e-uso.md`
(`≥95% bom · 85–95% atenção · <85% crítico`), cada uma devolvendo um valor diferente pro mesmo
limiar:

```dax
OTD % (Text Color) =
VAR vValor = [OTD %]
RETURN
SWITCH(
    TRUE(),
    vValor >= 0.95, "#047857",
    vValor >= 0.85, "#B45309",
    vValor <  0.85, "#B91C1C"
)

OTD % (Background Color) =
VAR vValor = [OTD %]
RETURN
SWITCH(
    TRUE(),
    vValor >= 0.95, "#ECFDF5",
    vValor >= 0.85, "#FFFBEB",
    vValor <  0.85, "#FEF2F2"
)

OTD % (Legend) =
VAR vValor = [OTD %]
RETURN
SWITCH(
    TRUE(),
    vValor >= 0.95, "Bom!",
    vValor >= 0.85, "Atenção!",
    vValor <  0.85, "Crítico!"
)
```
Formato: texto.
**Onde aplicar:** `OTD % (Text Color)` / `(Background Color)` em Formatação condicional → cor
da fonte / plano de fundo → Campo, no cartão de KPI e no cartograma por UF. `OTD % (Legend)`
alimenta o texto do badge de status.
**Por que texto na tonalidade 700 e fundo na 50, não a cor bruta do tema (`good`/`neutral`/
`bad`):** contraste — a cor 500 sozinha não passa no piso de 3:1 sobre fundo claro; o par
texto-escuro-sobre-fundo-claro resolve isso sem inventar uma quarta cor fora do sistema.

```dax
Meta OTD = 0.95
```
Formato: geral. Expõe o limiar "bom" como constante — alimenta a linha de referência do
gráfico de evolução mensal, em vez de ficar hardcoded dentro da formatação de cada visual que
precisar dele.

### Rótulo seletivo da linha de evolução

```dax
OTD % (por Data de Entrega) — Rótulo Final =
VAR UltimoPontoComDados =
    CALCULATE(
        MAX(dim_calendario[sk_data]),
        FILTER(
            ALLSELECTED(dim_calendario),
            NOT ISBLANK([OTD % (por Data de Entrega)])
        )
    )
RETURN
IF(
    MAX(dim_calendario[sk_data]) = UltimoPontoComDados,
    [OTD % (por Data de Entrega)],
    BLANK()
)
```
Formato: geral. Alimenta uma segunda série invisível (linha de espessura 0, sem marcador) no
gráfico "Evolução Mensal do OTD" — só essa série tem rótulo de dado ligado, e só ela retorna
valor no último ponto com dado, deixando a linha real intocada e sem rótulo em cada mês.
**Por que o `FILTER`:** `NOT ISBLANK([OTD % (por Data de Entrega)])` direto como filtro do
`CALCULATE`, sem `FILTER()`, dispara "A function ... has been used in a True/False expression
that is used as a table filter expression" — medida com `CALCULATE`/`USERELATIONSHIP` por trás
não pode virar condição booleana solta; precisa do contexto de linha que o `FILTER` cria.

### Texto formatado

```dax
Lead Time Médio Format = FORMAT([Lead Time Médio], "#.0 Dias")
Dias em Atraso (Format) = FORMAT([Dias de Atraso (méd)], "#.0 Dias")
```

Formato: texto. Versão textual das duas medidas, com o sufixo "Dias" embutido — usada onde o
visual não aceita `formatString` numérico customizado.

---

## Pendências fora do escopo deste documento

- **Hierarquia de calendário** (`Ano` → `Trimestre` → `Mês` → `Dia`) — construída visualmente
  no Desktop, não é medida DAX, não entra aqui.
- ~~Descrições de medida~~ — **tentado e revertido**, não é mais pendência: `description` não
  é propriedade suportada pelo parser TMDL deste workspace, em nenhum nível (tabela, coluna ou
  medida). Ver `ADR-005-qa-nao-suportado-em-direct-lake.md`, seção "Tentativa de descrições,
  revertida".
