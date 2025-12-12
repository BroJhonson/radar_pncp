# backend/worker_notificacoes.py
import os
import firebase_admin
from firebase_admin import credentials, messaging
from dotenv import load_dotenv
import mysql.connector
import logging

load_dotenv()

# LOGS
LOG_PATH = os.path.join(os.path.dirname(__file__), '../logs/notificacoes.log')
# Garante que a pasta existe
if not os.path.exists(os.path.dirname(LOG_PATH)):
    os.makedirs(os.path.dirname(LOG_PATH))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - WORKER - %(message)s',
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# FIREBASE INIT
if not firebase_admin._apps:
    try:
        cred_path = os.path.join(os.path.dirname(__file__), '../firebase_credentials.json')
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        logger.critical(f"ERRO CRÍTICO FIREBASE: {e}")
        exit(1)

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('MARIADB_HOST'),
        user=os.getenv('MARIADB_USER'),
        password=os.getenv('MARIADB_PASSWORD'),
        database=os.getenv('MARIADB_DATABASE')
    )

def verificar_match_complexo(licitacao, alerta):
    """
    Verifica se a licitação atende a TODOS os critérios do alerta (AND).
    Dentro de cada critério (UF, Modalidade) é (OR).
    """

    # 1. STATUS (Deve estar aberta)
    # Lógica: Se status for diferente de recebendo proposta, rejeita.
    status_real = (licitacao['situacaoReal'] or "").lower()
    if "recebendo proposta" not in status_real:
        return False

    # 2. LOCALIZAÇÃO (UF) - Multi-seleção
    # Alerta pode ter "BA,SP". Licitação tem "BA". (BA está em BA,SP? Sim)
    if alerta['uf']:
        lic_uf = (licitacao['unidadeOrgaoUfSigla'] or "").strip().upper()
        # Cria lista ['BA', 'SP']
        ufs_alvo = [u.strip().upper() for u in alerta['uf'].split(',') if u.strip()]
        if lic_uf not in ufs_alvo:
            return False

    # 3. LOCALIZAÇÃO (MUNICÍPIO) - Multi-seleção
    if alerta['municipio']:
        lic_muni = (licitacao['unidadeOrgaoMunicipioNome'] or "").strip().lower()
        munis_alvo = [m.strip().lower() for m in alerta['municipio'].split(',') if m.strip()]
        # Nota: Comparação exata de string. Idealmente normalizar acentos se possível, mas direto funciona bem se os dados do IBGE forem padronizados.
        if lic_muni not in munis_alvo:
            return False

    # 4. MODALIDADES - Multi-seleção
    # O app pode salvar IDs (1, 2) ou Nomes (Pregão). Vamos comparar o que vier.
    if alerta['modalidades']:
        lic_mod_id = str(licitacao.get('modalidadeId', ''))
        lic_mod_nome = (licitacao.get('modalidadeNome', '') or "").lower()
        
        mods_alvo = [m.strip().lower() for m in alerta['modalidades'].split(',') if m.strip()]
        
        # Match se bater ID ou se bater Nome (contido)
        match_mod = False
        for mod in mods_alvo:
            if mod == lic_mod_id or mod in lic_mod_nome:
                match_mod = True
                break
        
        if not match_mod:
            return False

    # 5. TERMOS INCLUSÃO (Texto - OR)
    lic_objeto = (licitacao['objetoCompra'] or "").lower()
    
    if not alerta['termos_inclusao']:
        return False # Regra de segurança: alerta sem termo é ignorado
    
    termos_inc = [t.strip().lower() for t in alerta['termos_inclusao'].split(',') if t.strip()]
    
    # Verifica se ALGUM termo está presente no objeto
    if not any(t in lic_objeto for t in termos_inc):
        return False

    # 6. TERMOS EXCLUSÃO (Texto - NOT OR)
    if alerta['termos_exclusao']:
        termos_exc = [t.strip().lower() for t in alerta['termos_exclusao'].split(',') if t.strip()]
        # Verifica se ALGUM termo proibido está presente
        if any(t in lic_objeto for t in termos_exc):
            return False

    # Passou por tudo!
    return True

