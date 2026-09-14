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
`nb_silver_para_gold` ganha três colunas em `fato_entrega`: `uf_origem` (vendedor do item de
maior `preco` no pedido, `numero_item` como desempate secundário — mesmo padrão do ADR-002,
ajustado porque `sk_item` só existe depois que `fato_item_pedido` é montado), `uf_destino`
(mesmo join que já gerava `sk_geografia_destino`, agora também exposto como UF) e `rota`
(`CONCAT(uf_origem, ' → ', uf_destino)`, pronta pra uso direto em visual sem depender de coluna
calculada em DAX).

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
de Direct Lake. `uf_origem`, `uf_destino` e `rota` ficam disponíveis pros dois painéis, não só
pro de Frete e Rotas, e `rota` já sai pronta pra uso em visual, sem coluna calculada em DAX.

**Negativas, e aceitas.** O gráfico "por rota" previsto inicialmente para a fase 4 em
`00-arquitetura.md` não saiu nessa fase — o documento foi ajustado pra refletir isso.
`uf_origem` (e por extensão `rota`) é uma aproximação em **≈1,3% dos pedidos** (1.278 de
98.666 pedidos com item) — os que têm item de mais de um vendedor. Nesses casos, a UF
registrada é a do vendedor com o item de maior preço, não uma junção fiel de todas as origens
reais. Aceito porque a alternativa (uma linha por combinação vendedor×pedido) foi rejeitada
acima pelo mesmo motivo do ADR-001.

## Status — implementado e validado

Construído em `nb_silver_para_gold`, célula `fato_entrega`. Validação rodada e conferida:

| Validação | Esperado | Real |
|---|---|---|
| Linhas em `fato_entrega` | 99.441 | **99.441** |
| `uf_origem` nulo | 775 (pedidos sem item) | **775** |
| `uf_destino` nulo | igual a `sk_geografia_destino` nulo | **279**, zero divergência |
| `rota` nulo | ≥ 775 (união dos dois lados) | **1.050** = 775 + 279 − 4 (só 4 pedidos nulos nos dois) |
| Pedidos com item e mais de um vendedor | — | **1.278** de 98.666 (**≈1,3%**) |

`uf_destino` e `rota` foram adicionados junto com `uf_origem`, além do escopo mínimo original
desta ADR — os três reaproveitam os mesmos `JOIN`s já existentes na célula (`dim_vendedor` e
`dim_geografia`), então saíram sem custo extra de junção. Com isso, o eixo de rota (UF origem →
UF destino) já existe como coluna física, pronto pro Painel de Frete e Rotas da fase 5 — sem
tabela calculada, sem `TREATAS`, sem depender de recurso em preview.
