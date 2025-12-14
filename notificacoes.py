# backend/worker_notificacoes.py (Versão 2.0 - Com filtro de Status e Município)
import os
import firebase_admin
from firebase_admin import credentials, messaging
from dotenv import load_dotenv
import mysql.connector
import logging
import time

load_dotenv()

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Firebase Init
if not firebase_admin._apps:
    cred_path = os.path.join(os.path.dirname(__file__), 'firebase_credentials.json')
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('MARIADB_HOST'), user=os.getenv('MARIADB_USER'),
        password=os.getenv('MARIADB_PASSWORD'), database=os.getenv('MARIADB_DATABASE')
    )

def resgatar_zumbis(cursor, conn):  # Função para resgatar licitações travadas
    """
    Faxina de segurança: Procura licitações travadas no status 2
    há mais de 15 minutos (crash do script) e reseta para 0.
    """
    try:
        # Define o tempo limite (ex: 15 minutos atrás)
        # Se uma notificação demora mais que 15min para ser enviada, algo deu errado.
        cursor.execute("""
            UPDATE licitacoes 
            SET notificacao_processada = 0, -- Volta para a fila
                processamento_inicio = NULL 
            WHERE notificacao_processada = 2 
            AND processamento_inicio < DATE_SUB(NOW(), INTERVAL 15 MINUTE)
        """)
        
        afetados = cursor.rowcount
        if afetados > 0:
            conn.commit()
            logger.warning(f"🧟 ZUMBIS RESGATADOS: {afetados} licitações travadas foram resetadas.")
            
    except Exception as e:
        logger.error(f"Erro ao resgatar zumbis: {e}")

def processar_notificacoes():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # --- NOVO: RODA O RESGATE ANTES DE TUDO ---
    resgatar_zumbis(cursor, conn)

    # 1. LOCK: Marca licitações como "Processando" (Status 2)
    # Pega até 200 por vez para não sobrecarregar
    cursor.execute("""
        UPDATE licitacoes 
        SET notificacao_processada = 2, 
            processamento_inicio = NOW() 
        WHERE notificacao_processada = 0 
        LIMIT 200
    """)
    conn.commit()

    # 2. SELEÇÃO: Pega os dados das licitações travadas
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
        return

    logger.info(f"Analisando lote de {len(licitacoes)} licitações...")
    mensagens_para_enviar = []

    # 3. QUERY DE BUSCA REVERSA (Atualizada com Município)
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
            AND u.status_assinatura IN ('active', 'trial')

            -- 1. Filtro de UF
            AND (
                NOT EXISTS (SELECT 1 FROM alertas_ufs WHERE alerta_id = pa.id)
                OR EXISTS (SELECT 1 FROM alertas_ufs au WHERE au.alerta_id = pa.id AND au.uf = %s)
            )

            -- 2. Filtro de Município (NOVO!)
            -- Se o usuário não cadastrou municípios, ele quer o estado todo (NOT EXISTS)
            -- Se cadastrou, a licitação tem que ser de um desses municípios (EXISTS)
            AND (
                NOT EXISTS (SELECT 1 FROM alertas_municipios WHERE alerta_id = pa.id)
                OR EXISTS (SELECT 1 FROM alertas_municipios am 
                           WHERE am.alerta_id = pa.id 
                           AND am.municipio_nome = %s) -- Compara string exata (ou ajuste para LIKE se preferir)
            )

            -- 3. Filtro de Modalidade
            AND (
                NOT EXISTS (SELECT 1 FROM alertas_modalidades WHERE alerta_id = pa.id)
                OR EXISTS (SELECT 1 FROM alertas_modalidades am WHERE am.alerta_id = pa.id AND am.modalidade_id = %s)
            )

            -- 4. Filtro de Termos (Inclusão - Obrigatório ter 1)
            AND EXISTS (
                SELECT 1 FROM alertas_termos at 
                WHERE at.alerta_id = pa.id 
                AND at.tipo = 'INCLUSAO'
                AND INSTR(%s, at.termo) > 0 
            )
            
            -- 5. Filtro de Termos (Exclusão - Não pode ter nenhum)
            AND NOT EXISTS (
                SELECT 1 FROM alertas_termos at 
                WHERE at.alerta_id = pa.id 
                AND at.tipo = 'EXCLUSAO'
                AND INSTR(%s, at.termo) > 0
            )
            
            -- Join para pegar o termo que deu match (para o título do push)
            LEFT JOIN alertas_termos at_inc ON at_inc.alerta_id = pa.id 
                AND at_inc.tipo = 'INCLUSAO' 
                AND INSTR(%s, at_inc.termo) > 0
            LIMIT 1000
    """

    for lic in licitacoes:
        # --- A. FILTRO DE STATUS (Evita notificar coisa velha/cancelada) ---
        # Ajuste essa lista conforme os status exatos do PNCP
        status_valido = False
        status_real = (lic['situacaoReal'] or "").lower()
        
        # Termos que indicam que vale a pena avisar
        termos_aceitos = ['a receber/recebendo proposta', 'recebendo proposta']
        
        for termo in termos_aceitos:
            if termo in status_real:
                status_valido = True
                break
        
        # Se o status for ruim (ex: "Fracassada", "Cancelada"), pulamos o envio
        # Mas ela continuará no fluxo para ser marcada como 'processada' no final
        if not status_valido:
            continue 

        # --- B. PREPARAÇÃO DADOS ---
        objeto = (lic['objetoCompra'] or "").lower()
        uf = (lic['unidadeOrgaoUfSigla'] or "")
        municipio = (lic['unidadeOrgaoMunicipioNome'] or "") # Importante manter case original ou padronizar
        mod_id = lic['modalidadeId']

        # --- C. EXECUTA O MATCH ---
        # Parâmetros: UF, MUNICIPIO, MOD_ID, OBJETO, OBJETO, OBJETO
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
                    body=f"{status_real.title()} | {val_est}\n{lic['objetoCompra'][:80]}..."
                ),
                data={
                    "click_action": "FLUTTER_NOTIFICATION_CLICK",
                    "pncp": str(lic['numeroControlePNCP']),
                    "licitacao_id": str(lic['id'])
                }
            )
            mensagens_para_enviar.append(msg)

    # 4. ENVIO EM LOTE
    if mensagens_para_enviar:
        logger.info(f"Enviando {len(mensagens_para_enviar)} notificações...")
        # Lotes de 500 (Limite Firebase)
        for i in range(0, len(mensagens_para_enviar), 500):
            try:
                messaging.send_each(mensagens_para_enviar[i:i+500])
            except Exception as e:
                logger.error(f"Erro batch: {e}")

    # 5. FINALIZAÇÃO
    # Marca TODAS as licitações lidas (mesmo as de status inválido) como processadas
    ids_processados = [l['id'] for l in licitacoes]
    if ids_processados:
        format_strings = ','.join(['%s'] * len(ids_processados))
        cursor.execute(f"UPDATE licitacoes SET notificacao_processada = 1, processamento_inicio = NULL WHERE id IN ({format_strings})", tuple(ids_processados))
        conn.commit()

    cursor.close()
    conn.close()

if __name__ == "__main__":
    while True:
        try:
            processar_notificacoes()
        except Exception as e:
            logger.error(f"Erro fatal no loop: {e}")
            # Importante: Se der erro de conexão DB, espera um pouco mais
            time.sleep(30)
        
        time.sleep(10)