# arquivo : backend/run_sync.sh
#!/bin/bash

# --- Configuração ---
LOG_FILE="/var/www/radar-pncp/logs/sync.log"
EMAIL_ALERTA="joaby.codes@gmail.com"
APP_DIR="/var/www/radar-pncp"

# --- Função de Alerta de Falha ---
function handle_error {
  local exit_code=$?
  local line_number=$1
  local error_message="Erro na linha $line_number com código de saída $exit_code."
  local email_body="O script de sincronização do FINND falhou em $(date).

Detalhes do erro:
$error_message

Verifique o log para mais informações: $LOG_FILE
Últimas 20 linhas do log:
$(tail -n 20 "$LOG_FILE")"

  echo "$email_body" | mail -s "[ALERTA DE FALHA] FINND Sync" "$EMAIL_ALERTA"
  echo "--- [CRON WRAPPER] ERRO: Script falhou e alerta foi enviado. ---"
}

# --- Execução Principal ---
trap 'handle_error $LINENO' ERR
cd "$APP_DIR" || exit

echo "--- [CRON WRAPPER] Iniciando sync em $(date) ---"
source venv/bin/activate > /dev/null 2>&1
python sync_api.py

# Verifica status de saída do python anterior. Só roda notificação se sync foi OK.
if [ $? -eq 0 ]; then
    echo "--- Sync finalizado com sucesso em $(date). Iniciando Processamento de Notificações... ---"
    python notificacoes.py
else
    echo "--- Sync falhou. Pulando notificações. ---"
fi

echo "--- Processo finalizado em $(date) ---"