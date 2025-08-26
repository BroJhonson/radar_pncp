# python sync_api.py
# Essa é a parte principal do backend que lida com a sincronização das licitações do PNCP com o banco de dados local. 

import mysql.connector
from mysql.connector import errors # (Para tratamento de erros de conexão e SQL)
import requests # (Para fazer requisições HTTP)
import json # (Para lidar com dados JSON da API, embora 'requests' já faça muito disso)
import os # (Para caminhos de arquivo)
import time
from datetime import datetime, date, timedelta # (Para trabalhar com datas)
import logging 
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type # Importar de tenacity para usar Retentativas
from dotenv import load_dotenv # Importe a biblioteca

load_dotenv()

# ======= Configuração do Logging =======
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) # Define o nível mínimo de log que este logger irá processar
# Cria um handler para escrever logs no console (stdout)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO) # Logs INFO e acima irão para o console
# Cria um handler para escrever logs em um arquivo
# O arquivo será 'sync_api.log' na mesma pasta do script.
log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sync_api.log') # isso garante que o log será salvo no mesmo diretório do script
file_handler = logging.FileHandler(log_file_path, mode='a') # 'a' para append
file_handler.setLevel(logging.ERROR) # Logs Error e acima irão para o arquivo
# Cria um formatador para definir o formato das mensagens de log
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)
# Adiciona os handlers ao logger
# Evita adicionar handlers duplicados se o script for importado ou reconfigurado
if not logger.handlers:
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
# --- Fim da Configuração do Logging ---


# ======= Configuração de Retentativas para Chamadas de API =======
# Define quais exceções do 'requests' devem acionar uma retentativa
RETRYABLE_REQUESTS_EXCEPTIONS = (
    requests.exceptions.Timeout,
    requests.exceptions.ConnectionError,
    requests.exceptions.HTTPError, # Vamos incluir HTTPError, mas filtrar por status codes abaixo
)
# Define quais status codes HTTP devem acionar uma retentativa
# (ex: erros de servidor, rate limiting, mas não erros de cliente como 404 ou 400)
RETRYABLE_STATUS_CODES = {500, 502, 503, 504, 429} # Internal Server Error, Bad Gateway, Service Unavailable, Gateway Timeout, Too Many Requests

def should_retry_http_error(exception_value):
    """Verifica se um HTTPError deve ser retentado baseado no status code."""
    if isinstance(exception_value, requests.exceptions.HTTPError):
        return exception_value.response.status_code in RETRYABLE_STATUS_CODES
    return False # Não é um HTTPError que queremos tentar novamente por status code
# Decorador de retentativa
# Tenta 3 vezes no total (1 original + 2 retentativas)
# Espera exponencialmente entre as tentativas (ex: 1s, 2s, 4s...) com um máximo de 10s
# Só tenta novamente para exceções de rede específicas ou HTTP status codes específicos
api_retry_decorator = retry(
    stop=stop_after_attempt(3), # Número máximo de tentativas (1 original + 2 retries)
    wait=wait_exponential(multiplier=1, min=1, max=10), # Espera exponencial: 1s, 2s, 4s... até 10s
    retry=(
        retry_if_exception_type(requests.exceptions.Timeout) |
        retry_if_exception_type(requests.exceptions.ConnectionError) |
        retry_if_exception_type(should_retry_http_error) # Nossa função customizada para HTTPError
    ),
    before_sleep=lambda retry_state: logger.warning(
        f"API_RETRY: Retentativa {retry_state.attempt_number} para {retry_state.fn.__name__} "
        f"devido a: {retry_state.outcome.exception()}. Esperando {retry_state.next_action.sleep:.2f}s..."
    ) # Loga antes de cada retentativa
)
# --- Fim da Configuração de Retentativas ---

# =========================================================================================== #
# ======== Configurações do Processamento das Licitações ========
# Define o caminho para a pasta backend
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Define o caminho completo para o arquivo do banco de dados
DATABASE_PATH = os.path.join(BASE_DIR, 'database.db')
TAMANHO_PAGINA_SYNC  = 50 # OBRIGATORIO
LIMITE_PAGINAS_TESTE_SYNC = None # OBRIGATORIO. Mudar para 'None' para buscar todas.
CODIGOS_MODALIDADE = [1, 2,  3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13] #(OBRIGATORIO)
DIAS_JANELA_SINCRONIZACAO = 365 #Periodo da busca
API_BASE_URL = "https://pncp.gov.br/api/consulta" # (URL base da API do PNCP)      
API_BASE_URL_PNCP_API = "https://pncp.gov.br/pncp-api"   # Para itens e arquivos    ## PARA TODOS OS LINKS DE ARQUIVOS E ITENS USAR PAGINAÇÃO SE NECESSARIO ##
# ======= Fim das Configurações do Processamento das Licitações ============================== #

# ===== Validação de Dados da Licitação para decidir se continua a buscar a licitação especifca ou não ===== 
def validar_dados_licitacao_api(licitacao_api_data):
    """
    Valida os campos essenciais dos dados de uma licitação vindos da API.
    Retorna True se válido, False caso contrário, e loga os problemas.
    """
    erros_validacao = []
    pncp_id = licitacao_api_data.get('numeroControlePNCP') # Usar para logs

    if not pncp_id:
        erros_validacao.append("Campo 'numeroControlePNCP' está ausente ou vazio.")
        # Se o PNCP ID está ausente, muitas outras validações podem não fazer sentido ou falhar.
        # Podemos retornar False imediatamente ou continuar coletando outros erros.
        return False #Para evitar continuar com dados incompletos
    
    if not licitacao_api_data.get('dataAtualizacao'):
        erros_validacao.append("Campo 'dataAtualizacao' está ausente ou vazio.")
        return False # Tambem é essencial para toda busca

    # Validação para campos necessários para buscar sub-dados (itens/arquivos)
    orgao_entidade = licitacao_api_data.get('orgaoEntidade', {}) # Pega o dict, ou um dict vazio se 'orgaoEntidade' não existir
    if not orgao_entidade.get('cnpj'):
        erros_validacao.append("Campo 'orgaoEntidade.cnpj' está ausente ou vazio.")
    if licitacao_api_data.get('anoCompra') is None: # Checa por None, pois 0 pode ser um ano válido em teoria (embora improvável)
        erros_validacao.append("Campo 'anoCompra' está ausente.")
    if licitacao_api_data.get('sequencialCompra') is None:
        erros_validacao.append("Campo 'sequencialCompra' está ausente.")

    # Posso adicionar outras validações importantes aqui:
    # Exemplo:
    # if not licitacao_api_data.get('modalidadeId'):
    #     erros_validacao.append("Campo 'modalidadeId' está ausente.")
    # if licitacao_api_data.get('valorTotalEstimado') is not None:
    #     try:
    #         float(licitacao_api_data.get('valorTotalEstimado'))
    #     except (ValueError, TypeError):
    #         erros_validacao.append(f"Campo 'valorTotalEstimado' ('{licitacao_api_data.get('valorTotalEstimado')}') não é um número válido.")
    if erros_validacao:
        logger.warning(f"VALIDACAO_FALHA (PNCP: {pncp_id if pncp_id else 'DESCONHECIDO'}): Dados da licitação inválidos: {'; '.join(erros_validacao)}. Dados brutos: {json.dumps(licitacao_api_data, ensure_ascii=False, indent=2)}")
        return False
    return True

