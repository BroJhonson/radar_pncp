import mysql.connector 
from mysql.connector import errors # Para tratamento de erros
# Importações para usuarios e admin
from flask_admin import Admin, BaseView, expose, AdminIndexView
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_bcrypt import Bcrypt
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_cors import CORS  # Adicionado para CORS
import requests  # Para chamar a API do IBGE
from markupsafe import Markup, escape
# Para envio de e-mail
import smtplib
from email.mime.text import MIMEText
import os  # Para ler variáveis de ambiente
from dotenv import load_dotenv  # Para carregar o arquivo .env
import csv #Esse e os tres de baixo são para o upload de arquivos CSV
import io
from flask import Response
import unicodedata  # Para normalizar strings (remover acentos, etc.)
import time
import datetime
import bleach

load_dotenv()  # Carrega as variáveis do arquivo .env para o ambiente

# --- Configurações ---
app = Flask(__name__)

# Configuração CORS para permitir comunicação com frontend
CORS(app, origins=["*"])  # Em produção, especificar domínios específicos

# Configurações de segurança e login
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' # Redireciona para a rota 'login' se não estiver logado
login_manager.login_message = "Por favor, faça login para acessar esta página."
login_manager.login_message_category = "info"
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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # Acho que isso não é mais necessário
DATABASE_PATH = os.path.join(BASE_DIR, 'database', 'database.db')   # Ajustado para nova estrutura

# BLOCO DE CÓDIGO 1: CONFIGURAÇÃO DO USUÁRIO PARA FLASK-LOGIN
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

# --- Função para formatar datas em JSON ---
def formatar_datas_para_json(licitacao_dict):
    """Converte objetos date/datetime em strings ISO para serialização JSON."""
    if licitacao_dict is None:
        return None
    for key, value in licitacao_dict.items():
        if isinstance(value, (datetime.date, datetime.datetime)):
            licitacao_dict[key] = value.isoformat()
    return licitacao_dict

# --- Filtro personalizado nl2br para quebra de linha ---
def nl2br_filter(value):
    if value is None:
        return ''
    # Escapa o HTML para segurança, substitui \n por <br>\n, e marca como Markup seguro
    return Markup(str(escape(value)).replace('\n', '<br>\n'))

app.jinja_env.filters['nl2br'] = nl2br_filter  # Registra o filtro

# --- Rota erro 404
@app.errorhandler(404)
def pagina_nao_encontrada(e):    
    print(f"Erro 404 - Página não encontrada: {request.url} (Erro original: {e})")
    return render_template('404.html', 
                           page_title="Página Não Encontrada", 
                           body_class="page-error"), 404

@app.errorhandler(500)
def erro_interno_servidor_erro(e):
    # Em um ambiente de produção, NUNCA deve vazar detalhes do erro 'e' para o usuário.
    # O template 500.html deve ter uma mensagem genérica.
    print(f"Erro 500 detectado: {e} para a URL: {request.url}") # Para debug local MUDAR ISSO DEPOIS EM PREDUÇÃO ++++++++++++++++++++++++++++++++++++
    return render_template('500.html', 
                           page_title="Erro Interno no Servidor", # ALIAS PARECE QUE JA ESTÁ RESOLVIDO
                           body_class="page-error"), 500

# =========================================================================
# ROTAS DE AUTENTICAÇÃO E ADMINISTRAÇÃO de USUÁRIOS
# =========================================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        conn = None
        
        try:
            conn = get_db_connection()
            if not conn:
                flash("Erro de conexão com o banco de dados. Tente novamente mais tarde.", "danger")
                return render_template('login.html', page_title="Login")
            
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM usuarios WHERE username = %s", (username,))
            user_data = cursor.fetchone()

            if user_data and bcrypt.check_password_hash(user_data['password_hash'], password):
                user = User(id=user_data['id'], username=user_data['username'], password_hash=user_data['password_hash'])
                login_user(user)
                # Redireciona para o painel de admin após o login
                return redirect(url_for('admin.index'))
            else:
                flash('Login inválido. Verifique o usuário e a senha.', 'danger')

        except mysql.connector.Error as err:
            app.logger.error(f"Erro de banco de dados no login: {err}")
            flash("Ocorreu um erro inesperado. Tente novamente.", "danger")
        finally:
            if conn and conn.is_connected():
                if 'cursor' in locals():
                    cursor.close()
                conn.close()
            
    return render_template('login.html', page_title="Login")

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você foi desconectado com sucesso.', 'info')
    return redirect(url_for('login'))
