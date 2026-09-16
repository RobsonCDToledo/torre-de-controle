# Fase 5 — plano de início

**Status:** itens 1 a 3 concluídos (`ADR-003`, `ADR-004`, `ADR-005`). Seguindo pros itens 4 e 5.
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

### 3. ~~Dicionário de dados completo~~ ✅ concluído, com uma ressalva

- Sinônimos e descrições de campo documentados em `docs/dicionario-de-dados.md`.
- ~~Esquema linguístico configurado no modelo semântico~~ — **bloqueado por limitação de
  plataforma**: Q&A não é suportado em Direct Lake, testado em três contextos diferentes.
  Registrado em `ADR-005`. A seção de sinônimos fica como documentação de intenção, sem
  aplicação no modelo.

### 4. Painel de Frete e Rotas

- Depende do item 1.
- Conteúdo: custo de frete por rota, frete sobre faturamento, custo por quilo, dispersão e
  outliers, top rotas por custo.
- Visual: reaproveita o design system existente (`design/theme/theme_torre_de_controle.json`,
  `design/paleta-e-uso.md`) — nenhuma decisão de paleta/tipografia nova, só composição de
  conteúdo sobre o sistema já validado.

### 5. Teste de aceite da fase

Critério do `cronograma.md`: "um analista externo consegue responder uma pergunta nova sem
pedir ajuda." **Papel do "analista externo" simulado por Claude**, usando só o material
publicado — o relatório (visuais e filtros) e `docs/dicionario-de-dados.md` — sem contexto
desta conversa. Ajustado pelo `ADR-005`: a validação **não** passa pela caixa de Q&A (não
suportada em Direct Lake), passa por navegar o relatório e responder com o que ele expõe.

## Decisões resolvidas no início da fase

- **RLS por UF de origem** (vendedor), não destino — `ADR-004`.
- **Q&A nativo aceito como indisponível** em Direct Lake, modelo mantido como está — `ADR-005`.
- **Teste de aceite:** Claude simula o analista externo, usando relatório + dicionário
  publicados, depois que o item 4 (Painel de Frete e Rotas) estiver pronto.