# --- Configuração do Log de Falhas Persistentes ---
FAILED_DATA_LOG_PATH = os.path.join(BASE_DIR, 'failed_processing_data.jsonl')

def logar_falha_persistente(tipo_dado, dado_problematico, motivo_falha):
    """
    Loga dados problemáticos e o motivo da falha em um arquivo JSON Lines.
    """
    try:
        entrada_log_falha = {
            "timestamp": datetime.now().isoformat(),
            "tipo_dado": tipo_dado, # ex: "licitacao_principal", "item_api", "arquivo_api"
            "motivo_falha": motivo_falha,
            "dado": dado_problematico # O dict/lista original da API
        }
        with open(FAILED_DATA_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entrada_log_falha, ensure_ascii=False) + '\n')
        logger.warning(f"FALHA_PERSISTENTE: Dados do tipo '{tipo_dado}' logados em {FAILED_DATA_LOG_PATH}. Motivo: {motivo_falha}. PNCP_ID (se aplicável): {dado_problematico.get('numeroControlePNCP', 'N/A')}")
    except Exception as e:
        logger.error(f"FALHA_LOG_DLQ: Erro ao tentar logar dados problemáticos para {FAILED_DATA_LOG_PATH}: {e}")
# Fim da Configuração do Log de Falhas Persistentes e Validação de Dados


# ==== CONFIGURAÇÃO DA API PARA ENCONTRAR OS ITENS/ARQUIVOS DAS LICITAÇÕES ====
@api_retry_decorator # Decorador para retentativas
def fetch_itens_from_api(cnpj_orgao, ano_compra, sequencial_compra, pagina=1, tamanho_pagina=TAMANHO_PAGINA_SYNC):
    """Busca uma página de itens de uma licitação."""
    url = f"{API_BASE_URL_PNCP_API}/v1/orgaos/{cnpj_orgao}/compras/{ano_compra}/{sequencial_compra}/itens"
    params = {'pagina': pagina, 'tamanhoPagina': tamanho_pagina}
    headers = {'Accept': 'application/json'}
    logger.debug(f"ITENS_API: Buscando em {url} com params {params}")
    try:
        response = requests.get(url, params=params, headers=headers, timeout=60) # timeout original da requisição
        response.raise_for_status() # Isso levantará HTTPError para status 4xx/5xx
        if response.status_code == 204:
            logger.debug(f"ITENS_API: Recebido status 204 (No Content) para {url} com params {params}.")
            return []
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        # Este bloco só será atingido se o HTTPError NÃO for um dos que acionam retentativa,
        # OU se todas as retentativas para um HTTPError retentável falharem.
        if http_err.response.status_code not in RETRYABLE_STATUS_CODES:
            logger.error(f"ITENS_API: Erro, HTTP NÃO RETENTÁVEL ou falha em todas as retentativas ao buscar itens para {cnpj_orgao}/{ano_compra}/{sequencial_compra} (Pag: {pagina}): {http_err}")
        # Se foi retentável e falhou todas as vezes, o log de warning da retentativa já ocorreu.
        # Podemos logar um erro final aqui.
        # A tenacity já terá logado os warnings das tentativas.
        # O logger.error abaixo já cobre o caso de falha final.
        else:
            logger.error(f"ITENS_API: Todas as retentativas falharam para HTTPError {http_err.response.status_code} ao buscar itens...")
        if http_err.response is not None:
             logger.error(f"ITENS_API: Detalhes da resposta final - Status: {http_err.response.status_code}, Texto: {http_err.response.text[:200]}")
        return None
    except Exception as e: # Outras exceções que não são de requests (ex: json.JSONDecodeError se a resposta não for JSON válido)
        logger.exception(f"ITENS_API: Erro GERAL (não-requests) ao buscar itens para {cnpj_orgao}/{ano_compra}/{sequencial_compra} (Pag: {pagina})")
        return None


@api_retry_decorator # Decorador para retentativas    
def fetch_arquivos_from_api(cnpj_orgao, ano_compra, sequencial_compra, pagina=1, tamanho_pagina=TAMANHO_PAGINA_SYNC ):
    # """Busca uma página de arquivos de uma licitação específica da API."""
    url = f"{API_BASE_URL_PNCP_API}/v1/orgaos/{cnpj_orgao}/compras/{ano_compra}/{sequencial_compra}/arquivos"

    params = {'pagina': pagina, 'tamanhoPagina': tamanho_pagina}
    headers = {'Accept': 'application/json'}
    logger.debug(f"ARQUIVOS_API: Buscando em {url} com params {params}")
    try:
        response = requests.get(url, params=params, headers=headers, timeout=60)
        response.raise_for_status()
        if response.status_code == 204:
            logger.debug(f"ARQUIVOS_API: Recebido status 204 (No Content) para {url} com params {params}.")
            return []
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        if http_err.response.status_code not in RETRYABLE_STATUS_CODES:
            logger.error(f"ARQUIVOS_API: Erro HTTP NÃO RETENTÁVEL ao buscar arquivos para {cnpj_orgao}/{ano_compra}/{sequencial_compra} (Pag: {pagina}): {http_err}")
        if http_err.response is not None:
             logger.error(f"ARQUIVOS_API: Detalhes da resposta final - Status: {http_err.response.status_code}, Texto: {http_err.response.text[:200]}")
        return None
    except Exception as e:
        logger.exception(f"ARQUIVOS_API: Erro GERAL (não-requests) ao buscar arquivos para {cnpj_orgao}/{ano_compra}/{sequencial_compra} (Pag: {pagina})")
        return None



