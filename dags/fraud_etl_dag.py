"""
DAG de ETL para detección de fraude.

Replica en Python/DuckDB el pipeline que antes hacía Apache Hop:
    bronze_fraud  ->  silver_fraud  ->  gold_fraud

- bronze_fraud: tabla cruda ya existente en DuckDB (no se transforma).
- silver_fraud: renombra Class -> es_fraude y castea tipos.
- gold_fraud:   copia directa de silver (sin transformaciones).

Cada tarea usa CREATE OR REPLACE para ser idempotente: volver a correr
el DAG deja las tablas limpias, sin duplicar filas (equivale al
truncate=Y de Hop).
"""

from __future__ import annotations

import duckdb
import pendulum
from airflow.decorators import dag, task

# Ruta de la base de datos DENTRO del contenedor (volumen ./data montado).
# NO es la ruta de Windows: es la que ve el contenedor del scheduler.
DUCKDB_PATH = "/opt/airflow/data/fraude.duckdb"


@dag(
    dag_id="fraud_etl",
    # En este proyecto el dataset es estático (no llegan transacciones
    # nuevas), por lo que dejamos el disparo en manual. En un escenario
    # real con ingesta diaria de transacciones, este pipeline se
    # programaría con algo como schedule="@daily" (o una expresión cron,
    # ej. "0 2 * * *" para lanzarlo cada noche a las 2:00 AM) para que
    # Airflow regenere bronze->silver->gold automáticamente sin
    # intervención manual.
    schedule=None,
    start_date=pendulum.datetime(2026, 1, 1, tz="Europe/Madrid"),
    catchup=False,
    tags=["fraude", "etl"],
)
def fraud_etl():
    """Pipeline ETL: bronze_fraud -> silver_fraud -> gold_fraud."""

    @task()
    def silver():
        """Bronze -> Silver: renombra Class a es_fraude y castea tipos."""
        # V1..V28 se castean a DOUBLE; los generamos en bucle para no
        # repetir 28 lineas a mano.
        v_cols = ",\n            ".join(
            f"CAST(V{i} AS DOUBLE) AS V{i}" for i in range(1, 29)
        )

        sql = f"""
        CREATE OR REPLACE TABLE silver_fraud AS
        SELECT
            CAST(Time AS BIGINT) AS Time,
            {v_cols},
            CAST(Amount AS DOUBLE) AS Amount,
            CAST(Class AS BIGINT) AS es_fraude
        FROM bronze_fraud;
        """

        con = duckdb.connect(DUCKDB_PATH)
        try:
            con.execute(sql)
            n = con.execute("SELECT COUNT(*) FROM silver_fraud").fetchone()[0]
            print(f"silver_fraud creada con {n} filas")
        finally:
            con.close()

    @task()
    def gold():
        """Silver -> Gold: copia directa, sin transformaciones."""
        con = duckdb.connect(DUCKDB_PATH)
        try:
            con.execute(
                "CREATE OR REPLACE TABLE gold_fraud AS "
                "SELECT * FROM silver_fraud;"
            )
            n = con.execute("SELECT COUNT(*) FROM gold_fraud").fetchone()[0]
            print(f"gold_fraud creada con {n} filas")
        finally:
            con.close()

    # Dependencia: gold no arranca hasta que silver termina con exito.
    silver() >> gold()


fraud_etl()
