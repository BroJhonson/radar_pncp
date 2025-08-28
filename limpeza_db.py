import mysql.connector
from mysql.connector import errorcode
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# --- Configurações ---
DIAS_RETENCAO_LICITACOES = 370 # Manter licitações atualizadas nos últimos 370 dias

def get_db_connection():
    """Retorna uma conexão com o banco de dados MariaDB."""
    try:
        conn = mysql.connector.connect(
            host=os.getenv('MARIADB_HOST'),
            user=os.getenv('MARIADB_USER'),
            password=os.getenv('MARIADB_PASSWORD'),
            database=os.getenv('MARIADB_DATABASE')
        )
        print("LIMPEZA: Conexão com MariaDB bem-sucedida.")
        return conn
    except mysql.connector.Error as err:
        print(f"LIMPEZA: Erro ao conectar ao MariaDB: {err}")
        return None

def cleanup_licitacoes_antigas():
    """
    Remove licitações antigas da base de dados MariaDB e otimiza as tabelas.
    """
    conn = get_db_connection()
    if not conn:
        return # Sai se não conseguiu conectar

    cursor = conn.cursor()
    
    # Calcula a data limite para manter os registros
    data_limite = datetime.now() - timedelta(days=DIAS_RETENCAO_LICITACOES)
    data_limite_str = data_limite.strftime('%Y-%m-%d')

    try:
        print(f"LIMPEZA: Iniciando remoção de licitações com dataAtualizacao < {data_limite_str}")
        
        # O 'ON DELETE CASCADE' definido nas chaves estrangeiras no MariaDB
        # garante que itens e arquivos associados também sejam removidos.
        # Usamos %s como placeholder.
        query_delete = "DELETE FROM licitacoes WHERE dataAtualizacao < %s"
        
        cursor.execute(query_delete, (data_limite_str,))
        deleted_count = cursor.rowcount
        
        # Confirma a exclusão dos dados
        conn.commit()
        
        print(f"LIMPEZA: {deleted_count} licitações antigas (e seus itens/arquivos) removidas com sucesso.")

        # A otimização no MariaDB/MySQL é feita com 'OPTIMIZE TABLE'
        if deleted_count > 0:
            print("LIMPEZA: Otimizando as tabelas (OPTIMIZE TABLE)...")
            # Lista de tabelas que foram afetadas pela exclusão em cascata
            tabelas_para_otimizar = ['licitacoes', 'itens_licitacao', 'arquivos_licitacao']
            for tabela in tabelas_para_otimizar:
                print(f"  - Otimizando tabela '{tabela}'...")
                cursor.execute(f"OPTIMIZE TABLE {tabela}")
            print("LIMPEZA: Otimização concluída.")
        else:
            print("LIMPEZA: Nenhuma licitação antiga para remover. Otimização não necessária.")

    except mysql.connector.Error as err:
        print(f"LIMPEZA: Erro durante a limpeza: {err}")
        try:
            conn.rollback() # Desfaz as alterações em caso de erro
            print("LIMPEZA: Rollback realizado.")
        except mysql.connector.Error as rb_err:
            print(f"LIMPEZA: Erro adicional durante o rollback: {rb_err}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            print("LIMPEZA: Conexão com o banco de dados fechada.")

if __name__ == '__main__':
    print("Iniciando script de limpeza de dados antigos do MariaDB...")
    cleanup_licitacoes_antigas()
    print("Script de limpeza finalizado.")