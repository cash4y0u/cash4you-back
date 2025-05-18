from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import BaseModel
from starlette import status

# Chave secreta para gerar token (em produção, guarde isso em variável de ambiente)
SECRET_KEY = "super-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Simulação de "banco de dados"
fake_user_db = {
    "usuario@email.com": {
        "username": "usuario@email.com",
        "password": "123456",  # senha em texto puro (apenas para exemplo)
    }
}

class Token(BaseModel):
    access_token: str
    token_type: str

def create_access_token(data: dict):
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def verificar_token(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou ausente",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        return username  # ou dados do payload, se quiser
    except JWTError:
        raise credentials_exception




