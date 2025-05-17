import calendar
import json
from typing import List, Optional

from fastapi import FastAPI, Path, Request, Query, Depends, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
import pymysql
from pydantic import BaseModel, EmailStr
import pytz
# Cria a aplicação FastAPI
app = FastAPI()

from fastapi.security import OAuth2PasswordBearer
# Configura o CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Permite apenas o frontend (React, por exemplo)
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos os métodos (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Permite todos os cabeçalhos
)

# Função para conectar ao banco de dados MySQL
def get_db_connection():
    conn = pymysql.connect(
        host='localhost',      # Endereço do servidor MySQL
        user='root',          # Usuário do MySQL
        password='secret',    # Senha do MySQL
        database='cash4you',  # Nome do banco de dados
        cursorclass=pymysql.cursors.DictCursor  # Retorna resultados como dicionários
    )
    return conn


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


def agora_sp():
    tz = pytz.timezone("America/Sao_Paulo")
    return datetime.now(tz)

# Rota para buscar todos os clientes (apenas ID e nome)
@app.get("/clientes", dependencies=[Depends(verificar_token)])
def buscar_clientes():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Faz a consulta no banco de dados
        cursor.execute("SELECT id, name FROM cash4you.customers;")
        customers = cursor.fetchall()

        # Verifica se há resultados
        if not customers:
            raise HTTPException(status_code=404, detail="Nenhum cliente encontrado")

        # Retorna apenas os campos id e name
        return {"customers": customers}
    finally:
        conn.close()

@app.get("/clientes/{id}", dependencies=[Depends(verificar_token)])
def buscar_cliente_por_id(id: int = Path(..., description="ID do cliente")):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Busca os detalhes do cliente
        cursor.execute("SELECT * FROM cash4you.customers WHERE id = %s;", (id,))
        cliente = cursor.fetchone()

        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")

        return cliente
    finally:
        conn.close()

class Address(BaseModel):
    city: str
    type: str
    state: str
    number: str
    street: str
    zipcode: str
    district: str
    favorite: bool


class ClientUpdate(BaseModel):
    nome: str
    birth: str
    document: str
    email: EmailStr
    phone: str
    addresses: List[Address]


# Rota para atualizar um cliente
@app.put("/clientes/{id}", dependencies=[Depends(verificar_token)])
async def update_client(id: int, request: Request):
    # 1️⃣ FORÇA UM PRINT LOGO NO INÍCIO PARA SABER SE A FUNÇÃO ESTÁ SENDO CHAMADA
    print(f"\n🚀 Recebida requisição PUT /clientes/{id}")

    # 2️⃣ PEGA O JSON BRUTO E IMPRIME ANTES DE VALIDAR
    raw_body = await request.body()  # Captura o body bruto
    body_str = raw_body.decode("utf-8")  # Decodifica para string
    print(f"\n📌 Body bruto recebido:\n{body_str}")  # Print do JSON recebido como string

    try:
        # 3️⃣ CONVERTE O BODY PARA JSON (DICT) E PRINTA
        json_body = json.loads(body_str)
        print(f"\n✅ Body convertido para JSON:\n{json.dumps(json_body, indent=2)}")

        # 4️⃣ VALIDA OS DADOS COM Pydantic
        client = ClientUpdate(**json_body)

        # 5️⃣ EXECUTA A QUERY PARA ATUALIZAR O CLIENTE
        query = """
            UPDATE customers SET 
            name = %s, 
            birth = %s, 
            document = %s, 
            email = %s, 
            phone = %s, 
            adresses = %s 
            WHERE id = %s
        """
        values = (
            client.nome,
            client.birth,
            client.document,
            client.email,
            client.phone,
            json.dumps([address.dict() for address in client.addresses]),
            id
        )

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()

        print("\n🎉 Cliente atualizado com sucesso!")
        return {"message": "Cliente atualizado com sucesso!"}

    except Exception as e:
        print(f"\n❌ Erro ao processar requisição: {e}")
        raise HTTPException(status_code=422, detail=f"Erro ao validar JSON: {str(e)}")


@app.post("/clientes", include_in_schema=False, dependencies=[Depends(verificar_token)])
@app.post("/clientes/", include_in_schema=True, dependencies=[Depends(verificar_token)])
async def create_client(request: Request):
    print("\n🚀 Recebida requisição POST /clientes")

    raw_body = await request.body()
    body_str = raw_body.decode("utf-8")
    print(f"\n📌 Body bruto recebido:\n{body_str}")

    try:
        json_body = json.loads(body_str)
        print(f"\n✅ Body convertido para JSON:\n{json.dumps(json_body, indent=2)}")

        # 4️⃣ VALIDA OS DADOS COM Pydantic
        client = ClientUpdate(**json_body)

        # 5️⃣ CONVERTE OS OBJETOS Address PARA DICIONÁRIOS
        addresses_serialized = json.dumps([address.dict() for address in client.addresses])

        # 6️⃣ EXECUTA A QUERY PARA INSERIR O CLIENTE
        query = """
            INSERT INTO customers (name, birth, document, email, phone, adresses, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s,%s);
        """
        values = (
            client.nome,
            client.birth,
            client.document,
            client.email,
            client.phone,
            addresses_serialized,
            agora_sp(),
            agora_sp()# ✅ Agora serializável
        )

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, values) # Obtém o ID do cliente inserido
        conn.commit()
        cursor.close()
        conn.close()

        print("\n🎉 Cliente cadastrado com sucesso!")
        return {"message": "Cliente cadastrado com sucesso!"}

    except Exception as e:
        print(f"\n❌ Erro ao processar requisição: {e}")
        raise HTTPException(status_code=422, detail=f"Erro ao validar JSON: {str(e)}")


