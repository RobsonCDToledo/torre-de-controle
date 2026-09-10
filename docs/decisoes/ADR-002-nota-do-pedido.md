# ADR-002 · A nota do pedido é a avaliação mais recente

**Status:** aceito
**Contexto:** construção da `fato_entrega`, fase 3

---

## Contexto

A `fato_entrega` tem grão de **pedido** e precisa de uma coluna `nota` para servir de proxy
de qualidade percebida da entrega. A origem não entrega isso pronto.

A relação entre pedido e avaliação é **muitos-para-muitos legítima**, nos dois sentidos:

| Situação | Quantidade |
|---|---|
| Pedidos com mais de uma avaliação | **547** |
| Pedidos sem nenhuma avaliação | **768** |
| Avaliações que cobrem mais de um pedido | **789** |

Ou seja: **não existe "a nota do pedido" neste dataset.** Ela precisa ser construída por uma
regra declarada, e a regra escolhida muda o indicador de qualidade que o painel executivo vai
mostrar.

O grão da `fato_entrega` não está em discussão — OTD é atributo do pedido, e essa decisão
está no ADR-001 e no desenho de dois fatos. O que se decide aqui é como colapsar de uma a
várias avaliações em um único número por pedido.

## Decisão

**A nota do pedido é a da avaliação de `data_avaliacao` mais recente.** Em caso de empate na
data, desempata por `id_avaliacao` para que a reconstrução da gold seja determinística.

**Pedido sem avaliação recebe nulo, nunca zero.** A escala da origem vai de 1 a 5; zero não
existe nela. Preencher com zero criaria 768 notas mínimas artificiais que afundariam
qualquer média — e o problema seria invisível, porque o número resultante continua plausível.

## Alternativas consideradas

**Média das notas.** Usa toda a informação disponível e é a escolha mais defensável
estatisticamente. Rejeitada por duas razões: produz valores fracionados (3,5) que não existem
na escala de 1 a 5 e ficam estranhos num painel que mostra estrelas; e mistura opiniões que
podem ser sobre coisas diferentes, já que a segunda avaliação de um pedido às vezes é uma
retificação da primeira, não uma segunda medição do mesmo fenômeno.

**A menor nota.** Conservadora, e alinhada à leitura logística de que uma entrega ruim
contamina a experiência inteira do pedido. Rejeitada porque puxa o indicador para baixo de
forma deliberada, o que exigiria uma nota explicativa em todo painel onde a média aparecesse
— e porque a intenção aqui é medir qualidade percebida, não construir um índice de risco.

**Manter o grão de avaliação num terceiro fato.** Tecnicamente o mais correto: preservaria a
relação muitos-para-muitos inteira, sem perda. Rejeitada pelo custo — um terceiro fato com
tabela ponte, para um atributo que é secundário no projeto. O objetivo da plataforma é
visibilidade logística; a avaliação é proxy de qualidade, não o indicador central.

## Consequências

**Positivas.** A regra é uma frase, cabe no dicionário de dados e no tooltip do painel.
Trata a segunda avaliação como retificação da primeira, que é a leitura mais provável do
comportamento do cliente. E é determinística: a gold reconstruída devolve a mesma nota.

**Negativas, e aceitas.** Quando as duas avaliações de um pedido são sobre itens diferentes,
a mais recente descarta informação real. São 547 pedidos em 99.441 — 0,55% —, e o efeito na
média agregada é desprezível; num pedido individual, não é. Quem consultar o pedido no
endpoint SQL vê uma nota e não sabe que houve outra.

**Mitigação.** A `silver.avaliacoes` preserva as 99.224 linhas com a chave composta intacta.
Nenhuma avaliação foi perdida na plataforma — o colapso acontece só no fato, e é reversível
por consulta à silver.

## Decisão relacionada, tomada na mesma sessão

**`sk_data_entrega` fica nulo nos 2.965 pedidos sem `data_entrega_real`**, sem linha
sentinela na `dim_calendario`.

O argumento decisivo não foi de modelagem, foi de negócio: **não se sabe por que o pedido não
foi entregue.** O dataset não tem base de devoluções, cancelamentos logísticos ou ocorrências,
então não há como distinguir entrega em trânsito de entrega recusada, extraviada ou devolvida.
Atribuir qualquer data — inclusive uma sentinela batizada de "desconhecida" — dá aparência de
tratamento a um fato que simplesmente não foi observado.

O nulo mantém a ausência visível, e o OTD já exclui pedidos não entregues por definição.

**Desdobramento para a fase 4:** esses 2.965 pedidos são uma **fila de trabalho**, não um
descarte. A recomendação é expor os casos mais antigos como lista acionável no painel, para
que quem acompanha entrega priorize contato. É a diferença entre um painel que informa e uma
ferramenta que gera trabalho — e vale como demonstração no case.
