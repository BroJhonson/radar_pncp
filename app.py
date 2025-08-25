import mysql.connector 
from mysql.connector import errors # Para tratamento de erros
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
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

load_dotenv()  # Carrega as variáveis do arquivo .env para o ambiente

# --- Configurações ---
app = Flask(__name__)
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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'database.db')

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
    # Você pode logar o erro 'e' aqui se quiser
    print(f"Erro 404 - Página não encontrada: {request.url} (Erro original: {e})")
    return render_template('404.html', 
                           page_title="Página Não Encontrada", 
                           body_class="page-error"), 404

@app.errorhandler(500)
def erro_interno_servidor_erro(e):
    # Em um ambiente de produção, NUNCA deve vazar detalhes do erro 'e' para o usuário.
    # O template 500.html deve ter uma mensagem genérica.
    print(f"Erro 500 detectado: {e} para a URL: {request.url}") # Para debug local
    return render_template('500.html', 
                           page_title="Erro Interno no Servidor", 
                           body_class="page-error"), 500


# --- Dados de exemplo para o blog ---
posts_blog_exemplo = [
    {
        "id": 1,
        "slug": "como-encontrar-licitacoes-por-palavra-chave",
        "titulo": "Como Encontrar Licitações por Palavra-chave",
        "data": "06/06/2024",
        "resumo": "Aprenda a usar filtros estratégicos para encontrar licitações perfeitas para o seu negócio.",
        "imagem_destaque": "artigo1.jpg",
        "conteudo_completo": """<h2>Entendendo a Busca por Palavra-Chave</h2>
            <p>A busca por palavra-chave é uma das ferramentas mais poderosas ao procurar licitações. 
            No entanto, para ser eficaz, é preciso estratégia...</p>
            <p>Imagine que você vende 'equipamentos de informática'. Digitar apenas 'informática' pode trazer
            milhares de resultados, incluindo serviços de manutenção que não são seu foco.</p>
            <h3>Dicas para Otimizar sua Busca:</h3>
            <ul>
                <li><strong>Seja Específico:</strong> Em vez de "material", tente "material de escritório" ou "material de construção".</li>
                <li><strong>Use Múltiplas Palavras (com vírgula no Radar PNCP):</strong> "consultoria ambiental, licenciamento" para encontrar ambos.</li>
                <li><strong>Pense em Sinônimos:</strong> Se você oferece "treinamento", tente também "capacitação", "curso".</li>
                <li><strong>Utilize Palavras de Exclusão:</strong> Se você vende produtos novos, pode querer excluir termos como "usado" ou "reparo".</li>
            </ul>
            <p>No nosso sistema Radar PNCP, a interface de tags para palavras-chave (que estamos desenvolvendo!) 
            facilitará ainda mais esse processo, permitindo adicionar e remover termos de forma visual e intuitiva.</p>
            <p>Lembre-se também de combinar o filtro de palavras-chave com outros filtros como UF, modalidade e status 
            para refinar ainda mais seus resultados e encontrar as oportunidades que realmente importam para o seu negócio.</p>
        """
    },
    {
        "id": 2,
        "slug": "nova-lei-de-licitacoes-o-que-voce-precisa-saber",
        "titulo": "Nova Lei de Licitações: O Que Você Precisa Saber",
        "data": "07/06/2024",
        "resumo": "Entenda o impacto da nova legislação e como se adaptar a tempo para aproveitar as mudanças.",
        "imagem_destaque": "artigo2.jpg",
        "conteudo_completo": """<h2>Principais Mudanças da Lei 14.133/2021</h2>
            <p>A Nova Lei de Licitações e Contratos Administrativos (Lei nº 14.133/2021) trouxe modernização e 
            novos paradigmas para as compras públicas no Brasil...</p>
            <p>Alguns pontos de destaque incluem:</p>
            <ul>
                <li><strong>Novas Modalidades:</strong> Como o diálogo competitivo.</li>
                <li><strong>Portal Nacional de Contratações Públicas (PNCP):</strong> Centralização das informações.</li>
                <li><strong>Foco no Planejamento:</strong> Ênfase na fase preparatória das licitações.</li>
                <li><strong>Critérios de Julgamento:</strong> Além do menor preço, o maior desconto, melhor técnica ou conteúdo artístico, etc.</li>
            </ul>
            <p>Adaptar-se a essa nova realidade é fundamental. Isso inclui revisar processos internos, capacitar equipes
            e entender os novos instrumentos como o Estudo Técnico Preliminar (ETP) e o Termo de Referência.</p>
        """
    },
    {
        "id": 3,
        "slug": "erros-comuns-em-propostas-de-licitacao",
        "titulo": "Erros Comuns em Propostas de Licitação e Como Evitá-los",
        "data": "08/06/2024",
        "resumo": "Evite armadilhas que podem desclassificar sua empresa nas licitações públicas.",
        "imagem_destaque": "artigo3.jpg",
        "conteudo_completo": """<h2>Não Deixe que Pequenos Erros Custem Grandes Oportunidades</h2>
            <p>Participar de licitações pode ser um processo complexo, e pequenos descuidos na elaboração da proposta
            podem levar à desclassificação. Conhecer os erros mais comuns é o primeiro passo para evitá-los.</p>
            <h3>Principais Armadilhas:</h3>
            <ol>
                <li><strong>Documentação Incompleta ou Vencida:</strong> Certidões negativas, balanços, atestados de capacidade técnica. Tudo deve estar rigorosamente em dia e conforme solicitado no edital.</li>
                <li><strong>Não Atender às Especificações Técnicas:</strong> O produto ou serviço ofertado deve corresponder exatamente ao que foi descrito no Termo de Referência ou Projeto Básico. Qualquer desvio pode ser motivo para desclassificação.</li>
                <li><strong>Erros na Planilha de Preços:</strong> Cálculos incorretos, omissão de custos, ou preços inexequíveis (muito baixos) ou excessivos.</li>
                <li><strong>Perda de Prazos:</strong> Tanto para envio de propostas quanto para recursos ou envio de documentação complementar.</li>
                <li><strong>Assinaturas Ausentes ou Inválidas:</strong> Propostas e declarações devem ser devidamente assinadas por quem tem poderes para tal.</li>
            </ol>
            <p>A atenção aos detalhes, uma leitura minuciosa do edital e um bom planejamento são seus maiores aliados para evitar esses erros e aumentar suas chances de sucesso.</p>
        """
    }
]

