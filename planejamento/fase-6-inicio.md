# Fase 6 — plano de início

**Status:** notebook escrito, ainda não executado no Fabric. **Restrição de calendário:** o trial do
Fabric tinha 11 dias restantes em 07/10/2026, o que dá até ~18/10/2026. Tudo que exige execução
(treino, escrita na gold, modelo semântico) precisa caber nesse prazo; documentação não.

## Ordem de execução

### 1. Rodar `nb_ml_atraso` — 🔄 a fazer no Fabric
- Sincronizar o workspace (Atualizar tudo) e abrir `nb_ml_atraso`, com `lh_gold` como padrão.
- Executar célula por célula. O notebook não foi testado fora do Fabric (scikit-learn e Spark
  indisponíveis localmente), então a primeira execução pode revelar ajustes de código.
- **Critérios de aceite:** a trava anti-vazamento passa; os conjuntos de treino, validação e teste
  não se sobrepõem no tempo; `predicao_atraso` com 98.666 linhas (pedidos com item), `sk_pedido`
  único, probabilidade em [0, 1]; modelo registrado como `modelo_atraso_entrega`.
- **Esperado, a confirmar:** ROC-AUC do modelo acima do baseline (prazo prometido + distância). Se
  o ganho for pequeno, isso é resultado e fica registrado como tal — não se "melhora" com atributo
  que vaze.

### 2. Documentar a gold e as decisões
- `predicao_atraso` no dicionário de dados, com o aviso do `conjunto`.
- ADR da regra de vazamento e da divisão temporal, com números reais da execução.

### 3. Levar a predição ao modelo semântico
- Tabela `predicao_atraso` no modelo, relacionamento com `fato_entrega[sk_pedido]` (1:1), medidas
  de probabilidade média, atrasos previstos, precisão e revocação, sempre filtradas em `teste`.

### 4. Painel de comparação previsto × realizado
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
