import pymysql


def get_db_connection():
    conn = pymysql.connect(
        host='localhost',      # Endereço do servidor MySQL
        user='root',          # Usuário do MySQL
        password='secret',    # Senha do MySQL
        database='cash4you',  # Nome do banco de dados
        cursorclass=pymysql.cursors.DictCursor  # Retorna resultados como dicionários
    )
    return conn