# Esse é um script de backup para o banco de dados SQLite usado pelo Radar PNCP.
# Ele cria um backup do banco de dados, compacta o arquivo e remove backups antigos.
# Certifique-se de que o script tenha permissões de execução: chmod +x backup.sh    
#!/bin/bash

DB_PATH="/var/www/radar-pncp/database.db"
BACKUP_DIR="/var/www/radar-pncp/backups"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_FILE="$BACKUP_DIR/backup_$TIMESTAMP.db.gz"

# Cria o diretório de backup se não existir
mkdir -p "$BACKUP_DIR"

echo "Iniciando backup de $DB_PATH para $BACKUP_FILE..."

# Usa o comando .backup para criar uma cópia consistente e depois a compacta com gzip
sqlite3 "$DB_PATH" ".backup '$BACKUP_DIR/temp_backup.db'" && gzip -c "$BACKUP_DIR/temp_backup.db" > "$BACKUP_FILE" && rm "$BACKUP_DIR/temp_backup.db"

if [ $? -eq 0 ]; then
  echo "Backup concluído com sucesso."
  # Lógica de retenção: remove backups mais antigos que 7 dias
  find "$BACKUP_DIR" -type f -name "*.db.gz" -mtime +7 -delete
  echo "Backups antigos removidos."
else
  echo "ERRO: Falha ao criar o backup." >&2
fi


#Deve restringir o acesso ao backup
# Assumindo que seu app roda com o usuário 'www-data' (comum para servidores web)
sudo chown www-data:www-data /var/www/radar-pncp/database.db
sudo chmod 600 /var/www/radar-pncp/database.db