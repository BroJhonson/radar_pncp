# backend/notificacoes.py
import os
import firebase_admin
from firebase_admin import credentials, messaging
from dotenv import load_dotenv
import mysql.connector
import requests
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

# Firebase Init (Robusto)
if not firebase_admin._apps:
    try:
        # Tenta achar o arquivo em múltiplos lugares
        base_dir = os.path.dirname(os.path.abspath(__file__)) # Pasta atual (backend)
        root_dir = os.path.dirname(base_dir) # Pasta pai (radar-pncp)
        
        caminhos_possiveis = [
            os.path.join(base_dir, 'firebase_credentials.json'),      # ./backend/firebase_credentials.json
            os.path.join(root_dir, 'firebase_credentials.json'),      # ./firebase_credentials.json
            '/var/www/radar-pncp/firebase_credentials.json'           # Caminho absoluto hardcoded (último recurso)
        ]
        
        cred_path = None
        for p in caminhos_possiveis:
            if os.path.exists(p):
                cred_path = p
                break
        
        if not cred_path:
            raise FileNotFoundError(f"Arquivo firebase_credentials.json não encontrado em: {caminhos_possiveis}")

        logger.info(f"Carregando credenciais Firebase de: {cred_path}")
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin inicializado.")
        
    except Exception as e:
        logger.critical(f"ERRO CRÍTICO AO INICIAR FIREBASE: {e}")
        # IMPORTANTE: Se não conectar no Firebase, o script DEVE parar, senão fica em loop de erro
        exit(1)

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('MARIADB_HOST'), user=os.getenv('MARIADB_USER'),
        password=os.getenv('MARIADB_PASSWORD'), database=os.getenv('MARIADB_DATABASE')
    )

