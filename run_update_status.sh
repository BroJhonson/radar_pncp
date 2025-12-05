#arquivo: backend/run_update_status.sh
#!/bin/bash

# --- Configuração ---
LOG_FILE="/var/www/radar-pncp/logs/update_status.log"
EMAIL_ALERTA="joaby.codes@gmail.com"
APP_DIR="/var/www/radar-pncp"

# --- Função de Alerta de Falha ---
function handle_error {
  local exit_code=$?
  local line_number=$1
  local email_body="O script de ATUALIZAÇÃO DE STATUS do Radar PNCP falhou em $(date)..."
  echo "$email_body" | mail -s "[ALERTA DE FALHA] Radar PNCP Update Status" "$EMAIL_ALERTA"
  echo "--- [CRON WRAPPER] ERRO: Script de atualização de status falhou. ---"
}

# --- Execução Principal ---
trap 'handle_error $LINENO' ERR
cd "$APP_DIR" || exit

echo "--- [CRON WRAPPER] Iniciando atualização de status em $(date) ---"
source venv/bin/activate > /dev/null 2>&1
python atualizar_status.py
echo "--- [CRON WRAPPER] Atualização de status finalizada com sucesso em $(date) ---"