# =========================================================================

# --- Rotas Frontend (Renderização de Páginas) ---
@app.route('/')
def inicio():
    # Busca apenas os 3 posts marcados como destaque
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM posts WHERE is_featured = TRUE ORDER BY data_publicacao DESC LIMIT 3")
    posts_destacados = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('index.html', 
                           posts=posts_destacados, 
                           page_title="Bem-vindo ao RADAR PNCP", 
                           body_class="page-home")

@app.route('/radarPNCP')
def buscador_licitacoes():
    return render_template('radar.html', page_title="Buscar Licitações - RADAR PNCP", body_class="page-busca-licitacoes")

def get_blog_sidebar_data(cursor):
    """Função auxiliar para buscar dados comuns da sidebar do blog."""
    cursor.execute("SELECT nome, slug FROM categorias ORDER BY nome")
    categorias = cursor.fetchall()
    
    # Busca todas as tags
    cursor.execute("SELECT nome FROM tags ORDER BY nome")
    tags = cursor.fetchall()
    return categorias, tags

@app.route('/blog')
def pagina_blog():
    conn = None
    cursor = None
    posts = []
    categorias = []
    tags = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT p.*, c.nome as categoria_nome, c.slug as categoria_slug 
            FROM posts p 
            LEFT JOIN categorias c ON p.categoria_id = c.id 
            ORDER BY p.data_publicacao DESC
        """)
        posts = cursor.fetchall()
        # Modificado para receber categorias e tags
        categorias, tags = get_blog_sidebar_data(cursor)
    except Exception as err:
        app.logger.error(f"Erro ao buscar posts para o blog: {err}")
        return render_template("500.html", page_title="Erro ao carregar Blog"), 500
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    return render_template('pagina_blog.html',
                           posts=posts,
                           categorias=categorias,
                           tags=tags,  # Passando as tags para o template
                           page_title="Nosso Blog",
                           body_class="page-blog")

@app.route('/blog/categoria/<string:categoria_slug>')
def posts_por_categoria(categoria_slug):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT p.*, c.nome as categoria_nome, c.slug as categoria_slug 
        FROM posts p JOIN categorias c ON p.categoria_id = c.id 
        WHERE c.slug = %s ORDER BY p.data_publicacao DESC
    """, (categoria_slug,))
    posts = cursor.fetchall()
    
    categoria_nome = posts[0]['categoria_nome'] if posts else categoria_slug
    
    # Modificado para receber categorias e tags
    categorias_sidebar, tags_sidebar = get_blog_sidebar_data(cursor)
    
    cursor.close()
    conn.close()

    return render_template('pagina_blog.html', 
                           posts=posts, 
                           categorias=categorias_sidebar, 
                           tags=tags_sidebar, # Passando as tags para o template
                           page_title=f"Posts em '{categoria_nome}'")

