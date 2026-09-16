# ADR-005 · Q&A e esquema linguístico não são suportados em Direct Lake

**Status:** aceito
**Contexto:** item 3 da fase 5 — dicionário de dados e self-service com perguntas nativas

---

## Contexto

`cronograma.md` prevê, na fase 5, "perguntas em linguagem natural" como parte do self-service.
O plano (`planejamento/fase-5-inicio.md`, item 3) previa configurar o **esquema linguístico**
do Q&A em cima do dicionário de dados já existente.

Testado em **três contextos diferentes**, todos com o recurso indisponível:

1. **Modelagem Web do Fabric** — a faixa de opções nem tem um grupo de Q&A. O recurso não
   aparece, não é só um botão desabilitado.
2. **Desktop, conectado via `.pbip` no modo "Live editing... Direct Lake"** — "Q&A setup" e
   "Linguistic schema" aparecem na faixa, mas desabilitados.
3. **Desktop, live connect clássico** (fora da ponte de edição ao vivo do Git/PBIP, mesmo
   caminho que destravou o teste de RLS no `ADR-004`) — "Q&A setup" continua desabilitado.
   "Linguistic schema" abre a caixa de diálogo, mas **Import e Export ficam desabilitados**
   dentro dela.

O terceiro teste é o que descarta a ponte de edição ao vivo como causa: mesmo na conexão mais
"normal" possível, sem nenhuma das camadas de Git/PBIP envolvidas, o recurso continua
bloqueado. **Não é bug de sincronização — é limitação de plataforma do Direct Lake**, mesma
categoria do achado do `ADR-003` sobre tabela calculada: Direct Lake ainda não suporta todo
recurso clássico do motor de Analysis Services.

**Pesquisa adicional mostra que o problema é maior do que Direct Lake.** A documentação
oficial da Microsoft confirma que o **Q&A clássico está sendo descontinuado globalmente no
Power BI**, independente de modo de armazenamento — não é uma lacuna temporária de Direct Lake
a esperar suporte, é um recurso com data de validade em qualquer modelo. A recomendação oficial
da Microsoft é o **Copilot para Power BI** como substituto moderno de consulta em linguagem
natural, e a preparação recomendada pra isso é seguir as **práticas recomendadas de modelo
semântico para o agente de dados do Fabric** — que giram em torno de **descrições** em
tabelas, colunas e medidas, não em torno de sinônimo/esquema linguístico do motor antigo.

**Essa segunda tentativa também esbarrou em limitação de plataforma — ver "Tentativa de
descrições, revertida" abaixo.** Descrição não é, nesta versão de schema TMDL deste workspace,
o caminho disponível agora.

## Decisão

**O modelo continua em Direct Lake. Q&A nativo fica de fora do escopo entregável da fase 5,**
documentado como limitação conhecida e aceita, não como lacuna escondida.

A seção "Sinônimos para Q&A" em `docs/dicionario-de-dados.md` **permanece no documento** como
referência de intenção — o mapeamento de termos de negócio pra campo é conhecimento válido
independente da ferramenta conseguir aplicá-lo hoje. Se o Direct Lake ganhar suporte a Q&A no
futuro, a seção já está pronta pra virar configuração real sem trabalho de redescoberta.

**Self-service, nesta fase, acontece pelos visuais e filtros do relatório e pelo dicionário de
dados**, não por uma caixa de pergunta em linguagem natural. O teste de aceite (item 5 do
plano) é ajustado de acordo — ver `planejamento/fase-5-inicio.md`.

**A tentativa de adicionar descrições ao modelo foi revertida — ver "Tentativa de descrições,
revertida" abaixo.** O conteúdo já redigido continua útil como referência: as descrições
pensadas para cada tabela, coluna e medida ficam documentadas no histórico do commit revertido
e podem ser reaplicadas se este workspace ganhar suporte à propriedade, ou aplicadas campo a
campo pela interface (não pelo TMDL bruto) caso valha o esforço manual no futuro.

