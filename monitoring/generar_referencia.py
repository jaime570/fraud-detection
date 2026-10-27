"""
Genera dos datasets para el análisis de drift con Evidently:
    - referencia.csv -> simula los datos de entrenamiento (distribución "normal")
    - actual.csv      -> simula datos de producción, con drift artificial
                         inyectado en algunas columnas para que el reporte
                         tenga señal que mostrar (en un caso real, este
                         segundo dataset serían las transacciones nuevas
                         que va recibiendo el modelo en producción).
"""

import duckdb
import numpy as np
import pandas as pd

DUCKDB_PATH = "data/fraude.duckdb"  # ejecutar desde la raíz del proyecto

con = duckdb.connect(DUCKDB_PATH)
df = con.execute("SELECT * FROM gold_fraud").df()
con.close()

df = df.drop(columns=["es_fraude"])

# Partimos el dataset en dos mitades aleatorias
referencia, actual = np.array_split(df.sample(frac=1, random_state=42), 2)

referencia = referencia.reset_index(drop=True)
actual = actual.reset_index(drop=True)

# Inyectamos drift artificial en "actual":
# - Amount: simulamos un incremento generalizado del importe medio de las
#   transacciones (p.ej. inflación o cambio de comportamiento de compra)
actual["Amount"] = actual["Amount"] * 1.8 + 15

# - V14: una de las variables más correlacionadas con fraude, le añadimos
#   ruido y desplazamos su distribución para simular un cambio de patrón
actual["V14"] = actual["V14"] * 1.5 - 2

referencia.to_csv("monitoring/referencia.csv", index=False)
actual.to_csv("monitoring/actual.csv", index=False)

print(f"Referencia: {referencia.shape}")
print(f"Actual:     {actual.shape}")
print("Datasets guardados en monitoring/")