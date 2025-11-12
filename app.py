import mysql.connector 
from mysql.connector import errors # Para tratamento de erros
# Importações para usuarios e admin
from flask_admin import Admin, BaseView, expose, AdminIndexView
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user
from flask_bcrypt import Bcrypt
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, Response
import requests  # Para chamar a API do IBGE
from markupsafe import Markup, escape
from functools import wraps
import shlex  # biblioteca padrão que entende aspas em strings
# Para envio de e-mail
import smtplib
from email.mime.text import MIMEText
from pydantic import BaseModel, EmailStr, ValidationError
import os  # Para ler variáveis de ambiente
from dotenv import load_dotenv  # Para carregar o arquivo .env
import csv #Esse e os tres de baixo são para o upload de arquivos CSV
import io
import re
from flask import Response
import time
from datetime import datetime, date
import bleach
from flask_cors import CORS
from flask_caching import Cache
import logging
from logging.handlers import RotatingFileHandler # Para log rotate
from decimal import Decimal # Para manipular números decimais do banco
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
load_dotenv()  # Carrega as variáveis do arquivo .env para o ambiente

# --- Configurações ---
app = Flask(__name__, template_folder='templates') # O template_folder agora aponta para 'backend/templates/'

# --- Definição do Schema de Validação (Pydantic) ---
class ContatoSchema(BaseModel):
    nome_contato: str
    email_usuario: EmailStr # Valida automaticamente se é um e-mail
    assunto_contato: str
    mensagem_contato: str

# --- CONFIGURAÇÃO DO CACHE ---
# Configura o cache para usar Redis, com um timeout padrão de 1 hora (3600 segundos)
cache = Cache(app, config={
    'CACHE_TYPE': 'RedisCache',
    'CACHE_REDIS_URL': 'redis://localhost:6379/0',
    'CACHE_DEFAULT_TIMEOUT': 10800 # 3600 # (Segundos) Equivale a 1 hora - Mas vou deixar 3 horas nessa porra
})

# --- CONFIGURAÇÃO DE LOGGING PARA A APLICAÇÃO FLASK ---
# Garante que o diretório de logs exista
if not os.path.exists('logs'):
    os.mkdir('logs')

# Cria um handler que rotaciona os arquivos de log
# Manterá 5 arquivos de 10MB cada. Quando o log atual atinge 10MB,
# ele é renomeado para app.log.1 e um novo app.log é criado.
file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240000, backupCount=5)

# Define o formato do log
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))

# Define o nível do log
file_handler.setLevel(logging.INFO) # Em produção, INFO é um bom nível. Para depurar, use logging.DEBUG

# Adiciona o handler ao logger da aplicação Flask
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)

app.logger.info('Aplicação Radar PNCP iniciada')
# --- FIM DA CONFIGURAÇÃO DE LOGGING ---

# --- INÍCIO DA CONFIGURAÇÃO DO RATE LIMITER ---
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"], # Limite padrão para todas as rotas
    storage_uri="redis://localhost:6379" # Use 'memory://' ou configure um Redis
)
# --- FIM DA CONFIGURAÇÃO DO RATE LIMITER ---

# Chave secreta para sessões e flash messages
app.secret_key = os.getenv('FLASK_SECRET_KEY')
if not app.secret_key:    
    message = "ERRO CRÍTICO DE CONFIGURAÇÃO: A variável de ambiente FLASK_SECRET_KEY não está definida. A aplicação não pode iniciar de forma segura."
    app.logger.critical(message) # O logger do Flask pode não estar totalmente pronto aqui, mas tentamos.
    # Para garantir que a mensagem apareça e a aplicação pare:
    import sys
    sys.stderr.write(message + "\n")
    raise ValueError(message) # Impede que a aplicação continue sem a chave.
# Se chegou até aqui, a app.secret_key foi carregada com sucesso.
app.logger.info("FLASK_SECRET_KEY carregada com sucesso do ambiente.")

### Configuração de CORS baseada no ambiente ###
AMBIENTE = os.getenv('AMBIENTE', 'desenvolvimento')

if AMBIENTE == 'producao':
    # Pega a string do .env e a transforma em uma lista de URLs
    allowed_origins_str = os.getenv('FRONTEND_URL_PROD', '')
    allowed_origins = allowed_origins_str.split(',')
else:
    # Em desenvolvimento, permita o acesso do servidor de dev do frontend
    allowed_origins = os.getenv('FRONTEND_URL_DEV', 'http://localhost:3000')

# Habilita o CORS apenas para as rotas da API pública, permitindo que o frontend faça requisições
# A área /admin não precisa de CORS pois será acessada diretamente no mesmo domínio do backend.
CORS(app, resources={r"/api/.*": {"origins": allowed_origins}})

# Configurações de segurança e login
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' # Redireciona para a rota 'login' se não estiver logado
login_manager.login_message = "Por favor, faça login para acessar esta página."
login_manager.login_message_category = "info"


# --- Função Auxiliares e de Conecção para o Banco de Dados ---
def get_db_connection(max_retries=3, delay=2):
    """
    Retorna uma conexão com o banco de dados MariaDB com retry automático
    para erros de conexão.
    """
    attempt = 0
    while attempt < max_retries:
        try:
            conn = mysql.connector.connect(
                host=os.getenv('MARIADB_HOST'),
                user=os.getenv('MARIADB_USER'),
                password=os.getenv('MARIADB_PASSWORD'),
                database=os.getenv('MARIADB_DATABASE')
            )
            return conn
        except (errors.InterfaceError, errors.OperationalError) as err:
            # Problema de rede ou servidor indisponível → vale a pena tentar de novo
            app.logger.warning(
                f"Tentativa {attempt+1}/{max_retries} falhou (erro de conexão): {err}"
            )
            attempt += 1
            time.sleep(delay)
        except errors.ProgrammingError as err:
            # Erro de credenciais, banco inexistente, etc → retry não resolve
            app.logger.error(f"Erro de programação (credenciais/SQL inválido): {err}")
            break
        except errors.IntegrityError as err:
            # Violação de constraint (chave duplicada, FK inválida) → retry não resolve
            app.logger.error(f"Erro de integridade: {err}")
            break
        except mysql.connector.Error as err:
            # Qualquer outro erro inesperado
            app.logger.error(f"Erro inesperado no MariaDB: {err}")
            break
    app.logger.error("Falha ao conectar ao banco de dados após múltiplas tentativas.")
    return None

