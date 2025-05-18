from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from database import get_db_connection
from auth import verificar_token
from datetime import datetime, timedelta, date
import json
from utils import agora_sp

router = APIRouter(
    prefix="/emprestimos",
    tags=["Empréstimos"],
    dependencies=[Depends(verificar_token)]
)

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

def calcular_datas_parcelas(data_inicio: date, quantidade: int, ciclo: str):
    datas = []
    atual = data_inicio

    for _ in range(quantidade):
        datas.routerend(atual)
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

@router.post("")
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

@router.get("")
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
