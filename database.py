import os

import pymysql
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    conn = pymysql.connect(
        host=os.getenv("HOST"),      # Endereço do servidor MySQL
        user=os.getenv("USER"),          # Usuário do MySQL
        password=os.getenv("SECRET"),    # Senha do MySQL
        database=os.getenv("DATABASE"),  # Nome do banco de dados
        cursorclass=pymysql.cursors.DictCursor  # Retorna resultados como dicionários
    )
    return conn