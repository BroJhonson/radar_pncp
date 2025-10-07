# python create_admin.py
import os
import mysql.connector
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
import getpass  # <--- getpass para entrada segura de senha escrita diretamente no terminal

load_dotenv()

# --- Configurações ---
db_host = os.getenv('MARIADB_HOST')
db_user = os.getenv('MARIADB_USER')
db_password = os.getenv('MARIADB_PASSWORD')
db_name = os.getenv('MARIADB_DATABASE')

# --- Lógica ---
try:
    # --- COLETA INTERATIVA DE DADOS ---
    username = input("Digite o nome de usuário do novo administrador: ")
    # getpass.getpass não mostra a senha enquanto digita
    password = getpass.getpass("Digite a senha do administrador: ")
    password_confirm = getpass.getpass("Confirme a senha: ")

    if not password or password != password_confirm:
        print("As senhas não conferem ou estão vazias. Operação cancelada.")
        exit() # Sai do script

    bcrypt = Bcrypt()
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    conn = mysql.connector.connect(
        host=db_host,
        user=db_user,
        password=db_password,
        database=db_name
    )
    cursor = conn.cursor()

    query = "INSERT INTO usuarios (username, password_hash) VALUES (%s, %s)"
    cursor.execute(query, (username, hashed_password))

    conn.commit()

    print(f"Usuário administrador '{username}' criado com sucesso!")

except mysql.connector.Error as err:
    print(f"Erro ao criar usuário: {err}")
    # Se der erro de "usuário já existe", a mensagem de erro do mysql.connector será clara
finally:
    if 'conn' in locals() and conn.is_connected():
        cursor.close()
        conn.close()