# Apresentação técnica em PDF — plano reservado

**Status:** reservado, não iniciado. Retomar quando a Fase 4 for fechada ou quando fizer
sentido dentro do ritmo de rede/candidaturas.

## Por que existe

`Publish to Web` do Power BI não é viável pro Painel Executivo — `sm_torre_de_controle` é um
modelo semântico **compartilhado** de propósito ("um modelo, muitos relatórios"), e esse é
exatamente o tipo de modelo que o recurso não suporta, independente de RLS ou de workspace.

Em vez de forçar um link ao vivo, a saída é um **PDF autocontido expondo 100% do projeto** —
arquitetura, decisões, modelo de dados, processo de design, o painel em si — pra usar como
mídia na seção Projetos do LinkedIn. Refina o que `cronograma.md` → Fechamento já previa
("link para o repositório"): o PDF vira o anexo visual, o link do repositório continua sendo
o "prove que é verdade" pra quem quiser ir mais fundo.

## Estrutura de conteúdo proposta

| # | Seção | Conteúdo | Fonte |
|---|---|---|---|
| 1 | Capa | Nome do projeto, autor, contexto profissional, stack (Fabric, Direct Lake, PySpark, DAX, Figma) | novo |
| 2 | Contexto de negócio | Que problema a Torre de Controle resolve — visibilidade de OTD, decomposição de atraso, self-service | `00-arquitetura.md` |
| 3 | Arquitetura Medalhão | Fluxograma bronze → silver → gold → modelo semântico → relatórios, com "uma ferramenta por camada" em destaque | `00-arquitetura.md`, ADR-001 |
| 4 | Decisões de arquitetura | 2-3 ADRs resumidos visualmente (contexto → decisão → alternativa rejeitada → por quê) | `docs/decisoes/` |
| 5 | Modelo de dados | Diagrama do esquema estrela — dois fatos, cinco dimensões, `dim_calendario` | dicionário de dados |
| 6 | Camada semântica | Direct Lake explicado (comparação com Import/DirectQuery), 1-2 medidas DAX com nuance real (Jensen, TREATAS) | `02-replicar-funcoes-dax.md` |
| 7 | Processo de design | Paleta validada por CVD, tema, mockup, Figma → Power BI | `03-design-visual.md`, `paleta-e-uso.md` |
| 8 | O painel | Screenshots reais do Painel Executivo (não link — captura) | screenshot já existente |
| 9 | Roadmap | Fases 5 e 6 — self-service, RLS, Q&A, ML sem vazamento temporal | `cronograma.md` |
| 10 | Fechamento | Link do repositório público, contato | novo |

## Assets a produzir

- **Fluxograma da arquitetura Medalhão** (seção 3) — diagrama novo.
- **Diagrama do esquema estrela** (seção 5) — diagrama novo.
- **Cards de stack/tecnologia** (seção 1) — elemento novo, curto.

## Assets já existentes, só reaproveitar

- Paleta, tipografia e tokens: `design/theme/theme_torre_de_controle.json` + `design/paleta-e-uso.md` — o PDF usa a **mesma identidade visual** do painel, não uma nova.
- Screenshot real do Painel Executivo (já capturado nesta conversa).
- Texto-base da seção de contexto: `trash/descricao-linkedin-torre-de-controle.md` já tem boa parte da narrativa em prosa.

## Abordagem de produção

Montar como artboards de apresentação (`print: "fixed"`, uma página por artboard) usando a
mesma skill de canvas já usada pro mockup — exporta PDF multi-página nativamente, e mantém a
produção dentro do mesmo fluxo que já validamos nesta sessão. Os diagramas (medalhão, esquema
estrela) entram como SVG desenhado à mão, no mesmo estilo de traço dos ícones do mockup —
nada de biblioteca externa de diagramação.

## Checklist de execução, quando retomar

1. Fechar o roteiro definitivo (confirmar as 10 seções acima, cortar ou expandir).
2. Desenhar os dois diagramas que faltam (medalhão, esquema estrela).
3. Montar os artboards com o conteúdo + assets reaproveitados.
4. Exportar PDF, revisar em tela cheia (nada cortado, nada ilegível em zoom de LinkedIn).
5. Publicar como mídia na seção Projetos do LinkedIn, ao lado do link do repositório.