### ARQUIVOS ###
def fetch_all_arquivos_metadata_from_api(cnpj_orgao, ano_compra, sequencial_compra):
    """
    Busca TODOS os METADADOS de arquivos de uma licitação específica da API,
    lidando com a paginação da API.
    Retorna uma lista de dicionários (metadados dos arquivos) ou None em caso de erro crítico.
    """
    todos_arquivos_api_metadados = [] # Lista para guardar os metadados de todos os arquivos
    pagina_atual_arquivos = 1
    logger.info(f"ARQUIVOS (Busca Metadados): Iniciando busca para {cnpj_orgao}/{ano_compra}/{sequencial_compra}")

    while True:
        # 1. Busca uma página de METADADOS de arquivos
        arquivos_pagina_metadados = fetch_arquivos_from_api( # Sua função que busca UMA página
            cnpj_orgao, ano_compra, sequencial_compra,
            pagina_atual_arquivos, TAMANHO_PAGINA_SYNC # TAMANHO_PAGINA_SYNC é sua constante global
        )

        if arquivos_pagina_metadados is None: # Erro crítico na chamada da API
            logger.critical(f"ARQUIVOS (Busca Metadados): Falha crítica ao buscar página {pagina_atual_arquivos}. Abortando busca de arquivos para esta licitação.")
            return None # Indica que a busca de metadados falhou

        if not arquivos_pagina_metadados: # Lista vazia, significa que não há mais arquivos ou nenhum arquivo
            break # Sai do loop while

        todos_arquivos_api_metadados.extend(arquivos_pagina_metadados)

        # Se a página retornada tem menos itens que o tamanho da página, é a última página
        if len(arquivos_pagina_metadados) < TAMANHO_PAGINA_SYNC:
            break # Sai do loop while

        pagina_atual_arquivos += 1
        time.sleep(0.2) # Pausa para não sobrecarregar a API

    logger.info(f"ARQUIVOS (Busca Metadados): Total de {len(todos_arquivos_api_metadados)} metadados de arquivos encontrados para {cnpj_orgao}/{ano_compra}/{sequencial_compra}.")
    return todos_arquivos_api_metadados

def salvar_arquivos_no_banco(conn, licitacao_id_local, lista_arquivos_metadata_api, cnpj_orgao, ano_compra, sequencial_compra):
    """
    Salva uma lista de metadados de arquivos no banco de dados para uma licitação específica.
    Deleta arquivos antigos dessa licitação antes de inserir os novos.
    Constrói o link de download para cada arquivo.
    """
    if not lista_arquivos_metadata_api: # Se a lista estiver vazia (None ou [])
        logger.info(f"ARQUIVOS_SAVE: Sem metadados de arquivos para salvar para licitação ID {licitacao_id_local}.") # Mudado para INFO
        return # Nada a fazer

    cursor = conn.cursor()
    # Deletar arquivos antigos desta licitação antes de (re)inserir
    try:
        logger.debug(f"ARQUIVOS_SAVE: Garantindo limpeza de arquivos pré-existentes para licitação ID {licitacao_id_local} antes de inserir novos.")
        cursor.execute("DELETE FROM arquivos_licitacao WHERE licitacao_id = %s", (licitacao_id_local,))
        if cursor.rowcount > 0:
            logger.debug(f"ARQUIVOS_SAVE: {cursor.rowcount} arquivos antigos foram efetivamente deletados para licitação ID {licitacao_id_local}.")
    except mysql.connector.Error as e:
        logger.exception(f"ARQUIVOS_SAVE: Erro no Banco de Dados ao tentar limpar arquivos antigos (lic_id {licitacao_id_local})")
        return

    sql_insert_arquivo = """
    INSERT INTO arquivos_licitacao (
        licitacao_id, titulo, link_download, dataPublicacaoPncp, anoCompra, statusAtivo
    ) VALUES (%s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE licitacao_id = VALUES(licitacao_id);
    """ # A parte do UPDATE não faz nada de útil, mas transforma o INSERT em um "INSERT IGNORE"

    # 1. Preparar a lista de tuplas
    arquivos_para_inserir = []
    arquivos_com_dados_invalidos = 0

    for arquivo_md_api in lista_arquivos_metadata_api:
        nome_do_arquivo = arquivo_md_api.get('titulo')
        id_do_documento_api = arquivo_md_api.get('sequencialDocumento')

        if not (nome_do_arquivo and id_do_documento_api is not None):
            logger.warning(f"ARQUIVOS_SAVE: Metadados do arquivo incompletos para lic_id {licitacao_id_local}. Título: {nome_do_arquivo}, ID Doc: {id_do_documento_api}. Pulando arquivo.")
            arquivos_com_dados_invalidos +=1
            continue

        link_de_download_individual = f"{API_BASE_URL_PNCP_API}/v1/orgaos/{cnpj_orgao}/compras/{ano_compra}/{sequencial_compra}/arquivos/{id_do_documento_api}"
        data_pub_pncp_str = arquivo_md_api.get('dataPublicacaoPncp')
        data_pub_pncp_db = data_pub_pncp_str.split('T')[0] if data_pub_pncp_str else None

        arquivo_db_tuple = (
            licitacao_id_local,
            nome_do_arquivo,
            link_de_download_individual,
            data_pub_pncp_db,
            arquivo_md_api.get('anoCompra'),
            bool(arquivo_md_api.get('statusAtivo')) # Convertendo para booleano explicitamente
        )
        arquivos_para_inserir.append(arquivo_db_tuple)

    if arquivos_com_dados_invalidos > 0:
        logger.warning(f"ARQUIVOS_SAVE: {arquivos_com_dados_invalidos} arquivos foram pulados devido a dados incompletos para lic_id {licitacao_id_local}.")

    # 2. Executar a inserção em lote
    if arquivos_para_inserir:
        try:
            cursor.executemany(sql_insert_arquivo, arquivos_para_inserir)
            # conn.commit() # Commit principal em save_licitacao_to_db
            logger.info(f"ARQUIVOS_SAVE: {cursor.rowcount} arquivos inseridos/ignorados (ON CONFLICT) em lote para licitação ID {licitacao_id_local}.")
            # Para ON CONFLICT DO NOTHING, rowcount pode não ser o número de itens na lista se houver conflitos.
            # Ele geralmente reflete o número de linhas realmente modificadas/inseridas.
            if cursor.rowcount < len(arquivos_para_inserir):
                logger.info(f"ARQUIVOS_SAVE: {len(arquivos_para_inserir) - cursor.rowcount} arquivos foram ignorados devido a conflito de 'link_download' (UNIQUE) para lic_id {licitacao_id_local}.")
        except mysql.connector.Error as e:
            logger.exception(f"ARQUIVOS_SAVE: Erro no Banco de Dados durante executemany para licitação ID {licitacao_id_local}")
            logger.debug(f"ARQUIVOS_SAVE: Primeiros arquivos na tentativa de lote (max 5): {arquivos_para_inserir[:5]}")
    elif not arquivos_com_dados_invalidos:
        logger.info(f"ARQUIVOS_SAVE: Nenhum arquivo válido encontrado na lista para inserir para lic_id {licitacao_id_local}.")

    
