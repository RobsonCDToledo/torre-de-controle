# Contexto do projeto

**Torre de Controle** — plataforma de dados end-to-end em Microsoft Fabric, construída como
peça de portfólio profissional. Leia `README.md` e `docs/00-arquitetura.md` antes de propor
qualquer mudança estrutural.

## Quem constrói e por quê

Robson Carlos de Toledo, especialista em BI e Analytics para Supply Chain. Está no setor
logístico desde 2014 e, nos últimos 8+ anos, exclusivamente em análise de dados — DHL,
FedEx e Grupo Cimed. Buscando recolocação como Analista de BI Sênior desde agosto de 2026.

Este projeto existe para demonstrar Fabric moderno em ambiente público e alimentar a seção
Projetos do LinkedIn. O plano de recolocação que o originou vive em `e:\Projetos\exposição`.

## Decisões já fechadas — não relitigar sem motivo novo

- **Uma ferramenta por camada.** Data Pipeline ingere, Dataflow Gen2 faz bronze→silver,
  notebook PySpark faz silver→gold. O raciocínio e as alternativas rejeitadas estão em
  `docs/decisoes/ADR-001-ferramenta-por-camada.md`.
- **Gold em Lakehouse, não Warehouse** — endpoint SQL para analistas e Spark para ML na
  mesma base, sem duplicar dado.
- **Modelo semântico em Direct Lake**, nunca Import. É o diferencial que o projeto existe
  para mostrar.
- **Dois grãos de fato.** `fato_entrega` por pedido, `fato_item_pedido` por item. Achatar
  tudo no grão de item distorce o OTD em favor de pedidos grandes.
- **A pasta `dados/origem/` não é a camada bronze.** É o sistema de origem simulado. A
  bronze vive no Lakehouse.
- **Transformação não acontece na origem.** A agregação da geolocalização pertence à silver,
  onde fica versionada e reversível.
- **ML sem vazamento temporal.** Só entram atributos conhecidos no instante da compra —
  `order_approved_at` e `order_delivered_carrier_date` estão proibidos como features.

## Restrições

- **Nenhum dado do Grupo Cimed**, nem anonimizado. A fonte é pública (Olist/Kaggle) ou
  sintética. Repositório público com dado de ex-empregador é risco jurídico e reputacional.
- O dataset Olist tem licença Creative Commons **não comercial**. Manter a atribuição.
- O repositório precisa ser público — o pipeline lê os arquivos por URL bruta.

## Convenções

- Documentação e nomes de coluna a partir da silver: **português**.
- Toda decisão de arquitetura com alternativa descartada vira um ADR em `docs/decisoes/`.
- Cada fase do `planejamento/cronograma.md` termina em commit que se sustenta sozinho.
- O dicionário de dados é entregável, não opcional: sem ele, a promessa de self-service
  da fase 5 não se cumpre.
