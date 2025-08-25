import sqlite3
import os
from datetime import datetime, timedelta

# --- Configurações ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'database.db')
DIAS_RETENCAO_LICITACOES = 30 # Quantos dias manter licitações baseadas na dataAtualizacao

def get_db_connection():
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        print(f"LIMPEZA: Conexão com SQLite DB bem-sucedida.")
    except sqlite3.Error as e:
        print(f"LIMPEZA: Erro ao conectar ao banco: {e}")
    return conn

def cleanup_licitacoes_antigas():
    conn = get_db_connection()
    if not conn:
        return # Sai se não conseguiu conectar

    cursor = conn.cursor()
    agora = datetime.now()
    data_limite_permanencia_dt = agora - timedelta(days=DIAS_RETENCAO_LICITACOES)
    data_limite_permanencia_db_str = data_limite_permanencia_dt.strftime('%Y-%m-%d')

    try:
        print(f"LIMPEZA: Iniciando limpeza de licitações com dataAtualizacao < {data_limite_permanencia_db_str}")
        
        # Graças ao ON DELETE CASCADE, apenas precisamos deletar da tabela 'licitacoes'
        # Os registros relacionados em 'itens_licitacao' e 'arquivos_licitacao' serão removidos automaticamente.
        cursor.execute("DELETE FROM licitacoes WHERE dataAtualizacao < ?", (data_limite_permanencia_db_str,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        print(f"LIMPEZA: {deleted_count} licitações antigas (e seus itens/arquivos associados) removidas com sucesso.")

        if deleted_count > 0: # Só executa VACUUM se algo foi deletado
            print("LIMPEZA: Otimizando o banco de dados (VACUUM)...")
            cursor.execute("VACUUM;")
            conn.commit() # VACUUM precisa de seu próprio commit em algumas configurações/versões
            print("LIMPEZA: Otimização concluída.")
        else:
            print("LIMPEZA: Nenhuma licitação antiga encontrada para remover. Otimização (VACUUM) não necessária.")

    except sqlite3.Error as e:
        print(f"LIMPEZA: Erro durante a limpeza de licitações antigas: {e}")
        try:
            conn.rollback() # Tenta reverter em caso de erro
        except sqlite3.Error as rb_err:
            print(f"LIMPEZA: Erro adicional durante o rollback: {rb_err}")
    finally:
        if conn:
            conn.close()
            print("LIMPEZA: Conexão com o banco de dados fechada.")

if __name__ == '__main__':
    print("Iniciando script de limpeza de dados antigos...")
    cleanup_licitacoes_antigas()
    print("Script de limpeza finalizado.")