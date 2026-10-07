# Fase 5 — plano de início

**Status:** itens 1 a 4 concluídos (`ADR-003`, `ADR-004`, `ADR-005`). Item 5 implementado; falta a conferência visual no Power BI Desktop (ver abaixo). O escopo já
está fechado em `cronograma.md` e `docs/00-arquitetura.md`; aqui é a ordem e as dependências
entre as partes.

## Ordem de execução

### 1. ~~Pré-requisito — `uf_origem` em `fato_entrega` (`ADR-003`)~~ ✅ concluído

- **Onde:** `nb_silver_para_gold`, célula `fato_entrega`.
- **Entrega:** `uf_origem`, `uf_destino` e `rota` implementados e validados — ver
  "Status — implementado e validado" no `ADR-003`.

### 2. ~~Governança do modelo compartilhado~~ ✅ concluído

- Permissão de build em `sm_torre_de_controle` — usuário de teste com `Read, Build`.
- Endosso — `Promoted` aplicado.
- **RLS por UF de origem (vendedor)** — `ADR-004`, dois papéis (`RLS - SP`, `RLS - RJ`) criados
  e validados via live connect avulso no Desktop.
- Endpoint SQL da gold — usuário de teste com `Read, ReadAll` em `lh_gold`.

### 3. ~~Dicionário de dados completo~~ ✅ concluído, com uma ressalva

- Sinônimos e descrições de campo documentados em `docs/dicionario-de-dados.md`.
- ~~Esquema linguístico configurado no modelo semântico~~ — **bloqueado por limitação de
  plataforma**: Q&A não é suportado em Direct Lake, testado em três contextos diferentes.
  Registrado em `ADR-005`. A seção de sinônimos fica como documentação de intenção, sem
  aplicação no modelo.

### 4. ~~Painel de Frete e Rotas~~ ✅ concluído

- Relatório novo `rpt_painel_frete_rotas`, live connection (`byPath`) pro `sm_torre_de_controle`
  compartilhado — confirma "um modelo, muitos relatórios" na prática, não só em doc.
- Conteúdo: treemap (volume × eficiência por rota), gauge de frete sobre faturamento, dispersão
  peso × custo com outliers, tabela de rotas críticas, cartão de insight narrativo.
- 5 medidas novas de ponte/ranking em `_medidas.tmdl` (`Peso Total (kg) por Rota`,
  `Custo por Quilo (por Rota)`, `Rota Mais Cara por Kg`, `Custo por Kg da Rota Mais Cara`,
  `Custo por Kg Médio (Top 10)`, `Múltiplo Custo por Kg`, `Insight Frete e Rotas`).
- Mockup em `design/mockups/FreteRotas.dc.html`, composição deliberadamente distinta do Painel
  Executivo (sem repetir a mesma grade de cards).

### 5. Teste de aceite da fase — ✅ implementado, 🔎 conferência visual pendente

Critério do `cronograma.md`: "um analista externo consegue responder uma pergunta nova sem
pedir ajuda." **Papel do "analista externo" simulado por Claude**, usando só o material
publicado — o relatório (visuais e filtros) e `docs/dicionario-de-dados.md` — sem contexto
desta conversa. Ajustado pelo `ADR-005`: a validação **não** passa pela caixa de Q&A (não
suportada em Direct Lake), passa por navegar o relatório e responder com o que ele expõe.

**Rodado contra as 5 perguntas do dicionário — resultado: 1 passa, 1 parcial, 3 falham.**

| Pergunta | Resultado |
|---|---|
| OTD por UF de origem | ❌ só existia por UF de destino |
| Pedidos atrasados por estado do vendedor (contagem) | ❌ só existia média de atraso, não contagem |
| Lead time médio por mês | ⚠️ só via iteração manual no slicer, sem visual de tendência |
| Nota média por categoria de produto | ❌ `dim_produto` não aparecia em nenhum visual |
| Frete sobre faturamento por rota | ✅ passa direto |

**Remediação implementada:** relatório `rpt_painel_atribuicao_causas`, mesmo padrão "um modelo,
muitos relatórios" (live connection `byPath` ao `sm_torre_de_controle`). 11 visuais sobre o
layout do mockup `design/mockups/AtribuicaoCausas.dc.html`: 4 cartões de diagnóstico, faixa de
insight, barras de desvio de OTD por UF de origem, top 3 UFs por pedidos atrasados, nota média
das 10 maiores categorias, cartão "Categoria em Foco" e 2 filtros (Ano, UF de Origem). Medidas
reaproveitam a bridge `TREATAS` — ver `docs/02-replicar-funcoes-dax.md`.

**Segunda rodada, por inspeção da definição (PBIR) — o que cada pergunta encontra:**

| Pergunta | Onde responde | Resultado esperado |
|---|---|---|
| OTD por UF de origem | Atribuição de Causas — barras de desvio de OTD | ✅ |
| Pedidos atrasados por estado do vendedor | Atribuição de Causas — top 3 UFs | ✅ |
| Lead time médio por mês | Painel Executivo, cartão `Lead Time Médio` filtrado pelos slicers de período | ⚠️ limitação aceita |
| Nota média por categoria de produto | Atribuição de Causas — 10 maiores categorias | ✅ |
| Frete sobre faturamento por rota | Painel de Frete e Rotas | ✅ |

**Decisão sobre o lead time por mês:** fica como limitação conhecida e fora de escopo. A medida
existe; falta só um visual de tendência (a evolução mensal do Painel Executivo mostra OTD, não
lead time). O analista chega à resposta iterando o filtro de período, com um passo a mais.

**Conferência pendente (só o Desktop faz):** o PBIR foi gerado e verificado por script (JSON
válido, as 11 referências de medida existem no modelo), mas não foi aberto no Power BI Desktop.
Antes de marcar a fase como fechada: abrir `rpt_painel_atribuicao_causas.pbip`, confirmar que os
visuais renderizam sobre o fundo, que o top 3 e o top 10 filtram certo, e que os cartões de
texto cabem. Ajustes finos de posição são esperados.

## Decisões resolvidas no início da fase

- **RLS por UF de origem** (vendedor), não destino — `ADR-004`.
- **Q&A nativo aceito como indisponível** em Direct Lake, modelo mantido como está — `ADR-005`.
- **Teste de aceite:** Claude simula o analista externo, usando relatório + dicionário
  publicados, depois que o item 4 (Painel de Frete e Rotas) estiver pronto.
