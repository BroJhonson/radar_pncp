#!/bin/bash

# Configurações
BACKUP_NAME="radar_pncp_db_$(date +%Y-%m-%d_%H-%M).sql.gz"
LOCAL_PATH="/home/joaby/$BACKUP_NAME"
REMOTE_PATH="gdrive:Backups_VPS_Finnd" # Vai criar essa pasta no seu Drive
CREDENTIALS="/home/joaby/.my.cnf"

# 1. Gera o Backup Local
echo "Gerando backup local: $BACKUP_NAME"
mysqldump --defaults-extra-file=$CREDENTIALS radar_pncp_db | gzip > $LOCAL_PATH

# 2. Envia para o Google Drive
echo "Enviando para o Google Drive..."
/usr/bin/rclone copy $LOCAL_PATH $REMOTE_PATH

# 3. Limpeza Local (Mantém apenas os últimos 2 dias na VPS para economizar disco)
echo "Limpando arquivos locais antigos..."
find /home/joaby -name "*.sql.gz" -mtime +2 -delete

# 4. (Opcional) Limpeza na Nuvem (Apaga backups com mais de 30 dias no Drive)
# Descomente a linha abaixo se quiser economizar espaço no Drive
# /usr/bin/rclone delete $REMOTE_PATH --min-age 30d

echo "Backup concluído com sucesso!"