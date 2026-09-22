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

## Painel de Atribuição de Causas — reaproveitando a ponte por vendedor

Nasceu do teste de aceite da fase 5 (item 5): simulando um analista externo respondendo só com
o que os dois painéis publicados expunham, três perguntas do dicionário falharam — OTD por UF
de origem, contagem de atrasados por UF de origem e nota média por categoria de produto não
tinham visual nem medida nenhuma. As três usam a mesma ponte `TREATAS` de
`Dias de Atraso (méd) por Vendedor` (`fato_item_pedido` → `fato_entrega`, ver seção acima) —
nenhuma ponte nova, só a mesma bridge envolvendo três expressões diferentes.

```dax
OTD % por Vendedor =
CALCULATE(
    [OTD %],
    TREATAS(VALUES(fato_item_pedido[sk_pedido]), fato_entrega[sk_pedido])
)
```
Formato: `#,0.0%`

```dax
Pedidos Atrasados por Vendedor =
CALCULATE(
    COUNTROWS(fato_entrega),
    fato_entrega[dias_de_atraso] > 0,
    TREATAS(VALUES(fato_item_pedido[sk_pedido]), fato_entrega[sk_pedido])
)
```
Formato: `#,0`
Não reaproveita `[Dias de Atraso (méd) por Vendedor]` porque essa mede a *média* dos dias — aqui
o pedido é a *contagem* de pedidos atrasados, então o filtro `dias_de_atraso > 0` entra direto
no `CALCULATE`, ao lado da ponte, em vez de compor sobre outra medida.

```dax
Nota Média por Categoria =
CALCULATE(
    [Nota Média],
    TREATAS(VALUES(fato_item_pedido[sk_pedido]), fato_entrega[sk_pedido])
)
```
Formato: `#,0.00`
**Por que a mesma ponte serve pra categoria de produto, não só pra vendedor:** a `TREATAS`
propaga qualquer filtro que já esteja em vigor sobre `fato_item_pedido[sk_pedido]` — não importa
se esse filtro chegou de `dim_vendedor` (via `sk_vendedor`) ou de `dim_produto` (via
`sk_produto`). A ponte não sabe nem precisa saber qual dimensão originou o filtro; ela só
carrega o conjunto de pedidos resultante para dentro de `fato_entrega`. Por isso não foi preciso
escrever uma quarta bridge — as três medidas moram em `Fato item pedido\Ponte Virtual`, mesma
pasta da ponte original.

```dax
Desvio OTD por Vendedor = [OTD % por Vendedor] - [OTD %]
```
Formato: `#,0.0%`. Pensada pra ir direto num gráfico de barras com `dim_vendedor[uf]` no eixo —
diferente das medidas "Mais Crítica" acima, que devolvem um valor único, esta devolve um valor
por UF. Funciona porque `dim_vendedor` não tem relacionamento físico com `fato_entrega`: dentro
de um visual com `uf` no eixo, `[OTD %]` (que só enxerga `fato_entrega`) permanece no total
nacional em toda linha, então a subtração já dá o desvio direto — sem precisar de
`ALLSELECTED`/`REMOVEFILTERS` pra "desfazer" um filtro que nunca chegou lá.

```dax
Quantidade de Itens = COUNTROWS(fato_item_pedido)
```
Formato: `#,0`, pasta `Fato item pedido\Financeiro e Frete`. Medida de volume genérica — critério
de corte "Top N por volume" nos visuais de categoria de produto, e reaproveitada como `@Itens`
nas três medidas de ranking por categoria abaixo, em vez de repetir `CALCULATE(COUNTROWS(...))`
inline três vezes.

### Cartão de insight — quem é a UF e a categoria mais críticas

Mesma família de "medida de ranking → valor no ranking → comparativo → texto" da seção acima,
com uma UF de origem no lugar de uma rota, e uma categoria de produto no lugar de um Top 10 por
frete. Moram em `Fato item pedido\Insight Atribuição de Causas`.

```dax
UF Mais Crítica (Vendedor) =
VAR Ranking =
    ADDCOLUMNS(
        SUMMARIZE(dim_vendedor, dim_vendedor[uf]),
        "@OTD", [OTD % por Vendedor]
    )
VAR Filtrado =
    FILTER(Ranking, NOT ISBLANK(dim_vendedor[uf]) && NOT ISBLANK([@OTD]))
VAR Pior =
    TOPN(1, Filtrado, [@OTD], ASC)
RETURN
    MAXX(Pior, dim_vendedor[uf])
```
Formato: texto. Mesmo cuidado de `Rota Mais Cara por Kg`: ignora UF em branco ou OTD em branco,
não uma UF real disputando o fundo do ranking.

```dax
OTD % da UF Mais Crítica =
VAR Ranking =
    ADDCOLUMNS(
        SUMMARIZE(dim_vendedor, dim_vendedor[uf]),
        "@OTD", [OTD % por Vendedor]
    )
VAR Filtrado =
    FILTER(Ranking, NOT ISBLANK(dim_vendedor[uf]) && NOT ISBLANK([@OTD]))
RETURN
    MINX(Filtrado, [@OTD])
```
Formato: `#,0.0%`
**Por que `MINX` na tabela de ranking, e não `CALCULATE([OTD % por Vendedor], dim_vendedor[uf] =
[UF Mais Crítica (Vendedor)])`:** a segunda forma é exatamente o padrão que já quebrou com o erro
PLACEHOLDER em `Custo por Kg da Rota Mais Cara` — comparar uma coluna a uma medida complexa
dentro de `CALCULATE` não linhariza quando a medida da direita já tem `CALCULATE`/`TREATAS` por
trás. `MINX` sobre a própria tabela de ranking já filtrada evita o filtro por igualdade por
completo.

