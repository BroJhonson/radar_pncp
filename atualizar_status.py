# atualizar_status.py
import os
import sys
import fcntl
import mysql.connector

# --- REUTILIZAÇÃO DA LÓGICA EXISTENTE ---
from sync_api import get_db_connection, logger

# --- CONFIGURAÇÕES ---
LOCK_FILE = "sync_api.lock"  # OBRIGATÓRIO: usar o mesmo lock dos outros scripts

def atualizar_status_baseado_no_tempo():
    """
    Atualiza o 'situacaoReal' de licitações cuja data de encerramento já passou.
    Esta é uma operação de manutenção de dados internos.
    """
    logger.info("UPDATE_STATUS: Iniciando script de atualização de status.")
    
    conn = get_db_connection()
    if not conn:
        logger.critical("UPDATE_STATUS: Não foi possível conectar ao banco de dados. Abortando.")
        return

    cursor = None
    try:
        cursor = conn.cursor()

        # Esta é a query principal. Ela é projetada para ser eficiente:
        # 1. ATUALIZA a tabela 'licitacoes'.
        # 2. DEFINE o novo status.
        # 3. USA um WHERE para encontrar apenas as linhas que:
        #    - Estão com o status que precisa mudar ('A Receber/Recebendo Proposta').
        #    - A data de encerramento NÃO é nula.
        #    - A data de encerramento é ANTERIOR à data atual do servidor de BD (CURDATE()).
        query_update = """
            UPDATE licitacoes
            SET situacaoReal = 'Em Julgamento/Propostas Encerradas'
            WHERE 
                situacaoReal = 'A Receber/Recebendo Proposta'
                AND dataEncerramentoProposta IS NOT NULL
                AND dataEncerramentoProposta < NOW();
        """

        logger.info("UPDATE_STATUS: Executando query para atualizar status de propostas encerradas...")
        cursor.execute(query_update)
        
        # O cursor.rowcount nos diz quantas linhas foram efetivamente alteradas.
        updated_count = cursor.rowcount
        
        conn.commit()

        if updated_count > 0:
            logger.info(f"UPDATE_STATUS: SUCESSO. {updated_count} licitações tiveram seu status atualizado para 'Em Julgamento/Propostas Encerradas'.")
        else:
            logger.info("UPDATE_STATUS: Nenhuma licitação para atualizar. Os status estão consistentes com as datas.")

    except mysql.connector.Error as err:
        logger.error(f"UPDATE_STATUS: Erro durante a atualização de status: {err}")
        try:
            conn.rollback()
        except mysql.connector.Error as rb_err:
            logger.error(f"UPDATE_STATUS: Erro adicional durante o rollback: {rb_err}")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

if __name__ == '__main__':
    # --- MECANISMO DE LOCK (IDÊNTICO AOS OUTROS SCRIPTS) ---
    # Garante que este script não execute ao mesmo tempo que o sync ou o reprocessamento.
    try:
        lock_handle = open(LOCK_FILE, "w")
        fcntl.lockf(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        logger.info("UPDATE_STATUS: Lock adquirido. Iniciando atualização de status.")
    except IOError:
        logger.warning("UPDATE_STATUS: Outro script de sincronização já está em execução. Saindo.")
        sys.exit(0)
    
    atualizar_status_baseado_no_tempo()
    logger.info("UPDATE_STATUS: Script de atualização de status finalizado.")