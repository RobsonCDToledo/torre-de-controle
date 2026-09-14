# Paleta visual do Painel Executivo

Registra de onde vem cada cor do tema (`theme/theme_torre_de_controle.json`), por que ela
tem esse papel e não outro, e como aplicar no Power BI Desktop. As imagens em `img/` são
referência de estilo (mockups genéricos de UI, não peça de portfólio — ver nota no fim).

## Origem da paleta

As sete cores em `img/data-visualization-palette.png` são a escala **Tailwind CSS**, não uma
paleta inédita:

| Nome na imagem | Hex | Tailwind |
|---|---|---|
| Primary Blue | `#4F46E5` | `indigo-600` |
| Info Teal | `#06B6D4` | `cyan-500` |
| Success Emerald | `#10B981` | `emerald-500` |
| Warning Amber | `#F59E0B` | `amber-500` |
| Error Rose | `#EF4444` | `red-500` |
| Slate Deep | `#0F172A` | `slate-900` |
| Muted Lavender | `#C7D2FE` | `indigo-200` |

Isso importa porque **Muted Lavender não é uma cor de identidade separada** — é a ponta clara
da própria rampa do azul primário (`indigo-200`). Ela não entra como cor categórica; é usada
como tom de fundo do estado "filtro aplicado" e como extremo claro de rampas sequenciais.
Ter a escala Tailwind completa também significa que qualquer tom adicional (`indigo-700`,
`cyan-300` etc.) já vem pronto, sem inventar hex novo se um visual precisar de mais um degrau.

## Papel de cada cor

Cor não é escolhida no olho — seguindo a metodologia da skill `dataviz`, toda cor cumpre um
job (categórico, sequencial, ordinal ou status) e passa pelo validador antes de entrar no
tema.

### Categórico — identidade de série

`#4F46E5` (azul) e `#06B6D4` (teal) são as únicas duas cores da marca fora da família
verde/âmbar/vermelho — por isso são as únicas usadas deliberadamente para identidade de série
(ex.: linha "OTD real" vs. linha "Meta"). `#E87BA4` (magenta) e `#4A3AA7` (violeta) completam
o array `dataColors` do tema como reserva — são as duas cores extras já validadas pela própria
skill `dataviz` para conviver com azul/teal em pares adjacentes; existem para o Power BI não
inventar um tom ruim se um visual futuro pedir uma 3ª ou 4ª série, mas não synthesizei uma
paleta de 8 cores torcendo a marca para caber hipóteses que a Fase 4 não tem — se aparecer
essa necessidade real, valida-se de novo antes de usar de propósito.

Validado (`validate_palette.js`, `--surface #F8FAFC`): CVD adjacente ΔE 8.8–23.7, piso de visão
normal 25.3–28.8, ambos acima do alvo. Contraste do teal e do magenta contra o fundo fica
abaixo de 3:1 (WARN) — por isso **todo visual que usa essas cores mantém rótulo de dado ou
legenda visível**, nunca a cor sozinha carregando o valor.

**Limite de uso:** esse conjunto de 4 só foi validado em pares *adjacentes* (barra empilhada,
coluna, linha). Falha no teste `--pairs all` (azul vs. violeta ficam indistinguíveis lado a
lado sem vizinhança fixa) — não usar em dispersão, mapa de calor ou pequenos múltiplos com mais
de duas séries simultâneas sem revalidar.

### Status — OTD, nunca reciclada como série

`good` = `#10B981`, `neutral` = `#F59E0B`, `bad` = `#EF4444`. Fixas, com significado
reservado — nunca aparecem como cor de série categórica, mesmo que uma delas "sobrasse" visualmente
bonita para isso.

**Faixas do OTD % — meu ponto de partida:**

| Faixa | Corte | Cor |
|---|---|---|
| Bom | ≥ 95% | `#10B981` |
| Atenção | 85–95% | `#F59E0B` |
| Crítico | < 85% | `#EF4444` |

Referência de mercado (last-mile/e-commerce). **Ajustável** — é só trocar os dois literais na
medida abaixo depois de ver a distribuição real do OTD por UF/mês no modelo.

