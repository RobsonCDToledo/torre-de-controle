[StagingDefinition = [Kind = "FastCopy"]]
section Section1;
shared bronze_particao = /*  bronze_particao
    ------------------------------------------------------------------
    Devolve a LINHA da particao mais recente da bronze, com dois campos:
      [Name]    -> a data da particao, ex. "2026-08-31"
      [Content] -> a tabela com os nove arquivos

    A navegacao existe aqui e em nenhum outro lugar. bronze_particao_atual e
    particao_data sao acessores de uma linha sobre esta. Se o workspace for
    recriado, ha um lugar a corrigir, nao dois.
*/
let
    // Lakehouse.Contents liga a consulta ao item do Fabric, e nao a um
    // caminho de armazenamento: o vinculo sobrevive a recriacao do item.
    Fonte          = Lakehouse.Contents(null),
    Workspace      = Fonte{[workspaceId = "528a4166-a694-4105-90bd-d6509fcc0536"]}[Data],
    Bronze         = Workspace{[lakehouseId = "5e8ea3ef-c577-43b0-82d0-6de3b9a954bf"]}[Data],
    Arquivos       = Bronze{[Id = "Files", ItemKind = "Folder"]}[Data],
    Particoes      = Arquivos{[Name = "olist"]}[Content],

    // O pipeline nomeia a particao como yyyy-MM-dd. E o formato ISO que faz
    // a maior string ser tambem a data mais recente. Se o pipeline mudar
    // para dd-MM-yyyy, esta linha passa a escolher a pasta errada e nao
    // levanta erro nenhum — o dado e que vem velho.
    UltimaParticao = List.Max(Particoes[Name]),
    Linha          = Particoes{[Name = UltimaParticao]}
in
    Linha;