# Conecta com banco de dados; com retry para erros de conexão.
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
            logger.warning(
                f"Tentativa {attempt+1}/{max_retries} falhou (erro de conexão): {err}"
            )
            attempt += 1
            time.sleep(delay)
        except errors.ProgrammingError as err:
            # Erro de credenciais, banco inexistente, etc → retry não resolve
            logger.critical(f"Erro de programação (credenciais/SQL inválido): {err}")
            break
        except errors.IntegrityError as err:
            # Violação de constraint (chave duplicada, FK inválida) → retry não resolve
            logger.critical(f"Erro de integridade: {err}")
            break
        except mysql.connector.Error as err:
            # Qualquer outro erro inesperado
            logger.critical(f"Erro inesperado no MariaDB: {err}")
            break
    logger.error("Falha ao conectar ao banco de dados após múltiplas tentativas.")
    return None
# Fim da configuração do banco de dados

def format_datetime_for_api(dt_obj): 
    """Formata um objeto datetime para YYYYMMDD."""
    return dt_obj.strftime('%Y%m%d')

@api_retry_decorator # Aplicar o decorador
def fetch_licitacoes_por_atualizacao(data_inicio_str, data_fim_str, codigo_modalidade_api, pagina=1, tamanho_pagina=TAMANHO_PAGINA_SYNC):
    """Busca licitações da API /v1/contratacoes/atualizacao."""
    params_api = {
        'dataInicial': data_inicio_str,
        'dataFinal': data_fim_str,
        'pagina': pagina,
        'tamanhoPagina': tamanho_pagina,
        'codigoModalidadeContratacao': codigo_modalidade_api
    }
    url_api_pncp = f"{API_BASE_URL}/v1/contratacoes/atualizacao"
    logger.info(f"SYNC_API: Buscando em {url_api_pncp} com params {params_api}") # INFO aqui é bom para o fluxo principal
    try:
        response = requests.get(url_api_pncp, params=params_api, timeout=120) # Timeout maior para esta API principal
        response.raise_for_status()
        if response.status_code == 204: # Improvável para esta API, mas para consistência
            logger.info(f"SYNC_API: Recebido status 204 (No Content) para {url_api_pncp} com params {params_api}.")
            return None, 0 # (data, paginasRestantes)
        data_api = response.json()
        return data_api.get('data'), data_api.get('paginasRestantes', 0)
    except requests.exceptions.HTTPError as http_err:
        if http_err.response.status_code not in RETRYABLE_STATUS_CODES:
            logger.error(f"SYNC_API: Erro HTTP NÃO RETENTÁVEL (modalidade {codigo_modalidade_api}, pag {pagina}): {http_err}")
        # O log de warning da tenacity já terá sido emitido para erros retentáveis.
        # Podemos logar um erro final se todas as tentativas falharem.
        # else:
        #     logger.error(f"SYNC_API: Todas as retentativas falharam para HTTPError {http_err.response.status_code} (modalidade {codigo_modalidade_api}, pag {pagina})")

        # O logger.critical na função chamadora (sync_licitacoes_ultima_janela_anual)
        # já trata o caso de licitacoes_data ser None.
        # Se quisermos ser mais explícitos aqui sobre a falha final:
        if http_err.response is not None:
             logger.error(f"SYNC_API: Detalhes da resposta final - Status: {http_err.response.status_code}, Texto: {http_err.response.text[:200]}")
        return None, 0 # (data, paginasRestantes) - Indica falha
    except Exception as e:
        logger.exception(f"SYNC_API: Erro GERAL (não-requests) ao buscar (modalidade {codigo_modalidade_api}, pag {pagina})")
        return None, 0 # (data, paginasRestantes) - Indica falha


