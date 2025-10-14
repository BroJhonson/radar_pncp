# arquivo reprocessar_pag_fail.py
import os
import sys
import json
import time
import fcntl
import mysql.connector
from datetime import datetime

# --- REUTILIZAÇÃO DA LÓGICA DO SCRIPT PRINCIPAL ---
from sync_api import (
    get_db_connection,
    fetch_licitacoes_por_atualizacao,
    save_licitacao_to_db,
    logger
)

# --- CONFIGURAÇÕES ---
FAILED_PAGES_FILE = "failed_pages.jsonl"
FAILED_PAGES_DEAD_FILE = "failed_pages_dead.jsonl"
LOCK_FILE = "sync_api.lock"  # OBRIGATÓRIO: usar o mesmo lock do script principal
MAX_REPROCESS_ATTEMPTS = 5   # depois disso consideramos "falha final"
BASE_BACKOFF_SECONDS = 1     # tempo base do backoff exponencial


def reprocessar_paginas_com_falha():
    """Lê o arquivo de páginas com falha, tenta reprocessá-las e atualiza os arquivos."""

    if not os.path.exists(FAILED_PAGES_FILE):
        logger.info("REPROCESS: Arquivo de páginas com falha não encontrado. Nada a fazer.")
        return

    # Lê todas as páginas que precisam ser reprocessadas
    try:
        with open(FAILED_PAGES_FILE, 'r', encoding='utf-8') as f:
            pages_to_reprocess = [json.loads(line) for line in f if line.strip()]
    except (IOError, json.JSONDecodeError) as e:
        logger.error(f"REPROCESS: Erro ao ler ou decodificar {FAILED_PAGES_FILE}: {e}")
        return

    if not pages_to_reprocess:
        logger.info("REPROCESS: Arquivo de páginas com falha está vazio. Nada a fazer.")
        os.remove(FAILED_PAGES_FILE)
        return

    logger.info(f"REPROCESS: Encontradas {len(pages_to_reprocess)} páginas para reprocessar.")

    conn = get_db_connection()
    if not conn:
        logger.critical("REPROCESS: Não foi possível conectar ao banco de dados. Abortando.")
        return

    still_failed_pages = []
    dead_pages = []
    success_count = 0

    for page_info in pages_to_reprocess:
        modalidade = page_info['modalidade']
        pagina = page_info['pagina']
        data_inicio = page_info['data_inicio']
        data_fim = page_info['data_fim']

        logger.info(f"--- REPROCESS: Tentando Modalidade {modalidade}, Página {pagina} ---")

        licitacoes_data, _ = fetch_licitacoes_por_atualizacao(
            data_inicio, data_fim, modalidade, pagina
        )

        if licitacoes_data is not None:
            logger.info(f"REPROCESS: SUCESSO ao buscar página {pagina}. "
                        f"Processando {len(licitacoes_data)} licitações.")
            for lic_api in licitacoes_data:
                try:
                    save_licitacao_to_db(conn, lic_api)
                    conn.commit()
                except mysql.connector.Error as db_err:
                    logger.error(f"REPROCESS_DB: Falha ao salvar licitação "
                                 f"{lic_api.get('numeroControlePNCP')}: {db_err}. Rollback executado.")
                    conn.rollback()
                except Exception as e:
                    logger.error(f"REPROCESS_UNEXPECTED: Erro inesperado ao salvar licitação "
                                 f"{lic_api.get('numeroControlePNCP')}: {e}. Rollback executado.")
                    conn.rollback()
            success_count += 1
            time.sleep(1)  # pequena pausa entre sucessos
        else:
            # Falha persistente
            page_info.setdefault('reprocess_attempts', 0)
            page_info['reprocess_attempts'] += 1
            page_info['last_attempt_timestamp'] = datetime.now().isoformat()

            if page_info['reprocess_attempts'] >= MAX_REPROCESS_ATTEMPTS:
                logger.error(f"REPROCESS: Página Modalidade {modalidade}, "
                             f"Página {pagina} atingiu {page_info['reprocess_attempts']} tentativas. "
                             f"Movendo para {FAILED_PAGES_DEAD_FILE}.")
                dead_pages.append(page_info)
            else:
                still_failed_pages.append(page_info)

            # backoff exponencial: 1s, 2s, 4s, 8s...
            backoff_time = BASE_BACKOFF_SECONDS * (2 ** (page_info['reprocess_attempts'] - 1))
            logger.info(f"REPROCESS: Backoff de {backoff_time}s antes da próxima página.")
            time.sleep(backoff_time)

    conn.close()

    # --- Atualização do arquivo de falhas com escrita atômica ---
    try:
        tmp_file = FAILED_PAGES_FILE + ".tmp"
        with open(tmp_file, 'w', encoding='utf-8') as f:
            for page_info in still_failed_pages:
                f.write(json.dumps(page_info, ensure_ascii=False) + "\n")
        os.replace(tmp_file, FAILED_PAGES_FILE)
        logger.info(f"REPROCESS: Arquivo de falhas atualizado. "
                    f"{len(still_failed_pages)} páginas ainda pendentes.")
    except IOError as e:
        logger.critical(f"REPROCESS: Erro crítico ao escrever {FAILED_PAGES_FILE}: {e}")

    # --- Registrar páginas que viraram falhas finais ---
    if dead_pages:
        try:
            with open(FAILED_PAGES_DEAD_FILE, 'a', encoding='utf-8') as f:
                for page_info in dead_pages:
                    f.write(json.dumps(page_info, ensure_ascii=False) + "\n")
            logger.warning(f"REPROCESS: {len(dead_pages)} páginas movidas para {FAILED_PAGES_DEAD_FILE}.")
        except IOError as e:
            logger.critical(f"REPROCESS: Erro crítico ao escrever {FAILED_PAGES_DEAD_FILE}: {e}")

    logger.info(f"--- Reprocessamento Concluído ---")
    logger.info(f"Total de páginas reprocessadas com sucesso: {success_count}")
    logger.info(f"Total de páginas ainda falhando: {len(still_failed_pages)}")
    logger.info(f"Total de páginas em falha final: {len(dead_pages)}")


if __name__ == '__main__':
    # --- Mecanismo de lock (idêntico ao script principal) ---
    try:
        lock_handle = open(LOCK_FILE, "w")
        fcntl.lockf(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        logger.info("REPROCESS: Lock adquirido. Iniciando reprocessamento.")
    except IOError:
        logger.warning("REPROCESS: Outra instância do script (principal ou reprocessamento) já está em execução. Saindo.")
        sys.exit(0)

    reprocessar_paginas_com_falha()
    logger.info("REPROCESS: Script de reprocessamento finalizado.")
