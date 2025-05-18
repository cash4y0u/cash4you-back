from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel
from database import get_db_connection
from auth import verificar_token
from utils import agora_sp
from datetime import date, timedelta

router = APIRouter(
    tags=["Parcelas"],
    dependencies=[Depends(verificar_token)]
)

class PagamentoRequest(BaseModel):
    valor_pago: float
    payment_date: date
    payment_method: str


@router.get("/parcelas-vencer")
def parcelas_vencer(periodo: str = Query("todos", description="Filtrar por hoje, amanha, 7, 30 ou todos")):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        filtro = ""
        hoje = date.today()

        if periodo == "hoje":
            filtro = f"AND DATE(p.maturity) = '{hoje}'"
        elif periodo == "amanha":
            amanha = hoje + timedelta(days=1)
            filtro = f"AND DATE(p.maturity) = '{amanha}'"
        elif periodo == "7":
            sete_dias = hoje + timedelta(days=7)
            filtro = f"AND DATE(p.maturity) BETWEEN '{hoje}' AND '{sete_dias}'"
        elif periodo == "30":
            trinta_dias = hoje + timedelta(days=30)
            filtro = f"AND DATE(p.maturity) BETWEEN '{hoje}' AND '{trinta_dias}'"
        # Se for "todos", não adiciona filtro extra

        cursor.execute(f"""
            SELECT 
                p.*, 
                c.customer_id, 
                c.split,
                cu.name as customer_name
            FROM cash4you.provisions p
            JOIN cash4you.contracts c ON p.contract_id = c.id
            JOIN cash4you.customers cu ON c.customer_id = cu.id
            WHERE p.status = 'pending'
            {filtro}
            ORDER BY 
            CASE 
                WHEN p.maturity = CURDATE() THEN 0
                ELSE 1
            END,
            p.maturity ASC
        """)
        provisions = cursor.fetchall()

        if not provisions:
            raise HTTPException(status_code=404, detail="Nenhuma parcela encontrada para o período selecionado.")

        return {"provisions": provisions, "total": len(provisions)}
    finally:
        conn.close()

@router.get("/parcelas-pagas")
def parcelas_pagas(periodo: str = Query("todos", description="Filtrar por hoje, ontem, 7, 15, 30 dias ou todos")):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        filtro = ""
        hoje = date.today()

        if periodo == "hoje":
            filtro = f"AND DATE(p.paid_at) = '{hoje}'"
        elif periodo == "ontem":
            ontem = hoje - timedelta(days=1)
            filtro = f"AND DATE(p.paid_at) = '{ontem}'"
        elif periodo == "7":
            sete_dias = hoje - timedelta(days=7)
            filtro = f"AND DATE(p.paid_at) BETWEEN '{sete_dias}' AND '{hoje}'"
        elif periodo == "15":
            quinze_dias = hoje - timedelta(days=15)
            filtro = f"AND DATE(p.paid_at) BETWEEN '{quinze_dias}' AND '{hoje}'"
        elif periodo == "30":
            trinta_dias = hoje - timedelta(days=30)
            filtro = f"AND DATE(p.paid_at) BETWEEN '{trinta_dias}' AND '{hoje}'"
        # Se for "todos", não adiciona filtro extra

        cursor.execute(f"""
            SELECT 
                p.*, 
                c.customer_id, 
                c.split,
                cu.name as customer_name
            FROM cash4you.provisions p
            JOIN cash4you.contracts c ON p.contract_id = c.id
            JOIN cash4you.customers cu ON c.customer_id = cu.id
            WHERE p.status = 'paid'
            {filtro}
            ORDER BY 
                CASE WHEN p.paid_at = CURDATE() THEN 0 ELSE 1 END,
                p.paid_at ASC
        """)
        provisions = cursor.fetchall()

        if not provisions:
            raise HTTPException(status_code=404, detail="Nenhuma parcela paga encontrada para o período selecionado.")

        return {
            "provisions": provisions,
            "total": len(provisions)
        }
    finally:
        conn.close()

@router.post("/parcelas/{id}/finalizar-pagamento")
def finalizar_pagamento(id: int, pagamento: PagamentoRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Buscar a parcela original
        cursor.execute("SELECT * FROM cash4you.provisions WHERE id = %s", (id,))
        parcela = cursor.fetchone()

        if not parcela:
            raise HTTPException(status_code=404, detail="Parcela não encontrada")

        if parcela["status"] == "paid":
            raise HTTPException(status_code=400, detail="Parcela já está paga")

        valor_pago = pagamento.valor_pago
        valor_parcela = float(parcela["amount"])
        contrato_id = parcela["contract_id"]
        data_pagamento = pagamento.payment_date

        # Atualizar a parcela original
        novo_status = "paid"
        cursor.execute("""
            UPDATE cash4you.provisions
            SET amount_paid = %s,
                status = %s,
                paid_at = %s,
                payment_method = %s,
                updated_at = %s
            WHERE id = %s
        """, (
            valor_pago,
            novo_status,
            data_pagamento,
            pagamento.payment_method,
            agora_sp(),
            id
        ))

        # Criar despesa no centro de custo "Financeiro" com type "in"
        descricao = f"Recebimento da parcela #{parcela['number']} do contrato {contrato_id}"

        cursor.execute("""
            INSERT INTO cash4you.expenses (
                description, value, cost_center, status, type, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            descricao,
            valor_pago,
            "Financeiro",
            "paid",
            "in",
            data_pagamento,
            data_pagamento
        ))

        # Se o valor for menor, cria nova parcela com o valor original
        if valor_pago < valor_parcela:
            restante = valor_parcela - valor_pago

            # Buscar última data de vencimento do contrato
            cursor.execute("""
                SELECT MAX(maturity) as ultima_data
                FROM cash4you.provisions
                WHERE contract_id = %s
            """, (contrato_id,))
            ultima = cursor.fetchone()
            data_ultima = ultima["ultima_data"]

            # Calcular próxima data
            data_nova = adicionar_um_mes(data_ultima)

            cursor.execute("""
                INSERT INTO cash4you.provisions (
                    number, contract_id, amount, amount_paid, maturity, status, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                int(parcela["number"]) + 1,
                contrato_id,
                valor_parcela,
                0,
                data_nova,
                "pending",
                agora_sp(),
                agora_sp()
            ))

        conn.commit()
        return {"message": "Pagamento processado com sucesso"}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"Erro ao processar pagamento: {str(e)}")
    finally:
        conn.close()

def adicionar_um_mes(data: date) -> date:
    import calendar
    ano = data.year
    mes = data.month + 1
    if mes > 12:
        mes = 1
        ano += 1
    dia = min(data.day, calendar.monthrange(ano, mes)[1])
    return date(ano, mes, dia)