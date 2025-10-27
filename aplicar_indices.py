# Esse script aplica índices no banco de dados MariaDB para otimizar consultas.

import mysql.connector
from dotenv import load_dotenv
import os

# Carrega as variáveis de ambiente
load_dotenv()

# Lista de comandos para executar
# IMPORTANTE: Colocamos 'IGNORE' para não dar erro se o índice já existir
comandos_sql = [
    # 1. Índice FTS (se ainda não tiver)
    "ALTER TABLE licitacoes ADD FULLTEXT idx_fts_busca (objetoCompra, orgaoEntidadeRazaoSocial, unidadeOrgaoNome, numeroControlePNCP, unidadeOrgaoMunicipioNome, unidadeOrgaoUfNome, orgaoEntidadeCnpj)",
    
    # 2. Índice para a página de DETALHES (essencial)
    "CREATE INDEX idx_num_pncp ON licitacoes (numeroControlePNCP)",
    
    # 3. Índice para o filtro principal (Status + Data)
    "CREATE INDEX idx_situacao_data_att ON licitacoes (situacaoReal, dataAtualizacao DESC)",
    
    # 4. Índice para filtros de Localização + Modalidade
    "CREATE INDEX idx_uf_modalidade ON licitacoes (unidadeOrgaoUfSigla, modalidadeId)",
    
    # 5. Índice para filtro/ordenação por Valor
    "CREATE INDEX idx_valor_estimado ON licitacoes (valorTotalEstimado)",
    
    # 6. Índice para filtro/ordenação por Data de Publicação
    "CREATE INDEX idx_data_pub ON licitacoes (dataPublicacaoPncp)",
    
    # 7. Índice para filtro por CNPJ
    "CREATE INDEX idx_cnpj_orgao ON licitacoes (orgaoEntidadeCnpj)"

    # 8. Índice para filtro combinado por Status + Modalidade
    "CREATE INDEX idx_status_modalidade ON licitacoes (situacaoReal, modalidadeId)",
]

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=os.getenv('MARIADB_HOST'),
            user=os.getenv('MARIADB_USER'),
            password=os.getenv('MARIADB_PASSWORD'),
            database=os.getenv('MARIADB_DATABASE')
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Erro ao conectar ao MariaDB: {err}")
        return None

def aplicar_indices():
    conn = get_db_connection()
    if not conn:
        return

    cursor = conn.cursor()
    print("Iniciando aplicação de índices...")

    for comando in comandos_sql:
        try:
            print(f"Executando: {comando[:80]}...")
            cursor.execute(comando)
            conn.commit()
            print("   -> OK!")
            
        except mysql.connector.Error as err:
            if err.errno == 1061: # Código de erro para "Índice duplicado"
                print(f"   -> AVISO: Índice já existe. (Ignorando erro {err.errno})")
            elif err.errno == 1060: # No ALTER TABLE, o erro é "Coluna duplicada" para FTS
                print(f"   -> AVISO: Índice FTS já existe. (Ignorando erro {err.errno})")
            else:
                print(f"   -> ERRO: {err}")
                conn.rollback()
    
    cursor.close()
    conn.close()
    print("Aplicação de índices concluída.")

if __name__ == '__main__':
    aplicar_indices()