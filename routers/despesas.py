from fastapi import APIRouter, Depends, HTTPException, Query, Request, Path
from pydantic import BaseModel
from datetime import date, timedelta
from database import get_db_connection
from auth import verificar_token
import json
from utils import agora_sp

router = APIRouter(
    prefix="/despesas",
    tags=["Despesas"],
    dependencies=[Depends(verificar_token)]
)

class DespesaCreate(BaseModel):
    description: str
    value: float
    cost_center: str
    status: str
    type: str# exemplo: "pending", "paid", etc.

@router.get("")
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

@router.post("")
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

@router.put("/{id}")
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

@router.delete("/{id}")
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