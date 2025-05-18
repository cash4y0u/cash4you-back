from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel
from database import get_db_connection
from auth import verificar_token
from datetime import datetime
from typing import Optional
import json
import pymysql

from utils import agora_sp

router = APIRouter(
    prefix="/rotas",
    tags=["Rotas"],
    dependencies=[Depends(verificar_token)]
)

# Modelo de entrada
class RotaCreate(BaseModel):
    provision_id: int
    motoboy_id: Optional[int] = None  # Inicialmente opcional, pois começa sem motoboy

@router.post("", status_code=201)
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

@router.get("")
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

@router.get("/{id}")
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


@router.delete("/{id}", status_code=204)
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

@router.patch("/{id}/token")
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


@router.patch("/{id}")
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
