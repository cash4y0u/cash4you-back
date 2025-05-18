from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel
from database import get_db_connection
from auth import verificar_token
from utils import agora_sp

router = APIRouter(
    prefix="/motoboys",
    tags=["Motoboys"],
    dependencies=[Depends(verificar_token)]
)

class MotoboyBase(BaseModel):
    name: str
    telephone: str
    active: bool

class MotoboyCreate(MotoboyBase):
    pass

class MotoboyUpdate(MotoboyBase):
    pass

@router.get("")
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

@router.post("")
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


@router.put("/{id}")
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


@router.delete("/{id}")
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
