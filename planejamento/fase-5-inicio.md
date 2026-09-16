# Fase 5 — plano de início

**Status:** itens 1 e 2 concluídos e validados (`ADR-003`, `ADR-004`). Seguindo pros itens 3–5.
O escopo já está fechado em `cronograma.md` e `docs/00-arquitetura.md`; aqui é a ordem e as
dependências entre as partes.

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

### 3. Dicionário de dados completo

- Sinônimos e descrições de campo pra Q&A.
- Esquema linguístico configurado no modelo semântico.
- Ponto de partida: `docs/dicionario-de-dados.md` já tem a base de tabelas/colunas/medidas —
  falta a camada de linguagem natural em cima.

### 4. Painel de Frete e Rotas

- Depende do item 1.
- Conteúdo: custo de frete por rota, frete sobre faturamento, custo por quilo, dispersão e
  outliers, top rotas por custo.
- Visual: reaproveita o design system existente (`design/theme/theme_torre_de_controle.json`,
  `design/paleta-e-uso.md`) — nenhuma decisão de paleta/tipografia nova, só composição de
  conteúdo sobre o sistema já validado.

### 5. Teste de aceite da fase

Critério do `cronograma.md`: "um analista externo consegue responder uma pergunta nova sem
pedir ajuda." **Papel do "analista externo" simulado por Claude**, usando só o dicionário/Q&A
publicado (item 3), sem contexto desta conversa — não é autoavaliação do autor do projeto.

## Decisões resolvidas no início da fase

- **RLS por UF de origem** (vendedor), não destino — `ADR-004`.
- **Teste de aceite:** Claude simula o analista externo, a partir só do material publicado
  (item 3), depois que o item 3 estiver pronto.