## Tentativa de descrições, revertida

Descrições foram escritas em TMDL bruto — `description: ...` em 7 tabelas, colunas com nuance
documentada e as 29 medidas — commitadas e sincronizadas via **Atualizar tudo** no portal do
Fabric. O pipeline de importação do workspace rejeitou o arquivo:

```text
Workload Error Code: Workload_FailedToParseFile
TMDL Format Error: Parsing error type - UnknownKeyword
Detailed error - Unsupported property - description is not a supported property
in the current context!
```

Primeira tentativa (medidas removidas, tabelas/colunas mantidas) isolou a causa: **não é só
medida.** A segunda tentativa (`dim_calendario`, primeira tabela do lote) recebeu o mesmo erro
na descrição de **tabela**. A propriedade `description` não é reconhecida pelo parser TMDL
deste pipeline de importação via Git, em nenhum nível — tabela, coluna ou medida.

Todas as descrições foram removidas e o modelo voltou ao estado anterior, validado por
sincronizar sem erro depois da reversão.

**Isso não invalida a decisão de manter Direct Lake nem a leitura sobre Copilot ser o caminho
oficial** — é uma limitação adicional, desta vez do pipeline de sincronização Git→workspace
especificamente, não necessariamente do motor Direct Lake em si. Não foi testado se a mesma
propriedade funcionaria autorada campo a campo pela interface (Desktop/Web), sem passar pelo
TMDL bruto via Git — ponto em aberto, não perseguido nesta fase pelo volume de campos
envolvido (~50) frente ao ganho.

## Alternativas consideradas

**Migrar o modelo semântico pra Import (ou um modelo composto/misto) só para restaurar Q&A.**
Rejeitada — Direct Lake é o diferencial central que o projeto existe para demonstrar
(`CLAUDE.md`, decisão fechada) e anda junto com a decisão de a gold não duplicar dado entre
motor analítico e ML. Trocar de modo pra resolver um recurso secundário derrubaria a lógica
das duas decisões de uma vez, por um ganho que nem seria completo: um modelo composto com só
uma tabela em Import não destrava o Q&A do modelo inteiro, porque a interpretação da pergunta
considera todas as tabelas.

**Rodar o Copilot do Fabric de verdade contra o modelo, agora.** É a direção oficial (Copilot
gera DAX dinamicamente, sem depender do motor clássico de Q&A), mas exige capacidade Fabric
paga (F64 ou superior) que o tenant trial deste projeto não tem. Adiada, não rejeitada: a
preparação de metadado (descrições) acontece agora; a execução fica pra quando a capacidade
permitir, sem trabalho de redescoberta.

## Consequências

**Positivas.** Direct Lake permanece intacto como a peça central do projeto. As duas
limitações documentadas e aceitas — em vez de escondidas ou forçadas por workaround frágil —
são, elas mesmas, demonstração de maturidade técnica: reconhecer o limite real de uma
plataforma nova (e de um recurso em fim de vida) é mais sênior do que insistir contra ele. A
seção de sinônimos no dicionário e o texto de descrição já redigido não foram trabalho
perdido — ficam como ativo pronto pra reaplicar se o workspace ganhar suporte, ou pra usar
manualmente pela interface se algum dia valer o esforço campo a campo.

**Negativas, e aceitas.** O item "perguntas em linguagem natural" do `cronograma.md` não sai
como uma caixa de Q&A funcional nesta fase — sai como documentação de sinônimos pronta, sem
aplicação. O modelo também não sai desta fase com descrições de campo aplicadas, ao contrário
do que a decisão original previa — a preparação pro agente de dados do Fabric fica só no nível
de intenção documentada, não de metadado real no modelo. O teste de aceite da fase precisa
validar self-service por outro caminho (visuais, filtros, dicionário), não pela pergunta
digitada livre que o cronograma original sugeria, nem por tooltip de descrição no campo.
