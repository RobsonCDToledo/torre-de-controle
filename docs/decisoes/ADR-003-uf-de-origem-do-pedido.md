# ADR-003 · UF de origem do pedido fica para a fase 5, construída na gold

**Status:** aceito
**Contexto:** construção do Painel Executivo, fase 4

---

## Contexto

Ao montar o gráfico de decomposição de atraso por rota do Painel Executivo, ficou claro que
**não existe UF de origem em `fato_entrega`** — ela só existe em `dim_vendedor`, ligada a
`fato_item_pedido`. Um pedido pode ter itens de mais de um vendedor, de UFs diferentes, então
"a UF de origem do pedido" não é um valor único até que uma regra escolha um vendedor — o
mesmo problema de "não existe 'a nota do pedido'" do ADR-002, agora na geografia de origem.

A primeira ideia foi resolver isso dentro do modelo semântico: uma tabela calculada em DAX
juntando `fato_item_pedido` e `fato_entrega` por `sk_pedido`, sumarizando dias de atraso por
(UF origem, UF destino). **Isso não é possível no Direct Lake**: tabela calculada só é
permitida quando não referencia nenhuma coluna de tabela Direct Lake — e as duas tabelas de
fato são Direct Lake. Não é lacuna de implementação, é limitação de plataforma.

## Decisão

**A "rota" (UF origem → UF destino) não existe na fase 4.** O Painel Executivo troca
"decomposição de atraso por rota" por "decomposição de atraso por UF de origem do vendedor" —
já resolvido pela medida `Dias de Atraso (méd) por Vendedor` (ponte `TREATAS`, documentada em
`docs/02-replicar-funcoes-dax.md`), que não exige grão único de origem por pedido.

A construção de "rota" de verdade fica para a **fase 5** (Painel de Frete e Rotas) e acontece
na **gold**, não no modelo semântico — mesma ferramenta-por-camada do ADR-001. O notebook
`nb_silver_para_gold` ganha uma coluna `uf_origem` em `fato_entrega`, resolvida por um critério
de desempate determinístico quando há mais de um vendedor: candidato natural é o vendedor do
item de maior `valor_itens` no pedido, com `sk_item` como desempate secundário — mesmo padrão
do ADR-002. A UF de destino já existe via `sk_geografia_destino → dim_geografia[uf]`, sem
mudança necessária.

## Alternativas consideradas

**Tabela calculada em DAX no modelo semântico.** Rejeitada — Direct Lake não permite tabela
calculada que referencie tabela Direct Lake. Não é contornável sem sair de Direct Lake, o que
reabriria uma decisão já fechada do projeto.

**Coluna calculada em DAX (Direct Lake, em preview) ligando as duas tabelas de fato via
`RELATED`.** Não há relacionamento entre `fato_entrega` e `fato_item_pedido` — foi removido de
propósito por ambiguidade com `dim_geografia`/`dim_calendario` (registrado no diário de
construção). Uma coluna calculada não recria esse caminho. Depende também de um recurso ainda
em preview — risco desnecessário para peça de portfólio.

**Mostrar "rota" sem desempate, uma linha por combinação vendedor×pedido.** Rejeitada — infla a
contagem de rotas em pedidos multi-vendedor e distorce a média de atraso a favor de pedidos com
muitos vendedores. Mesmo tipo de distorção que motivou manter dois grãos de fato no ADR-001.

## Consequências

**Positivas.** O Painel Executivo sai da fase 4 sem depender de recurso em preview nem de sair
de Direct Lake. Quando `uf_origem` for construída na fase 5, fica disponível pros dois
painéis, não só pro de Frete e Rotas.

**Negativas, e aceitas.** O gráfico "por rota" previsto inicialmente para a fase 4 em
`00-arquitetura.md` não sai nessa fase — o documento foi ajustado pra refletir isso.

## Desdobramento para a fase 5

Antes de construir o Painel de Frete e Rotas: adicionar `uf_origem` a `fato_entrega` no
notebook da gold, com o critério de desempate desta ADR (ou um substituto, se a distribuição
real dos dados sugerir outro — documentar a troca aqui se acontecer). Só depois disso o eixo de
rota (UF origem → UF destino) existe como coluna física, sem tabela calculada nem `TREATAS`.
