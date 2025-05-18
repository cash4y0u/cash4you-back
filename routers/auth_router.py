from fastapi import APIRouter, Form, HTTPException
from pydantic import BaseModel
from jose import jwt
from auth import SECRET_KEY, ALGORITHM
from database import get_db_connection
import bcrypt
import pymysql

router = APIRouter(tags=["Autenticação"])

class Token(BaseModel):
    access_token: str
    token_type: str

def create_access_token(data: dict):
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/login", response_model=Token)
async def login(
    username: str = Form(...),
    password: str = Form(...)
):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    try:
        cursor.execute("SELECT * FROM cash4you.users WHERE email = %s", (username,))
        user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=401, detail="Usuário não encontrado")

        # Comparar senha com hash
        if not bcrypt.checkpw(password.encode('utf-8'), user["password"].encode('utf-8')):
            raise HTTPException(status_code=401, detail="Senha inválida")

        access_token = create_access_token({"sub": user["email"]})
        return {
            "access_token": access_token,
            "token_type": "Bearer"
        }

    finally:
        cursor.close()
        conn.close()
