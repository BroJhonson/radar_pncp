# backend/notificacoes.py
import os
import firebase_admin
from firebase_admin import credentials, messaging
from dotenv import load_dotenv
import mysql.connector
import logging
from logging.handlers import RotatingFileHandler
import time

load_dotenv()

# ==============================================================================
# CONFIGURAÇÃO DE LOGGING (Padronizado)
# ==============================================================================
# Garante que o diretório de logs exista
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, '../logs') # Ajuste se sua pasta logs estiver na raiz
if not os.path.exists(LOG_DIR):
    try:
        os.makedirs(LOG_DIR)
    except OSError:
        pass # Se já existir ou erro de permissão (tenta usar local)
        LOG_DIR = 'logs'
        if not os.path.exists(LOG_DIR): os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, 'notificacoes.log')

# Cria o logger
logger = logging.getLogger('worker_notificacoes')
logger.setLevel(logging.INFO)

# Formato do log
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')

# 1. Handler de Arquivo (Rotaciona a cada 10MB, guarda 5 arquivos)
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=10240000, backupCount=5)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)

# 2. Handler de Console (Para ver no terminal se rodar manual)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.INFO)

# Adiciona os handlers (evita duplicação se recarregar)
if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

logger.info("--- WORKER DE NOTIFICAÇÕES INICIADO ---")
# ==============================================================================

# Firebase Init
if not firebase_admin._apps:
    try:
        cred_path = os.path.join(os.path.dirname(__file__), '../firebase_credentials.json')
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin inicializado.")
    except Exception as e:
        logger.critical(f"ERRO CRÍTICO AO INICIAR FIREBASE: {e}")
        exit(1)

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('MARIADB_HOST'), user=os.getenv('MARIADB_USER'),
        password=os.getenv('MARIADB_PASSWORD'), database=os.getenv('MARIADB_DATABASE')
    )

def resgatar_zumbis(cursor, conn):
    """
    Faxina de segurança: Procura licitações travadas no status 2 (Processando)
    há mais de 15 minutos (possível crash do script anterior) e reseta para 0.
    """
    try:
        cursor.execute("""
            UPDATE licitacoes 
            SET notificacao_processada = 0, 
                processamento_inicio = NULL 
            WHERE notificacao_processada = 2 
            AND processamento_inicio < DATE_SUB(NOW(), INTERVAL 15 MINUTE)
        """)
        
        afetados = cursor.rowcount
        if afetados > 0:
            conn.commit()
            logger.warning(f"🧟 ZUMBIS RESGATADOS: {afetados} licitações travadas foram resetadas para fila.")
            
    except mysql.connector.Error as err:
        # Se der erro pq a coluna não existe, avisa mas não trava tudo
        if err.errno == 1054: # Unknown column
            logger.error("Erro Zumbi: Coluna 'processamento_inicio' não existe na tabela licitacoes. Rode o SQL de atualização.")
        else:
            logger.error(f"Erro ao resgatar zumbis: {err}")