```dax
Desvio OTD da UF Mais Crítica = [OTD % da UF Mais Crítica] - [OTD %]
```
Formato: `#,0.0%`. Negativo por definição — combina duas medidas escalares por subtração
simples, sem risco de PLACEHOLDER porque não há filtro de tabela envolvido.

```dax
Pedidos Atrasados da UF Mais Crítica =
VAR Ranking =
    ADDCOLUMNS(
        SUMMARIZE(dim_vendedor, dim_vendedor[uf]),
        "@OTD", [OTD % por Vendedor],
        "@Atrasados", [Pedidos Atrasados por Vendedor]
    )
VAR Filtrado =
    FILTER(Ranking, NOT ISBLANK(dim_vendedor[uf]) && NOT ISBLANK([@OTD]))
VAR Pior =
    TOPN(1, Filtrado, [@OTD], ASC)
RETURN
    MAXX(Pior, [@Atrasados])
```
Formato: `#,0`. Adiciona a coluna `@Atrasados` na mesma tabela de ranking em vez de abrir uma
ponte nova — o `TOPN` já escolhe a linha da UF mais crítica pelo `@OTD`, então `MAXX` só precisa
ler a coluna extra da mesma linha.

```dax
Categoria Mais Crítica (Nota) =
VAR RankingVolume =
    ADDCOLUMNS(
        SUMMARIZE(dim_produto, dim_produto[categoria_rotulo]),
        "@Itens", CALCULATE(COUNTROWS(fato_item_pedido)),
        "@Nota", [Nota Média por Categoria]
    )
VAR Top10Volume =
    TOPN(10, FILTER(RankingVolume, NOT ISBLANK(dim_produto[categoria_rotulo])), [@Itens], DESC)
VAR Top10ComNota =
    FILTER(Top10Volume, NOT ISBLANK([@Nota]))
VAR Pior =
    TOPN(1, Top10ComNota, [@Nota], ASC)
RETURN
    MAXX(Pior, dim_produto[categoria_rotulo])
```
Formato: texto. "Maior volume" aqui é contagem de itens (`COUNTROWS(fato_item_pedido)`), não
`Valor de Frete` como no Painel de Frete e Rotas — o contexto de negócio é diferente (qualidade
percebida, não custo de transporte), então o corte de volume usa a métrica que faz sentido pra
essa pergunta.

```dax
Nota da Categoria Mais Crítica =
VAR RankingVolume =
    ADDCOLUMNS(
        SUMMARIZE(dim_produto, dim_produto[categoria_rotulo]),
        "@Itens", CALCULATE(COUNTROWS(fato_item_pedido)),
        "@Nota", [Nota Média por Categoria]
    )
VAR Top10Volume =
    TOPN(10, FILTER(RankingVolume, NOT ISBLANK(dim_produto[categoria_rotulo])), [@Itens], DESC)
VAR Top10ComNota =
    FILTER(Top10Volume, NOT ISBLANK([@Nota]))
RETURN
    MINX(Top10ComNota, [@Nota])

Melhor Nota (Top 10 Categorias) =
VAR RankingVolume =
    ADDCOLUMNS(
        SUMMARIZE(dim_produto, dim_produto[categoria_rotulo]),
        "@Itens", CALCULATE(COUNTROWS(fato_item_pedido)),
        "@Nota", [Nota Média por Categoria]
    )
VAR Top10Volume =
    TOPN(10, FILTER(RankingVolume, NOT ISBLANK(dim_produto[categoria_rotulo])), [@Itens], DESC)
VAR Top10ComNota =
    FILTER(Top10Volume, NOT ISBLANK([@Nota]))
RETURN
    MAXX(Top10ComNota, [@Nota])
```
Formato: `#,0.00` nas duas. Mesma tabela `RankingVolume`/`Top10ComNota` reconstruída em cada
medida — `MINX` pra pior nota, `MAXX` pra melhor. Recalcular a tabela em vez de compartilhar
entre medidas é o mesmo padrão já usado em `Rota Mais Cara por Kg` / `Custo por Kg da Rota Mais
Cara`: DAX não deixa reaproveitar uma `VAR` de tabela entre medidas diferentes.

```dax
Diferença Nota vs Melhor Categoria = [Melhor Nota (Top 10 Categorias)] - [Nota da Categoria Mais Crítica]
```
Formato: `#,0.00`

```dax
Insight Atribuição de Causas =
"A UF de origem " & [UF Mais Crítica (Vendedor)] & " é a mais crítica — " &
FORMAT([OTD % da UF Mais Crítica], "0,0%") & " de OTD, " &
FORMAT(ABS([Desvio OTD da UF Mais Crítica]) * 100, "0,0") & " pontos abaixo da média nacional, com " &
FORMAT([Pedidos Atrasados da UF Mais Crítica], "#,0") & " pedidos atrasados. Entre as categorias de maior volume, " &
[Categoria Mais Crítica (Nota)] & " tem a pior nota — " &
FORMAT([Nota da Categoria Mais Crítica], "0,0") & " estrelas, " &
FORMAT([Diferença Nota vs Melhor Categoria], "0,0") & " abaixo da melhor colocada."
```
Formato: texto. Mesmo padrão de `Insight Frete e Rotas` — concatena as medidas acima numa frase
pronta pro cartão de destaque. `ABS(...) * 100` converte a fração do desvio em pontos percentuais
direto na formatação, sem precisar de uma medida só pra isso.

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
