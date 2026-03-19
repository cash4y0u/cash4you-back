from fastapi import APIRouter, Form, HTTPException
from pydantic import BaseModel
from jose import jwt
from auth import SECRET_KEY, ALGORITHM
from database import get_db_connection
import bcrypt
import pymysql
from fastapi import Request, Form, HTTPException

router = APIRouter(tags=["Autenticação"])

class Token(BaseModel):
    access_token: str
    token_type: str
    user_name: str

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

        if not user["password"]:
            raise HTTPException(status_code=401, detail="Senha inválida")

        # Comparar senha com hash
        if not bcrypt.checkpw(password.encode('utf-8'), user["password"].encode('utf-8')):
            raise HTTPException(status_code=401, detail="Senha inválida")

        access_token = create_access_token({"sub": user["email"]})
        user_name = user.get("name") or user.get("nome") or user["email"]

        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "user_name": user_name
        }

    finally:
        cursor.close()
        conn.close()

@router.post("/register")
async def register(
    request: Request,
    name: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    token: str = Form(...),
    photo: str = Form(...),
    created_at: str = Form(...),
    updated_at: str = Form(...),
    phone: str = Form(...)
):
    auth_header = request.headers.get("Authorization")
    if auth_header != "Bearer secretcash4you":
        raise HTTPException(status_code=401, detail="Token inválido")

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM cash4you.users WHERE email = %s", (username,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Usuário já existe")

        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute(
            "INSERT INTO cash4you.users (name, email, password, token, photo, created_at, updated_at, phone) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (name, username, hashed, token, photo, created_at, updated_at, phone)
        )
        conn.commit()
        return {"message": "Usuário cadastrado com sucesso"}
    finally:
        cursor.close()
        conn.close()