def with_db_cursor(func):
    """
    Decorator para gerenciar automaticamente conexões e cursores de banco de dados
    para rotas de API (leitura) que retornam JSON.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            if not conn:
                app.logger.error(f"Falha de conexão em {func.__name__}")
                return jsonify(erro="Falha de conexão com o banco de dados."), 503
            
            # Passa o cursor para a função
            cursor = conn.cursor(dictionary=True)
            return func(cursor=cursor, *args, **kwargs)
            
        except mysql.connector.Error as err:
            app.logger.error(f"Erro de DB em {func.__name__}: {err}")
            # Não precisa de rollback() pois é para rotas GET (leitura)
            return jsonify(erro="Erro interno no banco de dados."), 500
        except Exception as e:
            app.logger.error(f"Erro inesperado em {func.__name__}: {e}")
            return jsonify(erro="Erro interno inesperado no servidor."), 500
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
    return wrapper

# --- Função para formatar um dicionário para JSON (datas e números) ---
def formatar_para_json(dicionario):
    """Converte objetos date/datetime para strings e Decimal para float/int."""
    if dicionario is None:
        return None
    
    for key, value in dicionario.items():
        # Tratamento de datas (como você já fazia)
        if isinstance(value, (datetime, date)):
            dicionario[key] = value.isoformat()
        # NOVO: Tratamento de números decimais
        elif isinstance(value, Decimal):
            # Converte Decimal para float
            float_value = float(value)
            # Se o número for inteiro (ex: 1.0000), converte para int (1)
            if float_value.is_integer():
                dicionario[key] = int(float_value)
            # Senão, mantém como float (ex: 123.45)
            else:
                dicionario[key] = float_value
                
    return dicionario


# --- Função para gerar slugs únicos ---
def generate_unique_slug(conn, base_slug, table='posts'):
    cursor = conn.cursor()
    slug = base_slug
    counter = 1
    while True:
        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE slug = %s", (slug,))
        if cursor.fetchone()[0] == 0:
            break
        slug = f"{base_slug}-{counter}"
        counter += 1
    cursor.close()
    return slug


# --- Filtro personalizado nl2br para quebra de linha ---
def nl2br_filter(value):
    if value is None:
        return ''
    # Escapa o HTML para segurança, substitui \n por <br>\n, e marca como Markup seguro
    return Markup(str(escape(value)).replace('\n', '<br>\n'))

app.jinja_env.filters['nl2br'] = nl2br_filter  # Registra o filtro


#   CONFIGURAÇÃO DO USUÁRIO PARA FLASK-LOGIN
class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

@login_manager.user_loader
def load_user(user_id):
    """Carrega um usuário do banco de dados com base no ID da sessão."""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return None
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuarios WHERE id = %s", (user_id,))
        user_data = cursor.fetchone()
        
        if user_data:
            return User(id=user_data['id'], username=user_data['username'], password_hash=user_data['password_hash'])
        return None
    except mysql.connector.Error as err:
        app.logger.error(f"Erro ao carregar usuário: {err}")
        return None
    finally:
        if conn and conn.is_connected():
            if 'cursor' in locals():
                cursor.close()
            conn.close()


# =========================================================================
# ROTAS DE AUTENTICAÇÃO E ADMINISTRAÇÃO de USUÁRIOS
# =========================================================================
@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute") # Limite específico para esta rota (previne força bruta)
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        conn = get_db_connection()
        if not conn:
            flash("Erro de conexão com o banco de dados.", "danger")
            return render_template('login.html', page_title="Login")

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuarios WHERE username = %s", (username,))
        user_data = cursor.fetchone()
        cursor.close()
        conn.close()

        if user_data and bcrypt.check_password_hash(user_data['password_hash'], password):
            user = User(id=user_data['id'], username=user_data['username'], password_hash=user_data['password_hash'])
            login_user(user)
            return redirect(url_for('admin.index'))
        else:
            flash('Login inválido.', 'danger')
    
    # Lembre-se de mover seu login.html para templates/admin/
    return render_template('login.html', page_title="Login")

@app.route('/logout')
def logout():
    logout_user()
    flash('Você foi desconectado.', 'info')
    return redirect(url_for('login'))

# =========================================================================
# Tratamento de erros agora retorna JSON para a API
@app.errorhandler(404)
def pagina_nao_encontrada(e):
    # 1. Rotas da API → sempre retornam JSON
    if request.path.startswith('/api/'):
        return jsonify({"erro": "Recurso não encontrado","status_code": 404}), 404

    # 2. Rotas do Admin → renderizam o template de admin com a variável necessária
    if request.path.startswith('/admin'):
        return render_template('admin/404.html', admin_base_template=admin_base_template), 404

    # 3. Outras rotas (/, /.env, etc.) → retornam JSON para evitar spam de bots
    return jsonify({"erro": "Página não encontrada", "status_code": 404}), 404

@app.errorhandler(500)
def erro_interno_servidor(e):
    logging.error(f"Erro 500: {e} na URL: {request.url}")
    # Para a API, sempre retorne JSON
    if request.path.startswith('/api/'):
        return jsonify(erro="Erro interno no servidor"), 500
    # Para o /admin
    return render_template('admin/500.html'), 500

# --- Rota para Processar o Formulário de Contato ---
@app.route('/api/contato', methods=['POST'])
@limiter.limit("5 per hour") # Limite específico para esta rota (previne spam)
def api_processar_contato():
    data = request.json

    # Validação dos dados usando Pydantic. a ideia é garantir que os dados estejam corretos antes de prosseguir, alem de evitar injeção de código.
    try:
        # 1. Valida os dados de entrada usando o schema
        contato_data = ContatoSchema(**data)
        
        # 2. Usa os dados validados e limpos
        nome = contato_data.nome_contato
        email_usuario = contato_data.email_usuario # Agora é garantido ser um e-mail válido
        assunto = contato_data.assunto_contato
        mensagem = contato_data.mensagem_contato

    except ValidationError as e:
        # Se a validação falhar, retorna um erro 400 claro
        app.logger.warning(f"API Contato: Falha de validação. Dados: {data}. Erro: {e.errors()}")
        return jsonify({'status': 'erro', 'mensagem': 'Dados inválidos.', 'detalhes': e.errors()}), 400
    # --- FIM DA VALIDAÇÃO ---

    email_remetente = os.getenv('EMAIL_REMETENTE')
    senha_remetente = os.getenv('SENHA_EMAIL_REMETENTE')
    email_destinatario = os.getenv('EMAIL_DESTINATARIO_FEEDBACK')

    if not all([email_remetente, senha_remetente, email_destinatario]):
        logging.error("API Contato: Variáveis de ambiente para e-mail não configuradas.")
        return jsonify({'status': 'erro', 'mensagem': 'Erro técnico no servidor.'}), 500

    corpo_email = f"Nome: {nome}\nE-mail: {email_usuario}\nAssunto: {assunto}\n\nMensagem:\n{mensagem}"
    msg = MIMEText(corpo_email)
    msg['Subject'] = f'Novo Contato Radar PNCP: {assunto}'
    msg['From'] = email_remetente
    msg['To'] = email_destinatario
    msg.add_header('reply-to', email_usuario)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(email_remetente, senha_remetente)
            server.sendmail(email_remetente, email_destinatario, msg.as_string())
        return jsonify({'status': 'sucesso', 'mensagem': 'Mensagem enviada com sucesso!'}), 200
    except Exception as e:
        logging.error(f"API Contato: Erro ao enviar e-mail: {e}")
        return jsonify({'status': 'erro', 'mensagem': 'Não foi possível enviar a mensagem.'}), 500

 
# ===========================================---- ROTAS BACKEND (API Principal) ----============================================ #
def _build_licitacoes_query(filtros):
    """
    Constrói a cláusula WHERE para MariaDB, com busca case-insensitive.
    """
    condicoes_db = []
    parametros_db = []
    status_radar = filtros.get('statusRadar')

    # --- Filtros normais (status, datas, etc.) ---
    if status_radar and status_radar.upper() != 'TODOS':
        condicoes_db.append("situacaoReal = %s")
        parametros_db.append(status_radar)
    elif filtros.get('statusId') is not None:
        condicoes_db.append("situacaoCompraId = %s")
        parametros_db.append(filtros['statusId'])

    if filtros.get('ufs'):
        placeholders = ', '.join(['%s'] * len(filtros['ufs']))
        condicoes_db.append(f"unidadeOrgaoUfSigla IN ({placeholders})")
        parametros_db.extend([uf.upper() for uf in filtros['ufs']])

    if filtros.get('modalidadesId'):
        placeholders = ', '.join(['%s'] * len(filtros['modalidadesId']))
        condicoes_db.append(f"modalidadeId IN ({placeholders})")
        parametros_db.extend(filtros['modalidadesId'])

    if filtros.get('dataPubInicio'):
        condicoes_db.append("dataPublicacaoPncp >= %s")
        parametros_db.append(filtros['dataPubInicio'])
    if filtros.get('dataPubFim'):
        condicoes_db.append("dataPublicacaoPncp <= %s")
        parametros_db.append(filtros['dataPubFim'])

    if filtros.get('valorMin') is not None:
        condicoes_db.append("valorTotalEstimado >= %s")
        parametros_db.append(filtros['valorMin'])
    if filtros.get('valorMax') is not None:
        condicoes_db.append("valorTotalEstimado <= %s")
        parametros_db.append(filtros['valorMax'])

    if filtros.get('dataAtualizacaoInicio'):
        condicoes_db.append("dataAtualizacao >= %s")
        parametros_db.append(filtros['dataAtualizacaoInicio'])
    if filtros.get('dataAtualizacaoFim'):
        condicoes_db.append("dataAtualizacao <= %s")
        parametros_db.append(filtros['dataAtualizacaoFim'])

    if filtros.get('municipiosNome'):
        placeholders = ', '.join(['%s'] * len(filtros['municipiosNome']))
        condicoes_db.append(f"unidadeOrgaoMunicipioNome IN ({placeholders})")
        parametros_db.extend(filtros['municipiosNome'])

    if filtros.get('anoCompra') is not None:
        condicoes_db.append("anoCompra = %s")
        parametros_db.append(filtros['anoCompra'])
    if filtros.get('cnpjOrgao'):
        condicoes_db.append("orgaoEntidadeCnpj = %s")
        parametros_db.append(filtros['cnpjOrgao'])

    
    # --- Filtros de Texto com FULLTEXT SEARCH (Lógica OU e Exclusão) ---
    search_terms = []

    # 🔍 Inclusão
    if filtros.get('palavrasChave'):
        # Exemplo recebido: 'curso empresa "escritorio de advocacia"'
        palavras_str = filtros['palavrasChave']
        # Usa shlex para quebrar respeitando aspas
        termos = shlex.split(palavras_str)
        # Adiciona aspas de novo em frases (para FULLTEXT exato)
        search_terms.extend([
            f'"{t}"' if ' ' in t else t for t in termos
        ])

    # 🔍 Exclusão
    if filtros.get('excluirPalavra'):
        palavras_str = filtros['excluirPalavra']
        termos = shlex.split(palavras_str)
        search_terms.extend([
            f'-"{t}"' if ' ' in t else f'-{t}' for t in termos
        ])

    # Se houver qualquer termo de busca (inclusão ou exclusão), montamos a query
    if search_terms:
        # --- SANITIZAÇÃO DE CARACTERES ---
        # Regex de caracteres NÃO permitidos.
        # Remove tudo que NÃO for:
        #   0-9a-zA-Zá-úÁ-ÚçÇ (letras, números, acentos)
        #   \-+ (operadores FTS)
        #   espaço ( )
        #   @\./_ (separadores comuns)
        #   " (para frases exatas)        
        invalid_chars_regex = r'[^0-9a-zA-Zá-úÁ-ÚçÇ\-\+ @\./_"]'

        # Limpa CADA termo individualmente
        sanitized_terms = [re.sub(invalid_chars_regex, '', term) for term in search_terms]

        # Junta os termos JÁ LIMPOS e filtrados de entradas vazias
        match_string = ' '.join(sanitized_terms).strip()

        if match_string:
            campos_fts = "objetoCompra, orgaoEntidadeRazaoSocial, unidadeOrgaoNome, orgaoEntidadeCnpj"
            condicoes_db.append(
                f"MATCH({campos_fts}) AGAINST (%s IN BOOLEAN MODE)"
            )
            parametros_db.append(match_string)

    query_where = ""
    if condicoes_db:
        query_where = " WHERE " + " AND ".join(condicoes_db)

    # lOG DE DEBUG DA QUERY CONSTRUÍDA (Saber qual foi a URL e os parâmetros)
    app.logger.info(f"Query Construída: WHERE = '{query_where}'")
    app.logger.info(f"Parâmetros da Query: {parametros_db}")
    
    return query_where, parametros_db

@app.route('/api/licitacoes', methods=['GET'])
@cache.cached(timeout=10800, query_string=True)   # Cacheia a resposta por 3 horas, considerando os parâmetros da query string. Mudar depois para "timeout=900" quando tiver muitos usuários
def get_licitacoes():
    # 1. Coleta e valida os parâmetros de paginação/ordenação
    pagina = request.args.get('pagina', default=1, type=int)
    por_pagina = request.args.get('porPagina', default=20, type=int)
    orderBy_param = request.args.get('orderBy', default='dataAtualizacao', type=str)
    orderDir_param = request.args.get('orderDir', default='DESC', type=str).upper()

    if pagina < 1:
        pagina = 1
    if por_pagina not in [10, 20, 50, 100]:
        por_pagina = 20

    campos_validos_ordenacao = [
        'dataPublicacaoPncp', 'dataAtualizacao', 'valorTotalEstimado',
        'dataAberturaProposta', 'dataEncerramentoProposta', 'modalidadeNome',
        'orgaoEntidadeRazaoSocial', 'unidadeOrgaoMunicipioNome', 'situacaoReal'
    ]
    if orderBy_param not in campos_validos_ordenacao:
        return jsonify({"erro": "Parâmetro de ordenação inválido."}), 400
    if orderDir_param not in ['ASC', 'DESC']:
        return jsonify({"erro": "Parâmetro de direção de ordenação inválido."}), 400

    # 2. Coleta todos os filtros em um único dicionário
    # Função auxiliar para limpar e dividir a string
    def parse_lista_param(param_name):
        value = request.args.get(param_name, '')
        # Primeiro, divide pela vírgula. Depois, remove espaços de cada item.
        # E por fim, filtra quaisquer itens que ficaram vazios.
        return [item.strip() for item in value.split(',') if item.strip()]

    filtros = {
        'ufs': parse_lista_param('uf'),
        'modalidadesId': [int(item) for item in parse_lista_param('modalidadeId') if item.isdigit()],
        'municipiosNome': parse_lista_param('municipioNome'),
        'palavrasChave': parse_lista_param('palavraChave'),
        'excluirPalavras': parse_lista_param('excluirPalavra'),
        # FIM DA REVISÃO AQUI ------------

        # 'ufs': request.args.getlist('uf'),

        # Recebe a string e a quebra em uma lista, removendo espaços vazios
        #'ufs': [uf.strip() for uf in request.args.get('uf', '').split(',') if uf.strip()],
        #'modalidadesId': [int(mid.strip()) for mid in request.args.get('modalidadeId', '').split(',') if mid.strip()],
        # 'modalidadesId': request.args.getlist('modalidadeId', type=int),
        'statusRadar': request.args.get('statusRadar'),
        'dataPubInicio': request.args.get('dataPubInicio'),
        'dataPubFim': request.args.get('dataPubFim'),
        'valorMin': request.args.get('valorMin', type=float),
        'valorMax': request.args.get('valorMax', type=float),
        # 'municipiosNome': request.args.getlist('municipioNome'),
        #'municipiosNome': [m.strip() for m in request.args.get('municipioNome', '').split(',') if m.strip()],
        'dataAtualizacaoInicio': request.args.get('dataAtualizacaoInicio'),
        'dataAtualizacaoFim': request.args.get('dataAtualizacaoFim'),
        'anoCompra': request.args.get('anoCompra', type=int),
        'cnpjOrgao': request.args.get('cnpjOrgao'),
        'statusId': request.args.get('statusId', type=int),
        # 'palavrasChave': request.args.getlist('palavraChave'),
        # 'excluirPalavras': request.args.getlist('excluirPalavra')
        #'palavrasChave': [kw.strip() for kw in request.args.get('palavraChave', '').split(',') if kw.strip()],
        #'excluirPalavras': [kw.strip() for kw in request.args.get('excluirPalavra', '').split(',') if kw.strip()],
    }
    # Limpa filtros vazios ou nulos
    filtros = {k: v for k, v in filtros.items() if v is not None and v != '' and v != []}

    # 3. Monta a cláusula WHERE e os parâmetros usando a função centralizada
    query_where, parametros_db = _build_licitacoes_query(filtros)

    # 4. Monta as queries de contagem e de dados
    query_contagem = f"SELECT COUNT(*) as total FROM licitacoes {query_where}"
    
    query_select_dados = f"""
        SELECT * FROM licitacoes
        {query_where}
        ORDER BY {orderBy_param} {orderDir_param}
        LIMIT %s OFFSET %s
    """
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"erro": "Falha na conexão com o banco de dados."}), 503

    licitacoes_lista = []
    total_registros = 0
    try:
        # Cria cursores que retornam dicionários
        cursor_dados = conn.cursor(dictionary=True)
        cursor_contagem = conn.cursor(dictionary=True)

        # --- INÍCIO DA MELHORIA: AJUSTE DO NÍVEL DE ISOLAMENTO ---
        # Definimos o nível de isolamento como READ COMMITTED para esta sessão.
        # Isso reduz a chance de a leitura bloquear o script de escrita (sync_api.py).
        cursor_contagem.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
        app.logger.info("Nível de isolamento da transação para API de leitura definido como READ COMMITTED.")
        # --- FIM DA MELHORIA ---
        
        # Executa a query de contagem total
        cursor_contagem.execute(query_contagem, parametros_db)
        resultado_contagem = cursor_contagem.fetchone()
        if resultado_contagem:
            total_registros = resultado_contagem['total']

        # Executa a query de dados com paginação
        parametros_dados_sql = parametros_db + [por_pagina, (pagina - 1) * por_pagina]
        cursor_dados.execute(query_select_dados, parametros_dados_sql)
        licitacoes_lista_bruta = cursor_dados.fetchall()
        
        licitacoes_lista = [formatar_para_json(row) for row in licitacoes_lista_bruta]



    except mysql.connector.Error as err:
        app.logger.error(f"Erro de SQL em get_licitacoes: {err}")
        return jsonify({"erro": "Erro interno ao processar sua busca.", "detalhes": str(err)}), 500
    finally:
        if conn and conn.is_connected():    # Verifica se a conexão e o cursor estão abertos, se tiverem então fecha
            if 'cursor_dados' in locals():
                cursor_dados.close()
            if 'cursor_contagem' in locals():
                cursor_contagem.close()
            conn.close()

    total_paginas = (total_registros + por_pagina - 1) // por_pagina if por_pagina > 0 else 0

    return jsonify({
        "pagina_atual": pagina,
        "por_pagina": por_pagina,
        "total_registros": total_registros,
        "total_paginas": total_paginas,
        "origem_dados": "banco_local_com_filtro_sql",
        "licitacoes": licitacoes_lista
    })
    
    #return jsonify({ "exemplo": "dados das licitacoes" }) # Placeholder


@app.route('/api/licitacao/<path:numero_controle_pncp>', methods=['GET'])
@with_db_cursor
def get_detalhe_licitacao(numero_controle_pncp, cursor):
    query_licitacao_principal = "SELECT * FROM licitacoes WHERE numeroControlePNCP = %s"
    cursor.execute(query_licitacao_principal, (numero_controle_pncp,))
    licitacao_principal_row = cursor.fetchone()

    if not licitacao_principal_row:
        return jsonify({"erro": "Licitação não encontrada", "numeroControlePNCP": numero_controle_pncp}), 404

    licitacao_principal_dict = formatar_para_json(licitacao_principal_row)
    licitacao_id_local = licitacao_principal_dict['id']

    query_itens = "SELECT * FROM itens_licitacao WHERE licitacao_id = %s"
    cursor.execute(query_itens, (licitacao_id_local,))
    itens_rows = cursor.fetchall()
    itens_lista = [formatar_para_json(row) for row in itens_rows]

    query_arquivos = "SELECT * FROM arquivos_licitacao WHERE licitacao_id = %s"
    cursor.execute(query_arquivos, (licitacao_id_local,))
    arquivos_rows = cursor.fetchall()
    arquivos_lista = [formatar_para_json(row) for row in arquivos_rows]

    resposta_final = {
        "licitacao": licitacao_principal_dict,
        "itens": itens_lista,
        "arquivos": arquivos_lista
    }
    return jsonify(resposta_final)

@app.route('/api/referencias/modalidades', methods=['GET'])
@with_db_cursor
def get_modalidades_referencia(cursor):
    cursor.execute("SELECT DISTINCT modalidadeId, modalidadeNome FROM licitacoes ORDER BY modalidadeNome")
    modalidades = [dict(row) for row in cursor.fetchall()]
    return jsonify(modalidades)

@app.route('/api/referencias/statuscompra', methods=['GET'])
@with_db_cursor
def get_statuscompra_referencia(cursor):
    cursor.execute("SELECT DISTINCT situacaoCompraId, situacaoCompraNome FROM licitacoes ORDER BY situacaoCompraNome")
    status_compra = [dict(row) for row in cursor.fetchall()]
    return jsonify(status_compra)

@app.route('/api/referencias/statusradar', methods=['GET'])
@with_db_cursor
def get_statusradar_referencia(cursor):
    cursor.execute("SELECT DISTINCT situacaoReal FROM licitacoes WHERE situacaoReal IS NOT NULL ORDER BY situacaoReal")
    status_radar_rows = cursor.fetchall()
    status_radar = [{"id": row['situacaoReal'], "nome": row['situacaoReal']} for row in status_radar_rows]
    return jsonify(status_radar)

# --- Rota API IBGE (mantida do frontend) ---
@app.route('/api/ibge/municipios/<uf_sigla>', methods=['GET'])
def api_get_municipios_ibge(uf_sigla):
    if not uf_sigla or len(uf_sigla) != 2 or not uf_sigla.isalpha():
        return jsonify({"erro": "Sigla da UF inválida."}), 400
    
    ibge_api_url = f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf_sigla.upper()}/municipios"
    try:
        response = requests.get(ibge_api_url)
        response.raise_for_status()
        municipios = [{"id": m["id"], "nome": m["nome"]} for m in response.json()]
        return jsonify(municipios)
    except requests.exceptions.HTTPError as http_err:
        return jsonify({"erro": f"Erro ao buscar municípios no IBGE: {http_err}", "status_code": http_err.response.status_code}), http_err.response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"erro": f"Erro de conexão com API do IBGE: {e}", "status_code": 503}), 503
    except ValueError:
        return jsonify({"erro": "Resposta inválida (JSON) da API do IBGE.", "status_code": 500}), 500
    
    #return jsonify([{"exemplo": f"municipios de {uf_sigla}"}]) # Placeholder
           
# EXPORTAR CSV - Mantendo separado de def get_licitacoes() sem refatorar posso enviar mais coisas ou menos. 
@app.route('/api/exportar-csv')
def exportar_csv():
    # 1. Coleta todos os filtros da URL em um único dicionário
    filtros = {
        'ufs': request.args.getlist('uf'),
        'modalidadesId': request.args.getlist('modalidadeId', type=int),
        'statusRadar': request.args.get('statusRadar'),
        'dataPubInicio': request.args.get('dataPubInicio'),
        'dataPubFim': request.args.get('dataPubFim'),
        'valorMin': request.args.get('valorMin', type=float),
        'valorMax': request.args.get('valorMax', type=float),
        'municipiosNome': request.args.getlist('municipioNome'),
        'dataAtualizacaoInicio': request.args.get('dataAtualizacaoInicio'),
        'dataAtualizacaoFim': request.args.get('dataAtualizacaoFim'),
        'anoCompra': request.args.get('anoCompra', type=int),
        'cnpjOrgao': request.args.get('cnpjOrgao'),
        'statusId': request.args.get('statusId', type=int),
        'palavrasChave': request.args.getlist('palavraChave'),
        'excluirPalavras': request.args.getlist('excluirPalavra')
    }
    # Limpa filtros que não foram preenchidos
    filtros = {k: v for k, v in filtros.items() if v is not None and v != '' and v != []}
    
    # Coleta parâmetros de ordenação
    orderBy_param = request.args.get('orderBy', default='dataPublicacaoPncp')
    orderDir_param = request.args.get('orderDir', default='DESC').upper()

    # --- INÍCIO DA CORREÇÃO DE SEGURANÇA ---
    # Reutilize a MESMA whitelist da sua rota get_licitacoes
    campos_validos_ordenacao = [
        'dataPublicacaoPncp', 'dataAtualizacao', 'valorTotalEstimado',
        'dataAberturaProposta', 'dataEncerramentoProposta', 'modalidadeNome',
        'orgaoEntidadeRazaoSocial', 'unidadeOrgaoMunicipioNome', 'situacaoReal'
    ]
    if orderBy_param not in campos_validos_ordenacao:
        app.logger.warning(f"Export CSV: Tentativa de ordenação inválida por '{orderBy_param}'")
        # Retorna um erro em vez de continuar
        return jsonify({"erro": "Parâmetro de ordenação inválido."}), 400
        
    if orderDir_param not in ['ASC', 'DESC']:
        app.logger.warning(f"Export CSV: Tentativa de direção de ordenação inválida '{orderDir_param}'")
        return jsonify({"erro": "Parâmetro de direção de ordenação inválido."}), 400
    # --- FIM DA CORREÇÃO DE SEGURANÇA ---


    # 2. Usa a função central para construir a cláusula WHERE e os parâmetros
    query_where_sql, parametros_db_sql = _build_licitacoes_query(filtros)
    
    # 3. Monta a query final de seleção (sem paginação para exportar tudo)
    query_select_dados = f"SELECT * FROM licitacoes {query_where_sql} ORDER BY {orderBy_param} {orderDir_param}"
    
    conn = get_db_connection()
    licitacoes_filtradas = []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query_select_dados, parametros_db_sql)
        # O resultado do banco já está completamente filtrado
        licitacoes_filtradas = cursor.fetchall()
    except mysql.connector.Error as e:
        app.logger.error(f"Erro ao buscar dados para exportar CSV: {e}")
        return jsonify({"erro": "Erro ao buscar dados para exportação"}), 500
    finally:
        if conn and conn.is_connected():
            if 'cursor' in locals():
                cursor.close()
            conn.close()


    # 4. Geração do CSV em memória
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', lineterminator='\n', quoting=csv.QUOTE_ALL)
    
    # Cabeçalho do CSV
    writer.writerow(['Data Atualizacao', 'Municipio/UF', 'Orgao', 'Modalidade', 'Status', 'Valor Estimado (R$)', 'Objeto da Compra', 'Link PNCP'])

    # Escreve as linhas de dados
    for lic in licitacoes_filtradas:
        municipio_uf = f"{lic.get('unidadeOrgaoMunicipioNome', '')}/{lic.get('unidadeOrgaoUfSigla', '')}"
        
        valor_str = 'N/I'
        if lic.get('valorTotalEstimado') is not None:
            # Formata o valor como moeda brasileira
            valor_str = f"{lic['valorTotalEstimado']:.2f}".replace('.', ',')
            
        writer.writerow([
            lic.get('dataAtualizacao', ''),
            municipio_uf,
            lic.get('orgaoEntidadeRazaoSocial', ''),
            lic.get('modalidadeNome', ''),
            lic.get('situacaoReal', ''),
            valor_str,
            lic.get('objetoCompra', ''),
            lic.get('link_portal_pncp', '')
        ])

    # 5. Prepara a resposta HTTP para o download do arquivo
    output.seek(0)
    return Response(
        output.getvalue().encode('utf-8-sig'), # utf-8-sig para compatibilidade com Excel
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=radar_pncp_licitacoes.csv"}
    )
    return Response(output, mimetype="text/csv", headers={"Content-Disposition":"attachment;filename=export.csv"})


# ===============================================================
# =================== Rotas para posts do blog ==================
# ===============================================================
@app.route('/api/posts', methods=['GET'])
@with_db_cursor
def get_all_posts(cursor):
    # --- 1. Captura de todos os parâmetros --- (mantida igual)
    categoria_slug = request.args.get('categoria')
    tag_nome = request.args.get('tag')
    query_busca = request.args.get('q')
    page = request.args.get('page', 1, type=int)
    per_page = 9
    offset = (page - 1) * per_page

    # --- 2. Monta as partes da query (JOINs e WHEREs) primeiro --- (mantida igual)
    joins = " LEFT JOIN categorias c ON p.categoria_id = c.id"
    where_clauses = []
    params = []

    if tag_nome:
        joins += " JOIN posts_tags pt ON p.id = pt.post_id JOIN tags t ON pt.tag_id = t.id"
        where_clauses.append("t.nome = %s")
        params.append(tag_nome)

    if categoria_slug:
        where_clauses.append("c.slug = %s")
        params.append(categoria_slug)

    if query_busca:
        where_clauses.append("(p.titulo LIKE %s OR p.resumo LIKE %s OR p.conteudo_completo LIKE %s)")
        search_term = f"%{query_busca}%"
        params.extend([search_term, search_term, search_term])
    
    where_sql = ""
    if where_clauses:
        where_sql = " WHERE " + " AND ".join(where_clauses)

    # --- 3. Executa a Query de Contagem (agora correta) --- (mantida igual)
    count_query = f"SELECT COUNT(DISTINCT p.id) as total FROM posts p{joins}{where_sql}"
    cursor.execute(count_query, params)
    total_posts = cursor.fetchone()['total']
    total_pages = (total_posts + per_page - 1) // per_page if total_posts > 0 else 0

    # --- 4. Executa a Query para buscar os dados da página --- (mantida igual)
    query_data = f"""
        SELECT p.id, p.titulo, p.slug, p.resumo, p.data_publicacao, p.imagem_destaque,
               c.nome AS categoria_nome, c.slug AS categoria_slug
        FROM posts p
        {joins}
        {where_sql}
        ORDER BY p.data_publicacao DESC
        LIMIT %s OFFSET %s
    """
    params_paginados = params + [per_page, offset]
    cursor.execute(query_data, params_paginados)
    posts = cursor.fetchall()
    
    posts_formatados = [formatar_para_json(p) for p in posts]
    
    # --- 5. Retorna o JSON com os dados da paginação --- (mantida igual)
    return jsonify(
        posts=posts_formatados,
        pagina_atual=page,
        total_paginas=total_pages
    )


@app.route('/api/post/<string:post_slug>', methods=['GET'])
@with_db_cursor
def get_single_post(post_slug, cursor):
    # --- PASSO 1: QUERY PRINCIPAL MODIFICADA --- (mantida igual)
    # Adicionamos o LEFT JOIN com a tabela 'categorias' para já pegar os dados da categoria.
    query_post = """
        SELECT 
            p.id, p.titulo, p.conteudo_completo, p.data_publicacao,
            c.nome AS categoria_nome, 
            c.slug AS categoria_slug
        FROM posts p
        LEFT JOIN categorias c ON p.categoria_id = c.id
        WHERE p.slug = %s
    """
    cursor.execute(query_post, (post_slug,))
    post = cursor.fetchone()
  
    if not post:
        return jsonify(erro="Post não encontrado"), 404

    # --- PASSO 2: NOVA QUERY PARA BUSCAR AS TAGS --- (mantida igual)
    # Usamos o ID do post que acabamos de encontrar para buscar suas tags.
    post_id = post['id']
    query_tags = """
        SELECT t.nome
        FROM tags t
        JOIN posts_tags pt ON t.id = pt.tag_id
        WHERE pt.post_id = %s
    """
    cursor.execute(query_tags, (post_id,))
    tags_result = cursor.fetchall()
    
    # Extrai apenas os nomes das tags para uma lista simples
    tags = [tag['nome'] for tag in tags_result]

    # Formata as datas e adiciona as tags ao resultado final
    post_formatado = formatar_para_json(post)
    post_formatado['tags'] = tags # Adiciona a lista de tags ao dicionário do post

    return jsonify(post=post_formatado)

@app.route('/api/posts/destaques', methods=['GET'])
@with_db_cursor
def get_featured_posts(cursor):
    # ### ALTERAÇÃO NA QUERY: Adicionado "WHERE is_featured = TRUE" e "LIMIT 3" ### (mantida igual)
    cursor.execute("""
        SELECT titulo, slug, resumo, data_publicacao, imagem_destaque 
        FROM posts 
        WHERE is_featured = TRUE 
        ORDER BY data_publicacao DESC 
        LIMIT 3
    """)
    posts = cursor.fetchall()

    posts_formatados = [formatar_para_json(p) for p in posts]
    return jsonify(posts=posts_formatados)


# =========================================================================
# ========= CONFIGURAÇÃO DO FLASK-ADMIN -- BACKEND ADMINISTRATIVO =========
# =========================================================================
# View principal do admin que verifica se o usuário está logado - HOME DO ADMIN
class MyAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Estatísticas
        cursor.execute("SELECT COUNT(*) as total FROM posts")
        total_posts = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM categorias")
        total_categorias = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM tags")
        total_tags = cursor.fetchone()['total']
        
        cursor.execute("SELECT * FROM posts ORDER BY data_publicacao DESC LIMIT 5")
        posts_recentes = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        stats = {
            'total_posts': total_posts,
            'total_categorias': total_categorias,
            'total_tags': total_tags,
        }
        
        return self.render('admin/index.html', stats=stats, posts_recentes=posts_recentes)
    
    def is_accessible(self):
        # Acessível apenas se o usuário estiver logado e autenticado
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        # Se não estiver logado, redireciona para a página de login
        flash("Você precisa estar logado para acessar a área administrativa.", "warning")
        return redirect(url_for('login', next=request.url))

class PostsView(BaseView):
    def is_accessible(self):
        # Acessível apenas se o usuário estiver logado
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        # Redireciona para o login se não estiver autenticado
        return redirect(url_for('login'))

    # Rota para a lista de posts
    @expose('/')
    def list_posts(self):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # --- LÓGICA DE PAGINAÇÃO ---
        page = request.args.get('page', 1, type=int) # Pega o nº da página da URL, padrão é 1
        per_page = 15 # Define quantos posts por página
        offset = (page - 1) * per_page # Calcula o deslocamento

        # Query para contar o total de posts (para saber quantas páginas teremos)
        cursor.execute("SELECT COUNT(*) as total FROM posts")
        total_posts = cursor.fetchone()['total']
        total_pages = (total_posts + per_page - 1) // per_page

        # Query principal MODIFICADA com LIMIT e OFFSET
        cursor.execute("""
            SELECT p.id, p.titulo, p.slug, p.data_publicacao, u.username as autor_nome 
            FROM posts p 
            LEFT JOIN usuarios u ON p.autor_id = u.id 
            ORDER BY p.data_publicacao DESC
            LIMIT %s OFFSET %s
        """, (per_page, offset))
        
        posts = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Passa as variáveis de paginação para o template
        return self.render('admin/posts_list.html', 
                        posts=posts, 
                        page=page, 
                        total_pages=total_pages)

    # Rota para o formulário de adicionar/editar post
    @expose('/edit/', methods=('GET', 'POST'))
    @expose('/edit/<int:post_id>', methods=('GET', 'POST'))
    def edit_post(self, post_id=None):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # --- BUSCAR DADOS PARA O FORMULÁRIO (CATEGORIAS E TAGS) ---
        cursor.execute("SELECT id, nome FROM categorias ORDER BY nome")
        todas_categorias = cursor.fetchall()
        
        cursor.execute("SELECT id, nome FROM tags ORDER BY nome")
        todas_tags = cursor.fetchall()

        post_para_formulario = {}
        tags_atuais_do_post = [] # Lista de IDs das tags já selecionadas

        # Se estiver editando, busca os dados do post e suas tags
        if post_id:
            cursor.execute("SELECT * FROM posts WHERE id = %s", (post_id,))
            post_para_formulario = cursor.fetchone()
            if not post_para_formulario:
                flash('Post não encontrado!', 'danger')
                cursor.close()
                conn.close()
                return redirect(url_for('.list_posts'))
            
            cursor.execute("SELECT tag_id FROM posts_tags WHERE post_id = %s", (post_id,))
            tags_atuais_do_post = [row['tag_id'] for row in cursor.fetchall()]
        
        # --- LÓGICA PARA REQUISIÇÃO POST (Quando o formulário é ENVIADO) ---
        if request.method == 'POST':
            # 1. Pega os dados brutos do formulário
            titulo = request.form.get('titulo')
            slug = request.form.get('slug')
            resumo = request.form.get('resumo')
            conteudo_bruto = request.form.get('conteudo_completo')
            imagem_destaque = request.form.get('imagem_destaque')
            is_featured = 'is_featured' in request.form
            categoria_id = request.form.get('categoria_id')
            # O Python None será traduzido para o SQL NULL pelo conector do banco.
            if categoria_id == '':
                categoria_id = None
            
            tags_selecionadas_ids = request.form.getlist('tags')
            
            import re
            slug_limpo = re.sub(r'[^a-z0-9\-]+', '', slug.lower()).strip('-')
            
            # 2. Sanitiza o conteúdo HTML
            conteudo_sanitizado = bleach.clean(conteudo_bruto,tags = [
                "p", "br", "hr", "div", "span",
                "h1", "h2", "h3", "h4", "h5", "h6",
                "strong", "b", "em", "i", "u", "mark", "small", "sup", "sub",
                "ul", "ol", "li", "dl", "dt", "dd",
                "blockquote", "pre", "code",
                "a", "img", "figure", "figcaption",
                "table", "thead", "tbody", "tfoot", "tr", "td", "th",
                "section", "article", "main", "aside", "header", "footer", "nav"
            ], attributes = {   # Atributos permitidos
                'a': ['href', 'title', "target", "rel"],
                'img': ['src', 'alt', 'title',"width", "height", 'style'],
                'div': ['class', 'id', 'style'],
                'span': ['class', 'id', 'style'],
                'section': ['class', 'id'],
                'article': ['class', 'id'],
                'main': ['class', 'id'],
                "table": ["class", "style", "border", "cellpadding", "cellspacing"],
                "td": ["class", "style", "colspan", "rowspan"],
                "th": ["class", "style", "colspan", "rowspan"],
                "*": ["class", "id", "style"]
            })

            try:
                # --- LÓGICA DE UNICIDADE PROATIVA ---
                cursor = conn.cursor(dictionary=True)
                
                # Query para verificar se o slug já existe em OUTRO post
                check_slug_query = "SELECT id FROM posts WHERE slug = %s AND id != %s"
                cursor.execute(check_slug_query, (slug_limpo, post_id if post_id else 0))
                
                slug_final = slug_limpo
                if cursor.fetchone():
                    # Se encontrou, o slug já está em uso. Chame sua função!
                    slug_final = generate_unique_slug(conn, slug_limpo)
                    flash(f"O slug '{slug_limpo}' já estava em uso e foi ajustado para '{slug_final}'.", 'warning')
                
                # --- INSERÇÃO OU ATUALIZAÇÃO DO POST ---
                if post_id:
                    # UPDATE
                    query = """UPDATE posts SET titulo=%s, slug=%s, resumo=%s, conteudo_completo=%s, imagem_destaque=%s, categoria_id=%s, is_featured=%s WHERE id=%s"""
                    cursor.execute(query, (titulo, slug_final, resumo, conteudo_sanitizado, imagem_destaque, categoria_id, is_featured, post_id))
                else:
                                        
                    # INSERT
                    query = """INSERT INTO posts (titulo, slug, resumo, conteudo_completo, autor_id, imagem_destaque, categoria_id, is_featured) 
                               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
                    cursor.execute(query, (titulo, slug_final, resumo, conteudo_sanitizado, current_user.id, imagem_destaque, categoria_id, is_featured))
                    post_id = cursor.lastrowid
                
                # Atualiza as tags na tabela de junção
                cursor.execute("DELETE FROM posts_tags WHERE post_id = %s", (post_id,))
                if tags_selecionadas_ids:
                    tags_para_inserir = [(post_id, tag_id) for tag_id in tags_selecionadas_ids]
                    cursor.executemany("INSERT INTO posts_tags (post_id, tag_id) VALUES (%s, %s)", tags_para_inserir)

                conn.commit()
                flash('Post salvo com sucesso!', 'success')
                
                # Fecha tudo e redireciona
                cursor.close()
                conn.close()
                return redirect(url_for('.list_posts'))
            
            except mysql.connector.Error as err:
                conn.rollback()
                if err.errno == 1062:
                    flash(f"Erro: O slug '{slug_limpo}' já existe. Por favor, escolha outro.", 'danger')
                    post_para_formulario = request.form
                else:
                    flash(f"Ocorreu um erro no banco de dados: {err}", "danger")
                    post_para_formulario = request.form
        
        # --- RENDERIZA O FORMULÁRIO (PARA REQUISIÇÃO GET OU APÓS ERRO NO POST) ---
        cursor.close()
        conn.close()
        
        tinymce_key = os.getenv('TINYMCE_API_KEY')
        return self.render('admin/post_form.html', 
                           post=post_para_formulario, 
                           post_id=post_id, 
                           tinymce_key=tinymce_key,
                           todas_categorias=todas_categorias,
                           todas_tags=todas_tags,
                           tags_atuais=tags_atuais_do_post)

    # Rota para deletar um post
    @expose('/delete/<int:post_id>', methods=('POST',))
    def delete_post(self, post_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM posts WHERE id = %s", (post_id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Post excluído com sucesso!', 'success')
        return redirect(url_for('.list_posts'))

# Inicializa o Flask-Admin
admin = Admin(
    app, 
    name='Painel RADAR PNCP', 
    template_mode='bootstrap4',
    index_view=MyAdminIndexView()
)

# BLOCO DE CÓDIGO 5: VIEW DE ADMINISTRAÇÃO PARA CATEGORIAS E TAGS
class CategoriaView(BaseView):
    def is_accessible(self):
        return current_user.is_authenticated

    @expose('/', methods=('GET', 'POST'))
    def index(self):
        if request.method == 'POST':
            nome = request.form.get('nome')
            slug = request.form.get('slug')
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO categorias (nome, slug) VALUES (%s, %s)", (nome, slug))
                conn.commit()
                flash('Categoria criada com sucesso!', 'success')
            except mysql.connector.Error as err:
                flash(f'Erro ao criar categoria: {err}', 'danger')
            finally:
                cursor.close()
                conn.close()
            return redirect(url_for('.index'))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM categorias ORDER BY nome")
        categorias = cursor.fetchall()
        cursor.close()
        conn.close()
        return self.render('admin/categorias_tags.html', items=categorias, title="Categorias", endpoint_name="categorias")

    @expose('/delete/<int:item_id>', methods=('POST',))
    def delete(self, item_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM categorias WHERE id = %s", (item_id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Categoria excluída com sucesso.', 'success')
        return redirect(url_for('.index'))

class TagView(BaseView):
    def is_accessible(self):
        return current_user.is_authenticated
    
    # Esta view é quase idêntica à de categorias, mas usa a tabela 'tags'
    @expose('/', methods=('GET', 'POST'))
    def index(self):
        if request.method == 'POST':
            nome = request.form.get('nome')
            # Tags não precisam de slug, apenas nome.
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO tags (nome) VALUES (%s)", (nome,))
                conn.commit()
                flash('Tag criada com sucesso!', 'success')
            except mysql.connector.IntegrityError as err:
                # Erro 1062 = chave duplicada
                if err.errno == 1062:
                    flash(f"A tag '{nome}' já existe. Escolha outro nome.", 'warning')
                else:
                    flash('Erro de integridade no banco de dados.', 'danger')
            except mysql.connector.Error as err:
                # Para qualquer outro erro do MySQL
                flash('Erro inesperado ao criar tag. Tente novamente.', 'danger')
                app.logger.error(f"Erro MySQL ao criar tag: {err}")
            finally:
                cursor.close()
                conn.close()
            return redirect(url_for('.index'))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM tags ORDER BY nome")
        tags = cursor.fetchall()
        cursor.close()
        conn.close()
        return self.render('admin/categorias_tags.html', items=tags, title="Tags", endpoint_name="tags")

    @expose('/delete/<int:item_id>', methods=('POST',))
    def delete(self, item_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tags WHERE id = %s", (item_id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Tag excluída com sucesso.', 'success')
        return redirect(url_for('.index'))
    
# =========================================================================
# =================== Rotas API para categorias e tags ==================
@app.route('/api/categorias', methods=['GET'])
@with_db_cursor
def get_all_categorias(cursor):
    cursor.execute("SELECT nome, slug FROM categorias ORDER BY nome")
    categorias = cursor.fetchall()
    return jsonify(categorias=categorias)

@app.route('/api/tags', methods=['GET'])
@with_db_cursor
def get_all_tags(cursor):
    cursor.execute("SELECT nome FROM tags ORDER BY nome")
    tags = cursor.fetchall()
    return jsonify(tags=tags)
# ============================================================================

admin.add_view(PostsView(name='Posts', endpoint='posts'))
admin.add_view(CategoriaView(name='Categorias', endpoint='categorias'))
admin.add_view(TagView(name='Tags', endpoint='tags'))

# ============= acaba aqui o Flask-Admin e rotas do admin ====================
# ============================================================================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    # Em produção real, você não usaria app.run(), mas sim um servidor WSGI como Gunicorn.
    # O debug=True também deve ser False ou controlado por uma variável de ambiente em produção.
    is_debug_mode = os.getenv('FLASK_DEBUG', '0') == '1'
    app.run(debug=is_debug_mode, host='0.0.0.0', port=port) # Modo debug esta configurado no arquivo .env
