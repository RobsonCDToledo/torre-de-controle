# Fase 5 — plano de início

**Status:** itens 1 a 4 concluídos (`ADR-003`, `ADR-004`, `ADR-005`). Falta só o 5. O escopo já
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

### 5. Teste de aceite da fase — 🔄 em andamento, achou lacunas reais

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

**Remediação em andamento:** novo relatório `rpt_painel_atribuicao_causas`, mesmo padrão
"um modelo, muitos relatórios", pra fechar as 3 lacunas que falharam (a parcial do lead time
por mês fica registrada como limitação conhecida, fora de escopo — não tem medida faltando, só
um visual de tendência que os outros dois painéis não cobrem). Três medidas-ponte novas em
`_medidas.tmdl`, reaproveitando a bridge `TREATAS` já validada (`OTD % por Vendedor`,
`Pedidos Atrasados por Vendedor`, `Nota Média por Categoria`) — ver
`docs/02-replicar-funcoes-dax.md`. Mockup em `design/mockups/AtribuicaoCausas.dc.html`.

## Decisões resolvidas no início da fase

- **RLS por UF de origem** (vendedor), não destino — `ADR-004`.
- **Q&A nativo aceito como indisponível** em Direct Lake, modelo mantido como está — `ADR-005`.
- **Teste de aceite:** Claude simula o analista externo, usando relatório + dicionário
  publicados, depois que o item 4 (Painel de Frete e Rotas) estiver pronto.
