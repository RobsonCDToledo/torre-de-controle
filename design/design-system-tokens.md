# Tokens do design system — Torre de Controle

Tabela de referência rápida (Bloco 6A do roteiro `prompt_design_system.txt`). Fonte de verdade
continua sendo `design/paleta-e-uso.md` e `design/theme/theme_torre_de_controle.json` — esta
tabela é um espelho tabular pra consulta rápida.

| Categoria | Nome do Token | Valor | Uso no Dashboard |
|---|---|---|---|
| Institucional | Primária | `#4F46E5` (indigo-600) | Título, ações, série principal |
| Institucional | Secundária | `#06B6D4` (cyan-500) | Segunda série, rampa ordinal |
| Institucional | Apoio (Lavanda) | `#C7D2FE` (indigo-200) | Ponta clara de rampa, "filtro aplicado" |
| Institucional | Fundo principal | `#F8FAFC` (slate-50) | Fundo da página |
| Institucional | Texto principal | `#0F172A` (slate-900) | Título, valor de KPI |
| Dashboard | `background-page` | `#F8FAFC` | Fundo geral do relatório |
| Dashboard | `background-card` | `#FFFFFF` | Cards e painéis |
| Dashboard | `background-header` | `#F8FAFC` | Cabeçalho — mesma cor da página |
| Dashboard | `color-primary` | `#4F46E5` | KPI em destaque, hyperlink |
| Dashboard | `color-secondary` | `#06B6D4` | Segunda série |
| Dashboard | `color-accent` | `#6366F1` (indigo-500) | Hover / estado ativo |
| Dashboard | `text-primary` | `#0F172A` | Título, valor de KPI |
| Dashboard | `text-secondary` | `#64748B` (slate-500) | Label, legenda |
| Dashboard | `text-muted` | `#94A3B8` (slate-400) | Eixo, nota mínima |
| Dashboard | `border-color` | `#E2E8F0` (slate-200) | Divisor, grade |
| Dashboard | `color-success` | bg `#ECFDF5` / texto `#047857` | OTD ≥ 95% |
| Dashboard | `color-warning` | bg `#FFFBEB` / texto `#B45309` | OTD 85–95% |
| Dashboard | `color-danger` | bg `#FEF2F2` / texto `#B91C1C` | OTD < 85%, atraso |
| Dashboard (bruto, tema PBI) | `good` | `#10B981` | Campo `good` do theme.json |
| Dashboard (bruto, tema PBI) | `neutral` | `#F59E0B` | Campo `neutral` do theme.json |
| Dashboard (bruto, tema PBI) | `bad` | `#EF4444` | Campo `bad` do theme.json |
| Séries | `series-1` | `#4F46E5` | Série 1 (marca) |
| Séries | `series-2` | `#06B6D4` | Série 2 (marca) |
| Séries | `series-3` | `#EB6834` | Série 3 (reserva) |
| Séries | `series-4` | `#4A3AA7` | Série 4 (reserva) |
| Séries | `series-5` | `#E87BA4` | Série 5 (reserva) |
| Séries | `series-6` | `#64748B` | Série 6 — neutro "Outros" (exceção deliberada) |
| Tipografia | `font-family` | `"Segoe UI", system-ui, -apple-system, sans-serif` | Título, corpo e número |
| Tipografia | `text-xs` | 11px / 600 | Label de KPI, nota de rodapé |
| Tipografia | `text-sm` | 12px / 400 | Legenda de gráfico, eixo |
| Tipografia | `text-base` | 13px / 400 | Corpo de card, filtro, tabela |
| Tipografia | `text-lg` | 15px / 600 | Título de card |
| Tipografia | `text-2xl` | 28px / 700 | Título de página |
| Tipografia | `text-3xl` | 32px / 700 | Valor hero de KPI |
| Geometria | `radius-card` | 12px | Cards e painéis |
| Geometria | `radius-pill` | 999px | Badge de status, filtro |
| Geometria | `radius-bar` | 4–6px | Barra de progresso/decomposição |
| Geometria | `shadow` | nenhuma | Cards usam borda 1px, não sombra |
| Ícone | `icon-style` | outline, 1.6–1.8px, grade 24px | Sem biblioteca externa — SVG inline |

**Nível de fidelidade:** Alta — sistema definido deliberadamente para o projeto (não extração de
terceiro), validado por CVD via skill `dataviz`.