**Implementado como três medidas, não uma** — `OTD % (Text Color)`, `OTD % (Background Color)`
e `OTD % (Legend)`, todas em `_medidas`, ocultas do painel de campos (`isHidden`). Código
completo e onde cada uma se aplica: `docs/02-replicar-funcoes-dax.md`, seção "Medidas de
formatação visual". O texto usa a tonalidade 700 e o fundo a 50 — não o `good`/`neutral`/`bad`
bruto do tema — porque a cor 500 sozinha não fecha 3:1 de contraste sobre fundo claro.

Aplicação: **Formatação condicional → cor da fonte/fundo → Campo** apontando pra
`OTD % (Text Color)` / `(Background Color)`. É assim que o cartograma por UF e o cartão de KPI
herdam a mesma régua de cor, em vez de cada visual inventar seu próprio corte.

### Sequencial — mapa por UF (Painel Executivo)

Rampa do azul primário (`indigo`), clara→escura: `#E0E7FF` (100) → `#C7D2FE` (200, Muted
Lavender) → `#818CF8` (400) → `#4F46E5` (600, Primary Blue) → `#3730A3` (800). Usar apenas
onde a métrica **não** é o OTD (ex.: volume de pedidos por UF) — quando o mapa mede OTD, ele
usa a régua de status acima, não essa rampa, porque OTD já tem semântica de bom/ruim e uma
rampa neutra esconderia isso.

### Ordinal — decomposição de atraso por etapa

As três etapas com ordem temporal real (`Dias até Aprovação` → `Dias até Coleta` → `Dias de
Transporte`) usam a rampa do teal, clara→escura: `#A5F3FC` (200) → `#22D3EE` (400) →
`#0891B2` (600). O quarto segmento do gráfico, `Dias de Atraso`, **não é uma quarta etapa** —
é um sinalizador de problema, então usa `bad` (`#EF4444`), fora da rampa ordinal. Isso segue a
mesma regra do OTD: cor de status nunca se disfarça de série.

## Fundo e texto

Mockup de referência é claro, não escuro (o `theme_base.json` original era o tema "Innovate"
de fábrica do Power BI, escuro — usado só como esqueleto de chaves do JSON, recolorido por
inteiro).

| Papel | Cor | Tailwind |
|---|---|---|
| Fundo da página (outspace) | `#F8FAFC` | `slate-50` |
| Fundo do card/visual | `#FFFFFF` | — |
| Texto primário (título, header) | `#0F172A` | `slate-900` |
| Texto secundário | `#64748B` | `slate-500` |
| Texto mudo / eixo | `#94A3B8` | `slate-400` |
| Linha de grade / borda | `#E2E8F0` | `slate-200` |

Números grandes de KPI (`callout`) ficam em texto escuro, não coloridos — a cor entra na
variação percentual ao lado (via medida + formatação condicional), não no número principal.
Confirmado no próprio mockup: "84.2%" e "14.2M" em preto, só o texto pequeno de delta em
verde.

## Como aplicar no Desktop

1. Power BI Desktop → guia **Exibir** → **Temas** → **Procurar temas** →
   `design/theme/theme_torre_de_controle.json`.
2. Cores de status (`good`/`neutral`/`bad`) e as sequenciais/ordinais do mapa e da
   decomposição de atraso **não** são aplicadas pelo tema sozinho — dependem da medida
   `OTD % Cor` (ou equivalente) existir no modelo e ser referenciada na formatação condicional
   de cada visual.

## O que ficou de fora do `component-library.png`

Botões, toggles, avatar, formulário, toast — vocabulário de UI de app, sem equivalente no
canvas do Power BI. O único conceito reaproveitado foi a linguagem de card com sombra leve e
badge/chip de status, que já está embutida no tema (`filterCard`, `background` branco sobre
`#F8FAFC`).

## Nota sobre `img/`

As duas imagens em `img/` são mockup de referência de terceiros (kit de UI genérico, não
autoral), usadas só pra extrair a paleta acima — não são artefato do projeto. Ver
`.gitignore`: ficam fora do Git pelo mesmo motivo que `docs/archive/` fica — material de
apoio, não peça de portfólio.