def processar_notificacoes():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. Resgate de segurança
        resgatar_zumbis(cursor, conn)

        # 2. LOCK: Marca licitações como "Processando" (Status 2)
        cursor.execute("""
            UPDATE licitacoes 
            SET notificacao_processada = 2, 
                processamento_inicio = NOW() 
            WHERE notificacao_processada = 0 
            LIMIT 200
        """)
        conn.commit()

        # 3. SELEÇÃO: Pega as licitações travadas para processar agora
        cursor.execute("""
            SELECT id, numeroControlePNCP, objetoCompra, valorTotalEstimado, situacaoReal,
                   unidadeOrgaoUfSigla, unidadeOrgaoMunicipioNome, modalidadeId
            FROM licitacoes 
            WHERE notificacao_processada = 2
        """)
        licitacoes = cursor.fetchall()

        if not licitacoes:
            cursor.close()
            conn.close()
            return # Nada a fazer, dorme

        logger.info(f"Processando lote de {len(licitacoes)} licitações...")
        mensagens_para_enviar = []

        # 4. QUERY DE MATCH (Complexa e Otimizada)
        query_match = """
            SELECT DISTINCT 
                d.token_push, 
                at_inc.termo as termo_match
            FROM preferencias_alertas pa
            JOIN usuarios_status u ON pa.usuario_id = u.id
            JOIN usuarios_dispositivos d ON pa.usuario_id = d.usuario_id
            
            WHERE 
                pa.ativo = 1 
                AND pa.enviar_push = 1
                AND u.is_pro = 1 
                AND u.status_assinatura IN ('active', 'trial', 'grace_period')

                -- 1. Filtro de UF
                AND (
                    NOT EXISTS (SELECT 1 FROM alertas_ufs WHERE alerta_id = pa.id)
                    OR EXISTS (SELECT 1 FROM alertas_ufs au WHERE au.alerta_id = pa.id AND au.uf = %s)
                )

                -- 2. Filtro de Município
                AND (
                    NOT EXISTS (SELECT 1 FROM alertas_municipios WHERE alerta_id = pa.id)
                    OR EXISTS (SELECT 1 FROM alertas_municipios am 
                               WHERE am.alerta_id = pa.id 
                               AND am.municipio_nome = %s)
                )

                -- 3. Filtro de Modalidade
                AND (
                    NOT EXISTS (SELECT 1 FROM alertas_modalidades WHERE alerta_id = pa.id)
                    OR EXISTS (SELECT 1 FROM alertas_modalidades am WHERE am.alerta_id = pa.id AND am.modalidade_id = %s)
                )

                -- 4. Filtro de Termos (Inclusão - Obrigatório)
                AND EXISTS (
                    SELECT 1 FROM alertas_termos at 
                    WHERE at.alerta_id = pa.id 
                    AND at.tipo = 'INCLUSAO'
                    AND INSTR(%s, at.termo) > 0 
                )
                
                -- 5. Filtro de Termos (Exclusão - Proibido)
                AND NOT EXISTS (
                    SELECT 1 FROM alertas_termos at 
                    WHERE at.alerta_id = pa.id 
                    AND at.tipo = 'EXCLUSAO'
                    AND INSTR(%s, at.termo) > 0
                )
                
                LEFT JOIN alertas_termos at_inc ON at_inc.alerta_id = pa.id 
                    AND at_inc.tipo = 'INCLUSAO' 
                    AND INSTR(%s, at_inc.termo) > 0
                LIMIT 1000
        """

        enviados_count = 0

        for lic in licitacoes:
            # Filtro Rápido de Status via Python (Evita enviar coisas canceladas)
            status_real = (lic['situacaoReal'] or "").lower()
            termos_aceitos = ['recebendo proposta', 'a receber']
            
            # Se não contiver nenhum termo aceito, pula envio (mas marca como lido no final)
            if not any(t in status_real for t in termos_aceitos):
                continue 

            # Prepara variáveis
            objeto = (lic['objetoCompra'] or "").lower()
            uf = (lic['unidadeOrgaoUfSigla'] or "")
            municipio = (lic['unidadeOrgaoMunicipioNome'] or "")
            mod_id = lic['modalidadeId']

            # Executa Match
            cursor.execute(query_match, (uf, municipio, mod_id, objeto, objeto, objeto))
            destinatarios = cursor.fetchall()

            for dest in destinatarios:
                token = dest['token_push']
                termo_usado = (dest['termo_match'] or "Licitação").title()
                
                val_est = ""
                if lic['valorTotalEstimado']:
                    val_est = f"R$ {float(lic['valorTotalEstimado']):,.2f}"

                msg = messaging.Message(
                    token=token,
                    notification=messaging.Notification(
                        title=f"{termo_usado} em {municipio}/{uf}",
                        body=f"{val_est}\n{lic['objetoCompra'][:90]}..."
                    ),
                    data={
                        "click_action": "FLUTTER_NOTIFICATION_CLICK",
                        "pncp": str(lic['numeroControlePNCP']),
                        "licitacao_id": str(lic['id']),
                        "tipo": "nova_licitacao"
                    }
                )
                mensagens_para_enviar.append(msg)

        # 5. ENVIO EM LOTE
        if mensagens_para_enviar:
            total_msgs = len(mensagens_para_enviar)
            logger.info(f"Preparando envio de {total_msgs} notificações via Firebase...")
            
            for i in range(0, total_msgs, 500):
                batch = mensagens_para_enviar[i:i+500]
                try:
                    resp = messaging.send_each(batch)
                    enviados_count += resp.success_count
                    if resp.failure_count > 0:
                        logger.warning(f"Firebase Batch: {resp.failure_count} falhas no lote.")
                except Exception as e:
                    logger.error(f"Erro crítico no envio batch Firebase: {e}")

        # 6. FINALIZAÇÃO (Marca como processado)
        ids_processados = [l['id'] for l in licitacoes]
        if ids_processados:
            format_strings = ','.join(['%s'] * len(ids_processados))
            # Reseta processamento_inicio para NULL para liberar espaço
            cursor.execute(f"UPDATE licitacoes SET notificacao_processada = 1, processamento_inicio = NULL WHERE id IN ({format_strings})", tuple(ids_processados))
            conn.commit()
            
            if enviados_count > 0:
                logger.info(f"Ciclo concluído. {len(ids_processados)} licitações processadas. {enviados_count} notificações enviadas.")
            else:
                logger.info(f"Ciclo concluído. {len(ids_processados)} licitações processadas (Sem matches ou status inválido).")

        cursor.close()
        conn.close()

    except Exception as e:
        logger.error(f"Erro no ciclo de processamento: {e}")
        if conn and conn.is_connected():
            conn.close()

if __name__ == "__main__":
    logger.info("Worker iniciado em loop contínuo.")
    while True:
        try:
            processar_notificacoes()
        except KeyboardInterrupt:
            logger.info("Worker interrompido pelo usuário.")
            break
        except Exception as e:
            logger.critical(f"Erro fatal não tratado no loop: {e}")
            time.sleep(30)
        
        time.sleep(10) # Intervalo entre verificações