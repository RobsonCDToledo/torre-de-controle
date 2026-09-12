# Processo de design visual

Documenta como o visual do Painel Executivo de Entregas foi decidido **antes** de abrir o
Power BI Desktop — a mesma disciplina de "decisão registrada, não relitigada sem motivo novo"
que rege o resto da arquitetura, aplicada à camada de apresentação.

## Por que um design system antes do Desktop

Construir visual direto no Power BI Desktop, "no olho", tende a três problemas: cor
inventada a cada visual novo sem critério, nenhum registro do porquê de uma escolha, e
retrabalho quando o resultado não bate com o que se tinha em mente. Como este projeto é peça
de portfólio — o visual comunica tanto quanto o dado —, o caminho foi inverso: decidir a
identidade visual, validar com uma metodologia (não no olho), documentar, e só então construir.

---

## 1. Referência de estilo

Duas imagens de inspiração em `design/img/` (mockups genéricos de UI, de terceiros —
gitignorados, não são peça de portfólio, ver nota em `design/paleta-e-uso.md`):

- `component-library.png` — kit de componentes de app SaaS. Útil só pela linguagem de card
  com sombra leve e badge/chip de status; o resto (botões, formulário, toggle, avatar, toast)
  não tem equivalente no canvas do Power BI e foi descartado.
- `data-visualization-palette.png` — a paleta de sete cores adotada. Descoberta ao investigar
  a origem: são hex exatos da escala **Tailwind CSS** (indigo-600, cyan-500, emerald-500,
  amber-500, red-500, slate-900, indigo-200), não uma paleta inédita — o que importa porque
  "Muted Lavender" não é uma cor de identidade própria, é a ponta clara da rampa do azul
  primário.

## 2. Metodologia de cor

Cor não foi escolhida no olho — usando a skill `dataviz`, toda cor cumpre um de quatro jobs
(categórico, sequencial, ordinal, status) e todo conjunto categórico passa pelo script
`validate_palette.js` (separação cromática sob simulação de daltonismo, piso de croma,
contraste) antes de entrar no tema.

Decisões que saíram dessa validação:

- Só **azul** (`#4F46E5`) e **teal** (`#06B6D4`) são cores categóricas deliberadas — as
  únicas da marca fora da família verde/âmbar/vermelho.
- **Verde/âmbar/vermelho são reservados a status** (OTD bom/atenção/crítico,
  ≥95% · 85–95% · <85%) e nunca reciclados como cor de série.
- Mapa por UF e decomposição de atraso usam a régua de status ou uma rampa ordinal de um
  hue só — nunca uma cor "bonita" sem papel definido.

Detalhe completo: `design/paleta-e-uso.md`.

## 3. Tema do Power BI

`design/theme/theme_base.json` — tema de fábrica do Power BI ("Innovate", escuro) — serviu só
de esqueleto de chaves JSON (quais campos existem: `dataColors`, `good`/`neutral`/`bad`,
`visualStyles` por tipo de visual). Todo valor foi recolorido para a paleta clara do projeto,
resultando em `design/theme/theme_torre_de_controle.json`, pronto pra importar no Desktop
(Exibir → Temas → Procurar temas).

## 4. Mockup do Painel Executivo

Antes de desenhar no Figma, um mockup estático validou a composição do layout: quatro KPIs,
evolução mensal, cartograma simplificado por UF, decomposição de atraso por etapa e "Atraso
médio por UF Vendedor" — o mesmo inventário de visuais do painel descrito em
`00-arquitetura.md`, já ajustado ao escopo da `ADR-003` (sem "rota", que ficou pra fase 5).

Vive em `design/mockups/` (`Main.dc.html` fonte, `canvas.json` layout) e publicado como
[artifact](https://claude.ai/code/artifact/735d571a-5942-42c7-81ac-b3b434183095). Todo mockup
deste projeto usa artboard **1920x1080 (16:9)** — padrão fixado depois da primeira versão
(1440x1060, proporção arbitrária).

## 5. Design system de validação

Pra checar a estrutura antes de levar pro Figma, o processo foi consolidado num design system
completo, seguindo o roteiro de `design/prompt_design_system.txt` (identidade, paleta
institucional/dashboard/séries, tipografia, estilo de componente, recomendações). Como não há
"site de terceiro" pra extrair — a identidade é a que o próprio projeto definiu — o documento
deixa isso explícito em vez de fingir uma extração que não existiu.

Três saídas, como o roteiro pede:

- Tabela de tokens: `design/design-system-tokens.md`
- JSON do tema: o mesmo `theme_torre_de_controle.json` do item 3 (não um divergente)
- HTML navegável, autocontido: `design/design-system.html`, publicado como
  [artifact](https://claude.ai/code/artifact/ee7f0b0b-5cc4-4adb-9d65-5475a4aacfbd)

Essa etapa também estendeu a paleta de séries de 2 para 6 cores (exigência do roteiro),
revalidando a ordem no `validate_palette.js` e documentando cinza-ardósia como exceção
deliberada de neutro para "Outros" — ele reprova o piso de croma da checagem categórica por
natureza, não por erro.

## 6. Figma — ponte entre o design system e o relatório real

O layout definitivo do Painel Executivo foi desenhado no **Figma**, com o design system e o
mockup como referência. O Power BI não importa Figma diretamente, então o caminho encontrado
foi exportar o layout do Figma como **imagem de fundo da página** e aplicá-la em Formatar
página → Imagem de fundo no Desktop — os visuais nativos (KPIs, gráficos, slicers) ficam
sobrepostos, alinhados ao grid do fundo exportado.

O PNG exportado vive em `design/theme/img/Painel Executivo de Entregas.png` — ao lado do tema
JSON porque cumpre o mesmo papel (formatação/tema da página, não referência de terceiro como
`design/img/`), e por isso é rastreado no Git normalmente. O Power BI faz sua própria cópia
interna ao aplicar o fundo (`fabric/relatorios/.../StaticResources/RegisteredResources/`) —
as duas cópias existem por razões diferentes: uma é o artefato de design versionado, a outra é
o jeito do Power BI de embutir o recurso no relatório.

Link do arquivo Figma: _(adicionar aqui quando houver um link compartilhável)_.

---

## Onde cada artefato vive

| Artefato | Caminho | Papel |
|---|---|---|
| Referências de estilo (terceiros) | `design/img/` | Inspiração — gitignorado, não é portfólio |
| Decisões e validação de paleta | `design/paleta-e-uso.md` | Fonte da verdade do raciocínio de cor |
| Tema Power BI | `design/theme/theme_torre_de_controle.json` | Importado no Desktop |
| Mockup do painel | `design/mockups/` | Referência de composição, 16:9 |
| Design system de validação | `design/design-system.html` + `design-system-tokens.md` | Checklist completo antes do Figma |
| Layout definitivo | Figma (link acima) | Alta fidelidade, base pro build no Desktop |
| Fundo de página exportado | `design/theme/img/Painel Executivo de Entregas.png` | Export final do Figma, aplicado como imagem de fundo no Desktop |
| Relatório real | `fabric/relatorios/rpt_painel_executivo_entregas.Report/` | Entregável — o que é publicado no Fabric |