def  save_licitacao_to_db(conn, licitacao_api_item): 
    # >>> PASSO DE VALIDAÇÃO INICIAL <<<
    if not validar_dados_licitacao_api(licitacao_api_item):
        logar_falha_persistente("licitacao_principal", licitacao_api_item, "Falha na validação inicial dos dados.")
        return None # Pula o processamento desta licitação
    
    # MODIFICADO: Usar 'dictionary=True' para acessar colunas por nome
    cursor = conn.cursor(dictionary=True)
      
    # Mapeamento de licitacao_db 
    licitacao_db_parcial = { # isso aqui cria o dicionario parcial. Para efeito de comparação simples é como se fosse um SELECT * FROM licitacao WHERE id = ?
        'numeroControlePNCP': licitacao_api_item.get('numeroControlePNCP'),
        'numeroCompra': licitacao_api_item.get('numeroCompra'),
        'anoCompra': licitacao_api_item.get('anoCompra'),
        'processo': licitacao_api_item.get('processo'),
        'tipolnstrumentoConvocatorioId': licitacao_api_item.get('tipoInstrumentoConvocatorioCodigo'),
        'tipolnstrumentoConvocatorioNome': licitacao_api_item.get('tipoInstrumentoConvocatorioNome'),
        'modalidadeId': licitacao_api_item.get('modalidadeId'),
        'modalidadeNome': licitacao_api_item.get('modalidadeNome'),
        'modoDisputaId': licitacao_api_item.get('modoDisputaId'),
        'modoDisputaNome': licitacao_api_item.get('modoDisputaNome'),
        'situacaoCompraId': licitacao_api_item.get('situacaoCompraId'),
        'situacaoCompraNome': licitacao_api_item.get('situacaoCompraNome'),
        'objetoCompra': licitacao_api_item.get('objetoCompra'),
        'informacaoComplementar': licitacao_api_item.get('informacaoComplementar'),
        'srp': licitacao_api_item.get('srp'),
        'amparoLegalCodigo': licitacao_api_item.get('amparoLegal', {}).get('codigo'),
        'amparoLegalNome': licitacao_api_item.get('amparoLegal', {}).get('nome'),
        'amparoLegalDescricao': licitacao_api_item.get('amparoLegal', {}).get('descricao'),
        'valorTotalEstimado': licitacao_api_item.get('valorTotalEstimado'),
        'valorTotalHomologado': licitacao_api_item.get('valorTotalHomologado'),
        'dataAberturaProposta': licitacao_api_item.get('dataAberturaProposta'),
        'dataEncerramentoProposta': licitacao_api_item.get('dataEncerramentoProposta'),
        'dataPublicacaoPncp': licitacao_api_item.get('dataPublicacaoPncp', '').split('T')[0] if licitacao_api_item.get('dataPublicacaoPncp') else None,
        'dataInclusao': licitacao_api_item.get('dataInclusao', '').split('T')[0] if licitacao_api_item.get('dataInclusao') else None,
        'dataAtualizacao': licitacao_api_item.get('dataAtualizacao', '').split('T')[0] if licitacao_api_item.get('dataAtualizacao') else None,
        'sequencialCompra': licitacao_api_item.get('sequencialCompra'),
        'orgaoEntidadeCnpj': licitacao_api_item.get('orgaoEntidade', {}).get('cnpj'),
        'orgaoEntidadeRazaoSocial': licitacao_api_item.get('orgaoEntidade', {}).get('razaoSocial'),
        'orgaoEntidadePoderId': licitacao_api_item.get('orgaoEntidade', {}).get('poderId'),
        'orgaoEntidadeEsferaId': licitacao_api_item.get('orgaoEntidade', {}).get('esferaId'),
        'unidadeOrgaoCodigo': licitacao_api_item.get('unidadeOrgao', {}).get('codigoUnidade'),
        'unidadeOrgaoNome': licitacao_api_item.get('unidadeOrgao', {}).get('nomeUnidade'),
        'unidadeOrgaoCodigoIbge': licitacao_api_item.get('unidadeOrgao', {}).get('codigoIbge'),
        'unidadeOrgaoMunicipioNome': licitacao_api_item.get('unidadeOrgao', {}).get('municipioNome'),
        'unidadeOrgaoUfSigla': licitacao_api_item.get('unidadeOrgao', {}).get('ufSigla'),
        'unidadeOrgaoUfNome': licitacao_api_item.get('unidadeOrgao', {}).get('ufNome'),
        'usuarioNome': licitacao_api_item.get('usuarioNome'),
        'linkSistemaOrigem': licitacao_api_item.get('linkSistemaOrigem'),
        'justificativaPresencial': licitacao_api_item.get('justificativaPresencial'),        
    }
           
    # Gerar link_portal_pncp
    cnpj_l = licitacao_db_parcial['orgaoEntidadeCnpj']
    ano_l = licitacao_db_parcial['anoCompra']
    seq_l = licitacao_db_parcial['sequencialCompra']
    link_pncp_val = None
    if cnpj_l and ano_l and seq_l is not None:
        try:
            seq_sem_zeros = str(int(str(seq_l)))
            link_pncp_val = f"https://pncp.gov.br/app/editais/{cnpj_l}/{ano_l}/{seq_sem_zeros}"
        except ValueError: link_pncp_val = None
    licitacao_db_parcial['link_portal_pncp'] = link_pncp_val

    # --- Determinar flag_houve_mudanca_real e obter licitacao_id_local_existente ---
    # Esta flag e o ID são importantes para decidir se buscamos itens/arquivos e para o UPSERT.
    licitacao_id_local_final = None
    flag_houve_mudanca_real = False
    
    cursor.execute("SELECT id, dataAtualizacao FROM licitacoes WHERE numeroControlePNCP = %s", (licitacao_db_parcial['numeroControlePNCP'],))
    row_existente = cursor.fetchone()
    api_data_att_str = licitacao_db_parcial.get('dataAtualizacao')
    api_data_att_dt = datetime.strptime(api_data_att_str, '%Y-%m-%d').date() if api_data_att_str else None

    if row_existente:
        licitacao_id_local_final = row_existente['id']  # modificado para dictionary por causa do cursor ser dictionary=True.
        # Comparar datas de atualização para ver se houve mudança real
        db_data_att_str = row_existente['dataAtualizacao']
        db_data_att_dt = datetime.strptime(db_data_att_str, '%Y-%m-%d').date() if db_data_att_str else None
        if api_data_att_dt and (not db_data_att_dt or api_data_att_dt > db_data_att_dt):
            flag_houve_mudanca_real = True
    else:
        flag_houve_mudanca_real = True # Nova licitação, considera como mudança

    # --- Buscar Itens (SEMPRE que houver mudança ou for nova, OU se não tiver itens e quisermos popular) ---    
    itens_da_licitacao_api = [] # Lista de itens buscados da API
    necessita_buscar_itens = False
    if flag_houve_mudanca_real:
        necessita_buscar_itens = True
    elif licitacao_id_local_final: # Se já existe no DB mas não houve mudança na dataAtualizacao
        cursor.execute("SELECT COUNT(id) FROM itens_licitacao WHERE licitacao_id = %s", (licitacao_id_local_final,))
        if cursor.fetchone()[0] == 0:
            necessita_buscar_itens = True
            logger.error(f"INFO (save_db): Licitação {licitacao_db_parcial['numeroControlePNCP']} sem itens no banco. Buscando...")


    if necessita_buscar_itens and licitacao_db_parcial['orgaoEntidadeCnpj'] and licitacao_db_parcial['anoCompra'] and licitacao_db_parcial['sequencialCompra'] is not None:
        logger.info(f"INFO (save_db): Iniciando busca de ITENS para {licitacao_db_parcial['numeroControlePNCP']} (para definir situacaoReal e salvar)")
        # fetch_all_itens_for_licitacao agora SÓ BUSCA e retorna a lista de itens da API
        # O salvamento dos itens será feito DEPOIS de salvar a licitação principal.
        itens_brutos_api = fetch_all_itens_for_licitacao_APENAS_BUSCA(
            licitacao_db_parcial['orgaoEntidadeCnpj'], 
            licitacao_db_parcial['anoCompra'], 
            licitacao_db_parcial['sequencialCompra']
        )
        if itens_brutos_api is None: # Se a busca de itens falhou criticamente
            logger.error(f"ITENS_FETCH_FAIL: Falha crítica ao buscar itens para {licitacao_db_parcial['numeroControlePNCP']}. A licitação pode ficar inconsistente.")
            logar_falha_persistente(
                "licitacao_itens_fetch_error",
                licitacao_api_item, # Loga a licitação principal
                f"Falha crítica ao buscar itens para PNCP ID {licitacao_db_parcial['numeroControlePNCP']}."
            )            
            return None # Para abortar o processamento desta licitação
        elif itens_brutos_api:
            itens_da_licitacao_api = itens_brutos_api
            # Guardamos para usar na lógica de situacaoReal e para salvar depois
    
    # --- LÓGICA PARA DEFINIR licitacao_db_parcial['situacaoReal'] ---
    hoje_date = date.today()
    data_encerramento_str = licitacao_db_parcial.get('dataEncerramentoProposta')
    status_compra_api = licitacao_db_parcial.get('situacaoCompraId')
    
    situacao_real_calculada = "Desconhecida" # Default

    status_api_encerram_definitivo = [2, 3] #  Anulada,  Deserta

    if status_compra_api in status_api_encerram_definitivo:
        situacao_real_calculada = "Encerrada"
    elif status_compra_api == 4: # TRATAMENTO EXPLÍCITO PARA SUSPENSA
        situacao_real_calculada = "Suspensa"
    elif licitacao_db_parcial.get('dataAberturaProposta') is None and data_encerramento_str is None:
        # Se NÃO HÁ datas de abertura E encerramento, você considera encerrada.
        # Isso pode ser um problema se a API nem sempre fornecer essas datas para licitações ativas.
        situacao_real_calculada = "Encerrada" # (Considerada encerrada por falta de datas)
    elif status_compra_api == 1: # Apenas se for "Divulgada no PNCP" pela API
        encerra_por_item_ou_julgamento = False
       
        if itens_da_licitacao_api: # VERIFICA SE HÁ ITENS
            status_itens_que_encerram = ["Homologado", "Fracassado", "Deserto", "Anulado/Revogado/Cancelado" ] 
            # ERRO POTENCIAL 1: Acessa [0] sem checar se itens_da_licitacao_api tem elementos. (Corrigido no código acima com 'if itens_da_licitacao_api:')
            # Mas ainda pode ter problemas se a lista for vazia após o 'if'
            
            # Assumindo que 'itens_da_licitacao_api' não é None, mas PODE SER UMA LISTA VAZIA
            if len(itens_da_licitacao_api) > 0:
                primeiro_item_status = itens_da_licitacao_api[0].get('situacaoCompraItemNome')
                if primeiro_item_status: # Verifica se o status do item não é None
                    primeiro_item_status_lower = primeiro_item_status.lower()
                
                    # ERRO POTENCIAL 2: Se 'situacaoCompraItemNome' for qualquer coisa que NÃO esteja em status_itens_que_encerram E NÃO seja 'Em Andamento', cai em "Em Julgamento"
                    if primeiro_item_status_lower in [s.lower() for s in status_itens_que_encerram]: # Comparação case-insensitive
                        situacao_real_calculada = "Encerrada"
                        encerra_por_item_ou_julgamento = True
                    # >>> ESTE É UM PONTO CRÍTICO <<<
                    elif primeiro_item_status_lower and primeiro_item_status_lower != "em andamento": 
                        # Se o status do primeiro item NÃO for "em andamento" e NÃO for um dos que encerram,
                        # ele se torna "Em Julgamento/Propostas Encerradas"
                        situacao_real_calculada = "Em Julgamento/Propostas Encerradas"
                        # status_item_para_julgamento = itens_da_licitacao_api[0].get('situacaoCompraItemNome') # Não usado, pode remover
                        encerra_por_item_ou_julgamento = True
                else: # Se o primeiro item não tem 'situacaoCompraItemNome'
                    # O que fazer aqui? Por enquanto, não define encerra_por_item_ou_julgamento, então a lógica abaixo baseada em datas será usada.
                    pass 
            # else: # Se itens_da_licitacao_api for uma lista vazia
                # Nenhuma lógica de item será aplicada. A lógica de datas abaixo será usada.

        # Se não foi encerrada/julgamento por item (encerra_por_item_ou_julgamento é False)
        if not encerra_por_item_ou_julgamento: 
            if data_encerramento_str:
                try:
                    data_encerramento_datetime_obj = datetime.fromisoformat(data_encerramento_str.replace('Z', '+00:00')) # Lida com 'Z' se presente
                    data_encerramento_date_obj = data_encerramento_datetime_obj.date() 
                    if hoje_date > data_encerramento_date_obj:                    
                        # Se a data de encerramento já passou, vira "Em Julgamento/Propostas Encerradas"
                        situacao_real_calculada = "Em Julgamento/Propostas Encerradas"
                    else:
                        situacao_real_calculada = "A Receber/Recebendo Proposta"
                except ValueError:
                     # Data de encerramento em formato inválido, o que fazer?
                     # Talvez tratar como "A Receber/Recebendo Proposta" ou "Desconhecida" e logar um aviso
                     logger.exception(f"AVISO: Formato inválido para dataEncerramentoProposta: {data_encerramento_str} para {licitacao_db_parcial['numeroControlePNCP']}")
                     situacao_real_calculada = "A Receber/Recebendo Proposta" # Ou outra default segura
            else: # Sem data de encerramento, mas ativa pela API e não definida por status de item
                  # E aqui se status_compra_api == 1, será "A Receber/Recebendo Proposta"
                situacao_real_calculada = "A Receber/Recebendo Proposta"
    # else:
        # Se status_compra_api não for 1, 2, 3 ou 4, e tiver datas de abertura/encerramento,
        # vai usar o 'situacao_real_calculada = "Desconhecida"' inicial.
        # Se você espera mais casos, precisa tratar outros status_compra_api.

    licitacao_db_parcial['situacaoReal'] = situacao_real_calculada
    # --- FIM DA LÓGICA situacaoReal ---


    # SQL UPSERT para MariaDB (INSERT ... ON DUPLICATE KEY UPDATE)
    colunas = licitacao_db_parcial.keys()
    placeholders = ', '.join(['%s'] * len(colunas))
    colunas_str = ', '.join(f'`{col}`' for col in colunas)
    
    updates_str = ', '.join([f'`{col}` = VALUES(`{col}`)' for col in colunas if col != 'numeroControlePNCP'])
    
    sql_upsert_licitacao = f"""
    INSERT INTO licitacoes ({colunas_str})
    VALUES ({placeholders})
    ON DUPLICATE KEY UPDATE {updates_str}
    """
    # FIM DO BLOCO SUBSTITUÍDO    
    
    try:
        if flag_houve_mudanca_real:
            # Prepara os parâmetros como uma tupla na ordem correta
            params = tuple(licitacao_db_parcial.values())
            cursor.execute(sql_upsert_licitacao, params)
            
            # Lógica para obter o ID após INSERT ou UPDATE
            if cursor.lastrowid:
                licitacao_id_local_final = cursor.lastrowid
                logger.info(f"INFO (SAVE_DB): Licitação {licitacao_db_parcial['numeroControlePNCP']} INSERIDA. ID: {licitacao_id_local_final}.")
            else:
                # Se foi um UPDATE, precisamos buscar o ID
                cursor.execute("SELECT id FROM licitacoes WHERE numeroControlePNCP = %s", (licitacao_db_parcial['numeroControlePNCP'],))
                id_row = cursor.fetchone()
                if id_row: 
                    licitacao_id_local_final = id_row[0]
                    logger.info(f"INFO (SAVE_DB): Licitação {licitacao_db_parcial['numeroControlePNCP']} ATUALIZADA. ID: {licitacao_id_local_final}.")

        elif row_existente:
            licitacao_id_local_final = row_existente['id'] # Em MariaDB, o resultado é uma tupla
            logger.info(f"INFO (SAVE_DB): Licitação {licitacao_db_parcial['numeroControlePNCP']} já atualizada. ID: {licitacao_id_local_final}.")

    except mysql.connector.Error as err:
        logger.exception(f"SAVE_DB: Erro MariaDB ao salvar principal {licitacao_db_parcial.get('numeroControlePNCP')}: {err}")
        logar_falha_persistente(
            "licitacao_principal_db_error",
            licitacao_api_item,
            f"Erro MariaDB durante UPSERT: {err}"
        )
        cursor.close()
        return None
        
    if not licitacao_id_local_final:
        logger.critical(f"AVISO CRÍTICO (SAVE_DB): Falha ao obter ID local para {licitacao_db_parcial.get('numeroControlePNCP')}")
        return None 

    # --- SALVAR ITENS E ARQUIVOS (usando licitacao_id_local_final e os itens_da_licitacao_api) ---
    # Somente se houve mudança real ou se os itens não existiam antes (essa lógica de "não existiam antes" foi feita para buscar_sub_detalhes)
    # A flag_houve_mudanca_real já cobre o caso de ser novo ou atualizado.
    # Se não houve mudança e os itens já existem, podemos pular o re-salvamento deles se não mudaram.
    # Mas para garantir consistência com 'situacaoReal', talvez seja bom sempre processar itens se 'flag_houve_mudanca_real'
    # ou se 'necessita_buscar_itens' era true.
    
    if necessita_buscar_itens and itens_da_licitacao_api: # Se buscamos e obtivemos itens
        salvar_itens_no_banco(conn, licitacao_id_local_final, itens_da_licitacao_api) # Nova função para apenas salvar

    # --- SALVAR ARQUIVOS (se necessário) ---
    necessita_buscar_arquivos = False # Definir uma flag para arquivos
    if flag_houve_mudanca_real: # Se a licitação principal mudou
        necessita_buscar_arquivos = True
    elif licitacao_id_local_final: # Se a licitação já existe no DB
        # Verificamos se já existem arquivos para ela no banco
        # Se não existirem, marcamos para buscar para saber se há arquivos na API dessa vez
        cursor.execute("SELECT COUNT(id) as total FROM itens_licitacao WHERE licitacao_id = %s", (licitacao_id_local_final,))
        resultado_contagem = cursor.fetchone()
        if resultado_contagem and resultado_contagem['total'] == 0:
            necessita_buscar_arquivos = True
            logger.info(f"INFO (ARQUIVOS): Licitação {licitacao_db_parcial['numeroControlePNCP']} (ID: {licitacao_id_local_final}) sem arquivos no banco. Marcando para buscar itens")

    if necessita_buscar_arquivos:
        # Verifica se temos os dados necessários para formar a URL da API de arquivos
        cnpj_lic = licitacao_db_parcial.get('orgaoEntidadeCnpj')
        ano_lic = licitacao_db_parcial.get('anoCompra')
        seq_lic = licitacao_db_parcial.get('sequencialCompra')

        if cnpj_lic and ano_lic and seq_lic is not None:
            # 1. Busca todos os metadados dos arquivos da API
            lista_arquivos_metadata = fetch_all_arquivos_metadata_from_api(
                cnpj_lic,
                ano_lic,
                seq_lic
            )

            # 2. Se a busca de metadados foi bem-sucedida (não retornou None)
            #    e temos um ID local para a licitação, então salvamos no banco.
            if lista_arquivos_metadata is not None and licitacao_id_local_final is not None:
                salvar_arquivos_no_banco(
                    conn, # A conexão com o banco
                    licitacao_id_local_final, # O ID da licitação no nosso banco
                    lista_arquivos_metadata, # A lista de metadados que acabamos de buscar
                    cnpj_lic, # CNPJ da licitação (para montar o link de download)
                    ano_lic,  # Ano da licitação
                    seq_lic   # Sequencial da licitação
                )
            elif lista_arquivos_metadata is None:
                logger.error(f"AVISO (ARQUIVOS): Não foi possível buscar metadados de arquivos para Lic. ID {licitacao_id_local_final}, salvamento de arquivos pulado.")
        else:
            logger.error(f"AVISO (ARQUIVOS): Dados insuficientes (CNPJ, Ano, Sequencial) para buscar arquivos da licitação {licitacao_db_parcial.get('numeroControlePNCP')}.")
    
    return licitacao_id_local_final # A função continua retornando o ID da licitação