@app.get("/parcelas-vencer", dependencies=[Depends(verificar_token)])
def parcelas_vencer(periodo: str = Query("todos", description="Filtrar por hoje, amanha, 7, 30 ou todos")):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        filtro = ""
        hoje = date.today()

        if periodo == "hoje":
            filtro = f"AND DATE(p.maturity) = '{hoje}'"
        elif periodo == "amanha":
            amanha = hoje + timedelta(days=1)
            filtro = f"AND DATE(p.maturity) = '{amanha}'"
        elif periodo == "7":
            sete_dias = hoje + timedelta(days=7)
            filtro = f"AND DATE(p.maturity) BETWEEN '{hoje}' AND '{sete_dias}'"
        elif periodo == "30":
            trinta_dias = hoje + timedelta(days=30)
            filtro = f"AND DATE(p.maturity) BETWEEN '{hoje}' AND '{trinta_dias}'"
        # Se for "todos", não adiciona filtro extra

        cursor.execute(f"""
            SELECT 
                p.*, 
                c.customer_id, 
                c.split,
                cu.name as customer_name
            FROM cash4you.provisions p
            JOIN cash4you.contracts c ON p.contract_id = c.id
            JOIN cash4you.customers cu ON c.customer_id = cu.id
            WHERE p.status = 'pending'
            {filtro}
            ORDER BY 
            CASE 
                WHEN p.maturity = CURDATE() THEN 0
                ELSE 1
            END,
            p.maturity ASC
        """)
        provisions = cursor.fetchall()

        if not provisions:
            raise HTTPException(status_code=404, detail="Nenhuma parcela encontrada para o período selecionado.")

        return {"provisions": provisions, "total": len(provisions)}
    finally:
        conn.close()


from datetime import date, timedelta

@app.get("/parcelas-pagas", dependencies=[Depends(verificar_token)])
def parcelas_pagas(periodo: str = Query("todos", description="Filtrar por hoje, ontem, 7, 15, 30 dias ou todos")):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        filtro = ""
        hoje = date.today()

        if periodo == "hoje":
            filtro = f"AND DATE(p.paid_at) = '{hoje}'"
        elif periodo == "ontem":
            ontem = hoje - timedelta(days=1)
            filtro = f"AND DATE(p.paid_at) = '{ontem}'"
        elif periodo == "7":
            sete_dias = hoje - timedelta(days=7)
            filtro = f"AND DATE(p.paid_at) BETWEEN '{sete_dias}' AND '{hoje}'"
        elif periodo == "15":
            quinze_dias = hoje - timedelta(days=15)
            filtro = f"AND DATE(p.paid_at) BETWEEN '{quinze_dias}' AND '{hoje}'"
        elif periodo == "30":
            trinta_dias = hoje - timedelta(days=30)
            filtro = f"AND DATE(p.paid_at) BETWEEN '{trinta_dias}' AND '{hoje}'"
        # Se for "todos", não adiciona filtro extra

        cursor.execute(f"""
            SELECT 
                p.*, 
                c.customer_id, 
                c.split,
                cu.name as customer_name
            FROM cash4you.provisions p
            JOIN cash4you.contracts c ON p.contract_id = c.id
            JOIN cash4you.customers cu ON c.customer_id = cu.id
            WHERE p.status = 'paid'
            {filtro}
            ORDER BY 
                CASE WHEN p.paid_at = CURDATE() THEN 0 ELSE 1 END,
                p.paid_at ASC
        """)
        provisions = cursor.fetchall()

        if not provisions:
            raise HTTPException(status_code=404, detail="Nenhuma parcela paga encontrada para o período selecionado.")

        return {
            "provisions": provisions,
            "total": len(provisions)
        }
    finally:
        conn.close()


@app.get("/emprestimos", dependencies=[Depends(verificar_token)])
def emprestimos(periodo: str = Query("todos", description="Filtrar por hoje, ontem, 7, 15, 30 dias ou todos")):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        filtro = ""
        hoje = date.today()

        if periodo == "hoje":
            filtro = f"AND DATE(c.created_at) = '{hoje}'"
        elif periodo == "ontem":
            ontem = hoje - timedelta(days=1)
            filtro = f"AND DATE(c.created_at) = '{ontem}'"
        elif periodo == "7":
            sete_dias = hoje - timedelta(days=7)
            filtro = f"AND DATE(c.created_at) BETWEEN '{sete_dias}' AND '{hoje}'"
        elif periodo == "15":
            quinze_dias = hoje - timedelta(days=15)
            filtro = f"AND DATE(c.created_at) BETWEEN '{quinze_dias}' AND '{hoje}'"
        elif periodo == "30":
            trinta_dias = hoje - timedelta(days=30)
            filtro = f"AND DATE(c.created_at) BETWEEN '{trinta_dias}' AND '{hoje}'"
        # Se for "todos", não adiciona filtro extra

        cursor.execute(f"""
            SELECT  
                c.*,  
                cu.name AS customer_name 
            FROM cash4you.contracts c 
            JOIN cash4you.customers cu ON c.customer_id = cu.id
            WHERE 1=1
            {filtro}
            ORDER BY c.created_at DESC
        """)
        contracts = cursor.fetchall()

        if not contracts:
            raise HTTPException(status_code=404, detail="Nenhum empréstimo encontrado para o período selecionado.")

        return {
            "contracts": contracts,
            "total": len(contracts)
        }
    finally:
        conn.close()

@app.get("/contas-bancarias", dependencies=[Depends(verificar_token)])
def buscar_contas_bancarias():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Faz a consulta no banco de dados
        cursor.execute("SELECT * FROM cash4you.account_bank;")
        accounts = cursor.fetchall()

        # Verifica se há resultados
        if not accounts:
            raise HTTPException(status_code=404, detail="Nenhum cliente encontrado")

        # Retorna apenas os campos id e name
        return {"accounts": accounts}
    finally:
        conn.close()


