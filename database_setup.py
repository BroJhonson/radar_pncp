# python database_setup.py

import sqlite3 # (Importa o módulo sqlite3 para interagir com bancos de dados SQLite)
import os # (Importa o módulo os para manipulação de caminhos de arquivos e diretórios)

# Define o caminho para a pasta backend
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # (Obtém o caminho absoluto do diretório onde o script está)
# Define o caminho completo para o arquivo do banco de dados
DATABASE_PATH = os.path.join(BASE_DIR, 'database.db') # (Cria o caminho 'backend/database.db')

def create_connection(db_file):
    """ Cria conexão com o banco de dados SQLite especificado por db_file """
    conn = None # (Inicializa a variável de conexão como None)
    try: 
        conn = sqlite3.connect(db_file) # (Tenta conectar ao banco. Se o arquivo não existir, ele será criado)
        print(f"Conexão com SQLite DB versão {sqlite3.sqlite_version} bem-sucedida.")
        print(f"Banco de dados criado em: {db_file}")
    except sqlite3.Error as e:
        print(e) # (Se ocorrer um erro na conexão, imprime o erro)
    return conn # (Retorna o objeto de conexão)

def create_table(conn, create_table_sql):
    """ Criarmos qualquer tabela a partir da instrução create_table_sql """
    try:
        c = conn.cursor() # (Cria um objeto cursor para executar comandos SQL)
        c.execute(create_table_sql) # (Executa o comando SQL para criar a tabela)
    except sqlite3.Error as e:
        print(e) # (Se ocorrer um erro ao criar a tabela, imprime o erro)

