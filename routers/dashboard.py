from fastapi import APIRouter, Depends, HTTPException, Query
from database import get_db_connection
from auth import verificar_token
from datetime import date, datetime, timedelta

router = APIRouter(
    tags=["Dashboard"],
    dependencies=[Depends(verificar_token)]
)

@router.get("/transacoes")
def obter_transacoes_dashboard(
        inicio: date = Query(..., description="Data de início"),
        fim: date = Query(..., description="Data de fim")
):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            -- Empréstimos (Saída)
            SELECT 
                'Saída' AS tipo,
                c.id AS id,
                c.created_at AS data,
                CONCAT('Novo empréstimo - ', cu.name) COLLATE utf8mb4_unicode_ci AS descricao,
                c.amount AS valor
            FROM cash4you.contracts c
            JOIN cash4you.customers cu ON c.customer_id = cu.id
            WHERE DATE(c.created_at) BETWEEN %s AND %s
            
            UNION ALL
            
            -- Pagamento de parcelas (Entrada)
            SELECT 
                'Entrada' AS tipo,
                p.id AS id,
                p.maturity AS data,
                CONCAT('Pagamento de parcela - ', cu.name) COLLATE utf8mb4_unicode_ci AS descricao,
                p.amount_paid AS valor
            FROM cash4you.provisions p
            JOIN cash4you.contracts c ON p.contract_id = c.id
            JOIN cash4you.customers cu ON c.customer_id = cu.id
            WHERE p.status = 'paid' AND DATE(p.maturity) BETWEEN %s AND %s
            ORDER BY data DESC
        """, (inicio, fim, inicio, fim))

        transacoes = cursor.fetchall()
        return {"transacoes": transacoes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar transações: {str(e)}")
    finally:
        conn.close()


@router.get("/contracts/count")
def count_contracts(
    start_date: str = Query(..., description="Data inicial (YYYY-MM-DD)"),
    end_date: str = Query(..., description="Data final (YYYY-MM-DD)")
):
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)  # inclui o dia final inteiro

        connection = get_db_connection()
        with connection.cursor() as cursor:
            query = """
                SELECT COUNT(*) AS total
                FROM cash4you.contracts
                WHERE created_at >= %s AND created_at < %s
            """
            cursor.execute(query, (start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")))
            result = cursor.fetchone()
            return {
                "start_date": start_date,
                "end_date": end_date,
                "contracts_count": result["total"]
            }
    except ValueError:
        return {"error": "Formato de data inválido. Use YYYY-MM-DD."}
    except Exception as e:
        return {"error": str(e)}


@router.get("/clients/count")
def count_clients(
    start_date: str = Query(..., description="Data inicial (YYYY-MM-DD)"),
    end_date: str = Query(..., description="Data final (YYYY-MM-DD)")
):
    try:
        # Validação do formato das datas
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        connection = get_db_connection()
        with connection.cursor() as cursor:
            query = """
                SELECT COUNT(*) AS total
                FROM cash4you.customers
                WHERE created_at BETWEEN %s AND %s
            """
            cursor.execute(query, (start_date, end_date))
            result = cursor.fetchone()
            return {
                "start_date": start_date,
                "end_date": end_date,
                "customers_count": result["total"]
            }
    except ValueError:
        return {"error": "Formato de data inválido. Use YYYY-MM-DD."}
    except Exception as e:
        return {"error": str(e)}

@router.get("/contracts/profit/monthly")
def get_monthly_profit(
    start_date: str = Query(...),
    end_date: str = Query(...)
):
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)

        connection = get_db_connection()
        with connection.cursor() as cursor:
            query = """
                SELECT DATE_FORMAT(created_at, '%%Y-%%m') AS month, SUM(amount_profit) AS total
                FROM contracts
                WHERE created_at >= %s AND created_at < %s
                AND deleted_at IS NULL
                GROUP BY month
                ORDER BY month
            """

            cursor.execute(query, (start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")))
            results = cursor.fetchall()
            return results
    except Exception as e:
        return {"error": str(e)}