def processar_notificacoes():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # A. Busca Pendentes (Limit 300 por ciclo para segurança)
    query_lic = """
        SELECT id, numeroControlePNCP, objetoCompra, situacaoReal, 
               unidadeOrgaoUfSigla, unidadeOrgaoMunicipioNome, valorTotalEstimado,
               modalidadeId, modalidadeNome
        FROM licitacoes 
        WHERE notificacao_processada = 0
        LIMIT 300
    """
    cursor.execute(query_lic)
    licitacoes = cursor.fetchall()

    if not licitacoes:
        logger.info("Nenhuma licitação pendente.")
        cursor.close()
        conn.close()
        return

    # B. Busca Alertas Ativos (E seus tokens)
    query_alertas = """
        SELECT pa.nome_alerta, pa.uf, pa.municipio, pa.modalidades, 
               pa.termos_inclusao, pa.termos_exclusao,
               d.token_push
        FROM preferencias_alertas pa
        JOIN usuarios_dispositivos d ON pa.usuario_id = d.usuario_id
        JOIN usuarios_status u ON pa.usuario_id = u.id
        WHERE pa.ativo = 1 
          AND pa.enviar_push = 1 
          AND d.token_push IS NOT NULL
          
          -- REGRA CRÍTICA: Só envia se for PRO e assinatura estiver ok
          AND u.is_pro = 1 
          AND (u.status_assinatura = 'active' OR u.status_assinatura = 'trial')
    """
    cursor.execute(query_alertas)
    alertas = cursor.fetchall()

    logger.info(f"Processando: {len(licitacoes)} licitações vs {len(alertas)} alertas.")
    
    mensagens = []

    # C. Cruzamento
    for lic in licitacoes:
        for alerta in alertas:
            if verificar_match_complexo(lic, alerta):
                # Personalização da Mensagem
                uf = lic['unidadeOrgaoUfSigla'] or "BR"
                municipio = lic['unidadeOrgaoMunicipioNome'] or ""
                valor = "R$ 0,00"
                if lic['valorTotalEstimado']:
                    try:
                        valor = f"R$ {float(lic['valorTotalEstimado']):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    except: pass
                
                # Tenta pegar o termo que deu match para o título ficar chamativo
                # Ex: Se user quer "Trator, Pneu" e licitação tem "Pneu", título vira "Pneu..."
                termos_inc = [t.strip().title() for t in alerta['termos_inclusao'].split(',')]
                titulo_prefixo = termos_inc[0] # Pega o primeiro por padrão
                
                msg = messaging.Message(
                    token=alerta['token_push'],
                    notification=messaging.Notification(
                        title=f"{titulo_prefixo} em {municipio}/{uf}",
                        body=f"{lic['objetoCompra'][:100]}...\n{valor}"
                    ),
                    data={
                        "click_action": "FLUTTER_NOTIFICATION_CLICK",
                        "tipo": "nova_licitacao",
                        "licitacao_id": str(lic['id']),
                        "pncp": str(lic['numeroControlePNCP'])
                    }
                )
                mensagens.append(msg)

    # D. Envio em Massa
    if mensagens:
        try:
            # Envia em lotes de 500 (limite Firebase)
            total = len(mensagens)
            logger.info(f"Enviando {total} notificações...")
            
            for i in range(0, total, 500):
                batch = mensagens[i:i+500]
                response = messaging.send_each(batch)
                logger.info(f"Lote {i}: {response.success_count} enviados, {response.failure_count} falhas.")
                
        except Exception as e:
            logger.error(f"Erro envio Firebase: {e}")

    # E. Atualiza Flag (Sempre, mesmo se não enviou nada)
    ids = [l['id'] for l in licitacoes]
    if ids:
        format_str = ','.join(['%s'] * len(ids))
        cursor.execute(f"UPDATE licitacoes SET notificacao_processada = 1 WHERE id IN ({format_str})", tuple(ids))
        conn.commit()

    cursor.close()
    conn.close()

if __name__ == "__main__":
    processar_notificacoes()