# Nova função para buscar itens sem salvar (para desacoplar)
def fetch_all_itens_for_licitacao_APENAS_BUSCA(cnpj_orgao, ano_compra, sequencial_compra):
    todos_itens_api = []
    pagina_atual_itens = 1
    # ... (lógica de loop e chamada a fetch_itens_from_api como em fetch_all_itens_for_licitacao) ...
    # MAS SEM A PARTE DE SALVAR NO BANCO AQUI DENTRO
    while True:
        itens_pagina = fetch_itens_from_api(cnpj_orgao, ano_compra, sequencial_compra, pagina_atual_itens, TAMANHO_PAGINA_SYNC)
        if itens_pagina is None: 
            logger.critical(f"ITENS (Busca Geral): Falha crítica ao buscar página {pagina_atual_itens} de itens para {cnpj_orgao}/{ano_compra}/{sequencial_compra}. Abortando busca de itens.")
            return None 
        if not itens_pagina: break
        todos_itens_api.extend(itens_pagina)
        if len(itens_pagina) < TAMANHO_PAGINA_SYNC: break
        pagina_atual_itens += 1
        time.sleep(0.2)
    logger.info(f"ITENS (Busca): Total de {len(todos_itens_api)} itens encontrados para {cnpj_orgao}/{ano_compra}/{sequencial_compra}.")
    return todos_itens_api


