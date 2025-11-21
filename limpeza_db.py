import mysql.connector
from mysql.connector import errorcode
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# --- Configurações ---
DIAS_RETENCAO_LICITACOES = 300 # Dias para manter as licitações na base de dados

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
        
        total_deleted = 0
        while True:
            # DELETA APENAS 1000 LINHAS POR VEZ E TODAS COM STATUS ENCERRADA
            query_delete = """
                DELETE FROM licitacoes 
                WHERE 
                    dataAtualizacao < %s 
                    AND situacaoReal = 'Encerrada'
                LIMIT 1000
            """
            cursor.execute(query_delete, (data_limite_str,))
            deleted_count_this_batch = cursor.rowcount
            conn.commit()

            if deleted_count_this_batch == 0:
                # Se não deletou nada, significa que terminamos
                break

            total_deleted += deleted_count_this_batch
            print(f"LIMPEZA: {deleted_count_this_batch} registros removidos neste lote. Total removido: {total_deleted}.")
            time.sleep(1) # Pausa de 1 segundo para não sobrecarregar o banco

        print(f"LIMPEZA: {total_deleted} licitações antigas (e seus itens/arquivos) removidas com sucesso.")

        if total_deleted > 0:
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