@app.post("/contas-bancarias", include_in_schema=True, dependencies=[Depends(verificar_token)])
async def create_account_bank(request: Request):
    import json
    from fastapi import HTTPException
    from datetime import datetime

    print("\n🏦 Recebida requisição POST /contas-bancarias")

    try:
        raw_body = await request.body()
        body_str = raw_body.decode("utf-8")
        print(f"\n📌 Body bruto recebido:\n{body_str}")

        data = json.loads(body_str)
        print(f"\n✅ Body convertido para JSON:\n{json.dumps(data, indent=2)}")

        # Validação simples dos campos esperados
        nome = data.get("banco")
        agencia = data.get("agencia")
        conta = data.get("conta")
        saldo = float(data.get("saldo", 0))

        if not all([nome, agencia, conta]):
            raise HTTPException(status_code=400, detail="Campos obrigatórios ausentes.")

        # Inserção no banco
        query = """
            INSERT INTO cash4you.account_bank (name, agency, account, balance, created_at, updated_at)
            VALUES (%s, %s, %s, %s,%s,%s);
        """
        values = (nome, agencia, conta, saldo,agora_sp(),agora_sp())

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()

        print("\n✅ Conta bancária cadastrada com sucesso!")
        return {"message": "Conta bancária cadastrada com sucesso!"}

    except Exception as e:
        print(f"\n❌ Erro ao processar requisição: {e}")
        raise HTTPException(status_code=422, detail=f"Erro ao processar JSON: {str(e)}")


@app.get("/centros-custo", dependencies=[Depends(verificar_token)])
def buscar_centro_custo():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Faz a consulta no banco de dados
        cursor.execute("SELECT * FROM cash4you.cost_center;")
        cost_center = cursor.fetchall()

        # Verifica se há resultados
        if not cost_center:
            raise HTTPException(status_code=404, detail="Nenhum cliente encontrado")

        # Retorna apenas os campos id e name
        return {"cost_center": cost_center}
    finally:
        conn.close()


class CentroCustoCreate(BaseModel):
    name: str
    description: str

@app.post("/centros-custo", dependencies=[Depends(verificar_token)])
async def criar_centro_custo(request: Request):
    try:
        # Lê e imprime o body bruto
        raw_body = await request.body()
        body_str = raw_body.decode("utf-8")
        print(f"\n📥 Body recebido:\n{body_str}")

        # Converte para JSON e valida com Pydantic
        data = json.loads(body_str)
        centro = CentroCustoCreate(**data)

        # Query de inserção
        query = """
            INSERT INTO cash4you.cost_center (name, description, created_at, updated_at)
            VALUES (%s, %s, %s, %s);
        """
        values = (centro.name, centro.description, agora_sp(),agora_sp())

        # Executa a inserção
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()

        print("✅ Centro de custo inserido com sucesso.")
        return {"message": "Centro de custo cadastrado com sucesso."}

    except Exception as e:
        print(f"❌ Erro ao inserir centro de custo: {e}")
        raise HTTPException(status_code=400, detail=f"Erro ao cadastrar: {str(e)}")

class CentroCustoUpdate(BaseModel):
    name: str
    description: str

@app.put("/centros-custo/{id}", dependencies=[Depends(verificar_token)])
async def atualizar_centro_custo(id: int = Path(...), request: Request = None):
    try:
        # Lê o corpo da requisição
        raw_body = await request.body()
        body_str = raw_body.decode("utf-8")
        print(f"\n✏️ Body recebido para atualização:\n{body_str}")

        # Valida os dados
        data = json.loads(body_str)
        centro = CentroCustoUpdate(**data)

        # Atualiza o registro
        query = """
            UPDATE cash4you.cost_center
            SET name = %s, description = %s, updated_at = %s
            WHERE id = %s;
        """
        values = (centro.name, centro.description, agora_sp(), id)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, values)
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Centro de custo não encontrado.")

        cursor.close()
        conn.close()

        print("✅ Centro de custo atualizado com sucesso.")
        return {"message": "Centro de custo atualizado com sucesso."}

    except Exception as e:
        print(f"❌ Erro ao atualizar centro de custo: {e}")
        raise HTTPException(status_code=400, detail=f"Erro ao atualizar: {str(e)}")

@app.delete("/centros-custo/{id}", dependencies=[Depends(verificar_token)])
def deletar_centro_custo(id: int = Path(..., description="ID do centro de custo a ser deletado")):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Executa o DELETE
        query = "DELETE FROM cash4you.cost_center WHERE id = %s;"
        cursor.execute(query, (id,))
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Centro de custo não encontrado.")

        cursor.close()
        conn.close()

        print(f"🗑️ Centro de custo com ID {id} deletado com sucesso.")
        return {"message": "Centro de custo deletado com sucesso."}

    except Exception as e:
        print(f"❌ Erro ao deletar centro de custo: {e}")
        raise HTTPException(status_code=400, detail=f"Erro ao deletar: {str(e)}")

from datetime import timedelta, datetime, date
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import JWTError, jwt

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

from fastapi import Form

@app.post("/login", response_model=Token)
async def login(
    username: str = Form(...),
    password: str = Form(...)
):
    user = fake_user_db.get(username)
    print(user)
    if not user or user["password"] != password:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    access_token = create_access_token({"sub": user["username"]})
    print(access_token)
    return {
        "access_token": access_token,
        "token_type": "Bearer"
    }

@app.get("/despesas",dependencies=[Depends(verificar_token)])
def listar_despesas(
    periodo: str = Query("todos", description="Filtrar por hoje, ontem, 7, 15, 30 dias ou todos")
):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        filtro = ""
        hoje = date.today()

        if periodo == "hoje":
            filtro = f"AND DATE(e.created_at) = '{hoje}'"
        elif periodo == "ontem":
            ontem = hoje - timedelta(days=1)
            filtro = f"AND DATE(e.created_at) = '{ontem}'"
        elif periodo == "7":
            sete_dias = hoje - timedelta(days=7)
            filtro = f"AND DATE(e.created_at) BETWEEN '{sete_dias}' AND '{hoje}'"
        elif periodo == "15":
            quinze_dias = hoje - timedelta(days=15)
            filtro = f"AND DATE(e.created_at) BETWEEN '{quinze_dias}' AND '{hoje}'"
        elif periodo == "30":
            trinta_dias = hoje - timedelta(days=30)
            filtro = f"AND DATE(e.created_at) BETWEEN '{trinta_dias}' AND '{hoje}'"
        # Se for "todos", não aplica filtro

        cursor.execute(f"""
            SELECT * FROM cash4you.expenses e
            WHERE 1=1
            {filtro}
            ORDER BY e.created_at DESC
        """)
        despesas = cursor.fetchall()

        if not despesas:
            raise HTTPException(status_code=404, detail="Nenhuma despesa encontrada para o período selecionado.")

        return {"despesas": despesas, "total": len(despesas)}
    finally:
        conn.close()


