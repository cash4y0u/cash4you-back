from fastapi import FastAPI
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
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