@app.route('/blog/tag/<string:tag_nome>')
def posts_por_tag(tag_nome):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Busca os posts que têm la tag específica
    cursor.execute("""
        SELECT p.*, c.nome as categoria_nome, c.slug as categoria_slug
        FROM posts p
        JOIN posts_tags pt ON p.id = pt.post_id
        JOIN tags t ON pt.tag_id = t.id
        LEFT JOIN categorias c ON p.categoria_id = c.id
        WHERE t.nome = %s
        ORDER BY p.data_publicacao DESC
    """, (tag_nome,))
    posts = cursor.fetchall()
    
    categorias_sidebar, tags_sidebar = get_blog_sidebar_data(cursor)
    
    cursor.close()
    conn.close()
    return render_template('pagina_blog.html', 
                           posts=posts, 
                           categorias=categorias_sidebar, 
                           tags=tags_sidebar, 
                           page_title=f"Posts com a tag '{tag_nome}'")

@app.route('/blog/search')
def search_blog():
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('pagina_blog'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    search_term = f"%{query}%"
    cursor.execute("""
        SELECT p.*, c.nome as categoria_nome, c.slug as categoria_slug 
        FROM posts p LEFT JOIN categorias c ON p.categoria_id = c.id 
        WHERE p.titulo LIKE %s OR p.conteudo_completo LIKE %s 
        ORDER BY p.data_publicacao DESC
    """, (search_term, search_term))
    posts = cursor.fetchall()
    
    # Modificado para receber categorias e tags
    categorias_sidebar, tags_sidebar = get_blog_sidebar_data(cursor)
    
    cursor.close()
    conn.close()
    return render_template('pagina_blog.html', 
                           posts=posts, 
                           categorias=categorias_sidebar, 
                           tags=tags_sidebar, # Passando as tags para o template
                           page_title=f"Resultados para '{query}'")

@app.route('/blog/<string:post_slug>')
def pagina_post_blog(post_slug):
    conn = None
    cursor = None
    post_encontrado = None
    categorias = []
    tags = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT p.*, c.nome as categoria_nome, c.slug as categoria_slug, u.username as autor_nome
            FROM posts p 
            LEFT JOIN categorias c ON p.categoria_id = c.id 
            LEFT JOIN usuarios u ON p.autor_id = u.id 
            WHERE p.slug = %s
        """, (post_slug,))
        post_encontrado = cursor.fetchone()

        if post_encontrado:
             # Modificado para receber categorias e tags
            categorias, tags = get_blog_sidebar_data(cursor)
    except Exception as err:
        app.logger.error(f"Erro ao buscar post {post_slug}: {err}")
        return render_template("500.html", page_title="Erro ao carregar Post"), 500
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    if post_encontrado:
        return render_template('pagina_post_individual.html',
                               post=post_encontrado,
                               categorias=categorias,
                               tags=tags, # Passando as tags para o template
                               page_title=post_encontrado["titulo"],
                               body_class="page-post-individual")
    else:
        return render_template('404.html',
                               page_title="Post não encontrado",
                               body_class="page-error"), 404

@app.route('/contato')
def pagina_contato():
    return render_template('pagina_contato.html', page_title="Fale Conosco", body_class="page-contato")

@app.route('/politica-de-privacidade')
def pagina_politica_privacidade():
    return render_template('pagina_politica_privacidade.html', page_title="Política de Privacidade", body_class="page-legal")

@app.route('/politica-de-cookies')
def pagina_politica_cookies():
    return render_template('pagina_politica_cookies.html', page_title="Política de Cookies", body_class="page-legal")

# --- Rota para Processar o Formulário de Contato ---
@app.route('/processar-contato', methods=['POST'])
def processar_contato():
    if request.method == 'POST':
        nome = request.form.get('nome_contato')
        email_usuario = request.form.get('email_usuario')
        assunto = request.form.get('assunto_contato')
        mensagem = request.form.get('mensagem_contato')

        # Validação simples no servidor
        if not nome or not email_usuario or not assunto or not mensagem:
            flash('Erro: Todos os campos do formulário são obrigatórios.', 'danger')
            return redirect(url_for('pagina_contato'))

        # Configurações do e-mail (lidas do .env)
        email_remetente = os.getenv('EMAIL_REMETENTE')
        senha_remetente = os.getenv('SENHA_EMAIL_REMETENTE')
        email_destinatario = os.getenv('EMAIL_DESTINATARIO_FEEDBACK')

        # --- DEBUG: Verificar variáveis ---
        print(f"DEBUG: EMAIL_REMETENTE lido do env = '{email_remetente}'")
        print(f"DEBUG: SENHA_EMAIL_REMETENTE lida do env = '{senha_remetente}' (Comprimento: {len(senha_remetente) if senha_remetente else 0})")
        print(f"DEBUG: EMAIL_DESTINATARIO_FEEDBACK lido do env = '{email_destinatario}'")
        # --- FIM DEBUG ---

        if not all([email_remetente, senha_remetente, email_destinatario]):
            print("ALERTA DE CONFIGURAÇÃO: As variáveis de ambiente para e-mail não estão definidas no arquivo .env!")
            flash('Desculpe, ocorreu um erro técnico ao tentar enviar sua mensagem. Por favor, tente mais tarde.', 'danger')
            return redirect(url_for('pagina_contato'))

        # Montar o corpo do e-mail
        corpo_email = f"""
        Nova mensagem recebida do formulário de contato do site RADAR PNCP:

        Nome: {nome}
        E-mail do Remetente: {email_usuario}
        Assunto: {assunto}
        -----------------------------------------
        Mensagem:
        {mensagem}
        -----------------------------------------
        """
        
        msg = MIMEText(corpo_email)
        msg['Subject'] = f'Novo Contato Radar PNCP: {assunto}'
        msg['From'] = email_remetente
        msg['To'] = email_destinatario
        if email_usuario:
            msg.add_header('reply-to', email_usuario)

        try:
            print(f"Tentando enviar e-mail de {email_remetente} para {email_destinatario} via smtp.gmail.com:465")
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(email_remetente, senha_remetente)
                server.sendmail(email_remetente, email_destinatario, msg.as_string())
            print("E-mail de contato enviado com sucesso!")
            flash('Sua mensagem foi enviada com sucesso! Entraremos em contato em breve, se necessário.', 'success')
        except smtplib.SMTPAuthenticationError:
            print("Erro de autenticação SMTP. Verifique usuário/senha ou configurações 'App menos seguro'/'Senha de App' do Gmail.")
            flash('Erro de autenticação ao enviar o e-mail. Verifique as configurações do servidor.', 'danger')
        except Exception as e:
            print(f"Ocorreu um erro geral ao enviar e-mail: {e}")
            flash(f'Desculpe, ocorreu um erro ao enviar sua mensagem. Tente novamente mais tarde.', 'danger')
        
        return redirect(url_for('pagina_contato'))

    return redirect(url_for('pagina_contato'))

 
# ===========================================---- ROTAS BACKEND (API Principal) ----============================================ #
def _build_licitacoes_query(filtros):
    """
    Constrói a cláusula WHERE para MariaDB, com busca case-insensitive.
    """
    condicoes_db = []
    parametros_db = []

    # --- Filtros normais (status, datas, etc.) ---
    if filtros.get('statusRadar'):
        condicoes_db.append("situacaoReal = %s")
        parametros_db.append(filtros['statusRadar'])
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

    # --- Filtros de Texto ---
    campos_texto_busca = ["objetoCompra", "orgaoEntidadeRazaoSocial", "unidadeOrgaoNome", "numeroControlePNCP", "unidadeOrgaoMunicipioNome", "unidadeOrgaoUfNome", "orgaoEntidadeCnpj"]
    
    # Inclusão
    if filtros.get('palavrasChave'):
        for palavra in filtros['palavrasChave']:
            # Bloco (campo1 LIKE %p% COLLATE utf8mb4_general_ci OR ...)
            like_exprs = [f"{campo} LIKE %s COLLATE utf8mb4_general_ci" for campo in campos_texto_busca]
            condicoes_db.append(f"({' OR '.join(like_exprs)})")
            parametros_db.extend([f"%{palavra}%"] * len(campos_texto_busca))
    
    # Exclusão
    if filtros.get('excluirPalavras'):
        for palavra in filtros['excluirPalavras']:
            # Bloco NOT (campo1 LIKE %p% COLLATE utf8mb4_general_ci OR ...)
            like_exprs = [f"{campo} LIKE %s COLLATE utf8mb4_general_ci" for campo in campos_texto_busca]
            condicoes_db.append(f"NOT ({' OR '.join(like_exprs)})")
            parametros_db.extend([f"%{palavra}%"] * len(campos_texto_busca))

    query_where = ""
    if condicoes_db:
        query_where = " WHERE " + " AND ".join(condicoes_db)
    
    return query_where, parametros_db

@app.route('/licitacoes', methods=['GET'])
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

        # Executa a query de contagem total
        cursor_contagem.execute(query_contagem, parametros_db)
        resultado_contagem = cursor_contagem.fetchone()
        if resultado_contagem:
            total_registros = resultado_contagem['total']

        # Executa a query de dados com paginação
        parametros_dados_sql = parametros_db + [por_pagina, (pagina - 1) * por_pagina]
        cursor_dados.execute(query_select_dados, parametros_dados_sql)
        licitacoes_lista_bruta = cursor_dados.fetchall()
        
        # FORMATAÇÃO AQUI
        licitacoes_lista = [formatar_datas_para_json(row) for row in licitacoes_lista_bruta]


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


@app.route('/licitacao/<path:numero_controle_pncp>', methods=['GET'])
def get_detalhe_licitacao(numero_controle_pncp):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    query_licitacao_principal = "SELECT * FROM licitacoes WHERE numeroControlePNCP = %s"
    cursor.execute(query_licitacao_principal, (numero_controle_pncp,))
    licitacao_principal_row = cursor.fetchone()

    if not licitacao_principal_row:
        conn.close()
        return jsonify({"erro": "Licitação não encontrada", "numeroControlePNCP": numero_controle_pncp}), 404

    licitacao_principal_dict = formatar_datas_para_json(licitacao_principal_row)
    licitacao_id_local = licitacao_principal_dict['id']

    query_itens = "SELECT * FROM itens_licitacao WHERE licitacao_id = %s"
    cursor.execute(query_itens, (licitacao_id_local,))
    itens_rows = cursor.fetchall()
    itens_lista = [formatar_datas_para_json(row) for row in itens_rows]

    query_arquivos = "SELECT * FROM arquivos_licitacao WHERE licitacao_id = %s"
    cursor.execute(query_arquivos, (licitacao_id_local,))
    arquivos_rows = cursor.fetchall()
    arquivos_lista = [formatar_datas_para_json(row) for row in arquivos_rows]

    conn.close()

    resposta_final = {
        "licitacao": licitacao_principal_dict,
        "itens": itens_lista,
        "arquivos": arquivos_lista
    }
    return jsonify(resposta_final)

@app.route('/referencias/modalidades', methods=['GET'])
def get_modalidades_referencia():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT DISTINCT modalidadeId, modalidadeNome FROM licitacoes ORDER BY modalidadeNome")
    modalidades = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(modalidades)

@app.route('/referencias/statuscompra', methods=['GET'])
def get_statuscompra_referencia():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT DISTINCT situacaoCompraId, situacaoCompraNome FROM licitacoes ORDER BY situacaoCompraNome")
    status_compra = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(status_compra)

@app.route('/referencias/statusradar', methods=['GET'])
def get_statusradar_referencia():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT DISTINCT situacaoReal FROM licitacoes WHERE situacaoReal IS NOT NULL ORDER BY situacaoReal")
    status_radar_rows = cursor.fetchall()
    status_radar = [{"id": row['situacaoReal'], "nome": row['situacaoReal']} for row in status_radar_rows]
    conn.close()
    return jsonify(status_radar)

# --- Rota API IBGE (mantida do frontend) ---
@app.route('/api/ibge/municipios/<uf_sigla>', methods=['GET'])
def api_get_municipios_ibge(uf_sigla):
    if not uf_sigla or len(uf_sigla) != 2 or not uf_sigla.isalpha():
        return jsonify({"erro": "Sigla da UF inválida."}), 400
    
    ibge_api_url = f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf_sigla.upper()}/municipios"
    print(f"Frontend API: Chamando IBGE API: {ibge_api_url}")
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

# --- Rotas API Frontend (adaptadas para chamar funções locais) ---
@app.route('/api/frontend/licitacoes', methods=['GET'])
def api_get_licitacoes():
    params_from_js = request.args.to_dict(flat=False)
    print(f"Frontend API: Chamando /licitacoes com params: {params_from_js}")
    return get_licitacoes()

@app.route('/api/frontend/licitacao/<path:pncp_id>', methods=['GET'])
def api_get_licitacao_detalhes(pncp_id):
    print(f"Frontend API: Chamando /licitacao/{pncp_id}")
    return get_detalhe_licitacao(pncp_id)

@app.route('/api/frontend/referencias/modalidades', methods=['GET'])
def api_get_referencia_modalidades():
    print("Frontend API: Chamando /referencias/modalidades")
    return get_modalidades_referencia()

@app.route('/api/frontend/referencias/statusradar', methods=['GET'])
def api_get_referencia_statusradar():
    print("Frontend API: Chamando /referencias/statusradar")
    return get_statusradar_referencia()

@app.route('/api/frontend/referencias/statuscompra', methods=['GET'])
def api_get_referencia_statuscompra():
    print("Frontend API: Chamando /referencias/statuscompra")
    return get_statuscompra_referencia()

           
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

# =========================================================================
# CONFIGURAÇÃO DO FLASK-ADMIN
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
        cursor.execute("""
            SELECT p.id, p.titulo, p.slug, p.data_publicacao, u.username as autor_nome 
            FROM posts p 
            LEFT JOIN usuarios u ON p.autor_id = u.id 
            ORDER BY p.data_publicacao DESC
        """)
        posts = cursor.fetchall()
        cursor.close()
        conn.close()
        return self.render('admin/posts_list.html', posts=posts)

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
                if post_id:
                    # UPDATE
                    query = """UPDATE posts SET titulo=%s, slug=%s, resumo=%s, conteudo_completo=%s, imagem_destaque=%s, categoria_id=%s, is_featured=%s WHERE id=%s"""
                    cursor.execute(query, (titulo, slug_limpo, resumo, conteudo_sanitizado, imagem_destaque, categoria_id, is_featured, post_id))
                else:
                    # INSERT
                    query = """INSERT INTO posts (titulo, slug, resumo, conteudo_completo, autor_id, imagem_destaque, categoria_id, is_featured) 
                               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
                    cursor.execute(query, (titulo, slug_limpo, resumo, conteudo_sanitizado, current_user.id, imagem_destaque, categoria_id, is_featured))
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

# =========================================================================

# =========================================================================
# BLOCO DE CÓDIGO 5: VIEW DE ADMINISTRAÇÃO PARA CATEGORIAS E TAGS
# =========================================================================
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

admin.add_view(PostsView(name='Posts', endpoint='posts'))
admin.add_view(CategoriaView(name='Categorias', endpoint='categorias'))
admin.add_view(TagView(name='Tags', endpoint='tags'))

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    # Em produção real, você não usaria app.run(), mas sim um servidor WSGI como Gunicorn.
    # O debug=True também deve ser False ou controlado por uma variável de ambiente em produção.
    is_debug_mode = os.getenv('FLASK_DEBUG', '0') == '1'
    app.run(debug=is_debug_mode, host='0.0.0.0', port=port) # Modo debug esta configurado no arquivo .env