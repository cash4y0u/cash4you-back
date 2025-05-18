from fastapi import APIRouter, Form, HTTPException
from pydantic import BaseModel
from jose import jwt
from auth import SECRET_KEY, ALGORITHM

router = APIRouter(tags=["Autenticação"])

# Banco fake (ou substitua por seu repositório real)
fake_user_db = {
    "usuario@email.com": {
        "username": "usuario@email.com",
        "password": "123456"
    }
}

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
    user = fake_user_db.get(username)
    if not user or user["password"] != password:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    access_token = create_access_token({"sub": user["username"]})
    return {
        "access_token": access_token,
        "token_type": "Bearer"
    }