# Função para salvar itens no banco (separada da busca)
def salvar_itens_no_banco(conn, licitacao_id_local, lista_itens_api):
    if not lista_itens_api:
        logger.info(f"ITENS_SAVE: Sem itens para salvar para licitação ID {licitacao_id_local}.") # Mudado para INFO
        return

    cursor = conn.cursor()
    try:
        # Deletar itens antigos ANTES do loop, uma única vez
        logger.debug(f"ITENS_SAVE: Garantindo limpeza de itens pré-existentes para licitação ID {licitacao_id_local} antes de inserir novos.")
        cursor.execute("DELETE FROM itens_licitacao WHERE licitacao_id = %s", (licitacao_id_local,))
        if cursor.rowcount > 0:
            logger.debug(f"ITENS_SAVE: {cursor.rowcount} itens antigos foram efetivamente deletados para licitação ID {licitacao_id_local}.")
    except mysql.connector.Error as e:
        logger.exception(f"ITENS_SAVE: Erro MariaDB ao tentar limpar itens antigos (lic_id {licitacao_id_local})")
        return

    sql_insert_item = """
    INSERT INTO itens_licitacao (
        licitacao_id, numeroItem, descricao, materialOuServicoNome, quantidade,
        unidadeMedida, valorUnitarioEstimado, valorTotal, orcamentoSigiloso,
        itemCategoriaNome, categoriaItemCatalogo, criterioJulgamentoNome,
        situacaoCompraItemNome, tipoBeneficioNome, incentivoProdutivoBasico, dataInclusao,
        dataAtualizacao, temResultado, informacaoComplementar
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""" # 19 placeholders

    # 1. Preparar a lista de tuplas para executemany()
    itens_para_inserir = []
    itens_com_dados_invalidos = 0

    for item_api in lista_itens_api:
        # Validação básica de dados do item (opcional, mas bom)
        if item_api.get('numeroItem') is None: # Exemplo de validação
            logger.warning(f"ITENS_SAVE: Item para lic_id {licitacao_id_local} sem 'numeroItem'. Pulando item: {item_api}")
            itens_com_dados_invalidos +=1
            continue

        item_db_tuple = (
            licitacao_id_local,
            item_api.get('numeroItem'),
            item_api.get('descricao'),
            item_api.get('materialOuServicoNome'),
            item_api.get('quantidade'),
            item_api.get('unidadeMedida'),
            item_api.get('valorUnitarioEstimado'),
            item_api.get('valorTotal'),
            bool(item_api.get('orcamentoSigiloso')),
            item_api.get('itemCategoriaNome'),
            item_api.get('categoriaItemCatalogo'),
            item_api.get('criterioJulgamentoNome'),
            item_api.get('situacaoCompraItemNome'),
            item_api.get('tipoBeneficioNome'),
            bool(item_api.get('incentivoProdutivoBasico')),
            item_api.get('dataInclusao', '').split('T')[0] if item_api.get('dataInclusao') else None,
            item_api.get('dataAtualizacao', '').split('T')[0] if item_api.get('dataAtualizacao') else None,
            bool(item_api.get('temResultado')),
            item_api.get('informacaoComplementar')
        )
        itens_para_inserir.append(item_db_tuple)

    if itens_com_dados_invalidos > 0:
        logger.warning(f"ITENS_SAVE: {itens_com_dados_invalidos} itens foram pulados devido a dados inválidos para lic_id {licitacao_id_local}.")

    # 2. Executar a inserção em lote se houver itens válidos
    if itens_para_inserir:
        try:
            cursor.executemany(sql_insert_item, itens_para_inserir)
            # conn.commit() # O commit principal geralmente é feito na função que chama esta (save_licitacao_to_db)
            logger.info(f"ITENS_SAVE: {cursor.rowcount} itens inseridos em lote para licitação ID {licitacao_id_local}.")
            if cursor.rowcount != len(itens_para_inserir):
                 logger.warning(f"ITENS_SAVE: Esperava-se inserir {len(itens_para_inserir)} itens, mas {cursor.rowcount} foram afetados para lic_id {licitacao_id_local}.")
        except mysql.connector.Error as e:
            logger.exception(f"ITENS_SAVE: Erro no Banco de Dados durante executemany para licitação ID {licitacao_id_local}")
            # Logar os primeiros N itens para ajudar na depuração, se necessário
            logger.debug(f"ITENS_SAVE: Primeiros itens na tentativa de lote (max 5): {itens_para_inserir[:5]}")
    elif not itens_com_dados_invalidos: # Se não há itens para inserir e nenhum foi invalidado
        logger.info(f"ITENS_SAVE: Nenhum item válido encontrado na lista para inserir para lic_id {licitacao_id_local}.")

    