def main():
    """ Função principal para criar o banco de dados e as tabelas """

    # SQL para criar a tabela 'LICITA~ÇÕES
    sql_create_licitacoes_table = """
    CREATE TABLE IF NOT EXISTS licitacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numeroControlePNCP TEXT UNIQUE NOT NULL, -- (Chave única da API, não pode ser nula)
        numeroCompra TEXT,
        anoCompra INTEGER,
        processo TEXT,
        tipolnstrumentoConvocatorioId INTEGER,
        tipolnstrumentoConvocatorioNome TEXT,
        modalidadeId INTEGER,
        modalidadeNome TEXT,
        modoDisputaId INTEGER,
        modoDisputaNome TEXT,
        situacaoCompraId INTEGER, -- (Apenas 1 para ativas inicialmente)
        situacaoCompraNome TEXT,
        objetoCompra TEXT,
        informacaoComplementar TEXT,
        srp BOOLEAN, -- (SQLite armazena BOOLEAN como INTEGER 0 ou 1)
        amparoLegalCodigo INTEGER,
        amparoLegalNome TEXT,
        amparoLegalDescricao TEXT,
        valorTotalEstimado REAL,
        valorTotalHomologado REAL,
        dataAberturaProposta TEXT, -- (Formato ISO YYYY-MM-DD)
        dataEncerramentoProposta TEXT, -- (Formato ISO YYYY-MM-DD)
        dataPublicacaoPncp TEXT, -- (Formato ISO YYYY-MM-DD)
        dataInclusao TEXT, -- (Formato ISO YYYY-MM-DD)
        dataAtualizacao TEXT, -- (Formato ISO YYYY-MM-DD)
        sequencialCompra INTEGER,
        orgaoEntidadeCnpj TEXT,
        orgaoEntidadeRazaoSocial TEXT,
        orgaoEntidadePoderId TEXT,
        orgaoEntidadeEsferaId TEXT,
        unidadeOrgaoCodigo TEXT,
        unidadeOrgaoNome TEXT,
        unidadeOrgaoCodigoIbge INTEGER,
        unidadeOrgaoMunicipioNome TEXT,
        unidadeOrgaoUfSigla TEXT,
        unidadeOrgaoUfNome TEXT,
        usuarioNome TEXT,
        linkSistemaOrigem TEXT,
        link_portal_pncp TEXT,
        justificativaPresencial TEXT,
        situacaoReal TEXT
    );
    """

    # SQL para criar a tabela 'TABELA DE ITENS" itens_licitacoes
    sql_create_itens_licitacao_table = """
    CREATE TABLE IF NOT EXISTS itens_licitacao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        licitacao_id INTEGER NOT NULL,                          -- FK para licitacoes.id
        numeroItem INTEGER,
        descricao TEXT,                                         
        materialOuServicoNome TEXT,                             
        quantidade REAL,                                        -- RENOMEADO (era quantidadeEstimada)
        unidadeMedida TEXT,                                     
        valorUnitarioEstimado REAL,                             -- RENOMEADO (era valorUnitario)
        valorTotal REAL,                                        
        orcamentoSigiloso BOOLEAN,                              
        itemCategoriaNome TEXT,                                 -- RENOMEADO (era categoriaItemNome)
        categoriaItemCatalogo TEXT,                       
        criterioJulgamentoNome TEXT,                            
        situacaoCompraItemNome TEXT,                            
        tipoBeneficioNome TEXT,                                 
        incentivoProdutivoBasico BOOLEAN,                       
        dataInclusao TEXT,                                 -- (formato ISO YYYY-MM-DD)
        dataAtualizacao TEXT,                              -- (formato ISO YYYY-MM-DD)        
        temResultado BOOLEAN,                                   
        informacaoComplementar TEXT,                       
        FOREIGN KEY (licitacao_id) REFERENCES licitacoes (id) ON DELETE CASCADE
    );
    """
    # Manter índice em licitacao_id
    sql_create_index_itens_licitacao_id = "CREATE INDEX IF NOT EXISTS idx_itens_licitacao_licitacao_id ON itens_licitacao (licitacao_id);"


    #Criar tabela de "ARQUIVOS" arquivos_licitacoes
    sql_create_arquivos_licitacao_table = """
    CREATE TABLE IF NOT EXISTS arquivos_licitacao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        licitacao_id INTEGER NOT NULL,      -- FK para licitacoes.id
        titulo TEXT,                        -- Renomeei era nome_arquivo
        link_download TEXT UNIQUE NOT NULL, -- O link de download montado, UNIQUE
        dataPublicacaoPncp TEXT,
        anoCompra INTEGER,
        statusAtivo BOOLEAN,
        FOREIGN KEY (licitacao_id) REFERENCES licitacoes (id) ON DELETE CASCADE
    );
    """

    sql_create_index_arquivos_licitacao_id = "CREATE INDEX IF NOT EXISTS idx_arquivos_licitacao_licitacao_id ON arquivos_licitacao (licitacao_id);"
    # O índice em link_arquivo é criado automaticamente por ser UNIQUE.



    # SQL para criar índices na tabela 'licitacoes'
    # (Índice em numeroControlePNCP é criado automaticamente por ser UNIQUE, mas podemos ser explícitos)
    # (Na verdade, UNIQUE já cria um índice, então criar outro explicitamente não é necessário e pode ser redundante, mas alguns DBs otimizam, outros podem dar erro. SQLite geralmente lida bem.)
    # (Vou omitir a criação explícita do índice para numeroControlePNCP já que é UNIQUE)
    sql_create_index_licitacoes_situacao = "CREATE INDEX IF NOT EXISTS idx_licitacoes_situacao_compra_id ON licitacoes (situacaoCompraId);"
    sql_create_index_licitacoes_uf = "CREATE INDEX IF NOT EXISTS idx_licitacoes_unidade_orgao_uf_sigla ON licitacoes (unidadeOrgaoUfSigla);"
    sql_create_index_licitacoes_data_abertura = "CREATE INDEX IF NOT EXISTS idx_licitacoes_data_abertura_proposta ON licitacoes (dataAberturaProposta);"
    sql_create_index_licitacoes_data_atualizacao = "CREATE INDEX IF NOT EXISTS idx_licitacoes_data_atualizacao ON licitacoes (dataAtualizacao);"
    sql_create_index_licitacoes_cnpj_orgao = "CREATE INDEX IF NOT EXISTS idx_licitacoes_orgao_entidade_cnpj ON licitacoes (orgaoEntidadeCnpj);"

    # SQL para criar índice na tabela 'itens_licitacao'
    sql_create_index_itens_licitacao_id = "CREATE INDEX IF NOT EXISTS idx_itens_licitacao_licitacao_id ON itens_licitacao (licitacao_id);"

    # Cria a conexão com o banco de dados
    conn = create_connection(DATABASE_PATH) # (Chama a função para conectar/criar o banco)

    # Cria as tabelas e índices se a conexão for bem-sucedida
    if conn is not None:
        print("Criando tabela 'licitacoes'...")
        create_table(conn, sql_create_licitacoes_table) # (Cria a tabela licitacoes)

        print("Criando tabela 'itens_licitacao'...")
        create_table(conn, sql_create_itens_licitacao_table) # (Cria a tabela itens_licitacao)

        print("Criando índices para 'licitacoes'...")
        create_table(conn, sql_create_index_licitacoes_situacao) # (Cria índice em situacaoCompraId)
        create_table(conn, sql_create_index_licitacoes_uf) # (Cria índice em unidadeOrgaoUfSigla)
        create_table(conn, sql_create_index_licitacoes_data_abertura) # (Cria índice em dataAberturaProposta)
        create_table(conn, sql_create_index_licitacoes_data_atualizacao) # (Cria índice em dataAtualizacao)
        create_table(conn, sql_create_index_licitacoes_cnpj_orgao) # (Cria índice em orgaoEntidadeCnpj)

        print("Criando índices para 'itens_licitacao'...")
        create_table(conn, sql_create_index_itens_licitacao_id) # (Cria índice em licitacao_id)

        print("Criando tabela 'arquivos_licitacao'...")
        create_table(conn, sql_create_arquivos_licitacao_table) # Cria a tabela arquivos_licitacao

        print("Criando índices para 'arquivos_licitacao'...")
        create_table(conn, sql_create_index_arquivos_licitacao_id) # Cria índice em licitacao_id

        conn.commit() # (Salva (commit) as alterações no banco de dados)
        conn.close() # (Fecha a conexão com o banco de dados)
        print("Banco de dados e tabelas criados com sucesso.")
    else:
        print("Erro! Não foi possível criar a conexão com o banco de dados.")

if __name__ == '__main__':
    main() # (Executa a função main quando o script é rodado diretamente)""