from fastapi import APIRouter, HTTPException, Depends, Path
from typing import List
from pydantic import BaseModel, EmailStr
from starlette import status

from database import get_db_connection
from auth import verificar_token
import json
from utils import agora_sp

router = APIRouter(
    prefix="/clientes",
    tags=["Clientes"],
    dependencies=[Depends(verificar_token)]
)
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
    name: str
    birth: str
    document: str
    email: EmailStr
    phone: str
    addresses: List[Address]

@router.get("")
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

@router.get("/{id}")
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
# Rota para atualizar um cliente
@router.put("/{id}")
async def update_client(id: int, client: ClientUpdate):
    print(f"\n🚀 Recebida requisição PUT /clientes/{id}")
    try:
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
            client.name,
            client.birth,
            client.document,
            client.email,
            client.phone,
            json.dumps([address.model_dump() for address in client.addresses]),
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

@router.post("")
async def create_client(client: ClientUpdate):
    print("\n🚀 Recebida requisição POST /clientes")
    try:
        addresses_serialized = json.dumps([address.model_dump() for address in client.addresses])
        query = """
            INSERT INTO customers (name, birth, document, email, phone, adresses, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s,%s);
        """
        values = (
            client.name,
            client.birth,
            client.document,
            client.email,
            client.phone,
            addresses_serialized,
            agora_sp(),
            agora_sp()
        )
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()
        print("\n🎉 Cliente cadastrado com sucesso!")
        return {"message": "Cliente cadastrado com sucesso!"}
    except Exception as e:
        print(f"\n❌ Erro ao processar requisição: {e}")
        raise HTTPException(status_code=422, detail=f"Erro ao validar JSON: {str(e)}")

@router.get("/{id}/telefone")
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

@router.delete("/{id}", status_code=status.HTTP_200_OK)
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

@router.get("/parcela/{id_parcela}/telefone")
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