def sync_licitacoes_ultima_janela_anual():
    conn = get_db_connection()
    if not conn: return

    agora = datetime.now()
    data_fim_periodo_dt = agora
    data_inicio_periodo_dt = agora - timedelta(days=DIAS_JANELA_SINCRONIZACAO) # Quantos dias considerar para a janela de sincronização

    data_inicio_api_str = format_datetime_for_api(data_inicio_periodo_dt)
    data_fim_api_str = format_datetime_for_api(data_fim_periodo_dt)

    logger.info(f"SYNC ANUAL: Iniciando sincronização para licitações atualizadas entre {data_inicio_api_str} e {data_fim_api_str}")

    licitacoes_processadas_total = 0
    
    for modalidade_id_sync in CODIGOS_MODALIDADE:
        logger.info(f"\n--- SYNC JANELA: Processando Modalidade {modalidade_id_sync} ---")
        pagina_atual = 1
        paginas_processadas_modalidade = 0
        erros_api_modalidade = 0

        while True:
            if LIMITE_PAGINAS_TESTE_SYNC is not None and paginas_processadas_modalidade >= LIMITE_PAGINAS_TESTE_SYNC:
                logger.info(f"SYNC JANELA: Limite de {LIMITE_PAGINAS_TESTE_SYNC} páginas atingido para modalidade {modalidade_id_sync}.")
                break

            licitacoes_data, paginas_restantes = fetch_licitacoes_por_atualizacao(
                data_inicio_api_str, data_fim_api_str, modalidade_id_sync, pagina_atual
            )

            if licitacoes_data is None: # Erro
                erros_api_modalidade += 1
                if erros_api_modalidade > 4:
                    logger.critical(f"SYNC JANELA: Muitos erros de API para modalidade {modalidade_id_sync}. Abortando esta modalidade.")
                    break 
                if paginas_restantes == 0 : # Se API indicou erro e fim
                    logger.critical(f"SYNC JANELA: Muitos erros de API para modalidade {modalidade_id_sync}.")
                    break
    
            if not licitacoes_data: # Fim dos dados
                logger.info(f"SYNC JANELA: Nenhuma licitação na API para modalidade {modalidade_id_sync}, página {pagina_atual}.")
                # Verifique se paginas_restantes é 0 para confirmar o fim
                if paginas_restantes == 0:
                    break
                else: # Pode ser uma página vazia no meio, mas API indica mais páginas (raro)
                    logger.info(f"SYNC ANUAL: Página {pagina_atual} vazia, mas {paginas_restantes} páginas restantes. Tentando próxima.")
                    pagina_atual += 1
                    time.sleep(0.5)
                    continue

            logger.info(f"SYNC JANELA: Modalidade {modalidade_id_sync}, Página {pagina_atual}: Processando {len(licitacoes_data)} licitações.")
            for lic_api in licitacoes_data:
                save_licitacao_to_db(conn, lic_api) # Removido o set 
                licitacoes_processadas_total += 1
            
            conn.commit()
            logger.info(f"SYNC JANELA: Modalidade {modalidade_id_sync}, Página {pagina_atual} processada. {paginas_restantes} páginas restantes.")
            paginas_processadas_modalidade += 1
            
            if paginas_restantes == 0: break
            pagina_atual += 1
            time.sleep(0.5)

    
    conn.close()
    logger.info(f"\n--- Sincronização da Janela Anual Concluída ---")
    logger.info(f"Total de licitações da API (na janela de atualização) processadas: {licitacoes_processadas_total}")


if __name__ == '__main__':
    logger.info(f"Iniciando script de sincronização (janela de {DIAS_JANELA_SINCRONIZACAO} dias de atualizações)...")
    sync_licitacoes_ultima_janela_anual()
    logger.info("Script de sincronização finalizado.")
