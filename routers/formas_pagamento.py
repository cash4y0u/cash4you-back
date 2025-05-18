from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel
from typing import List
from database import get_db_connection
from auth import verificar_token

router = APIRouter(
    prefix="/formas-pagamento",
    tags=["Formas de Pagamento"],
    dependencies=[Depends(verificar_token)]
)

class FormaPagamento(BaseModel):
    id: int
    name: str
    description: str

@router.get("", response_model=List[FormaPagamento])
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

@router.post("")
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
@router.put("/{id}")
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

@router.delete("/{id}", status_code=status.HTTP_200_OK)
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


