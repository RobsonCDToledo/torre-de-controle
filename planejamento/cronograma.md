# Cronograma — seis fases

Cada fase termina com algo publicável: um commit que se sustenta sozinho e um post que sai
dele. O projeto nunca fica em estado "quase pronto e invisível".

**Regra de convivência com a busca por emprego:** este projeto entra *por cima* das 2h
semanais de rede e candidaturas, nunca no lugar delas. Se a semana apertar, a fase escorrega
— a rede, não.

---

## Fase 1 · Fundação

Repositório criado, dados de origem preparados e commitados, workspace com capacidade
atribuída, integração Git conectada **antes de qualquer artefato**, três Lakehouses criados,
e o pipeline de ingestão levando os nove arquivos para a bronze.

**Entrega:** o pipeline roda de ponta a ponta e a bronze tem dado particionado por data.
**Post:** por que o arquivo de geolocalização virou Parquet — decisão de engenharia contada
em cinco linhas.

---

## Fase 2 · Silver

Dataflow Gen2 lendo a bronze e escrevendo tabelas Delta tipadas. Nomes em português,
deduplicação por chave natural, colunas de rastro, tabelas de rejeitados para o que falha
nas regras. Agregação da geolocalização ao centroide por prefixo de CEP.

**Entrega:** oito tabelas silver, com regras de qualidade documentadas.
**Post:** o milhão de linhas que virou dezenove mil — e por que a agregação pertence à
silver, não à origem.

---

## Fase 3 · Gold

Notebook PySpark construindo o esquema estrela: dois fatos, cinco dimensões, chaves
substitutas e `dim_calendario` gerada. Indicadores de entrega materializados.

**Entrega:** modelo dimensional consultável pelo endpoint SQL.
**Post:** por que dois grãos de fato em vez de um — o erro de OTD que acontece quando se
achata tudo no grão de item.

---

## Fase 4 · Semântica e Painel Executivo

Modelo semântico em Direct Lake sobre a gold. Medidas DAX, hierarquias, formatação, colunas
técnicas ocultas. Painel Executivo de Entregas construído sobre ele.

**Entrega:** primeiro painel publicado, com o modelo versionado em TMDL.
**Post:** Direct Lake na prática — o que muda quando o modelo não precisa de atualização.

---

## Fase 5 · Self-service e perguntas nativas

Permissão de build no modelo compartilhado, endosso aplicado, RLS por UF, endpoint SQL
liberado. Dicionário de dados completo. Sinônimos, descrições de campo e esquema linguístico
configurados para Q&A. Painel de Frete e Rotas, sobre o mesmo modelo.

**Entrega:** um analista externo consegue responder uma pergunta nova sem pedir ajuda.
**Post:** self-service não é dar acesso ao dado — é dar acesso ao *significado* do dado.

---

## Fase 6 · Machine learning

Engenharia de atributos com recorte temporal correto, treino do modelo de predição de
atraso, registro no MLflow, escrita das predições de volta na gold e comparação entre atraso
previsto e realizado no painel.

**Entrega:** modelo registrado, com métricas e importância de atributos.
**Post:** o atributo que eu tive de jogar fora — vazamento temporal explicado com o caso
real do `order_delivered_carrier_date`.

---

## Fechamento

Com as seis fases concluídas: README final revisado, projeto adicionado à seção **Projetos**
do LinkedIn com link para o repositório, e uma entrada no portfólio existente.

O banco de temas do plano de recolocação ganha seis posts prontos, um por fase — o que
resolve seis semanas de conteúdo sem esforço adicional.
