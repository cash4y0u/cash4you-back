from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from routers import (
    clientes,
    emprestimos,
    parcelas,
    despesas,
    formas_pagamento,
    contas,
    centros_custo,
    rotas,
    motoboys,          # se tiver separado
    dashboard,
    fechamento,
    auth_router        # rota de login
)

app = FastAPI()

origins = [
    "*",  # ou domínio do seu frontend hospedado
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)        # /login
app.include_router(clientes.router)
app.include_router(emprestimos.router)
app.include_router(parcelas.router)
app.include_router(despesas.router)
app.include_router(formas_pagamento.router)
app.include_router(contas.router)
app.include_router(centros_custo.router)
app.include_router(rotas.router)
app.include_router(dashboard.router)
app.include_router(fechamento.router)
app.include_router(motoboys.router)

health_router = APIRouter()

@health_router.get("/health")
def health_check():
    return {"status": "ok"}

@health_router.get("/")
def root():
    return {"message": "Hello"}

app.include_router(health_router)
