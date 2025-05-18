from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel
from database import get_db_connection
from auth import verificar_token
from datetime import datetime, date

from utils import agora_sp

router = APIRouter(
    prefix="/fechamento",
    tags=["Fechamento"],
    dependencies=[Depends(verificar_token)]
)


@router.get("/fechamento-transacoes")
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


class FechamentoRequest(BaseModel):
    data: date

@router.post("")
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


