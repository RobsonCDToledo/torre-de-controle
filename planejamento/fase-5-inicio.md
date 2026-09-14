# Fase 5 — plano de início

**Status:** Fase 4 encerrada, pronta pra abrir. Este documento é o planejamento de execução —
o escopo já está fechado em `cronograma.md` e `docs/00-arquitetura.md`; aqui é a ordem e as
dependências entre as partes.

## Ordem de execução

### 1. Pré-requisito — `uf_origem` em `fato_entrega` (`ADR-003`)

- **Onde:** `nb_silver_para_gold`.
- **O quê:** coluna nova, resolvida por desempate determinístico quando o pedido tem item de
  mais de um vendedor — proposta na ADR: vendedor do item de maior `valor_itens`, `sk_item`
  como desempate secundário. Conferir a distribuição real antes de fechar (quantos pedidos
  realmente têm mais de um vendedor, se o critério proposto faz sentido nesses casos).
- **Por que primeiro:** o Painel de Frete e Rotas (item 4) não existe sem essa coluna, e a
  decisão de RLS (item 2) pode depender de qual UF vira o filtro de linha.
- **Entrega:** coluna testável na gold; atualizar a ADR-003 com o critério efetivamente usado,
  se divergir do proposto.

### 2. Governança do modelo compartilhado

- Permissão de build em `sm_torre_de_controle` liberada pra outros construírem relatório.
- Endosso (Promoted/Certified) aplicado.
- **RLS por UF — decisão em aberto:** UF de destino (`dim_geografia`, já existe) ou UF de
  origem (`uf_origem`, item 1)? `cronograma.md` diz só "RLS por UF", sem especificar qual — não
  assumir, decidir no início da fase e registrar como ADR se houver alternativa descartada.
- Endpoint SQL da gold liberado pra quem prefere consultar direto.

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
pedir ajuda." Definir quem faz esse teste antes de dar a fase por encerrada — não é
autoavaliação.

## Decisões em aberto (resolver no início da fase, não herdar default)

- RLS por UF de destino ou de origem?
- Quem é o "analista externo" do teste de aceite?
