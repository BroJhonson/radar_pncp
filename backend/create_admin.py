# python create_admin.py
import os
import mysql.connector
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv

load_dotenv()

# --- Configurações ---
db_host = os.getenv('MARIADB_HOST')
db_user = os.getenv('MARIADB_USER')
db_password = os.getenv('MARIADB_PASSWORD')
db_name = os.getenv('MARIADB_DATABASE')

username = "JoabsonAdmin"  # Meu usuario e senha
password = "Querocomer123@" 

# --- Lógica ---
bcrypt = Bcrypt()
hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

try:
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
finally:
    if 'conn' in locals() and conn.is_connected():
        cursor.close()
        conn.close()