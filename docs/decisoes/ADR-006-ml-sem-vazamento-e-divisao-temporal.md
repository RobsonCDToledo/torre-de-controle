# ADR-006 · Modelo de atraso: sem vazamento, divisão temporal e probabilidade para ranquear

**Status:** aceito
**Contexto:** fase 6 — `nb_ml_atraso`, predição de atraso no instante da compra

---

## Contexto

O alvo é `atraso = 1` quando `entregue_no_prazo = false`, só para pedidos entregues (96.476). Um modelo
de atraso é fácil de fazer parecer excelente: basta deixar entrar qualquer coisa que aconteça depois da
compra. O projeto existe para mostrar o contrário.

## Decisão

1. **Só entram atributos conhecidos na compra.** Proibidos: `dias_ate_aprovacao`, `dias_ate_coleta`,
   `lead_time_dias`, `dias_de_atraso`, `sk_data_entrega`, `nota`, `status_pedido` e qualquer derivado de
   `order_approved_at` ou `order_delivered_carrier_date`. O notebook **falha** se algum deles entrar na lista.
2. **Pontualidade do vendedor com janela estritamente anterior.** Para cada pedido, só contam entregas do
   mesmo vendedor com `data_entrega < data_compra` do pedido. Entrega no mesmo dia fica de fora.
3. **Divisão temporal 70/15/15 pela data de compra**, não aleatória. Treino 15/09/2016–14/04/2018,
   validação 15/04–20/06/2018, teste 21/06–29/08/2018. O limiar de decisão (0,1092) é escolhido no maior F1 da
   **validação** e só então aplicado ao teste.
4. **Predição gravada para todos os pedidos com item**, com a coluna `conjunto`. O painel compara previsto e
   realizado **só em `teste`**: em treino e validação a predição é dentro da amostra.
5. **Sem `class_weight`.** A probabilidade fica próxima da frequência real e é interpretável.

## Alternativas consideradas

**Divisão aleatória.** Rejeitada: pedidos do futuro ajudariam a prever pedidos do passado, e a métrica
sairia inflada. A divisão temporal é a que reproduz o uso real.

**Pontualidade do vendedor sobre a base inteira.** Rejeitada: carregaria o desfecho de pedidos futuros do
próprio vendedor para o treino.

**Balancear classes.** Rejeitado: distorce a probabilidade, e o painel precisa mostrar risco.

## Resultado (execução de 07/10/2026)

| Métrica (teste) | Baseline* | Modelo | Referência |
|---|---|---|---|
| ROC-AUC | 0,622 | **0,716** | 0,5 = acaso |
| PR-AUC | 0,065 | **0,089** | 0,043 = acaso |
| Precisão no limiar | 5,5% | 10,0% | 4,3% = acaso |
| Revocação no limiar | 17,1% | 28,2% | — |
| Atrasos capturados no top 10% de risco | 12,6% | **22,9%** | 10% = acaso |
| Brier | 0,046 | 0,041 | 0,041 = prever sempre a taxa |

\* Baseline: o mesmo algoritmo só com prazo prometido e distância.

**Leitura honesta:** o modelo é **modesto**. Ranqueia melhor que o acaso — o top 10% de risco captura 2,3×
mais atrasos que um sorteio —, mas a precisão de 10% significa que 9 em cada 10 alertas são falsos. Serve
para priorizar acompanhamento, não para decidir sozinho.

## Consequências

**Deriva temporal.** A taxa de atraso caiu de **7,84%** no treino para **4,3%** na validação e no teste.
O modelo prevê 6,1% de média no teste contra 4,3% real, e o Brier só empata com prever sempre a taxa. A
probabilidade serve para **ordenar** pedidos, não para ser lida como risco absoluto.

**O prazo prometido domina.** Importância por permutação no teste (queda do ROC-AUC): `prazo_prometido_dias`
0,217; `uf_destino` 0,020; `categoria_principal` 0,008; `distancia_km` 0,005. O prazo é conhecido na compra
(o cliente o vê no checkout), então é legítimo, mas parte do sinal vem de a plataforma já embutir o risco
na data prometida.

**A hipótese de pontualidade do vendedor não se sustentou.** `taxa_pontualidade_vendedor` derrubou o ROC-AUC
em só 0,0026, com desvio do mesmo tamanho: sinal fraco. O atributo foi construído com cuidado e entregou
pouco; fica registrado assim.

**Atributos com importância negativa** — `valor_frete` (−0,0076), `mesma_uf` (−0,0078), `valor_itens`
(−0,0015) — indicam ruído. **Não se poda atributo olhando o teste**: isso o contaminaria. Uma versão 2, se
houver, calcula a importância na validação, remove os negativos e mede o teste uma única vez.
