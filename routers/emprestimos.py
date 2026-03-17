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

class EmprestimoUpdate(BaseModel):
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

        # --- Comentado: Criação de despesa no centro de custo "Financeiro" ao conceder empréstimo ---
        # descricao_despesa = f"Concessão de empréstimo contrato #{contract_id}"
        # cursor.execute(
        #     """
        #     INSERT INTO cash4you.expenses (
        #         description, value, cost_center, status, type, created_at, updated_at
        #     )
        #     VALUES (%s, %s, %s, %s, %s, %s, %s)
        #     """,
        #     (
        #         descricao_despesa,
        #         emprestimo.amount,
        #         "Financeiro",
        #         "paid",
        #         "out" ,
        #
        #         agora_sp(),
        #         agora_sp()# saída de dinheiro
        #     )
        # )
        # --- Fim do trecho comentado ---

        conn.commit()
        print("✅ Empréstimo cadastrado com sucesso.")
        return {"message": "Empréstimo cadastrado com sucesso!"}

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

@router.get("/usuario/{customer_id}")
def emprestimos_usuario(customer_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT c.*, cu.name AS customer_name
            FROM cash4you.contracts c
            JOIN cash4you.customers cu ON c.customer_id = cu.id
            WHERE c.customer_id = %s
            ORDER BY c.created_at DESC
            """,
            (customer_id,)
        )
        contracts = cursor.fetchall()
        if not contracts:
            raise HTTPException(status_code=404, detail="Nenhum empréstimo encontrado para este usuário.")
        return {
            "contracts": contracts,
            "total": len(contracts)
        }
    finally:
        conn.close()

@router.put("/{contract_id}")
def editar_emprestimo(contract_id: int, emprestimo: EmprestimoUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        print(f"[DEBUG] PUT /emprestimos/{{contract_id}} - contract_id: {contract_id}, payload: {emprestimo}")
        # Buscar split atual
        cursor.execute("SELECT split, cycle, maturity FROM contracts WHERE id = %s", (contract_id,))
        row = cursor.fetchone()
        print(f"[DEBUG] row: {row}")
        if not row:
            print("[ERROR] Contrato não encontrado.")
            raise HTTPException(status_code=404, detail="Contrato não encontrado.")
        split_atual = row['split']
        cycle_atual = row['cycle']
        maturity_atual = row['maturity']
        print(f"[DEBUG] split_atual: {split_atual}, cycle_atual: {cycle_atual}, maturity_atual: {maturity_atual}")

        try:
            cursor.execute(
                """
                UPDATE contracts SET
                    customer_id = %s,
                    amount = %s,
                    split = %s,
                    amount_provision = %s,
                    amount_rate = %s,
                    amount_total = %s,
                    amount_profit = %s,
                    rate = %s,
                    cycle = %s,
                    maturity = %s,
                    updated_at = %s
                WHERE id = %s
                """,
                (
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
                    agora_sp(),
                    contract_id
                )
            )
            print("[DEBUG] Contrato atualizado com sucesso.")
        except Exception as e:
            print(f"[ERROR] Erro na atualização do contrato: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Erro na atualização do contrato: {str(e)}")

        # Se split aumentou, inserir novas parcelas
        if emprestimo.split > split_atual:
            try:
                cursor.execute("SELECT MAX(number) as max FROM provisions WHERE contract_id = %s", (contract_id,))
                result = cursor.fetchone()
                print(f"[DEBUG] result MAX(number): {result}")
                last_number = int(result['max']) if result and result['max'] is not None else 0
                print(f"[DEBUG] last_number: {last_number}")
                datas = calcular_datas_parcelas(emprestimo.maturity, emprestimo.split, emprestimo.cycle)
                for i in range(last_number + 1, emprestimo.split + 1):
                    vencimento = datas[i - 1]
                    print(f"[DEBUG] Inserindo parcela: number={i}, vencimento={vencimento}")
                    cursor.execute(
                        """
                        INSERT INTO provisions (
                            number, contract_id, amount, amount_paid, status, maturity,
                            created_at, updated_at
                        )
                        VALUES (%s, %s, %s, 0, %s, %s, %s, %s)
                        """,
                        (i, contract_id, emprestimo.amount_provision, 'pending', vencimento, agora_sp(), agora_sp())
                    )
                print("[DEBUG] Novas parcelas inseridas com sucesso.")
            except Exception as e:
                print(f"[ERROR] Erro ao inserir novas parcelas: {str(e)}")
                raise HTTPException(status_code=400, detail=f"Erro ao inserir novas parcelas: {str(e)}")
        try:
            conn.commit()
            print("[DEBUG] Commit realizado com sucesso.")
        except Exception as e:
            print(f"[ERROR] Erro no commit: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Erro no commit: {str(e)}")
        return {"message": "Empréstimo atualizado com sucesso!"}
    except Exception as e:
        print(f"[ERROR] Erro ao editar empréstimo: {repr(e)}")
        raise HTTPException(status_code=400, detail=f"Erro ao editar empréstimo: {repr(e)}")
    finally:
        conn.close()