class DespesaCreate(BaseModel):
    description: str
    value: float
    cost_center: str
    status: str
    type: str# exemplo: "pending", "paid", etc.

@app.post("/despesas", dependencies=[Depends(verificar_token)])
async def criar_despesa(request: Request):
    try:
        raw_body = await request.body()
        body_str = raw_body.decode("utf-8")
        print(f"\n📥 Body recebido:\n{body_str}")

        data = json.loads(body_str)
        despesa = DespesaCreate(**data)

        query = """
            INSERT INTO cash4you.expenses (description, value, cost_center, status, type, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s,%s,%s);
        """
        values = (
            despesa.description,
            despesa.value,
            despesa.cost_center,
            despesa.status,
            despesa.type,
            agora_sp(),
            agora_sp()
        )

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()

        print("✅ Despesa cadastrada com sucesso.")
        return {"message": "Despesa cadastrada com sucesso!"}

    except Exception as e:
        print(f"❌ Erro ao cadastrar despesa: {e}")
        raise HTTPException(status_code=400, detail=f"Erro ao cadastrar: {str(e)}")

@app.put("/despesas/{id}", dependencies=[Depends(verificar_token)])
async def atualizar_despesa(id: int, request: Request):
    try:
        raw_body = await request.body()
        body_str = raw_body.decode("utf-8")
        data = json.loads(body_str)

        # Validação básica
        if not all(key in data for key in ["description", "value", "cost_center", "status"]):
            raise HTTPException(status_code=400, detail="Campos obrigatórios ausentes.")

        query = """
            UPDATE cash4you.expenses
            SET description=%s, value=%s, cost_center=%s, status=%s, updated_at=%s
            WHERE id=%s
        """
        values = (
            data["description"],
            data["value"],
            data["cost_center"],
            data["status"],
            id,
            agora_sp()
        )

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()

        return {"message": "Despesa atualizada com sucesso!"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao atualizar: {str(e)}")

@app.delete("/despesas/{id}", dependencies=[Depends(verificar_token)])
def deletar_despesa(id: int = Path(..., description="ID da despesa a deletar")):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cash4you.expenses WHERE id = %s", (id,))
        conn.commit()
        cursor.close()
        conn.close()

        return {"message": "Despesa removida com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao deletar: {str(e)}")

class FormaPagamento(BaseModel):
    id: int
    name: str
    description: str

@app.get("/formas-pagamento", response_model=List[FormaPagamento], dependencies=[Depends(verificar_token)])
def listar_formas_pagamento():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, name, description FROM payments_methods")
            results = cursor.fetchall()
            print(results)
        return results
    finally:
        conn.close()


# Modelo de entrada
class FormaPagamentoCreate(BaseModel):
    name: str
    description: str

@app.post("/formas-pagamento", dependencies=[Depends(verificar_token)])
def criar_forma_pagamento(forma: FormaPagamentoCreate):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            query = "INSERT INTO payments_methods (name, description) VALUES (%s, %s)"
            cursor.execute(query, (forma.name, forma.description))
        conn.commit()
        return {"message": "Forma de pagamento criada com sucesso!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao criar forma de pagamento: {str(e)}")
    finally:
        conn.close()


class FormaPagamentoUpdate(BaseModel):
    name: str
    description: str

# Rota para atualizar forma de pagamento
@app.put("/formas-pagamento/{id}", dependencies=[Depends(verificar_token)])
def atualizar_forma_pagamento(id: int, dados: FormaPagamentoUpdate):
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            # Verifica se existe
            cursor.execute("SELECT * FROM payments_methods WHERE id = %s", (id,))
            existente = cursor.fetchone()
            if not existente:
                raise HTTPException(status_code=404, detail="Forma de pagamento não encontrada")

            # Atualiza os dados
            cursor.execute(
                """
                UPDATE payments_methods
                SET name = %s, description = %s
                WHERE id = %s
                """,
                (dados.name, dados.description, id),
            )
            connection.commit()

        return {"message": "Forma de pagamento atualizada com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection.close()

from fastapi import status

@app.delete("/formas-pagamento/{id}", status_code=status.HTTP_200_OK)
def deletar_forma_pagamento(id: int = Path(..., description="ID da forma de pagamento a ser removida")):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Verifica se a forma de pagamento existe
            cursor.execute("SELECT * FROM payments_methods WHERE id = %s", (id,))
            existente = cursor.fetchone()
            if not existente:
                raise HTTPException(status_code=404, detail="Forma de pagamento não encontrada")

            # Realiza a exclusão
            cursor.execute("DELETE FROM payments_methods WHERE id = %s", (id,))
        conn.commit()
        return {"message": "Forma de pagamento deletada com sucesso!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao deletar forma de pagamento: {str(e)}")
    finally:
        conn.close()


class PagamentoRequest(BaseModel):
    valor_pago: float
    payment_date: date
    payment_method: str

@app.post("/parcelas/{id}/finalizar-pagamento", dependencies=[Depends(verificar_token)])
def finalizar_pagamento(id: int, pagamento: PagamentoRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Buscar a parcela original
        cursor.execute("SELECT * FROM cash4you.provisions WHERE id = %s", (id,))
        parcela = cursor.fetchone()

        if not parcela:
            raise HTTPException(status_code=404, detail="Parcela não encontrada")

        if parcela["status"] == "paid":
            raise HTTPException(status_code=400, detail="Parcela já está paga")

        valor_pago = pagamento.valor_pago
        valor_parcela = float(parcela["amount"])
        contrato_id = parcela["contract_id"]
        data_pagamento = pagamento.payment_date

        # Atualizar a parcela original
        novo_status = "paid"
        cursor.execute("""
            UPDATE cash4you.provisions
            SET amount_paid = %s,
                status = %s,
                paid_at = %s,
                payment_method = %s,
                updated_at = %s
            WHERE id = %s
        """, (
            valor_pago,
            novo_status,
            data_pagamento,
            pagamento.payment_method,
            agora_sp(),
            id
        ))

        # Criar despesa no centro de custo "Financeiro" com type "in"
        descricao = f"Recebimento da parcela #{parcela['number']} do contrato {contrato_id}"

        cursor.execute("""
            INSERT INTO cash4you.expenses (
                description, value, cost_center, status, type, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            descricao,
            valor_pago,
            "Financeiro",
            "paid",
            "in",
            data_pagamento,
            data_pagamento
        ))

        # Se o valor for menor, cria nova parcela com o valor original
        if valor_pago < valor_parcela:
            restante = valor_parcela - valor_pago

            # Buscar última data de vencimento do contrato
            cursor.execute("""
                SELECT MAX(maturity) as ultima_data
                FROM cash4you.provisions
                WHERE contract_id = %s
            """, (contrato_id,))
            ultima = cursor.fetchone()
            data_ultima = ultima["ultima_data"]

            # Calcular próxima data
            data_nova = adicionar_um_mes(data_ultima)

            cursor.execute("""
                INSERT INTO cash4you.provisions (
                    number, contract_id, amount, amount_paid, maturity, status, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                int(parcela["number"]) + 1,
                contrato_id,
                valor_parcela,
                0,
                data_nova,
                "pending",
                agora_sp(),
                agora_sp()
            ))

        conn.commit()
        return {"message": "Pagamento processado com sucesso"}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"Erro ao processar pagamento: {str(e)}")
    finally:
        conn.close()


def adicionar_um_mes(data: date) -> date:
    import calendar
    ano = data.year
    mes = data.month + 1
    if mes > 12:
        mes = 1
        ano += 1
    dia = min(data.day, calendar.monthrange(ano, mes)[1])
    return date(ano, mes, dia)

from pydantic import BaseModel
from fastapi import Request

def calcular_datas_parcelas(data_inicio: date, quantidade: int, ciclo: str):
    datas = []
    atual = data_inicio

    for _ in range(quantidade):
        datas.append(atual)
        if ciclo == "daily":
            atual += timedelta(days=1)
        elif ciclo == "weekly":
            atual += timedelta(weeks=1)
        elif ciclo == "biweekly":
            atual += timedelta(weeks=2)
        elif ciclo == "monthly":
            mes = atual.month + 1
            ano = atual.year + (mes - 1) // 12
            mes = (mes - 1) % 12 + 1
            try:
                atual = atual.replace(year=ano, month=mes)
            except ValueError:
                atual = atual.replace(year=ano, month=mes, day=28)
    return datas

class EmprestimoCreate(BaseModel):
    customer_id: int
    amount: float
    split: int
    amount_provision: float
    amount_rate: float
    amount_total: float
    amount_profit: float
    rate: float
    cycle: str
    maturity: date

@app.post("/emprestimos", dependencies=[Depends(verificar_token)])
async def criar_emprestimo(request: Request):
    conn = None
    try:
        raw_body = await request.body()
        body_str = raw_body.decode("utf-8")
        print(f"\n📥 Body recebido:\n{body_str}")

        data = json.loads(body_str)
        emprestimo = EmprestimoCreate(**data)

        conn = get_db_connection()
        cursor = conn.cursor()

        # Inserir contrato
        query_contrato = """
            INSERT INTO contracts (
                customer_id, amount, split,
                amount_provision, amount_rate, amount_total,
                amount_profit, rate, cycle, maturity, rate_daily,
                created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        cursor.execute(query_contrato, (
            emprestimo.customer_id,
            emprestimo.amount,
            emprestimo.split,
            emprestimo.amount_provision,
            emprestimo.amount_rate,
            emprestimo.amount_total,
            emprestimo.amount_profit,
            emprestimo.rate,
            emprestimo.cycle,
            emprestimo.maturity,
            round(emprestimo.rate / 30, 4),
            agora_sp(),
            agora_sp()

        ))

        contract_id = cursor.lastrowid

        # Criar parcelas
        datas = calcular_datas_parcelas(emprestimo.maturity, emprestimo.split, emprestimo.cycle)
        for i, vencimento in enumerate(datas, start=1):
            cursor.execute(
                """
                INSERT INTO provisions (
                    number, contract_id, amount, amount_paid, status, maturity,
                    created_at, updated_at
                )
                VALUES (%s, %s, %s, 0, %s, %s, %s, %s)
                """,
                (i, contract_id, emprestimo.amount_provision, 'pending', vencimento,agora_sp(),agora_sp())
            )

        # NOVO: Criar despesa no centro de custo "Financeiro"
        descricao_despesa = f"Concessão de empréstimo contrato #{contract_id}"
        cursor.execute(
            """
            INSERT INTO cash4you.expenses (
                description, value, cost_center, status, type, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                descricao_despesa,
                emprestimo.amount,
                "Financeiro",
                "paid",
                "out" ,
                agora_sp(),
                agora_sp()# saída de dinheiro
            )
        )

        conn.commit()
        print("✅ Empréstimo e despesa cadastrados com sucesso.")
        return {"message": "Empréstimo e despesa cadastrados com sucesso!"}

    except Exception as e:
        print(f"❌ Erro ao cadastrar empréstimo: {e}")
        raise HTTPException(status_code=400, detail=f"Erro ao cadastrar empréstimo: {str(e)}")
    finally:
        if conn:
            conn.close()

from datetime import datetime

from fastapi import Query, HTTPException
from datetime import date

@app.get("/fechamento-transacoes", dependencies=[Depends(verificar_token)])
def obter_transacoes_do_dia(data: date = Query(..., description="Data do fechamento")):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            -- Apenas Despesas (Entrada e Saída de acordo com o campo 'type')
            SELECT 
                CASE 
                    WHEN e.type = 'in' THEN 'Entrada'
                    ELSE 'Saída'
                END COLLATE utf8mb4_unicode_ci AS tipo,
                e.id AS id,
                e.created_at AS data,
                e.description COLLATE utf8mb4_unicode_ci AS descricao,
                e.value AS valor,
                '-' COLLATE utf8mb4_unicode_ci AS formaPagamento,
                e.cost_center COLLATE utf8mb4_unicode_ci AS centroCusto,
                'Confirmado' COLLATE utf8mb4_unicode_ci AS status
            FROM cash4you.expenses e
            WHERE e.status = 'paid' 
              AND DATE(e.created_at) = %s
            ORDER BY e.created_at ASC
        """, (data,))

        transacoes = cursor.fetchall()
        return {"transacoes": transacoes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar transações: {str(e)}")
    finally:
        conn.close()


@app.get("/dashboard/transacoes", dependencies=[Depends(verificar_token)])
def obter_transacoes_dashboard(
        inicio: date = Query(..., description="Data de início"),
        fim: date = Query(..., description="Data de fim")
):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            -- Empréstimos (Saída)
            SELECT 
                'Saída' AS tipo,
                c.id AS id,
                c.created_at AS data,
                CONCAT('Novo empréstimo - ', cu.name) COLLATE utf8mb4_unicode_ci AS descricao,
                c.amount AS valor
            FROM cash4you.contracts c
            JOIN cash4you.customers cu ON c.customer_id = cu.id
            WHERE DATE(c.created_at) BETWEEN %s AND %s

            UNION

            -- Despesas (Entrada e Saída)
            SELECT 
                CASE WHEN e.type = 'in' THEN 'Entrada' ELSE 'Saída' END COLLATE utf8mb4_unicode_ci AS tipo,
                e.id AS id,
                e.created_at AS data,
                e.description COLLATE utf8mb4_unicode_ci AS descricao,
                e.value AS valor
            FROM cash4you.expenses e
            WHERE e.status = 'paid' AND DATE(e.created_at) BETWEEN %s AND %s

            ORDER BY data DESC
        """, (inicio, fim, inicio, fim))

        transacoes = cursor.fetchall()
        return {"transacoes": transacoes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar transações: {str(e)}")
    finally:
        conn.close()


from fastapi import FastAPI, Query
from datetime import datetime, timedelta

@app.get("/contracts/count", dependencies=[Depends(verificar_token)])
def count_contracts(
    start_date: str = Query(..., description="Data inicial (YYYY-MM-DD)"),
    end_date: str = Query(..., description="Data final (YYYY-MM-DD)")
):
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)  # inclui o dia final inteiro

        connection = get_db_connection()
        with connection.cursor() as cursor:
            query = """
                SELECT COUNT(*) AS total
                FROM cash4you.contracts
                WHERE created_at >= %s AND created_at < %s
            """
            cursor.execute(query, (start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")))
            result = cursor.fetchone()
            return {
                "start_date": start_date,
                "end_date": end_date,
                "contracts_count": result["total"]
            }
    except ValueError:
        return {"error": "Formato de data inválido. Use YYYY-MM-DD."}
    except Exception as e:
        return {"error": str(e)}


@app.get("/clients/count", dependencies=[Depends(verificar_token)])
def count_clients(
    start_date: str = Query(..., description="Data inicial (YYYY-MM-DD)"),
    end_date: str = Query(..., description="Data final (YYYY-MM-DD)")
):
    try:
        # Validação do formato das datas
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        connection = get_db_connection()
        with connection.cursor() as cursor:
            query = """
                SELECT COUNT(*) AS total
                FROM cash4you.customers
                WHERE created_at BETWEEN %s AND %s
            """
            cursor.execute(query, (start_date, end_date))
            result = cursor.fetchone()
            return {
                "start_date": start_date,
                "end_date": end_date,
                "customers_count": result["total"]
            }
    except ValueError:
        return {"error": "Formato de data inválido. Use YYYY-MM-DD."}
    except Exception as e:
        return {"error": str(e)}

@app.get("/contracts/profit/monthly",dependencies=[Depends(verificar_token)])
def get_monthly_profit(
    start_date: str = Query(...),
    end_date: str = Query(...)
):
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)

        connection = get_db_connection()
        with connection.cursor() as cursor:
            query = """
                SELECT DATE_FORMAT(created_at, '%%Y-%%m') AS month, SUM(amount_profit) AS total
                FROM contracts
                WHERE created_at >= %s AND created_at < %s
                AND deleted_at IS NULL
                GROUP BY month
                ORDER BY month
            """

            cursor.execute(query, (start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")))
            results = cursor.fetchall()
            return results
    except Exception as e:
        return {"error": str(e)}


class BankUpdate(BaseModel):
    banco: str
    agencia: str
    conta: str
    saldo: float

@app.put("/contas-bancarias/{id}", dependencies=[Depends(verificar_token)])
async def atualizar_conta_bancaria(id: int, request: Request):
    try:
        raw_body = await request.body()
        body_str = raw_body.decode("utf-8")
        data = json.loads(body_str)

        print(f"\n📥 Body recebido para atualização:\n{json.dumps(data, indent=2)}")

        # Validação dos campos obrigatórios
        if not all(key in data for key in ["banco", "agencia", "conta", "saldo"]):
            raise HTTPException(status_code=400, detail="Campos obrigatórios ausentes.")

        banco = data["banco"]
        agencia = data["agencia"]
        conta = data["conta"]
        saldo = float(data["saldo"])

        conn = get_db_connection()
        cursor = conn.cursor()

        # Verificar se a conta existe
        cursor.execute("SELECT * FROM cash4you.account_bank WHERE id = %s", (id,))
        existente = cursor.fetchone()
        if not existente:
            raise HTTPException(status_code=404, detail="Conta bancária não encontrada.")

        # Atualizar a conta bancária
        cursor.execute("""
            UPDATE cash4you.account_bank
            SET name = %s,
                agency = %s,
                account = %s,
                balance = %s,
                updated_at = %s
            WHERE id = %s
        """, (banco, agencia, conta, saldo,agora_sp(), id))

        conn.commit()
        cursor.close()
        conn.close()

        return {"message": "Conta bancária atualizada com sucesso!"}

    except Exception as e:
        print(f"❌ Erro ao atualizar conta bancária: {e}")
        raise HTTPException(status_code=400, detail=f"Erro ao atualizar conta bancária: {str(e)}")

class FechamentoRequest(BaseModel):
    data: date

@app.post("/fechamento", dependencies=[Depends(verificar_token)])
def realizar_fechamento(payload: FechamentoRequest = Body(...)):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. Buscar todas as transações do dia
        cursor.execute("""
            SELECT 
                CASE WHEN e.type = 'in' THEN 'Entrada' ELSE 'Saída' END AS tipo,
                e.value
            FROM cash4you.expenses e
            WHERE e.status = 'paid'
              AND DATE(e.created_at) = %s
        """, (payload.data,))
        transacoes = cursor.fetchall()

        if not transacoes:
            raise HTTPException(status_code=404, detail="Nenhuma transação encontrada para o dia selecionado.")

        # 2. Calcular o total de entradas e saídas
        total_entrada = sum(t["value"] for t in transacoes if t["tipo"] == "Entrada")
        total_saida = sum(t["value"] for t in transacoes if t["tipo"] == "Saída")
        saldo_final = total_entrada - total_saida

        print(f"✅ Entradas: {total_entrada}, Saídas: {total_saida}, Saldo a aplicar: {saldo_final}")

        # 3. Buscar a conta bancária principal
        cursor.execute("SELECT id, balance FROM cash4you.account_bank ORDER BY id ASC LIMIT 1")
        conta = cursor.fetchone()

        if not conta:
            raise HTTPException(status_code=404, detail="Nenhuma conta bancária encontrada.")

        novo_saldo = conta["balance"] + saldo_final

        # 4. Atualizar o saldo da conta
        cursor.execute("""
            UPDATE cash4you.account_bank
            SET balance = %s, updated_at = %s
            WHERE id = %s
        """, (novo_saldo, agora_sp(),conta["id"]))

        conn.commit()

        return {
            "message": "Fechamento realizado com sucesso.",
            "saldo_anterior": conta["balance"],
            "entrada_total": total_entrada,
            "saida_total": total_saida,
            "saldo_final": novo_saldo
        }
    except Exception as e:
        print(f"❌ Erro ao realizar fechamento: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao realizar fechamento: {str(e)}")
    finally:
        conn.close()


@app.get("/clientes/{id}/telefone", dependencies=[Depends(verificar_token)])
def buscar_telefone_cliente(id: int = Path(..., description="ID do cliente")):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Consulta somente o telefone pelo ID
        cursor.execute("SELECT phone FROM cash4you.customers WHERE id = %s", (id,))
        resultado = cursor.fetchone()

        if not resultado:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")

        telefone = resultado.get("phone")
        if not telefone:
            raise HTTPException(status_code=404, detail="Telefone não cadastrado para este cliente")

        return {"id": id, "telefone": telefone}
    finally:
        conn.close()

@app.delete("/clientes/{id}", status_code=status.HTTP_200_OK, dependencies=[Depends(verificar_token)])
def deletar_cliente(id: int = Path(..., description="ID do cliente a ser removido")):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Primeiro verifica se o cliente existe
        cursor.execute("SELECT id FROM cash4you.customers WHERE id = %s", (id,))
        cliente = cursor.fetchone()

        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")

        # Deleta o cliente
        cursor.execute("DELETE FROM cash4you.customers WHERE id = %s", (id,))
        conn.commit()

        return {"message": "Cliente deletado com sucesso!"}
    except Exception as e:
        print(f"❌ Erro ao deletar cliente: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao deletar cliente: {str(e)}")
    finally:
        conn.close()


@app.get("/clientes/parcela/{id_parcela}/telefone", dependencies=[Depends(verificar_token)])
def buscar_telefone_por_parcela(id_parcela: int = Path(..., description="ID da parcela")):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Primeiro: pegar o contract_id da parcela
        cursor.execute("SELECT contract_id FROM cash4you.provisions WHERE id = %s", (id_parcela,))
        provision = cursor.fetchone()

        if not provision:
            raise HTTPException(status_code=404, detail="Parcela não encontrada")

        contract_id = provision["contract_id"]

        # Segundo: pegar o customer_id do contrato
        cursor.execute("SELECT customer_id FROM cash4you.contracts WHERE id = %s", (contract_id,))
        contract = cursor.fetchone()

        if not contract:
            raise HTTPException(status_code=404, detail="Contrato não encontrado para a parcela")

        customer_id = contract["customer_id"]

        # Terceiro: buscar o telefone do cliente
        cursor.execute("SELECT phone FROM cash4you.customers WHERE id = %s", (customer_id,))
        customer = cursor.fetchone()

        if not customer:
            raise HTTPException(status_code=404, detail="Cliente não encontrado para o contrato")

        telefone = customer.get("phone")
        if not telefone:
            raise HTTPException(status_code=404, detail="Telefone não cadastrado para este cliente")

        return {
            "cliente_id": customer_id,
            "telefone": telefone
        }

    finally:
        conn.close()


class MotoboyBase(BaseModel):
    name: str
    telephone: str
    active: bool

class MotoboyCreate(MotoboyBase):
    pass

class MotoboyUpdate(MotoboyBase):
    pass

@app.get("/motoboys", dependencies=[Depends(verificar_token)])
def listar_motoboys():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id, name, telephone, active FROM cash4you.motoboys")
        motoboys = cursor.fetchall()
        return {"motoboys": motoboys}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar motoboys: {str(e)}")
    finally:
        conn.close()


@app.post("/motoboys", dependencies=[Depends(verificar_token)])
def criar_motoboy(motoboy: MotoboyCreate):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = """
            INSERT INTO cash4you.motoboys (name, telephone, active, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s)
        """
        now = agora_sp()
        cursor.execute(query, (motoboy.name, motoboy.telephone, motoboy.active, now, now))
        conn.commit()
        return {"message": "Motoboy criado com sucesso!"}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"Erro ao criar motoboy: {str(e)}")
    finally:
        conn.close()


@app.put("/motoboys/{id}", dependencies=[Depends(verificar_token)])
def atualizar_motoboy(id: int, motoboy: MotoboyUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id FROM cash4you.motoboys WHERE id = %s", (id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Motoboy não encontrado")

        query = """
            UPDATE cash4you.motoboys
            SET name = %s, telephone = %s, active = %s, updated_at = %s
            WHERE id = %s
        """
        cursor.execute(query, (motoboy.name, motoboy.telephone, motoboy.active, agora_sp(), id))
        conn.commit()
        return {"message": "Motoboy atualizado com sucesso!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar motoboy: {str(e)}")
    finally:
        conn.close()


@app.delete("/motoboys/{id}", dependencies=[Depends(verificar_token)])
def deletar_motoboy(id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id FROM cash4you.motoboys WHERE id = %s", (id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Motoboy não encontrado")

        cursor.execute("DELETE FROM cash4you.motoboys WHERE id = %s", (id,))
        conn.commit()
        return {"message": "Motoboy deletado com sucesso!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao deletar motoboy: {str(e)}")
    finally:
        conn.close()

# Modelo de entrada
class RotaCreate(BaseModel):
    provision_id: int
    motoboy_id: Optional[int] = None  # Inicialmente opcional, pois começa sem motoboy

@app.post("/rotas", status_code=201, dependencies=[Depends(verificar_token)])
def criar_rota(payload: RotaCreate):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM provisions WHERE id = %s", (payload.provision_id,))
        provision = cursor.fetchone()

        if not provision:
            raise HTTPException(status_code=404, detail="Parcela não encontrada")

        cursor.execute("SELECT * FROM routes WHERE provision_id = %s", (payload.provision_id,))
        rota_existente = cursor.fetchone()
        if rota_existente:
            raise HTTPException(status_code=400, detail="Parcela já está em uma rota")

        cursor.execute("""
            SELECT cu.id as customer_id FROM provisions p
            JOIN contracts c ON p.contract_id = c.id
            JOIN customers cu ON c.customer_id = cu.id
            WHERE p.id = %s
        """, (payload.provision_id,))
        cliente = cursor.fetchone()

        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente não encontrado para essa parcela")

        now = datetime.now()
        cursor.execute("""
            INSERT INTO routes (status, motoboy_id, value, token, customer_id, provision_id, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            'em rota',
            payload.motoboy_id,
            provision["amount"],
            '',  # token vazio por enquanto
            cliente["customer_id"],
            payload.provision_id,
            now,
            now
        ))

        conn.commit()
        return {"message": "Rota criada com sucesso"}

    except HTTPException:
        raise  # deixa o FastAPI lidar com ela normalmente

    except Exception as e:
        print(f"Erro ao criar rota: {e}")
        raise HTTPException(status_code=500, detail="Erro ao criar rota")

    finally:
        cursor.close()
        conn.close()

@app.get("/rotas", dependencies=[Depends(verificar_token)])
def listar_rotas():
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    try:
        cursor.execute("""
                    SELECT r.id, r.status, r.motoboy_id, r.value, r.token,
                           r.customer_id, r.provision_id, r.created_at, r.updated_at,
                           cu.name AS customer_name,
                           cu.adresses AS customer_addresses,
                           p.number AS provision_number
                    FROM cash4you.routes r
                    JOIN cash4you.customers cu ON r.customer_id = cu.id
                    JOIN cash4you.provisions p ON r.provision_id = p.id
                    WHERE r.status = 'em rota'
                    ORDER BY r.created_at DESC
                """)
        rotas = cursor.fetchall()

        for rota in rotas:
            try:
                enderecos = json.loads(rota.get("customer_addresses", "[]"))
                favorito = next((e for e in enderecos if e.get("favorite")), None)
                if not favorito and enderecos:
                    favorito = enderecos[0]

                rota["customer_address"] = favorito
            except Exception:
                rota["customer_address"] = None

            # Remove o campo bruto da resposta
            rota.pop("customer_addresses", None)

        return {"routes": rotas}
    finally:
        cursor.close()
        conn.close()



@app.get("/rotas/{id}", dependencies=[Depends(verificar_token)])
def obter_rota(id: int):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    try:
        cursor.execute("""
            SELECT r.id, r.status, r.motoboy_id, r.value, r.token,
                   r.customer_id, r.provision_id, r.created_at, r.updated_at,
                   cu.name AS customer_name,
                   p.number AS provision_number
            FROM routes r
            JOIN customers cu ON r.customer_id = cu.id
            JOIN provisions p ON r.provision_id = p.id
            WHERE r.id = %s
        """, (id,))
        rota = cursor.fetchone()

        if not rota:
            raise HTTPException(status_code=404, detail="Rota não encontrada")

        return rota

    finally:
        cursor.close()
        conn.close()


@app.delete("/rotas/{id}", status_code=204, dependencies=[Depends(verificar_token)])
def deletar_rota(id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM routes WHERE id = %s", (id,))
        rota = cursor.fetchone()

        if not rota:
            raise HTTPException(status_code=404, detail="Rota não encontrada")

        cursor.execute("DELETE FROM routes WHERE id = %s", (id,))
        conn.commit()
        return  # status 204 No Content

    finally:
        cursor.close()
        conn.close()


class TokenUpdate(BaseModel):
    token: str

@app.patch("/rotas/{id}/token", dependencies=[Depends(verificar_token)])
def atualizar_token_rota(id: int, payload: TokenUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Verifica se a rota existe
        cursor.execute("SELECT * FROM routes WHERE id = %s", (id,))
        rota = cursor.fetchone()

        if not rota:
            raise HTTPException(status_code=404, detail="Rota não encontrada")

        # Atualiza o token
        cursor.execute("""
            UPDATE routes
            SET token = %s, updated_at = %s
            WHERE id = %s
        """, (
            payload.token,
            datetime.now(),
            id
        ))

        conn.commit()
        return {"message": "Token atualizado com sucesso"}

    finally:
        cursor.close()
        conn.close()

class RotaUpdate(BaseModel):
    motoboy_id: int


@app.patch("/rotas/{id}", dependencies=[Depends(verificar_token)])
def atualizar_motoboy_rota(id: int, payload: RotaUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM routes WHERE id = %s", (id,))
        rota = cursor.fetchone()

        if not rota:
            raise HTTPException(status_code=404, detail="Rota não encontrada")

        cursor.execute("""
            UPDATE routes
            SET motoboy_id = %s, updated_at = %s
            WHERE id = %s
        """, (payload.motoboy_id, agora_sp(), id))

        conn.commit()
        return {"message": "Motoboy atribuído com sucesso à rota"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar rota: {str(e)}")
    finally:
        cursor.close()
        conn.close()
