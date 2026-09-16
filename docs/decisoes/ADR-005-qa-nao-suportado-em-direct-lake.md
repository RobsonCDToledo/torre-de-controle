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
Descrição é metadado comum, sempre suportado, inclusive em Direct Lake.

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

**A parte executável agora da recomendação oficial é adotada: descrições em tabelas, colunas e
medidas do modelo semântico**, transcritas do que já está em `docs/dicionario-de-dados.md`.
Não exige capacidade paga pra ser autorada — só pra rodar Copilot de verdade contra o modelo,
que fica fora do escopo desta fase por causa da capacidade trial. O trabalho de descrição não
depende disso: enriquece o modelo pra qualquer agente de IA (incluindo o próprio Copilot, se a
capacidade mudar no futuro) e melhora a tooltip de campo pra usuário humano hoje.

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

**Positivas.** Direct Lake permanece intacto como a peça central do projeto. A limitação
documentada e aceita — em vez de escondida ou forçada por um workaround frágil — é, ela mesma,
demonstração de maturidade técnica: reconhecer o limite real de uma plataforma nova (e de um
recurso em fim de vida) é mais sênior do que insistir contra ele. A seção de sinônimos no
dicionário não foi trabalho perdido — vira ativo pronto para quando (ou se) o recurso for
suportado. E o projeto sai desta fase seguindo a recomendação **atual** da Microsoft — Copilot
e descrições, não uma prática sendo descontinuada — com o modelo preparado pro caminho moderno
de IA, não só documentado sobre o caminho antigo que não funcionou.

**Negativas, e aceitas.** O item "perguntas em linguagem natural" do `cronograma.md` não sai
como uma caixa de Q&A funcional nesta fase — sai como documentação de sinônimos pronta, sem
aplicação. O teste de aceite da fase precisa validar self-service por outro caminho (visuais,
filtros, dicionário), não pela pergunta digitada livre que o cronograma original sugeria.