[DataDestinations = {[Definition = [Kind = "Reference", QueryName = "clientes_DataDestination", IsNewTarget = true], Settings = [Kind = "Automatic", TypeSettings = [Kind = "Table"]]]}]
shared clientes = /*  clientes
    Uma linha por cliente. Chave natural: customer_id — 99.441 registros,
    sem duplicata na origem.

    A origem tem dois identificadores e os dois precisam sobreviver:
    customer_id muda a cada pedido, customer_unique_id e a pessoa (96.096
    distintos). A dim_cliente da gold usa o segundo.
*/
let
  NomeArquivo          = "olist_customers_dataset.csv",
  Source               = bronze_particao_atual{[Name = NomeArquivo]}[Content],

  // QuoteStyle.Csv respeita aspas e aceita quebra de linha dentro do campo.
  Csv                  = Csv.Document(Source, [Delimiter = ",", Columns = 5, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
  PromoverCabecalhos   = Table.PromoteHeaders(Csv, [PromoteAllScalars = true]),

  // Tratamento de dados para evitar quebra de atualizacoes devido a perda de colunas.
  // Coluna adicionada na origem nao influencia no fluxo; coluna removida quebra
  // a atualizacao de proposito — e barato consertar hoje, caro descobrir depois
  // que a silver vinha com nulo desde marco.

  // Dicionario de colunas esperadas no arquivo.
  ColunasEsperadas     = {"customer_id", "customer_unique_id", "customer_zip_code_prefix",
                          "customer_city", "customer_state"},
  ColunasRecebidas     = Table.ColumnNames(PromoverCabecalhos),
  Diferenca            = List.Difference(ColunasEsperadas, ColunasRecebidas),

  Validado =
    if List.IsEmpty(Diferenca) then PromoverCabecalhos
    else error Error.Record(
        "Quebra de Atualização",
        "Tabela clientes: as seguintes colunas estão ausentes na origem — " & Text.Combine(Diferenca, ", "),
        [ QtdColunasRecebidas = List.Count(ColunasRecebidas),
          PrimeirasRecebidas  = Text.Combine(List.FirstN(ColunasRecebidas, 5), " | ") ]
        ),

  // Agora garantir que somente as colunas necessarias sejam carregadas caso
  // haja uma nova coluna na origem.
  Selecao              = Table.SelectColumns(Validado, ColunasEsperadas),

  RenomearColunas      = Table.RenameColumns(Selecao, {
                            {"customer_id",              "id_cliente"},
                            {"customer_unique_id",       "id_cliente_unico"},
                            {"customer_zip_code_prefix", "prefixo_cep"},
                            {"customer_city",            "cidade"},
                            {"customer_state",           "uf"}
                         }),

  // Tudo texto: nao ha quantidade nem data nesta tabela.
  // prefixo_cep em especial — "01151" perde o zero a esquerda se virar
  // numero, e a juncao com geografia falharia para 23.995 clientes.
  TipagemdosDados     = Table.TransformColumnTypes(RenomearColunas, {
                            {"id_cliente",       type text},
                            {"id_cliente_unico", type text},
                            {"prefixo_cep",      type text},
                            {"cidade",           type text},
                            {"uf",               type text}
                         }, "en-US")
                ,

  // Mesma normalizacao aplicada em geografia, para as tres tabelas contarem a
  // mesma historia: sem isso, geografia teria "Sao Paulo" e esta teria
  // "sao paulo", e ninguem consegue comparar cidade entre elas.
  // Trim e Clean sao o conserto real; Text.Proper e leitura. A caixa da
  // origem ja e uniforme, entao Proper nao corrige duplicata — melhora
  // apresentacao. Se preferir manter minusculo, remova so o Text.Proper.
  PadronizarTexto      = Table.TransformColumns(TipagemdosDados, {
                            {"cidade", each if _ = null then null else Text.Proper(Text.Trim(Text.Clean(_))), type text},
                            {"uf",     each if _ = null then null else Text.Upper(Text.Trim(_)),             type text}
                         }),

  // Sem duplicata na origem hoje. O passo fica porque declara a chave natural
  // no codigo e protege contra mudanca futura na origem.
  DeduplicarBase       = Table.Distinct(PadronizarTexto, {"id_cliente"}),

  // Rastro. A data vem da particao da bronze, nao do momento em que este
  // Dataflow rodou: e a silver que se reconstroi, o dado foi ingerido uma vez.
  DataParticao         = Date.FromText(particao_data),
  ComOrigem            = Table.AddColumn(DeduplicarBase, "_origem_arquivo", each NomeArquivo, type text),
  ComRastro            = Table.AddColumn(ComOrigem, "_ingerido_em", each DataParticao, type date)
in
    ComRastro;
shared particao_data = /*  particao_data
    A data da particao mais recente, como texto "yyyy-MM-dd".
    Acessor sobre bronze_particao. Alimenta a coluna _ingerido_em das oito.
*/
let
    Source = bronze_particao[Name]
in
    Source;
shared bronze_particao_atual = /*  bronze_particao_atual
    Os nove arquivos da particao mais recente. Acessor sobre bronze_particao.
    As oito consultas da silver escolhem o seu arquivo daqui.
*/
let

    Source = bronze_particao[Content]
in 
    Source;
[DataDestinations = {[Definition = [Kind = "Reference", QueryName = "itens_pedido_DataDestination", IsNewTarget = true], Settings = [Kind = "Automatic", TypeSettings = [Kind = "Table"]]]}]
shared itens_pedido = /*  itens_pedido
    Uma linha por item de um pedido. Chave natural: order_id + order_item_id
    — 112.650 registros, sem duplicata na origem.

    Existe como grao separado porque preco, frete e vendedor variam por item,
    e um pedido pode ter itens de vendedores diferentes. Sem este grao, o
    custo de frete por rota fica errado.

    O mesmo produto aparece varias vezes no mesmo pedido: e assim que a
    origem representa quantidade. Por isso product_id NAO entra na chave.
*/
let
  NomeArquivo          = "olist_order_items_dataset.csv",
  Source               = bronze_particao_atual{[Name = NomeArquivo]}[Content],

  // QuoteStyle.Csv respeita aspas e aceita quebra de linha dentro do campo.
  Csv                  = Csv.Document(Source, [Delimiter = ",", Columns = 7, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
  PromoverCabecalhos   = Table.PromoteHeaders(Csv, [PromoteAllScalars = true]),

  // Tratamento de dados para evitar quebra de atualizacoes devido a perda de colunas.
  // Coluna adicionada na origem nao influencia no fluxo; coluna removida quebra
  // a atualizacao de proposito — e barato consertar hoje, caro descobrir depois
  // que a silver vinha com nulo desde marco.

  // Dicionario de colunas esperadas no arquivo.
  ColunasEsperadas     = {"order_id", "order_item_id", "product_id", "seller_id", "shipping_limit_date", "price", "freight_value"},
  ColunasRecebidas     = Table.ColumnNames(PromoverCabecalhos),
  Diferenca            = List.Difference(ColunasEsperadas, ColunasRecebidas),

  Validado =
    if List.IsEmpty(Diferenca) then PromoverCabecalhos
    else error Error.Record(
        "Quebra de Atualização",
        "Tabela itens_pedido: as seguintes colunas estão ausentes na origem — " & Text.Combine(Diferenca, ", "),
        [ QtdColunasRecebidas = List.Count(ColunasRecebidas),
          PrimeirasRecebidas  = Text.Combine(List.FirstN(ColunasRecebidas, 5), " | ") ]
        ),

  // Agora garantir que somente as colunas necessarias sejam carregadas caso
  // haja uma nova coluna na origem.
  Selecao              = Table.SelectColumns(Validado, ColunasEsperadas),

  RenomearColunas      = Table.RenameColumns(Selecao, {{"order_id", "id_pedido"}, {"order_item_id", "numero_item"}, {"product_id", "id_produto"}, {"seller_id", "id_vendedor"}, {"shipping_limit_date", "data_limite_envio"}, {"price", "preco"}, {"freight_value", "valor_frete"}}),

  // id_pedido e id_produto sao identificadores: texto.
  // numero_item e contador posicional dentro do pedido (1 a 21): inteiro.
  // preco e valor_frete sao dinheiro: decimal fixo, nunca ponto flutuante.
  // "en-US" e obrigatorio — a origem usa ponto decimal (58.90).
  TipagemdosDados     = Table.TransformColumnTypes(RenomearColunas, {
    {"id_pedido", type text}, 
    {"numero_item", Int64.Type}, 
    {"id_produto", type text}, 
    {"id_vendedor", type text}, 
    {"data_limite_envio", type datetime}, 
    {"preco", Currency.Type}, 
    {"valor_frete", Currency.Type}
    }, "en-US"),

  // Chave natural: pedido + numero do item. NUNCA pedido + produto — o mesmo
  // produto aparece varias vezes no mesmo pedido (e assim que a origem
  // representa quantidade), e deduplicar por produto apagaria 10.225 linhas,
  // 9% da tabela, sem erro nenhum.
  DeduplicarBase       = Table.Distinct(TipagemdosDados, {"id_pedido", "numero_item"}),

  // Rastro. A data vem da particao da bronze, nao do momento em que este
  // Dataflow rodou: e a silver que se reconstroi, o dado foi ingerido uma vez.
  DataParticao         = Date.FromText(particao_data),
  ComOrigem            = Table.AddColumn(DeduplicarBase, "_origem_arquivo", each NomeArquivo, type text),
  ComRastro            = Table.AddColumn(ComOrigem, "_ingerido_em", each DataParticao, type date)
in
    ComRastro;
[DataDestinations = {[Definition = [Kind = "Reference", QueryName = "vendedores_DataDestination", IsNewTarget = true], Settings = [Kind = "Automatic", TypeSettings = [Kind = "Table"]]]}]
shared vendedores = /*  vendedores
    Uma linha por vendedor. Chave natural: seller_id — 3.095 registros,
    sem duplicata e sem nulo na origem.

    A mais simples das oito: quatro colunas, todas texto.
*/
let
  NomeArquivo          = "olist_sellers_dataset.csv",
  Source               = bronze_particao_atual{[Name = NomeArquivo]}[Content],

  // QuoteStyle.Csv respeita aspas e aceita quebra de linha dentro do campo.
  Csv                  = Csv.Document(Source, [Delimiter = ",", Columns = 4, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
  PromoverCabecalhos   = Table.PromoteHeaders(Csv, [PromoteAllScalars = true]),

  // Tratamento de dados para evitar quebra de atualizacoes devido a perda de colunas.
  // Coluna adicionada na origem nao influencia no fluxo; coluna removida quebra
  // a atualizacao de proposito — e barato consertar hoje, caro descobrir depois
  // que a silver vinha com nulo desde marco.

  // Dicionario de colunas esperadas no arquivo.
  ColunasEsperadas     = {"seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"},
  ColunasRecebidas     = Table.ColumnNames(PromoverCabecalhos),
  Diferenca            = List.Difference(ColunasEsperadas, ColunasRecebidas),

  Validado =
    if List.IsEmpty(Diferenca) then PromoverCabecalhos
    else error Error.Record(
        "Quebra de Atualização",
        "Tabela vendedores: as seguintes colunas estão ausentes na origem — " & Text.Combine(Diferenca, ", "),
        [ QtdColunasRecebidas = List.Count(ColunasRecebidas),
          PrimeirasRecebidas  = Text.Combine(List.FirstN(ColunasRecebidas, 5), " | ") ]
        ),

  // Agora garantir que somente as colunas necessarias sejam carregadas caso
  // haja uma nova coluna na origem.
  Selecao              = Table.SelectColumns(Validado, ColunasEsperadas),

  RenomearColunas      = Table.RenameColumns(Selecao, {{"seller_id", "id_vendedor"}, {"seller_zip_code_prefix", "prefixo_cep"}, {"seller_city", "cidade"}, {"seller_state", "uf"}}),

  // Tudo texto: nao ha quantidade nem data nesta tabela.
  // prefixo_cep em especial — e identificador, nao numero. Como texto ele
  // preserva o zero a esquerda e casa com geografia; como numero, nao.
  TipagemdosDados     = Table.TransformColumnTypes(RenomearColunas, {
    {"id_vendedor", type text}, 
    {"prefixo_cep", type text}, 
    {"cidade", type text}, 
    {"uf", type text}
    }),

  // Mesma normalizacao aplicada em geografia, para as tres tabelas contarem a
  // mesma historia: sem isso, geografia teria "Sao Paulo" e esta teria
  // "sao paulo", e ninguem consegue comparar cidade entre elas.
  // Trim e Clean sao o conserto real; Text.Proper e leitura. A caixa da
  // origem ja e uniforme, entao Proper nao corrige duplicata — melhora
  // apresentacao. Se preferir manter minusculo, remova so o Text.Proper.
  PadronizarTexto      = Table.TransformColumns(TipagemdosDados, {
                            {"cidade", each if _ = null then null else Text.Proper(Text.Trim(Text.Clean(_))), type text},
                            {"uf",     each if _ = null then null else Text.Upper(Text.Trim(_)),             type text}
                         }),

  // Sem duplicata na origem hoje. O passo fica porque declara a chave natural
  // no codigo e protege contra mudanca futura na origem.
  DeduplicarBase       = Table.Distinct(PadronizarTexto, {"id_vendedor"}),

  // Rastro. A data vem da particao da bronze, nao do momento em que este
  // Dataflow rodou: e a silver que se reconstroi, o dado foi ingerido uma vez.
  DataParticao         = Date.FromText(particao_data),
  ComOrigem            = Table.AddColumn(DeduplicarBase, "_origem_arquivo", each NomeArquivo, type text),
  ComRastro            = Table.AddColumn(ComOrigem, "_ingerido_em", each DataParticao, type date)
in
    ComRastro;
[DataDestinations = {[Definition = [Kind = "Reference", QueryName = "produtos_DataDestination", IsNewTarget = true], Settings = [Kind = "Automatic", TypeSettings = [Kind = "Table"]]]}]
shared produtos = /*  produtos
    Uma linha por produto. Chave natural: product_id — 32.951 registros,
    sem duplicata na origem.

    ATENCAO ao contrato: a origem escreve "lenght", nao "length". O erro de
    digitacao e do dataset original e precisa ser reproduzido exatamente,
    senao o contrato acusa ausencia de coluna que existe.

    610 produtos nao tem categoria e 2 nao tem peso. Nao sao rejeitados: sao
    produtos validos, e remove-los deixaria itens de pedido orfaos. Nulo em
    atributo descritivo e informacao — a gold decide o que fazer com ele.
*/
let
  NomeArquivo          = "olist_products_dataset.csv",
  Source               = bronze_particao_atual{[Name = NomeArquivo]}[Content],

  // QuoteStyle.Csv respeita aspas e aceita quebra de linha dentro do campo.
  Csv                  = Csv.Document(Source, [Delimiter = ",", Columns = 9, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
  PromoverCabecalhos   = Table.PromoteHeaders(Csv, [PromoteAllScalars = true]),

  // Tratamento de dados para evitar quebra de atualizacoes devido a perda de colunas.
  // Coluna adicionada na origem nao influencia no fluxo; coluna removida quebra
  // a atualizacao de proposito — e barato consertar hoje, caro descobrir depois
  // que a silver vinha com nulo desde marco.

  // Dicionario de colunas esperadas no arquivo.
  ColunasEsperadas     = {"product_id", "product_category_name", "product_name_lenght", "product_description_lenght", "product_photos_qty", "product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"},
  ColunasRecebidas     = Table.ColumnNames(PromoverCabecalhos),
  Diferenca            = List.Difference(ColunasEsperadas, ColunasRecebidas),

  Validado =
    if List.IsEmpty(Diferenca) then PromoverCabecalhos
    else error Error.Record(
        "Quebra de Atualização",
        "Tabela produtos: as seguintes colunas estão ausentes na origem — " & Text.Combine(Diferenca, ", "),
        [ QtdColunasRecebidas = List.Count(ColunasRecebidas),
          PrimeirasRecebidas  = Text.Combine(List.FirstN(ColunasRecebidas, 5), " | ") ]
        ),

  // Agora garantir que somente as colunas necessarias sejam carregadas caso
  // haja uma nova coluna na origem.
  Selecao              = Table.SelectColumns(Validado, ColunasEsperadas),

  RenomearColunas      = Table.RenameColumns(Selecao, {
    {"product_id", "id_produto"}, 
    {"product_category_name", "categoria"}, 
    {"product_name_lenght", "tamanho_nome"}, 
    {"product_description_lenght", "tamanho_descricao"}, 
    {"product_photos_qty", "qtd_fotos"}, 
    {"product_weight_g", "peso_gramas"}, 
    {"product_length_cm", "comprimento_cm"}, 
    {"product_height_cm", "altura_cm"},
    {"product_width_cm", "largura_cm"}

}),

  // Identificador em texto; medidas e contagens em inteiro.
  // categoria fica como veio: "cama_mesa_banho" e codigo de dominio, nao
  // rotulo. A traducao para leitura de negocio pertence a gold, junto com
  // o product_category_name_translation.csv.
  TipagemdosDados     = Table.TransformColumnTypes(RenomearColunas, {
    {"id_produto", type text}, 
    {"categoria", type text}, 
    {"tamanho_nome", Int64.Type}, 
    {"tamanho_descricao", Int64.Type}, 
    {"qtd_fotos", Int64.Type}, 
    {"peso_gramas", Int64.Type}, 
    {"comprimento_cm", Int64.Type}, 
    {"altura_cm", Int64.Type}, 
    {"largura_cm", Int64.Type} 
}, "en-US"),

  // Sem duplicata na origem hoje. O passo fica porque declara a chave natural
  // no codigo e protege contra mudanca futura na origem.
  DeduplicarBase  = Table.Distinct(TipagemdosDados, {"id_produto"}),

  // Csv.Document devolve texto vazio para campo vazio, nunca nulo. A tipagem
  // converte "" em nulo quando a coluna vira numero — por isso peso e tamanhos
  // ja chegam nulos — mas deixa "" intacto no texto. Sem este passo, os 610
  // produtos sem categoria mentem que tem valor, e um IS NULL na silver
  // devolve zero.
  VaziosParaNulo  = Table.ReplaceValue(DeduplicarBase, "", null, Replacer.ReplaceValue, {"categoria"}),

  // Rastro. A data vem da particao da bronze, nao do momento em que este
  // Dataflow rodou: e a silver que se reconstroi, o dado foi ingerido uma vez.
  DataParticao    = Date.FromText(particao_data),
  ComOrigem       = Table.AddColumn(VaziosParaNulo, "_origem_arquivo", each NomeArquivo, type text),
  ComRastro       = Table.AddColumn(ComOrigem, "_ingerido_em", each DataParticao, type date)
in
    ComRastro;
[DataDestinations = {[Definition = [Kind = "Reference", QueryName = "pedidos_DataDestination", IsNewTarget = true], Settings = [Kind = "Automatic", TypeSettings = [Kind = "Table"]]]}]
shared pedidos = /*  pedidos
    Uma linha por pedido. Chave natural: order_id — 99.441 registros,
    sem duplicata na origem.

    Os nulos nas datas sao legitimos e precisam sobreviver como nulos:
    160 sem aprovacao, 1.783 sem coleta, 2.965 sem entrega. Sao pedidos em
    transito, cancelados ou indisponiveis — 96.478 dos 99.441 tem status
    delivered. Substituir por data padrao inflaria o OTD.
*/
let
  NomeArquivo          = "olist_orders_dataset.csv",
  Source               = bronze_particao_atual{[Name = NomeArquivo]}[Content],

  // QuoteStyle.Csv respeita aspas e aceita quebra de linha dentro do campo.
  Csv                  = Csv.Document(Source, [Delimiter = ",", Columns = 8, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
  PromoverCabecalhos   = Table.PromoteHeaders(Csv, [PromoteAllScalars = true]),

  // Tratamento de dados para evitar quebra de atualizacoes devido a perda de colunas.
  // Coluna adicionada na origem nao influencia no fluxo; coluna removida quebra
  // a atualizacao de proposito — e barato consertar hoje, caro descobrir depois
  // que a silver vinha com nulo desde marco.

  // Dicionario de colunas esperadas no arquivo.
  ColunasEsperadas     = {"order_id", "customer_id", "order_status", "order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date", "order_delivered_customer_date", "order_estimated_delivery_date"},
  ColunasRecebidas     = Table.ColumnNames(PromoverCabecalhos),
  Diferenca            = List.Difference(ColunasEsperadas, ColunasRecebidas),

  Validado =
    if List.IsEmpty(Diferenca) then PromoverCabecalhos
    else error Error.Record(
        "Quebra de Atualização",
        "Tabela pedidos: as seguintes colunas estão ausentes na origem — " & Text.Combine(Diferenca, ", "),
        [ QtdColunasRecebidas = List.Count(ColunasRecebidas),
          PrimeirasRecebidas  = Text.Combine(List.FirstN(ColunasRecebidas, 5), " | ") ]
        ),

  // Agora garantir que somente as colunas necessarias sejam carregadas caso
  // haja uma nova coluna na origem.
  Selecao              = Table.SelectColumns(Validado, ColunasEsperadas),

  RenomearColunas      = Table.RenameColumns(Selecao, {
    {"order_id", "id_pedido"}, 
    {"customer_id", "id_cliente"}, 
    {"order_status", "status_pedido"}, 
    {"order_purchase_timestamp", "data_compra"}, 
    {"order_approved_at", "data_aprovacao"}, 
    {"order_delivered_carrier_date", "data_coleta"}, 
    {"order_delivered_customer_date", "data_entrega_real"}, 
    {"order_estimated_delivery_date", "data_entrega_prevista"}
}),

  // Identificadores e status em texto; as cinco datas em datetime.
  // Nenhuma data recebe valor padrao: nulo aqui significa que o evento nao
  // aconteceu, e o calculo de OTD depende de distinguir isso de atraso.
  TipagemdosDados     = Table.TransformColumnTypes(RenomearColunas, {
    {"id_pedido", type text}, 
    {"id_cliente", type text}, 
    {"status_pedido", type text}, 
    {"data_compra", type datetime}, 
    {"data_aprovacao", type datetime}, 
    {"data_coleta", type datetime}, 
    {"data_entrega_real", type datetime}, 
    {"data_entrega_prevista", type datetime}
}, "en-US"),

  // Sem duplicata na origem hoje. O passo fica porque declara a chave natural
  // no codigo e protege contra mudanca futura na origem.
  DeduplicarBase       = Table.Distinct(TipagemdosDados, {"id_pedido"}),

  // Rastro. A data vem da particao da bronze, nao do momento em que este
  // Dataflow rodou: e a silver que se reconstroi, o dado foi ingerido uma vez.
  DataParticao         = Date.FromText(particao_data),
  ComOrigem            = Table.AddColumn(DeduplicarBase, "_origem_arquivo", each NomeArquivo, type text),
  ComRastro            = Table.AddColumn(ComOrigem, "_ingerido_em", each DataParticao, type date)
in
    ComRastro;
[DataDestinations = {[Definition = [Kind = "Reference", QueryName = "pagamentos_DataDestination", IsNewTarget = true], Settings = [Kind = "Automatic", TypeSettings = [Kind = "Table"]]]}]
shared pagamentos = /*  pagamentos
    Uma linha por pagamento de um pedido. Chave natural:
    order_id + payment_sequential — 103.886 registros, sem duplicata.

    Um pedido pode ser pago em mais de uma forma, e o sequencial distingue
    as parcelas dessa divisao. 9 pagamentos tem valor zero, com explicacao
    de negocio plausivel (voucher cobrindo o pedido) — nao sao rejeitados.
*/
let
  NomeArquivo          = "olist_order_payments_dataset.csv",
  Source               = bronze_particao_atual{[Name = NomeArquivo]}[Content],

  // QuoteStyle.Csv respeita aspas e aceita quebra de linha dentro do campo.
  Csv                  = Csv.Document(Source, [Delimiter = ",", Columns = 5, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
  PromoverCabecalhos   = Table.PromoteHeaders(Csv, [PromoteAllScalars = true]),

  // Tratamento de dados para evitar quebra de atualizacoes devido a perda de colunas.
  // Coluna adicionada na origem nao influencia no fluxo; coluna removida quebra
  // a atualizacao de proposito — e barato consertar hoje, caro descobrir depois
  // que a silver vinha com nulo desde marco.

  // Dicionario de colunas esperadas no arquivo.
  ColunasEsperadas     = {"order_id", "payment_sequential", "payment_type", "payment_installments", "payment_value"},
  ColunasRecebidas     = Table.ColumnNames(PromoverCabecalhos),
  Diferenca            = List.Difference(ColunasEsperadas, ColunasRecebidas),

  Validado =
    if List.IsEmpty(Diferenca) then PromoverCabecalhos
    else error Error.Record(
        "Quebra de Atualização",
        "Tabela pagamentos: as seguintes colunas estão ausentes na origem — " & Text.Combine(Diferenca, ", "),
        [ QtdColunasRecebidas = List.Count(ColunasRecebidas),
          PrimeirasRecebidas  = Text.Combine(List.FirstN(ColunasRecebidas, 5), " | ") ]
        ),

  // Agora garantir que somente as colunas necessarias sejam carregadas caso
  // haja uma nova coluna na origem.
  Selecao              = Table.SelectColumns(Validado, ColunasEsperadas),

  RenomearColunas      = Table.RenameColumns(Selecao, {
    {"order_id", "id_pedido"}, 
    {"payment_sequential", "sequencial_pagamento"}, 
    {"payment_type", "tipo_pagamento"}, 
    {"payment_installments", "qtd_parcelas"}, 
    {"payment_value", "valor"}
}),

  // Identificadores e tipo em texto; sequencial e parcelas em inteiro.
  // valor e dinheiro: decimal fixo. "en-US" e obrigatorio — a origem usa
  // ponto decimal (99.33). Soma esperada da coluna: 16.008.872,12.
  TipagemdosDados     = Table.TransformColumnTypes(RenomearColunas, {
    {"id_pedido", type text}, 
    {"sequencial_pagamento", Int64.Type}, 
    {"tipo_pagamento", type text}, 
    {"qtd_parcelas", Int64.Type}, 
    {"valor", Currency.Type}
}, "en-US"),

  // Sem duplicata na origem hoje. O passo fica porque declara a chave natural
  // no codigo e protege contra mudanca futura na origem.
  DeduplicarBase       = Table.Distinct(TipagemdosDados, {"id_pedido", "sequencial_pagamento"}),

  // Rastro. A data vem da particao da bronze, nao do momento em que este
  // Dataflow rodou: e a silver que se reconstroi, o dado foi ingerido uma vez.
  DataParticao         = Date.FromText(particao_data),
  ComOrigem            = Table.AddColumn(DeduplicarBase, "_origem_arquivo", each NomeArquivo, type text),
  ComRastro            = Table.AddColumn(ComOrigem, "_ingerido_em", each DataParticao, type date)
in
    ComRastro;
[DataDestinations = {[Definition = [Kind = "Reference", QueryName = "avaliacoes_DataDestination", IsNewTarget = true], Settings = [Kind = "Automatic", TypeSettings = [Kind = "Table"]]]}]
shared avaliacoes = /*  avaliacoes
    Uma linha por avaliacao de um pedido. Chave natural composta:
    review_id + order_id — 99.224 registros, medida como unica.

    A relacao e muitos-para-muitos legitima, nos dois sentidos: 789
    avaliacoes cobrem mais de um pedido e 547 pedidos tem mais de uma
    avaliacao. review_id sozinho NAO e chave — usa-lo descartaria 814
    linhas diferentes entre si, com aparencia de limpeza.

    87.656 titulos e 58.247 comentarios sao nulos: a maioria das pessoas da
    nota sem escrever nada. Nulo aqui e esperado, nao falha de carga.
*/
let
  NomeArquivo          = "olist_order_reviews_dataset.csv",
  Source               = bronze_particao_atual{[Name = NomeArquivo]}[Content],

  // QuoteStyle.Csv respeita aspas e aceita quebra de linha dentro do campo.
  Csv                  = Csv.Document(Source, [Delimiter = ",", Columns = 7, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
  PromoverCabecalhos   = Table.PromoteHeaders(Csv, [PromoteAllScalars = true]),

  // Tratamento de dados para evitar quebra de atualizacoes devido a perda de colunas.
  // Coluna adicionada na origem nao influencia no fluxo; coluna removida quebra
  // a atualizacao de proposito — e barato consertar hoje, caro descobrir depois
  // que a silver vinha com nulo desde marco.

  // Dicionario de colunas esperadas no arquivo.
  ColunasEsperadas     = {"review_id", "order_id", "review_score", "review_comment_title", "review_comment_message", "review_creation_date", "review_answer_timestamp"},
  ColunasRecebidas     = Table.ColumnNames(PromoverCabecalhos),
  Diferenca            = List.Difference(ColunasEsperadas, ColunasRecebidas),

  Validado =
    if List.IsEmpty(Diferenca) then PromoverCabecalhos
    else error Error.Record(
        "Quebra de Atualização",
        "Tabela avaliacoes: as seguintes colunas estão ausentes na origem — " & Text.Combine(Diferenca, ", "),
        [ QtdColunasRecebidas = List.Count(ColunasRecebidas),
          PrimeirasRecebidas  = Text.Combine(List.FirstN(ColunasRecebidas, 5), " | ") ]
        ),

  // Agora garantir que somente as colunas necessarias sejam carregadas caso
  // haja uma nova coluna na origem.
  Selecao              = Table.SelectColumns(Validado, ColunasEsperadas),

  RenomearColunas      = Table.RenameColumns(Selecao, {
    {"review_id", "id_avaliacao"}, 
    {"order_id", "id_pedido"}, 
    {"review_score", "nota"}, 
    {"review_comment_title", "titulo_comentario"}, 
    {"review_comment_message", "comentario"}, 
    {"review_creation_date", "data_avaliacao"}, 
    {"review_answer_timestamp", "data_resposta"}
}),

  // Identificadores em texto, nota em inteiro, datas em datetime.
  // data_avaliacao e diaria na pratica (apenas 2 horarios distintos em
  // 99.224 linhas), mas fica datetime para nao descartar a excecao.
  TipagemdosDados     = Table.TransformColumnTypes(RenomearColunas, {
    {"id_avaliacao", type text}, 
    {"id_pedido", type text}, 
    {"nota", Int64.Type}, 
    {"titulo_comentario", type text}, 
    {"comentario", type text}, 
    {"data_avaliacao", type datetime}, 
    {"data_resposta", type datetime}
}, "en-US"),

  // Sem duplicata na origem hoje. O passo fica porque declara a chave natural
  // no codigo e protege contra mudanca futura na origem.
  DeduplicarBase       = Table.Distinct(TipagemdosDados, {"id_avaliacao", "id_pedido"}),

  // Texto livre: so limpeza estrutural. A caixa e preservada porque ela
  // carrega sinal — 3% dos comentarios estao em caixa alta, e sao os
  // clientes irritados. Trim e Clean resolvem o defeito real: 23% dos
  // comentarios preenchidos tem espaco sobrando nas pontas.
    PadronizarTexto = Table.TransformColumns(DeduplicarBase, {
                       {"titulo_comentario", each if _ = null then null else Text.Trim(Text.Clean(_)), type text},
                       {"comentario",        each if _ = null then null else Text.Trim(Text.Clean(_)), type text}
                    }),

  // precisa virar nulo aqui. A ordem inversa deixaria o espaco sobreviver.
  VaziosParaNulo  = Table.ReplaceValue(PadronizarTexto, "", null, Replacer.ReplaceValue, {"titulo_comentario", "comentario"}),

  DataParticao    = Date.FromText(particao_data),
  ComOrigem       = Table.AddColumn(VaziosParaNulo, "_origem_arquivo", each NomeArquivo, type text),
  ComRastro       = Table.AddColumn(ComOrigem, "_ingerido_em", each DataParticao, type date)
in
    ComRastro;
[DataDestinations = {[Definition = [Kind = "Reference", QueryName = "geografia_DataDestination", IsNewTarget = true], Settings = [Kind = "Automatic", TypeSettings = [Kind = "Table"]]]}]
shared geografia = /*  geografia
    Um centroide por prefixo de CEP. Grao: prefixo de CEP.

    E aqui que 1.000.163 linhas de geolocalizacao viram 19.011 centroides.
    A agregacao pertence a esta camada, e nao a origem: aqui ela fica
    visivel, versionada e reversivel.

    Destino: lh_silver. Ative o staging — e a unica das oito onde se paga.
*/
let
  Valido = Table.SelectRows(geografia_base, each [_valido] = true),

  // M nao tem funcao nativa de remocao de acento. A origem e toda minuscula,
  // entao o mapa minusculo basta.
  //
  // Precisa rodar ANTES do Table.Group: "sao paulo" e "são paulo" convivem na
  // origem (2.042 nomes distintos sao a mesma cidade escrita de duas formas),
  // e grafias diferentes dividem o voto do List.Mode. Medido: 12 prefixos
  // recebem cidade diferente conforme a ordem — no 36576, "vicosa" e "viçosa"
  // dividiram os votos e deixaram "porto firme" vencer.
  //
  // Tambem precisa vir antes de qualquer mudanca de caixa, senao os acentos
  // viram maiusculos e o mapa minusculo nao os alcanca.
  RemoverAcento = (t as nullable text) as nullable text =>
      if t = null then null
      else List.Accumulate(
             {{"á","a"},{"à","a"},{"ã","a"},{"â","a"},
              {"é","e"},{"ê","e"},
              {"í","i"},
              {"ó","o"},{"ô","o"},{"õ","o"},
              {"ú","u"},{"ü","u"},
              {"ç","c"}},
             t,
             (acc, par) => Text.Replace(acc, par{0}, par{1})
           ),
  SemAcento = Table.TransformColumns(Valido, {{"cidade", RemoverAcento, type text}}),

  // Mediana, nao media. 309 prefixos tem ponto a mais de 100 km do proprio
  // centroide — coordenadas dentro do Brasil, mas erradas para o CEP —, e a
  // media e arrastada por elas. Medido: 223 prefixos deslocam mais de 10 km
  // entre as duas funcoes, e o pior caso desloca 1.118 km.
  //
  // Ressalva: mediana de latitude e de longitude em separado nao e a mediana
  // geometrica verdadeira. Para nuvem compacta de pontos, que e o caso de um
  // prefixo de CEP, a aproximacao e boa e muito mais robusta que a media.
  //
  // Cidade e UF pelo modo: 8.554 prefixos declaram mais de uma cidade e 8
  // declaram mais de uma UF. O mais frequente e escolha declarada e
  // reproduzivel, em vez de "o primeiro que aparecer".
  Agregar = Table.Group(SemAcento, {"prefixo_cep"}, {
              {"latitude",  each List.Median([latitude]),  type number},
              {"longitude", each List.Median([longitude]), type number},
              {"cidade",    each List.Mode([cidade]),      type text},
              {"uf",        each List.Mode([uf]),          type text}
            }),

  // Formatacao depois da agregacao: 19.011 linhas em vez de 1.000.163.
  // So vale para Trim, Clean e caixa, que nao afetam o agrupamento — o
  // acento tinha de vir antes, porque ele muda quem ganha o voto.
  //
  // Text.Proper deixa "Rio De Janeiro" onde o correto em portugues seria
  // "Rio de Janeiro". Limitacao aceita e registrada no dicionario. A origem
  // tambem nao tem acento, entao "sao paulo" vira "Sao Paulo", nunca
  // "São Paulo" — corrigir isso exigiria uma base de municipios oficial.
  PadronizarTexto = Table.TransformColumns(Agregar, {
                       {"cidade", each if _ = null then null else Text.Proper(Text.Trim(Text.Clean(_))), type text},
                       {"uf",     each if _ = null then null else Text.Upper(Text.Trim(_)),             type text}
                    }),

  // Rastro. A data vem da particao da bronze, nao do momento em que este
  // Dataflow rodou: e a silver que se reconstroi, o dado foi ingerido uma vez.
  DataParticao = Date.FromText(particao_data),
  ComOrigem    = Table.AddColumn(PadronizarTexto, "_origem_arquivo", each "olist_geolocation_dataset.parquet", type text),
  ComRastro    = Table.AddColumn(ComOrigem, "_ingerido_em", each DataParticao, type date)
in
  ComRastro;
[DataDestinations = {[Definition = [Kind = "Reference", QueryName = "geografia_rejeitados_DataDestination", IsNewTarget = true], Settings = [Kind = "Automatic", TypeSettings = [Kind = "Table"]]]}]
shared geografia_rejeitados = /*  geografia_rejeitados
    As coordenadas descartadas da geografia, com o motivo. 31 linhas.

    Unica tabela de rejeitados do projeto: nas outras sete, nenhuma linha e
    removida. Regra que passa vira numero medido no dicionario, nao tabela
    vazia — tabela vazia nao distingue "nada falhou" de "a regra nao rodou".

    O que ha aqui nao e ruido aleatorio: e falha de geocodificacao por
    homonimo. O geocodificador nao encontrou o lugar brasileiro e caiu no
    primeiro toponimo de mesmo nome — e como nome brasileiro e portugues, 19
    das 31 pararam na Peninsula Iberica. "Porto Trombetas" virou Porto,
    "Santo Antonio" virou San Antonio, "Santa Rosa" caiu em Santa Rosa de La
    Pampa com dois decimais de precisao.

    Destino: lh_silver.
*/
let
  Invalido  = Table.SelectRows(geografia_base, each [_valido] = false),

  // A cidade fica como veio, sem remocao de acento nem Text.Proper: esta
  // tabela existe para auditoria, e auditoria quer o valor original.
  SemFlag   = Table.RemoveColumns(Invalido, {"_valido"}),

  // Sem o motivo, sao 31 linhas orfas e ninguem sabe por que sairam. Com ele,
  // um GROUP BY conta quantas cairam em cada regra quando houver mais de uma.
  ComMotivo = Table.AddColumn(SemFlag, "_motivo_rejeicao",
                each "coordenada fora dos limites do territorio brasileiro", type text),

  ComOrigem = Table.AddColumn(ComMotivo, "_origem_arquivo",
                each "olist_geolocation_dataset.parquet", type text),
  ComRastro = Table.AddColumn(ComOrigem, "_ingerido_em",
                each Date.FromText(particao_data), type date)
in
  ComRastro;
shared geografia_base = /*  geografia_base
    ------------------------------------------------------------------
    Preparo comum das coordenadas, sem destino. Existe porque o Power Query
    nao divide uma consulta em duas saidas: geografia e geografia_rejeitados
    referenciam esta e filtram lados opostos da coluna _valido.

    Origem: olist_geolocation_dataset.parquet — 1.000.163 linhas.
*/
let
  NomeArquivo      = "olist_geolocation_dataset.parquet",
  Source           = bronze_particao_atual{[Name = NomeArquivo]}[Content],

  // Parquet e autodescritivo: nao ha delimitador, encoding nem aspas a declarar.
  Parquet          = Parquet.Document(Source),

  // Contrato com a origem. Coluna que some derruba a carga de proposito;
  // coluna nova e ignorada pelo Table.SelectColumns abaixo.
  ColunasEsperadas = {"geolocation_zip_code_prefix", "geolocation_lat",
                      "geolocation_lng", "geolocation_city", "geolocation_state"},
  ColunasRecebidas = Table.ColumnNames(Parquet),
  Diferenca        = List.Difference(ColunasEsperadas, ColunasRecebidas),

  Validado =
    if List.IsEmpty(Diferenca) then Parquet
    else error Error.Record(
        "Quebra de Atualização",
        "Tabela geografia: colunas ausentes na origem — " & Text.Combine(Diferenca, ", "),
        [ QtdColunasRecebidas = List.Count(ColunasRecebidas),
          PrimeirasRecebidas  = Text.Combine(List.FirstN(ColunasRecebidas, 5), " | ") ]
        ),

  Selecao          = Table.SelectColumns(Validado, ColunasEsperadas),

  RenomearColunas  = Table.RenameColumns(Selecao, {
                        {"geolocation_zip_code_prefix", "prefixo_cep"},
                        {"geolocation_lat",             "latitude"},
                        {"geolocation_lng",             "longitude"},
                        {"geolocation_city",            "cidade"},
                        {"geolocation_state",           "uf"}
                     }),

  // O Parquet vem inteiramente em texto de proposito: o preparar_dados.py
  // desliga a inferencia de tipo do pandas para nao perder o zero a esquerda
  // do prefixo de CEP. Esta e a unica das oito tabelas que converte texto
  // para numero, e a cultura e obrigatoria — a origem usa ponto decimal.
  TipagemdosDados  = Table.TransformColumnTypes(RenomearColunas, {
                        {"prefixo_cep", type text},
                        {"latitude",    type number},
                        {"longitude",   type number},
                        {"cidade",      type text},
                        {"uf",          type text}
                     }, "en-US"),

  // Caixa delimitadora do territorio brasileiro.
  // O limite leste e -28.80 e nao -34.79: o segundo e o extremo CONTINENTAL
  // (Ponta do Seixas, PB) e descartaria Fernando de Noronha, prefixo 53990,
  // que tem coordenada correta. -28.80 cobre Noronha, Trindade e Martim Vaz.
  lat_min = -33.75,   // Arroio Chui, RS
  lat_max =   5.27,   // Monte Caburai, RR
  lng_min = -73.99,   // Serra do Divisor, AC
  lng_max = -28.80,   // ilhas oceanicas

  // O try/otherwise trata coordenada nula: comparacao com null devolve null,
  // e a linha sumiria das DUAS saidas em vez de cair numa delas.
  DentroDoBrasil = Table.AddColumn(TipagemdosDados, "_valido", each
                     try [latitude]  >= lat_min and [latitude]  <= lat_max
                     and  [longitude] >= lng_min and [longitude] <= lng_max
                     otherwise false, type logical)
in
  DentroDoBrasil;
shared geografia_rejeitados_DataDestination = let
  Pattern = Lakehouse.Contents([CreateNavigationProperties = false, EnableFolding = false, HierarchicalNavigation = true, EnableVorder = true, OutputMetadataRefresh = true]),
  Navigation_1 = Pattern{[workspaceId = "528a4166-a694-4105-90bd-d6509fcc0536"]}[Data],
  Navigation_2 = Navigation_1{[lakehouseId = "f6b1f2f6-b88e-4122-898d-b8fc04b30459"]}[Data],
  Navigation_3 = Navigation_2{[Id = "dbo", ItemKind = "Schema"]}[Data],
  TableNavigation = Navigation_3{[Id = "geografia_rejeitados", ItemKind = "Table"]}?[Data]?
in
  TableNavigation;
shared geografia_DataDestination = let
  Pattern = Lakehouse.Contents([CreateNavigationProperties = false, EnableFolding = false, HierarchicalNavigation = true, EnableVorder = true, OutputMetadataRefresh = true]),
  Navigation_1 = Pattern{[workspaceId = "528a4166-a694-4105-90bd-d6509fcc0536"]}[Data],
  Navigation_2 = Navigation_1{[lakehouseId = "f6b1f2f6-b88e-4122-898d-b8fc04b30459"]}[Data],
  Navigation_3 = Navigation_2{[Id = "dbo", ItemKind = "Schema"]}[Data],
  TableNavigation = Navigation_3{[Id = "geografia", ItemKind = "Table"]}?[Data]?
in
  TableNavigation;
shared avaliacoes_DataDestination = let
  Pattern = Lakehouse.Contents([CreateNavigationProperties = false, EnableFolding = false, HierarchicalNavigation = true, EnableVorder = true, OutputMetadataRefresh = true]),
  Navigation_1 = Pattern{[workspaceId = "528a4166-a694-4105-90bd-d6509fcc0536"]}[Data],
  Navigation_2 = Navigation_1{[lakehouseId = "f6b1f2f6-b88e-4122-898d-b8fc04b30459"]}[Data],
  Navigation_3 = Navigation_2{[Id = "dbo", ItemKind = "Schema"]}[Data],
  TableNavigation = Navigation_3{[Id = "avaliacoes", ItemKind = "Table"]}?[Data]?
in
  TableNavigation;
shared pagamentos_DataDestination = let
  Pattern = Lakehouse.Contents([CreateNavigationProperties = false, EnableFolding = false, HierarchicalNavigation = true, EnableVorder = true, OutputMetadataRefresh = true]),
  Navigation_1 = Pattern{[workspaceId = "528a4166-a694-4105-90bd-d6509fcc0536"]}[Data],
  Navigation_2 = Navigation_1{[lakehouseId = "f6b1f2f6-b88e-4122-898d-b8fc04b30459"]}[Data],
  Navigation_3 = Navigation_2{[Id = "dbo", ItemKind = "Schema"]}[Data],
  TableNavigation = Navigation_3{[Id = "pagamentos", ItemKind = "Table"]}?[Data]?
in
  TableNavigation;
shared pedidos_DataDestination = let
  Pattern = Lakehouse.Contents([CreateNavigationProperties = false, EnableFolding = false, HierarchicalNavigation = true, EnableVorder = true, OutputMetadataRefresh = true]),
  Navigation_1 = Pattern{[workspaceId = "528a4166-a694-4105-90bd-d6509fcc0536"]}[Data],
  Navigation_2 = Navigation_1{[lakehouseId = "f6b1f2f6-b88e-4122-898d-b8fc04b30459"]}[Data],
  Navigation_3 = Navigation_2{[Id = "dbo", ItemKind = "Schema"]}[Data],
  TableNavigation = Navigation_3{[Id = "pedidos", ItemKind = "Table"]}?[Data]?
in
  TableNavigation;
shared produtos_DataDestination = let
  Pattern = Lakehouse.Contents([CreateNavigationProperties = false, EnableFolding = false, HierarchicalNavigation = true, EnableVorder = true, OutputMetadataRefresh = true]),
  Navigation_1 = Pattern{[workspaceId = "528a4166-a694-4105-90bd-d6509fcc0536"]}[Data],
  Navigation_2 = Navigation_1{[lakehouseId = "f6b1f2f6-b88e-4122-898d-b8fc04b30459"]}[Data],
  Navigation_3 = Navigation_2{[Id = "dbo", ItemKind = "Schema"]}[Data],
  TableNavigation = Navigation_3{[Id = "produtos", ItemKind = "Table"]}?[Data]?
in
  TableNavigation;
shared vendedores_DataDestination = let
  Pattern = Lakehouse.Contents([CreateNavigationProperties = false, EnableFolding = false, HierarchicalNavigation = true, EnableVorder = true, OutputMetadataRefresh = true]),
  Navigation_1 = Pattern{[workspaceId = "528a4166-a694-4105-90bd-d6509fcc0536"]}[Data],
  Navigation_2 = Navigation_1{[lakehouseId = "f6b1f2f6-b88e-4122-898d-b8fc04b30459"]}[Data],
  Navigation_3 = Navigation_2{[Id = "dbo", ItemKind = "Schema"]}[Data],
  TableNavigation = Navigation_3{[Id = "vendedores", ItemKind = "Table"]}?[Data]?
in
  TableNavigation;
shared itens_pedido_DataDestination = let
  Pattern = Lakehouse.Contents([CreateNavigationProperties = false, EnableFolding = false, HierarchicalNavigation = true, EnableVorder = true, OutputMetadataRefresh = true]),
  Navigation_1 = Pattern{[workspaceId = "528a4166-a694-4105-90bd-d6509fcc0536"]}[Data],
  Navigation_2 = Navigation_1{[lakehouseId = "f6b1f2f6-b88e-4122-898d-b8fc04b30459"]}[Data],
  Navigation_3 = Navigation_2{[Id = "dbo", ItemKind = "Schema"]}[Data],
  TableNavigation = Navigation_3{[Id = "itens_pedido", ItemKind = "Table"]}?[Data]?
in
  TableNavigation;
shared clientes_DataDestination = let
  Pattern = Lakehouse.Contents([CreateNavigationProperties = false, EnableFolding = false, HierarchicalNavigation = true, EnableVorder = true, OutputMetadataRefresh = true]),
  Navigation_1 = Pattern{[workspaceId = "528a4166-a694-4105-90bd-d6509fcc0536"]}[Data],
  Navigation_2 = Navigation_1{[lakehouseId = "f6b1f2f6-b88e-4122-898d-b8fc04b30459"]}[Data],
  Navigation_3 = Navigation_2{[Id = "dbo", ItemKind = "Schema"]}[Data],
  TableNavigation = Navigation_3{[Id = "clientes", ItemKind = "Table"]}?[Data]?
in
  TableNavigation;
