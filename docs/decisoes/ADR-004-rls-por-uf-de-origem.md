# ADR-004 · RLS por UF de origem (vendedor), não UF de destino (cliente)

**Status:** aceito
**Contexto:** governança do modelo compartilhado, fase 5

---

## Contexto

`cronograma.md` fecha o escopo da fase 5 como "self-service com segurança por UF", sem dizer
qual UF. Depois do ADR-003, o modelo tem duas candidatas prontas para virar filtro de linha:

- **UF de destino** — em `dim_geografia`, já existia desde a fase 3, é a UF do cliente.
- **UF de origem** — em `fato_entrega` e `dim_vendedor` desde o ADR-003, é a UF do vendedor.

Cada uma conta uma história de acesso diferente. UF de destino modela um **gestor regional de
vendas**, que acompanha os pedidos entregues na praça dele. UF de origem modela um **gestor de
hub logístico**, que acompanha os pedidos que saem do centro de distribuição dele — e é essa a
leitura de negócio que a Torre de Controle existe para demonstrar (visibilidade de OTD do
ponto de vista de quem opera a expedição, não de quem vende).

## Decisão

**RLS filtra por UF de origem.** Um analista só vê os pedidos cujo vendedor principal
(critério do ADR-003) está na UF dele.

Como `uf_origem` é uma coluna física em `fato_entrega` (sem relacionamento com
`dim_vendedor`, por desenho do ADR-003) e também chega a `fato_item_pedido` por relacionamento
com `dim_vendedor`, o filtro de papel precisa ser declarado **duas vezes** para cobrir os dois
fatos:

| Tabela filtrada | Expressão DAX do papel |
|---|---|
| `fato_entrega` | `[uf_origem] = "SP"` |
| `dim_vendedor` | `[uf] = "SP"` (propaga para `fato_item_pedido` pelo relacionamento existente) |

Para o portfólio, bastam **2–3 papéis estáticos de exemplo** (ex.: `RLS - SP`, `RLS - RJ`) —
suficiente para provar o mecanismo via "Exibir como papel" no Power BI Desktop. Não há usuários
reais por UF neste tenant, então RLS dinâmico com tabela de mapeamento usuário→UF adicionaria
complexidade sem ganho demonstrável.

## Alternativas consideradas

**RLS por UF de destino.** Tecnicamente mais simples — `dim_geografia` já tem relacionamento
direto com as duas tabelas de fato, um único filtro por papel bastaria. Rejeitada porque conta
a história errada pro projeto: a Torre de Controle é uma vitrine de visibilidade logística
(expedição, OTD, atraso), não de território de vendas. Modelar acesso por onde o pedido *sai*
é mais fiel a esse recorte.

**RLS dinâmico via `USERPRINCIPALNAME()` e tabela de mapeamento usuário→UF.** Mais realista
para produção. Rejeitada para esta fase — exigiria criar identidades fictícias de usuário só
para a demonstração, o que é mais cenário de teste do que de portfólio. Fica registrado aqui
como próximo passo natural se o projeto crescer para simular múltiplos "analistas" de verdade.

## Consequências

**Positivas.** RLS por origem é consistente com a decisão de negócio já registrada no ADR-003
e reforça a mesma leitura de domínio (logística/expedição) em toda a plataforma, não só no
Painel de Frete e Rotas.

**Negativas, e aceitas.** Os **775 pedidos sem item** (`uf_origem` nulo, ADR-003) ficam fora de
qualquer papel restrito por origem — nenhum analista regional os vê, só quem acessa sem RLS
(build/admin). E como `uf_origem` já é uma aproximação em ≈1,3% dos pedidos multi-vendedor
(ADR-003), um analista de hub pode ocasionalmente ver um pedido cujo vendedor de maior valor é
da UF dele, mas que também teve item de outro vendedor de UF diferente — mesma aproximação já
aceita, agora com efeito em controle de acesso, não só em relatório.

## Status — implementado e validado

Construído direto no modelo semântico (edição via modelagem Web do Fabric, não pelo Desktop —
ver "Notas de execução" abaixo). Dois papéis criados:

| Papel | Filtro em `fato_entrega` | Filtro em `dim_vendedor` |
|---|---|---|
| `RLS - SP` | `[uf_origem] = "SP"` | `[uf] = "SP"` |
| `RLS - RJ` | `[uf_origem] = "RJ"` | `[uf] = "RJ"` |

**Validado** com uma conexão live connect avulsa no Power BI Desktop (arquivo descartável, fora
do `.pbip` versionado): tabela com `fato_entrega[uf_origem]` + medida de contagem, **Modelagem
→ Exibir como papel** → `RLS - SP` → confirmado que só linhas com `uf_origem = SP` aparecem.

**Ferramentas de teste padrão não serviram, e isso fica registrado porque provavelmente se
repete em qualquer sessão futura de RLS neste projeto:**

- **Desktop, "Exibir como papel"** fica desabilitado quando o `.pbip` é aberto no modo "Live
  editing... Direct Lake" (a ponte de edição ao vivo do Git/PBIP com o modelo hospedado no
  Fabric) — recurso ainda em amadurecimento, não suporta simulação local de papel nesse modo.
- **Serviço, "Test as role"** (Configurações do modelo → Segurança) falha com "Not supported —
  Test as role does not work with Single Sign-On (SSO)". Direct Lake consulta o OneLake com a
  identidade de quem pergunta (SSO); a ferramenta de teste do Serviço não suporta essa
  combinação hoje.
- **O que funcionou:** uma conexão live connect *comum* (Obter dados → Modelos semânticos do
  Power BI, não pelo `.pbip` git-integrado) — nessa conexão o "Exibir como papel" do Desktop
  funciona normalmente, porque não passa pela ponte de edição ao vivo.

## Notas de execução

**As colunas de origem precisaram ser adicionadas manualmente ao modelo.** `uf_origem`,
`uf_destino` e `rota` já existiam na tabela física `fato_entrega` na gold desde o ADR-003, mas
Direct Lake não descobre coluna nova sozinho — foi preciso declarar as três no TMDL do modelo
semântico antes de qualquer filtro de papel conseguir referenciá-las. Vale como lembrete geral:
toda vez que o notebook ganhar uma coluna nova em uma tabela que já existe no modelo, esse
passo de declarar a coluna no modelo semântico é manual e fica fácil de esquecer.

**O `.pbip` do relatório travou o Desktop repetidamente** ao abrir com o aviso "The PBIP and
semantic model metadata don't match" — sempre em torno da tabela `_medidas` (única em modo
Import no modelo, vazia por design, usada só pra organizar medidas — não representa risco real
de dado apesar do aviso mencionar perda de dado importado). A causa provável era um cache local
obsoleto (`*.Report/.pbi/localSettings.json`, arquivo por máquina, fora do git) guardando uma
assinatura de conexão antiga; apagar esse arquivo e reabrir resolveu o travamento. Editar o
modelo pela modelagem Web do Fabric (bypassa o Desktop inteiramente) foi o caminho que
efetivamente destravou a criação dos papéis.
