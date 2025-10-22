#!/bin/bash

# --- Configuração ---
LOG_FILE="/var/www/radar-pncp/logs/reprocess.log"
EMAIL_ALERTA="joaby.codes@gmail.com"
APP_DIR="/var/www/radar-pncp"

# --- Função de Alerta de Falha ---
function handle_error {
  local exit_code=$?
  local line_number=$1
  local error_message="Erro na linha $line_number com código de saída $exit_code."
  local email_body="O script de REPROCESSAMENTO do Radar PNCP falhou em $(date).

Detalhes do erro:
$error_message

Verifique o log para mais informações: $LOG_FILE
Últimas 20 linhas do log:
$(tail -n 20 "$LOG_FILE")"

  echo "$email_body" | mail -s "[ALERTA DE FALHA] Radar PNCP Reprocess" "$EMAIL_ALERTA"
  echo "--- [CRON WRAPPER] ERRO: Script de reprocessamento falhou e alerta foi enviado. ---"
}

# --- Execução Principal ---
trap 'handle_error $LINENO' ERR
cd "$APP_DIR" || exit

echo "--- [CRON WRAPPER] Iniciando reprocessamento em $(date) ---"
source venv/bin/activate > /dev/null 2>&1
python reprocessar_pag_fail.py
echo "--- [CRON WRAPPER] Reprocessamento finalizado com sucesso em $(date) ---"