# --- Rotas Frontend (Renderização de Páginas) ---
@app.route('/')
def inicio():
    return render_template('index.html', page_title="Bem-vindo ao RADAR PNCP", body_class="page-home")

@app.route('/radarPNCP')
def buscador_licitacoes():
    return render_template('radar.html', page_title="Buscar Licitações - RADAR PNCP", body_class="page-busca-licitacoes")

@app.route('/blog')
def pagina_blog():
    return render_template('pagina_blog.html', posts=posts_blog_exemplo, page_title="Nosso Blog", body_class="page-blog")

@app.route('/blog/<string:post_slug>')
def pagina_post_blog(post_slug):
    print(f"Recebido slug da URL: '{post_slug}'")  # DEBUG
    post_encontrado = None
    for p_exemplo in posts_blog_exemplo:
        print(f"Comparando '{post_slug}' com slug do post da lista: '{p_exemplo.get('slug')}'")  # DEBUG
        if p_exemplo.get("slug") == post_slug:
            post_encontrado = p_exemplo
            print(f"Match! Post encontrado: {p_exemplo['titulo']}")  # DEBUG
            break
    if post_encontrado:
        return render_template('pagina_post_individual.html',
                               post=post_encontrado,
                               page_title=post_encontrado["titulo"],
                               body_class="page-post-individual")
    else:
        print(f"Post com slug '{post_slug}' NÃO encontrado na lista!")  # DEBUG
        return render_template('404.html', page_title="Post não encontrado", body_class="page-error"), 404

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

 
if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    # Em produção real, você não usaria app.run(), mas sim um servidor WSGI como Gunicorn.
    # O debug=True também deve ser False ou controlado por uma variável de ambiente em produção.
    is_debug_mode = os.getenv('FLASK_DEBUG', '0') == '1'
    app.run(debug=is_debug_mode, host='0.0.0.0', port=port) # Modo debug esta configurado no arquivo .env