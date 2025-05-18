from fastapi import APIRouter, Depends, HTTPException, Path, Request
from pydantic import BaseModel
from database import get_db_connection
from auth import verificar_token
import json

from utils import agora_sp

router = APIRouter(
    prefix="/centros-custo",
    tags=["Centros de Custo"],
    dependencies=[Depends(verificar_token)]
)

class CentroCustoCreate(BaseModel):
    name: str
    description: str

class CentroCustoUpdate(BaseModel):
    name: str
    description: str

@router.get("")
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

@router.post("")
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

@router.put("/{id}")
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

@router.delete("/{id}")
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
