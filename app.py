from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import sqlite3
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

# --- Funções Auxiliares para o Banco de Dados ---
def get_db_connection():
    """
    Retorna uma conexão com o banco de dados SQLite com otimizações para produção.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH, timeout=10) # Aumenta o timeout de conexão base
        conn.row_factory = sqlite3.Row

        # Aplicando PRAGMAs recomendados para performance e concorrência
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 5000;") # 5000ms = 5s
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA temp_store = MEMORY;")
        conn.execute("PRAGMA cache_size = -20000;") # ~20MB de cache por conexão

        logger.debug("Conexão com SQLite DB estabelecida com PRAGMAs otimizados.")
    except sqlite3.Error as e:
        logger.critical(f"DB_CONNECTION: Falha CRÍTICA ao conectar ou configurar o banco de dados: {e}")
        if conn:
            conn.close() # Tenta fechar se a conexão foi aberta mas o pragma falhou
        return None
    return conn

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

 
# ===========================================---- ROTAS BACKEND (API Principal) ----============================================
@app.route('/licitacoes', methods=['GET'])
def get_licitacoes():
    filtros = {
        'ufs': request.args.getlist('uf'),
        'modalidadesId': request.args.getlist('modalidadeId', type=int),
        'statusId': request.args.get('status', default=None, type=int),
        'dataPubInicio': request.args.get('dataPubInicio', default=None, type=str),
        'dataPubFim': request.args.get('dataPubFim', default=None, type=str),
        'valorMin': request.args.get('valorMin', default=None, type=float),
        'valorMax': request.args.get('valorMax', default=None, type=float),
        'municipiosNome': request.args.getlist('municipioNome'),
        'dataAtualizacaoInicio': request.args.get('dataAtualizacaoInicio', default=None, type=str),
        'dataAtualizacaoFim': request.args.get('dataAtualizacaoFim', default=None, type=str),
        'palavrasChave': request.args.getlist('palavraChave'),
        'excluirPalavras': request.args.getlist('excluirPalavra'),
        'anoCompra': request.args.get('anoCompra', type=int),
        'cnpjOrgao': request.args.get('cnpjOrgao'),
        'statusRadar': request.args.get('statusRadar', default=None, type=str)
    }

    pagina = request.args.get('pagina', default=1, type=int)
    if pagina < 1:
        pagina = 1
    por_pagina = request.args.get('porPagina', default=20, type=int)
    if por_pagina < 1:
        por_pagina = 20
    elif por_pagina > 100:
        por_pagina = 100

    offset = (pagina - 1) * por_pagina

    orderBy_param = request.args.get('orderBy', default='dataPublicacaoPncp', type=str)
    orderDir_param = request.args.get('orderDir', default='DESC', type=str).upper()

    # Validação para evitar injeção de SQL
    campos_validos_ordenacao = [
        'dataPublicacaoPncp', 'dataAtualizacao', 'valorTotalEstimado',
        'dataAberturaProposta', 'dataEncerramentoProposta', 'modalidadeNome',
        'orgaoEntidadeRazaoSocial', 'unidadeOrgaoMunicipioNome',
        'situacaoReal'
    ]

    if orderBy_param not in campos_validos_ordenacao:
        return jsonify({
            "erro": "Parâmetro de ordenação inválido",
            "detalhes": f"O valor '{orderBy_param}' para 'orderBy' não é válido. Campos válidos: {', '.join(campos_validos_ordenacao)}."
        }), 400

    if orderDir_param not in ['ASC', 'DESC']:
        return jsonify({
            "erro": "Parâmetro de direção de ordenação inválido",
            "detalhes": f"O valor '{orderDir_param}' para 'orderDir' não é válido. Use 'ASC' ou 'DESC'."
        }), 400

    condicoes_db = []
    parametros_db = []

    if filtros['statusRadar']:
        condicoes_db.append("situacaoReal = ?")
        parametros_db.append(filtros['statusRadar'])
    elif filtros['statusId'] is not None:
        condicoes_db.append("situacaoCompraId = ?")
        parametros_db.append(filtros['statusId'])

    if filtros['ufs']:
        placeholders = ', '.join(['?'] * len(filtros['ufs']))
        condicoes_db.append(f"unidadeOrgaoUfSigla IN ({placeholders})")
        parametros_db.extend([uf.upper() for uf in filtros['ufs']])

    if filtros['modalidadesId']:
        placeholders = ', '.join(['?'] * len(filtros['modalidadesId']))
        condicoes_db.append(f"modalidadeId IN ({placeholders})")
        parametros_db.extend(filtros['modalidadesId'])

    if filtros['excluirPalavras']:
        campos_texto_busca = [
            "objetoCompra", "orgaoEntidadeRazaoSocial", "unidadeOrgaoNome",
            "numeroControlePNCP", "unidadeOrgaoMunicipioNome", "unidadeOrgaoUfNome",
            "CAST(unidadeOrgaoCodigoIbge AS TEXT)", "orgaoEntidadeCnpj"
        ]
        for palavra_excluir in filtros['excluirPalavras']:
            termo_excluir = f"%{palavra_excluir}%"
            condicoes_palavra_excluir_and = []
            for campo in campos_texto_busca:
                condicoes_palavra_excluir_and.append(f"COALESCE({campo}, '') NOT LIKE ?")
                parametros_db.append(termo_excluir)
            if condicoes_palavra_excluir_and:
                condicoes_db.append(f"({' AND '.join(condicoes_palavra_excluir_and)})")

    if filtros['palavrasChave']:
        campos_texto_busca = [
            "objetoCompra", "orgaoEntidadeRazaoSocial", "unidadeOrgaoNome",
            "numeroControlePNCP", "unidadeOrgaoMunicipioNome", "unidadeOrgaoUfNome",
            "CAST(unidadeOrgaoCodigoIbge AS TEXT)", "orgaoEntidadeCnpj"
        ]
        sub_condicoes_palavras_or_geral = []
        for palavra_chave in filtros['palavrasChave']:
            termo_like = f"%{palavra_chave}%"
            condicoes_campos_or_para_palavra = []
            for campo in campos_texto_busca:
                condicoes_campos_or_para_palavra.append(f"COALESCE({campo}, '') LIKE ?")
                parametros_db.append(termo_like)
            if condicoes_campos_or_para_palavra:
                sub_condicoes_palavras_or_geral.append(f"({' OR '.join(condicoes_campos_or_para_palavra)})")
        if sub_condicoes_palavras_or_geral:
            condicoes_db.append(f"({' OR '.join(sub_condicoes_palavras_or_geral)})")

    if filtros['dataPubInicio']:
        condicoes_db.append("dataPublicacaoPncp >= ?")
        parametros_db.append(filtros['dataPubInicio'])
    if filtros['dataPubFim']:
        condicoes_db.append("dataPublicacaoPncp <= ?")
        parametros_db.append(filtros['dataPubFim'])

    if filtros['valorMin'] is not None:
        condicoes_db.append("valorTotalEstimado >= ?")
        parametros_db.append(filtros['valorMin'])
    if filtros['valorMax'] is not None:
        condicoes_db.append("valorTotalEstimado <= ?")
        parametros_db.append(filtros['valorMax'])

    if filtros['dataAtualizacaoInicio']:
        condicoes_db.append("dataAtualizacao >= ?")
        parametros_db.append(filtros['dataAtualizacaoInicio'])
    if filtros['dataAtualizacaoFim']:
        condicoes_db.append("dataAtualizacao <= ?")
        parametros_db.append(filtros['dataAtualizacaoFim'])

    if filtros['anoCompra'] is not None:
        condicoes_db.append("anoCompra = ?")
        parametros_db.append(filtros['anoCompra'])

    if filtros['cnpjOrgao']:
        condicoes_db.append("orgaoEntidadeCnpj = ?")
        parametros_db.append(filtros['cnpjOrgao'])

    if filtros['municipiosNome']:
        sub_condicoes_municipio = []
        for nome_mun in filtros['municipiosNome']:
            termo_mun = f"%{nome_mun.upper()}%"
            sub_condicoes_municipio.append("UPPER(unidadeOrgaoMunicipioNome) LIKE ?")
            parametros_db.append(termo_mun)
        if sub_condicoes_municipio:
            condicoes_db.append(f"({ ' OR '.join(sub_condicoes_municipio) })")

    query_select_dados = "SELECT * FROM licitacoes"
    query_select_contagem = "SELECT COUNT(id) FROM licitacoes"
    query_where = ""
    if condicoes_db:
        query_where = " WHERE " + " AND ".join(condicoes_db)

    query_order_limit_offset_dados = f" ORDER BY {orderBy_param} {orderDir_param} LIMIT ? OFFSET ?"

    sql_query_dados_final = query_select_dados + query_where + query_order_limit_offset_dados
    parametros_dados_sql_final = parametros_db + [por_pagina, offset]

    sql_query_contagem_final = query_select_contagem + query_where

    conn = get_db_connection()
    cursor = conn.cursor()
    licitacoes_lista = []
    total_registros = 0
    try:
        cursor.execute(sql_query_dados_final, parametros_dados_sql_final)
        licitacoes_rows = cursor.fetchall()
        licitacoes_lista = [dict(row) for row in licitacoes_rows]

        cursor.execute(sql_query_contagem_final, parametros_db)
        total_registros_fetch = cursor.fetchone()
        if total_registros_fetch:
            total_registros = total_registros_fetch[0]

    except sqlite3.Error as e:
        print(f"Erro ao buscar/contar no banco local: {e}")
        if conn:
            conn.close()
        return jsonify({"erro": "Erro interno ao processar sua busca.", "detalhes": str(e)}), 500
    finally:
        if conn:
            conn.close()

    total_paginas_final = (total_registros + por_pagina - 1) // por_pagina if por_pagina > 0 and total_registros > 0 else 0
    if total_registros == 0:
        total_paginas_final = 0

    return jsonify({
        "pagina_atual": pagina,
        "por_pagina": por_pagina,
        "total_registros": total_registros,
        "total_paginas": total_paginas_final,
        "origem_dados": "banco_local_janela_anual",
        "licitacoes": licitacoes_lista
    })

@app.route('/licitacao/<path:numero_controle_pncp>', methods=['GET'])
def get_detalhe_licitacao(numero_controle_pncp):
    conn = get_db_connection()
    cursor = conn.cursor()
    query_licitacao_principal = "SELECT * FROM licitacoes WHERE numeroControlePNCP = ?"
    cursor.execute(query_licitacao_principal, (numero_controle_pncp,))
    licitacao_principal_row = cursor.fetchone()

    if not licitacao_principal_row:
        conn.close()
        return jsonify({"erro": "Licitação não encontrada", "numeroControlePNCP": numero_controle_pncp}), 404

    licitacao_principal_dict = dict(licitacao_principal_row)
    licitacao_id_local = licitacao_principal_dict['id']

    query_itens = "SELECT * FROM itens_licitacao WHERE licitacao_id = ?"
    cursor.execute(query_itens, (licitacao_id_local,))
    itens_rows = cursor.fetchall()
    itens_lista = [dict(row) for row in itens_rows]

    query_arquivos = "SELECT * FROM arquivos_licitacao WHERE licitacao_id = ?"
    cursor.execute(query_arquivos, (licitacao_id_local,))
    arquivos_rows = cursor.fetchall()
    arquivos_lista = [dict(row) for row in arquivos_rows]

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
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT modalidadeId, modalidadeNome FROM licitacoes ORDER BY modalidadeNome")
    modalidades = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(modalidades)

@app.route('/referencias/statuscompra', methods=['GET'])
def get_statuscompra_referencia():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT situacaoCompraId, situacaoCompraNome FROM licitacoes ORDER BY situacaoCompraNome")
    status_compra = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(status_compra)

@app.route('/referencias/statusradar', methods=['GET'])
def get_statusradar_referencia():
    conn = get_db_connection()
    cursor = conn.cursor()
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
    filtros = {
        'ufs': request.args.getlist('uf'),
        'modalidadesId': request.args.getlist('modalidadeId', type=int),
        'statusRadar': request.args.get('statusRadar', default=None, type=str),
        'dataPubInicio': request.args.get('dataPubInicio', default=None, type=str),
        'dataPubFim': request.args.get('dataPubFim', default=None, type=str),
        'valorMin': request.args.get('valorMin', default=None, type=float),
        'valorMax': request.args.get('valorMax', default=None, type=float),
        'municipiosNome': request.args.getlist('municipioNome'),
        'dataAtualizacaoInicio': request.args.get('dataAtualizacaoInicio', default=None, type=str),
        'dataAtualizacaoFim': request.args.get('dataAtualizacaoFim', default=None, type=str),
        'palavrasChave': request.args.getlist('palavraChave'),
        'excluirPalavras': request.args.getlist('excluirPalavra'),
        'statusId': request.args.get('status', default=None, type=int),
        'anoCompra': request.args.get('anoCompra', type=int),
        'cnpjOrgao': request.args.get('cnpjOrgao'),
    }
    orderBy_param = request.args.get('orderBy', default='dataPublicacaoPncp', type=str)
    orderDir_param = request.args.get('orderDir', default='DESC', type=str).upper()

    condicoes_db = []
    parametros_db = []
    
    if filtros['statusRadar']:
        condicoes_db.append("situacaoReal = ?")
        parametros_db.append(filtros['statusRadar'])
    elif filtros['statusId'] is not None:
        condicoes_db.append("situacaoCompraId = ?")
        parametros_db.append(filtros['statusId'])

    if filtros['ufs']:
        placeholders = ', '.join(['?'] * len(filtros['ufs']))
        condicoes_db.append(f"unidadeOrgaoUfSigla IN ({placeholders})")
        parametros_db.extend([uf.upper() for uf in filtros['ufs']])

    if filtros['modalidadesId']:
        placeholders = ', '.join(['?'] * len(filtros['modalidadesId']))
        condicoes_db.append(f"modalidadeId IN ({placeholders})")
        parametros_db.extend(filtros['modalidadesId'])

    if filtros['excluirPalavras']:
        campos_texto_busca = [
            "objetoCompra", "orgaoEntidadeRazaoSocial", "unidadeOrgaoNome",
            "numeroControlePNCP", "unidadeOrgaoMunicipioNome", "unidadeOrgaoUfNome",
            "CAST(unidadeOrgaoCodigoIbge AS TEXT)", "orgaoEntidadeCnpj"
        ]
        for palavra_excluir in filtros['excluirPalavras']:
            termo_excluir = f"%{palavra_excluir}%"
            condicoes_palavra_excluir_and = []
            for campo in campos_texto_busca:
                condicoes_palavra_excluir_and.append(f"COALESCE({campo}, '') NOT LIKE ?")
                parametros_db.append(termo_excluir)
            if condicoes_palavra_excluir_and:
                condicoes_db.append(f"({' AND '.join(condicoes_palavra_excluir_and)})")

    if filtros['palavrasChave']:
        campos_texto_busca = [
            "objetoCompra", "orgaoEntidadeRazaoSocial", "unidadeOrgaoNome",
            "numeroControlePNCP", "unidadeOrgaoMunicipioNome", "unidadeOrgaoUfNome",
            "CAST(unidadeOrgaoCodigoIbge AS TEXT)", "orgaoEntidadeCnpj"
        ]
        sub_condicoes_palavras_or_geral = []
        for palavra_chave in filtros['palavrasChave']:
            termo_like = f"%{palavra_chave}%"
            condicoes_campos_or_para_palavra = []
            for campo in campos_texto_busca:
                condicoes_campos_or_para_palavra.append(f"COALESCE({campo}, '') LIKE ?")
                parametros_db.append(termo_like)
            if condicoes_campos_or_para_palavra:
                sub_condicoes_palavras_or_geral.append(f"({' OR '.join(condicoes_campos_or_para_palavra)})")
        if sub_condicoes_palavras_or_geral:
            condicoes_db.append(f"({' OR '.join(sub_condicoes_palavras_or_geral)})")

    if filtros['dataPubInicio']:
        condicoes_db.append("dataPublicacaoPncp >= ?")
        parametros_db.append(filtros['dataPubInicio'])
    if filtros['dataPubFim']:
        condicoes_db.append("dataPublicacaoPncp <= ?")
        parametros_db.append(filtros['dataPubFim'])

    if filtros['valorMin'] is not None:
        condicoes_db.append("valorTotalEstimado >= ?")
        parametros_db.append(filtros['valorMin'])
    if filtros['valorMax'] is not None:
        condicoes_db.append("valorTotalEstimado <= ?")
        parametros_db.append(filtros['valorMax'])

    if filtros['dataAtualizacaoInicio']:
        condicoes_db.append("dataAtualizacao >= ?")
        parametros_db.append(filtros['dataAtualizacaoInicio'])
    if filtros['dataAtualizacaoFim']:
        condicoes_db.append("dataAtualizacao <= ?")
        parametros_db.append(filtros['dataAtualizacaoFim'])

    if filtros['anoCompra'] is not None:
        condicoes_db.append("anoCompra = ?")
        parametros_db.append(filtros['anoCompra'])

    if filtros['cnpjOrgao']:
        condicoes_db.append("orgaoEntidadeCnpj = ?")
        parametros_db.append(filtros['cnpjOrgao'])

    if filtros['municipiosNome']:
        sub_condicoes_municipio = []
        for nome_mun in filtros['municipiosNome']:
            termo_mun = f"%{nome_mun.upper()}%"
            sub_condicoes_municipio.append("UPPER(unidadeOrgaoMunicipioNome) LIKE ?")
            parametros_db.append(termo_mun)
        if sub_condicoes_municipio:
            condicoes_db.append(f"({ ' OR '.join(sub_condicoes_municipio) })")

    # 2. Conecte ao banco e faça a busca SEM paginação
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query_select = "SELECT * FROM licitacoes"
    query_where = ""
    if condicoes_db:
        query_where = " WHERE " + " AND ".join(condicoes_db)
    
    # A ÚNICA DIFERENÇA: SEM LIMIT E OFFSET
    query_order = f" ORDER BY {orderBy_param} {orderDir_param}"
    sql_query_final = query_select + query_where + query_order
 
    try:
        cursor.execute(sql_query_final, parametros_db)
        licitacoes_rows = cursor.fetchall()
        licitacoes = [dict(row) for row in licitacoes_rows]
    except sqlite3.Error as e:
        print(f"Erro ao exportar CSV: {e}")
        return jsonify({"erro": "Erro ao buscar dados para exportação"}), 500
    finally:
        if conn:
            conn.close()

    # 3. Gere o CSV em memória
    output = io.StringIO()
    # Usamos QUOTE_ALL para garantir que valores com ';' ou quebras de linha sejam tratados corretamente
    writer = csv.writer(output, delimiter=';', lineterminator='\n', quoting=csv.QUOTE_ALL)
    
    # Escreve o cabeçalho
    writer.writerow(['Data Atualizacao', 'Municipio/UF', 'Orgao', 'Modalidade', 'Status', 'Valor Estimado (R$)', 'Objeto da Compra', 'Link PNCP'])

    # Escreve os dados
    for lic in licitacoes:
        municipio_uf = f"{lic.get('unidadeOrgaoMunicipioNome', '')}/{lic.get('unidadeOrgaoUfSigla', '')}"
        # Formata o valor para o padrão brasileiro (vírgula como decimal)
        valor_str = 'N/I'
        if lic.get('valorTotalEstimado') is not None:
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

    # 4. Prepara a resposta para download
    output.seek(0)    
    return Response(
        output.getvalue().encode('utf-8-sig'), # 'utf-8-sig' é melhor para compatibilidade com Excel
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=radar_pncp_licitacoes.csv"}
    )

 
if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    # Em produção real, você não usaria app.run(), mas sim um servidor WSGI como Gunicorn.
    # O debug=True também deve ser False ou controlado por uma variável de ambiente em produção.
    is_debug_mode = os.getenv('FLASK_DEBUG', '0') == '1'
    app.run(debug=is_debug_mode, host='0.0.0.0', port=port) # Modo debug esta configurado no arquivo .env

# --- venv/scripts/activate
# --- python app.py