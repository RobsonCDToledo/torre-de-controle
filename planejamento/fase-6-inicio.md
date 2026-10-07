# Fase 6 — plano de início

**Status:** fase encerrada em 07/10/2026 — notebook executado, modelo registrado, predições na gold, tabela e medidas no modelo semântico e painel conferido no Fabric. **Restrição de calendário:** o trial do
Fabric tinha 11 dias restantes em 07/10/2026, o que dá até ~18/10/2026. Tudo que exige execução
(treino, escrita na gold, modelo semântico) precisa caber nesse prazo; documentação não.

## Ordem de execução

### 1. Rodar `nb_ml_atraso` — ✅ concluído
- Sincronizar o workspace (Atualizar tudo) e abrir `nb_ml_atraso`, com `lh_gold` como padrão.
- Executar célula por célula. O notebook não foi testado fora do Fabric (scikit-learn e Spark
  indisponíveis localmente), então a primeira execução pode revelar ajustes de código.
- **Critérios de aceite:** a trava anti-vazamento passa; os conjuntos de treino, validação e teste
  não se sobrepõem no tempo; `predicao_atraso` com 98.666 linhas (pedidos com item), `sk_pedido`
  único, probabilidade em [0, 1]; modelo registrado como `modelo_atraso_entrega`.
- **Esperado, a confirmar:** ROC-AUC do modelo acima do baseline (prazo prometido + distância). Se
  o ganho for pequeno, isso é resultado e fica registrado como tal — não se "melhora" com atributo
  que vaze.

### 2. Documentar a gold e as decisões — ✅ `ADR-006` e dicionário
- `predicao_atraso` no dicionário de dados, com o aviso do `conjunto`.
- ADR da regra de vazamento e da divisão temporal, com números reais da execução.

### 3. Levar a predição ao modelo semântico — ✅ sincronizado no Fabric sem erro
- Tabela `predicao_atraso` no modelo, relacionamento com `fato_entrega[sk_pedido]` (1:1), medidas
  de probabilidade média, atrasos previstos, precisão e revocação, sempre filtradas em `teste`.

### 4. Painel de comparação previsto × realizado — ✅ `rpt_painel_previsao_atraso` conferido no Fabric
- Página nova no relatório existente ou relatório próprio, seguindo "um modelo, muitos relatórios".

## Atributos (14 numéricos + 3 categóricos)
Conhecidos na compra: UF de origem e destino, categoria do item principal, prazo prometido,
distância entre centroides, mesma UF, mês e dia da semana, itens, vendedores, valor, frete, frete
sobre valor, peso, volume, pontualidade histórica do vendedor (só entregas anteriores à compra) e
quantidade dessas entregas.

## Decisões de projeto
- **Divisão temporal 70/15/15** pela data de compra, não aleatória.
- **Limiar escolhido na validação** (maior F1), nunca no teste.
- **Predição em todos os pedidos com item**, com coluna `conjunto`; o painel compara só `teste`,
  porque em `treino` e `validacao` a predição é dentro da amostra.
- **Sem desbalanceamento forçado:** probabilidade sem `class_weight`, para ser interpretável.

## Resultado

ROC-AUC 0,716 no teste contra 0,622 do baseline; o top 10% de risco captura 22,9% dos atrasos (2,3× o
acaso); precisão de 10% no limiar. Modelo **modesto**, com deriva temporal (7,8% de atraso no treino contra
4,3% no teste) — números e leitura completos no `ADR-006`.

## Pendências conhecidas, fora do escopo

- Versão 2 do modelo com poda de atributos pela importância na **validação** (não no teste).
- Calibração: a probabilidade superestima no período de teste; serve para ordenar, não como risco absoluto.
- Texto do aviso do painel tem números fixos (7,8%, 4,3% e as datas do teste); atualizar se o modelo for retreinado.

