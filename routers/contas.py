from fastapi import APIRouter, Depends, HTTPException, Path, Request
from pydantic import BaseModel
from database import get_db_connection
from auth import verificar_token
import json
from fastapi import HTTPException
from utils import agora_sp

router = APIRouter(
    prefix="/contas-bancarias",
    tags=["Contas Bancárias"],
    dependencies=[Depends(verificar_token)]
)
class BankUpdate(BaseModel):
    banco: str
    agencia: str
    conta: str
    saldo: float

@router.put("/{id}")
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

@router.get("")
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

@router.post("", include_in_schema=True)
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

@router.get("")
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

@router.post("", include_in_schema=True)
async def create_account_bank(request: Request):
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

