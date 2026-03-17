import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    conn = pymysql.connect(
        host=os.getenv("HOST"),
        user=os.getenv("USER"),
        password=os.getenv("SECRET"),
        database=os.getenv("DATABASE"),
        port=3306,
        cursorclass=pymysql.cursors.DictCursor
    )
    return conn