# Helper para o corpo de email
# Precisa ainda configurar a ação do click no link. ATENÇÃO!!!
def gerar_html_email(nome_usuario, titulo_licitacao, orgao, valor, municipio, uf, link_pncp, nome_alerta):
    # Cores da sua marca (Ajuste conforme necessário)
    COR_PRIMARIA = "#0056b3" # Azul Finnd
    COR_FUNDO = "#f4f4f7"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
        <style>
            body {{ background-color: {COR_FUNDO}; font-family: sans-serif; -webkit-font-smoothing: antialiased; font-size: 14px; line-height: 1.4; margin: 0; padding: 0; -ms-text-size-adjust: 100%; -webkit-text-size-adjust: 100%; }}
            table {{ border-collapse: separate; mso-table-lspace: 0pt; mso-table-rspace: 0pt; width: 100%; }}
            table td {{ font-family: sans-serif; font-size: 14px; vertical-align: top; }}
            .container {{ display: block; margin: 0 auto !important; max-width: 580px; padding: 10px; width: 580px; }}
            .content {{ box-sizing: border-box; display: block; margin: 0 auto; max-width: 580px; padding: 10px; }}
            .main {{ background: #ffffff; border-radius: 3px; width: 100%; }}
            .wrapper {{ box-sizing: border-box; padding: 20px; }}
            .content-block {{ padding-bottom: 10px; padding-top: 10px; }}
            .footer {{ clear: both; margin-top: 10px; text-align: center; width: 100%; }}
            .footer td, .footer p, .footer span, .footer a {{ color: #999999; font-size: 12px; text-align: center; }}
            h1, h2, h3 {{ color: #000000; font-family: sans-serif; font-weight: 400; line-height: 1.4; margin: 0; margin-bottom: 30px; }}
            h1 {{ font-size: 35px; font-weight: 300; text-align: center; text-transform: capitalize; }}
            p, ul, ol {{ font-family: sans-serif; font-size: 14px; font-weight: normal; margin: 0; margin-bottom: 15px; }}
            .btn {{ box-sizing: border-box; width: 100%; }}
            .btn > tbody > tr > td {{ padding-bottom: 15px; }}
            .btn table {{ width: auto; }}
            .btn table td {{ background-color: #ffffff; border-radius: 5px; text-align: center; }}
            .btn a {{ background-color: #ffffff; border: solid 1px {COR_PRIMARIA}; border-radius: 5px; box-sizing: border-box; color: {COR_PRIMARIA}; cursor: pointer; display: inline-block; font-size: 14px; font-weight: bold; margin: 0; padding: 12px 25px; text-decoration: none; text-transform: capitalize; }}
            .btn-primary table td {{ background-color: {COR_PRIMARIA}; }}
            .btn-primary a {{ background-color: {COR_PRIMARIA}; border-color: {COR_PRIMARIA}; color: #ffffff; }}
            .infos {{ background-color: #f8f9fa; padding: 15px; border-radius: 4px; margin-bottom: 20px; border-left: 4px solid {COR_PRIMARIA}; }}
            .badge {{ background: #e1ecf4; color: {COR_PRIMARIA}; padding: 2px 6px; border-radius: 4px; font-size: 12px; font-weight: bold; }}
        </style>
    </head>
    <body>
        <table role="presentation" border="0" cellpadding="0" cellspacing="0" class="body">
        <tr>
            <td>&nbsp;</td>
            <td class="container">
            <div class="content">
                <table role="presentation" class="main">
                <tr>
                    <td class="wrapper">
                    <table role="presentation" border="0" cellpadding="0" cellspacing="0">
                        <tr>
                        <td>
                            <p>Olá, <strong>{nome_usuario}</strong>!</p>
                            <p>O seu alerta <strong>"{nome_alerta}"</strong> encontrou uma nova oportunidade que pode te interessar.</p>
                            
                            <div class="infos">
                                <p style="margin-bottom: 5px; font-size: 16px;"><strong>{titulo_licitacao}</strong></p>
                                <p style="margin-bottom: 5px;">🏛️ {orgao}</p>
                                <p style="margin-bottom: 5px;">📍 {municipio} - {uf}</p>
                                <p style="margin-bottom: 0px;">💰 <strong>Valor Estimado: {valor}</strong></p>
                            </div>

                            <p>Toque no botão abaixo para ver o edital completo e os anexos diretamente no aplicativo.</p>
                            
                            <table role="presentation" border="0" cellpadding="0" cellspacing="0" class="btn btn-primary">
                            <tbody>
                                <tr>
                                <td align="center">
                                    <table role="presentation" border="0" cellpadding="0" cellspacing="0">
                                    <tbody>
                                        <tr>
                                        <td> <a href="{link_pncp}" target="_blank">Ver Oportunidade no App</a> </td>
                                        </tr>
                                    </tbody>
                                    </table>
                                </td>
                                </tr>
                            </tbody>
                            </table>
                            
                            <p style="font-size: 12px; color: #777;">Se o botão não funcionar, copie o link: {link_pncp}</p>
                        </td>
                        </tr>
                    </table>
                    </td>
                </tr>
                </table>
                <div class="footer">
                <table role="presentation" border="0" cellpadding="0" cellspacing="0">
                    <tr>
                    <td class="content-block">
                        <span class="apple-link">Enviado por Finnd - Licitações</span>
                        <br> Você recebeu este e-mail por causa do alerta "{nome_alerta}".
                    </td>
                    </tr>
                </table>
                </div>
            </div>
            </td>
            <td>&nbsp;</td>
        </tr>
        </table>
    </body>
    </html>
    """
    return html

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

def enviar_email_mailgun(destinatario_email, destinatario_nome, assunto, html_body):
    """Envia o e-mail usando a API do Mailgun"""
    try:
        domain = os.getenv('MAILGUN_DOMAIN')
        api_key = os.getenv('MAILGUN_API_KEY')
        sender = os.getenv('EMAIL_REMETENTE', f'Finnd Alertas <no-reply@{domain}>')
        
        if not domain or not api_key:
            logger.error("Mailgun não configurado no .env")
            return

        response = requests.post(
            f"https://api.mailgun.net/v3/{domain}/messages",
            auth=("api", api_key),
            data={
                "from": sender,
                "to": [destinatario_email],
                "subject": assunto,
                "html": html_body
            },
            timeout=5
        )
        if response.status_code != 200:
            logger.error(f"Erro Mailgun: {response.status_code} - {response.text}")
            
    except Exception as e:
        logger.error(f"Exceção ao enviar email: {e}")

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
                d.tipo as device_type,
                pa.enviar_email,  
                u.email as email_user, 
                u.nome as nome_user,   
                pa.nome_alerta,        
                at_inc.termo as termo_match
            FROM preferencias_alertas pa
            JOIN usuarios_status u ON pa.usuario_id = u.id
            JOIN usuarios_dispositivos d ON pa.usuario_id = d.usuario_id
            
            LEFT JOIN alertas_termos at_inc ON at_inc.alerta_id = pa.id 
                AND at_inc.tipo = 'INCLUSAO' 
                AND INSTR(%s, at_inc.termo) > 0 
            
            WHERE 
                pa.ativo = 1 
                AND (pa.enviar_push = 1 OR pa.enviar_email = 1) -- <--- AGORA PEGA QUEM QUER EMAIL TBM
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
                
            LIMIT 1000
        """

        enviados_count = 0
        
        # Variáveis de controle para não enviar e-mail duplicado
        # (Porque o JOIN com dispositivos pode trazer 3 linhas para o mesmo usuário se ele tiver 3 celulares)
        # Variáveis de controle para não enviar e-mail duplicado no mesmo ciclo
        emails_enviados_neste_ciclo = set()

        for lic in licitacoes:
            # 1. Filtro de Status (Apenas licitações abertas)
            status_real = (lic.get('situacaoReal') or "").lower()
            termos_aceitos = ['recebendo proposta', 'a receber']
            
            if not any(t in status_real for t in termos_aceitos):
                continue 

            # 2. Preparação de dados da licitação
            objeto = (lic.get('objetoCompra') or "").lower()
            uf = (lic.get('unidadeOrgaoUfSigla') or "")
            municipio = (lic.get('unidadeOrgaoMunicipioNome') or "")
            mod_id = lic.get('modalidadeId')
            
            # Formatação de valor
            val_est = f"R$ {float(lic['valorTotalEstimado']):,.2f}" if lic.get('valorTotalEstimado') else "Valor não informado"

            # 3. Executa Match de Usuários
            cursor.execute(query_match, (objeto, uf, municipio, mod_id, objeto, objeto))
            destinatarios = cursor.fetchall()

            for dest in destinatarios:
                # --- LÓGICA DE PUSH NOTIFICATION ---
                # Verifica se há token E se o usuário ativou PUSH para este alerta
                if dest.get('token_push') and dest.get('enviar_push'):
                    termo_usado = (dest.get('termo_match') or "Oportunidade").title()
                    titulo_push = f"{termo_usado} em {municipio}/{uf}"
                    corpo_push = f"{val_est}\n{lic['objetoCompra'][:90]}..."
                    
                    if dest.get('device_type') == 'web_browser':
                        link_destino = f"https://finnd.com.br/licitacao/{lic['numeroControlePNCP']}" 
                        msg = messaging.Message(
                            token=dest['token_push'],
                            notification=messaging.Notification(title=titulo_push, body=corpo_push),
                            webpush=messaging.WebpushConfig(
                                fcm_options=messaging.WebpushFCMOptions(link=link_destino),
                                notification=messaging.WebpushNotification(icon='/static/icons/icon-192x192.png')
                            ),
                            data={"pncp": str(lic['numeroControlePNCP']), "licitacao_id": str(lic['id'])}
                        )
                    else:
                        msg = messaging.Message(
                            token=dest['token_push'],
                            notification=messaging.Notification(title=titulo_push, body=corpo_push),
                            data={
                                "click_action": "FLUTTER_NOTIFICATION_CLICK",
                                "pncp": str(lic['numeroControlePNCP']),
                                "licitacao_id": str(lic['id']),
                                "tipo": "nova_licitacao"
                            }
                        )
                    mensagens_para_enviar.append(msg)

                # --- LÓGICA DE E-MAIL ---
                # Verifica se o usuário ativou EMAIL e se temos o endereço
                if dest.get('enviar_email') and dest.get('email_user'):
                    # Evita duplicidade (caso o user tenha múltiplos dispositivos logados)
                    chave_envio = f"{dest['email_user']}_{lic['id']}"
                    
                    if chave_envio not in emails_enviados_neste_ciclo:
                        emails_enviados_neste_ciclo.add(chave_envio)
                        
                        link_app = f"https://finnd.com.br/licitacao/{lic['numeroControlePNCP']}"
                        
                        html_body = gerar_html_email(
                            nome_usuario=dest.get('nome_user') or "Assinante",
                            titulo_licitacao=lic['objetoCompra'],
                            orgao="Órgão Público", 
                            valor=val_est,
                            municipio=municipio,
                            uf=uf,
                            link_pncp=link_app,
                            nome_alerta=dest.get('nome_alerta') or "Alerta Finnd"
                        )
                        
                        termo_email = (dest.get('termo_match') or "Oportunidade").title()
                        assunto = f"🎯 Nova Licitação encontrada: {termo_email}"
                        
                        enviar_email_mailgun(
                            destinatario_email=dest['email_user'],
                            destinatario_nome=dest['nome_user'],
                            assunto=assunto,
                            html_body=html_body
                        )
                
                """
                Envio de emails está dentro do loop. Para começar (até uns 1.000 e-mails por dia), isso roda tranquilo. O requests.post leva cerca de 0.5s.
                Se você escalar para 100.000 usuários, esse loop vai ficar lento. Nesse caso futuro, você não enviaria o e-mail aqui. 
                Você apenas salvaria numa tabela fila_emails e teria outro script só para disparar e-mails. 
                Mas para agora, faça direto no loop que funciona perfeitamente.
                """

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