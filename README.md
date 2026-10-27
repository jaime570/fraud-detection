# 🛡️ Detección de Fraude con Tarjetas — Sistema de ML de punta a punta

Sistema completo de detección de transacciones fraudulentas: desde la ingesta de los datos crudos hasta un modelo servido por API, con orquestación del ETL y monitorización de *data drift*. Todo levantado con Docker Compose.

> El objetivo no es solo entrenar un buen modelo, sino construir **todo lo que lo rodea** en un entorno real: capas de datos, orquestación, tracking de experimentos, serving y monitorización.

---

## 📌 Resultados

Dataset muy desbalanceado: **492 fraudes en 284.807 transacciones (0,17 %)**. Por eso la *accuracy* no sirve como métrica y la evaluación se centra en precisión, recall y F1 de la clase fraude, sobre un test real (20 %, estratificado y **sin** sobremuestreo).

| Modelo | SMOTE | AUC-ROC | Precisión | Recall | F1 |
|---|---|---|---|---|---|
| Decision Tree | No | 0,927 | 0,84 | 0,81 | 0,82 |
| Random Forest | No | 0,965 | 0,93 | 0,82 | 0,87 |
| **XGBoost** | **No** | **0,973** | **0,92** | **0,84** | **0,88** |
| XGBoost | Sí | 0,984 | 0,80 | 0,86 | 0,83 |
| LightGBM | Sí | 0,953 | 0,23 | 0,89 | 0,36 |

**Modelo final: XGBoost sin SMOTE con umbral de decisión 0,29** (en lugar del 0,5 por defecto). Sobre el test detecta 83 de 98 fraudes con una precisión del 89 % (F1 0,87).

### ¿Por qué estas decisiones?

- **SMOTE no compensó.** Mejora ligeramente el recall, pero dispara las falsas alarmas (con XGBoost: 21 frente a 7). En tres de los cuatro modelos el F1 fue mejor sin SMOTE.
- **El umbral es una decisión de negocio.** Un fraude no detectado cuesta el importe de la transacción; una falsa alarma cuesta atención al cliente y experiencia de usuario. Con la curva precisión-recall se eligió 0,29 como punto de equilibrio. Si al negocio le saliera más caro dejar pasar fraudes, bastaría con bajar el umbral.
- **Búsqueda de hiperparámetros en dos fases:** `RandomizedSearchCV` para explorar el espacio y `GridSearchCV` para afinar alrededor de lo mejor.

---

## 🏗️ Arquitectura

```
creditcard.csv (Kaggle)
        │
        ▼
┌───────────────────────── DuckDB ─────────────────────────┐
│  bronze_fraud  ──►  silver_fraud  ──►  gold_fraud        │   ◄── ETL orquestado con Airflow
│  (dato crudo)      (tipos, renombrado)  (listo para ML)  │       (antes con Apache Hop)
└──────────────────────────────────────────────────────────┘
        │
        ▼
 Notebooks: EDA + entrenamiento ──► MLflow (experimentos y métricas)
        │
        ▼
 modelo_xgboost.pkl ──► FastAPI  POST /predecir  →  {es_fraude, probabilidad}
        │
        ▼
 Streamlit + Evidently AI ──► dashboard de data drift
```

| Componente | Tecnología | Para qué |
|---|---|---|
| Almacenamiento | **DuckDB** | Arquitectura medallion (Bronze / Silver / Gold) |
| ETL | **Apache Hop** → **Airflow** | Primera versión visual en Hop; migrada a un DAG de Airflow (PostgreSQL + LocalExecutor), idempotente con `CREATE OR REPLACE` |
| Modelado | **scikit-learn, XGBoost, LightGBM, imbalanced-learn** | Comparativa de modelos, SMOTE, tuning y ajuste de umbral |
| Tracking | **MLflow** | Parámetros y métricas de cada modelo |
| Serving | **FastAPI + Pydantic** | API REST con validación de la entrada |
| Monitorización | **Evidently AI + Streamlit** | Detección de data drift entre entrenamiento y producción |
| Despliegue | **Docker Compose** | Levanta todos los servicios con un comando |

---

## 📂 Estructura del proyecto

```
fraud-detection/
├── dags/
│   └── fraud_etl_dag.py          # DAG de Airflow: bronze → silver → gold
├── hop/                          # Pipelines originales en Apache Hop (.hpl / .hwf)
├── notebooks/
│   ├── 01_eda.ipynb              # Análisis exploratorio
│   └── 02_modelo.ipynb           # Entrenamiento, comparativa y elección de umbral
├── src/
│   ├── main.py                   # API FastAPI
│   ├── schemas.py                # Esquemas de entrada/salida (Pydantic)
│   ├── modelo.py                 # Carga del modelo y predicción con umbral
│   └── modelo_xgboost.pkl        # Modelo entrenado
├── monitoring/
│   ├── generar_referencia.py     # Genera datos de referencia y "producción" con drift simulado
│   └── app.py                    # Dashboard de drift (Streamlit + Evidently)
├── data/                         # No incluido en el repo (ver instalación)
├── docker-compose.yml
├── Dockerfile                    # API
├── Dockerfile.airflow
├── Dockerfile.streamlit
└── requirements.txt
```

---

## 🚀 Cómo ejecutarlo

### Requisitos
- Docker y Docker Compose
- Python 3.11 (para notebooks y scripts locales)

### 1. Clonar y configurar
```bash
git clone https://github.com/jaime570/fraud-detection.git
cd fraud-detection
cp .env.example .env      # y rellena usuario/contraseña de Airflow
```

### 2. Descargar los datos
Descarga [Credit Card Fraud Detection](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud) de Kaggle y guarda `creditcard.csv` en `data/raw/`. Después carga la tabla `bronze_fraud` en `data/fraude.duckdb`:

```python
import duckdb
con = duckdb.connect("data/fraude.duckdb")
con.execute("CREATE OR REPLACE TABLE bronze_fraud AS SELECT * FROM read_csv_auto('data/raw/creditcard.csv')")
```

### 3. Levantar los servicios
```bash
docker compose up -d --build
```

| Servicio | URL |
|---|---|
| API (docs interactivas) | http://localhost:8000/docs |
| Airflow | http://localhost:8080 |
| MLflow | http://localhost:5000 |
| Dashboard de drift | http://localhost:8501 |

En Airflow, activa y lanza el DAG `fraud_etl` para generar las capas Silver y Gold. El dashboard necesita antes `python monitoring/generar_referencia.py`.

> **Nota:** el servicio de MLflow lee `mlflow.db`, que no se incluye en el repo. Se crea al ejecutar `notebooks/02_modelo.ipynb`; hazlo antes de levantar los servicios para que Docker no lo monte como carpeta vacía.

### 4. Probar la API
```bash
curl -X POST http://localhost:8000/predecir \
  -H "Content-Type: application/json" \
  -d '{"Time": 0, "V1": -1.36, "V2": -0.07, "V3": 2.54, "V4": 1.38, "V5": -0.34, "V6": 0.46, "V7": 0.24, "V8": 0.10, "V9": 0.36, "V10": 0.09, "V11": -0.55, "V12": -0.62, "V13": -0.99, "V14": -0.31, "V15": 1.47, "V16": -0.47, "V17": 0.21, "V18": 0.03, "V19": 0.40, "V20": 0.25, "V21": -0.02, "V22": 0.28, "V23": -0.11, "V24": 0.07, "V25": 0.13, "V26": -0.19, "V27": 0.13, "V28": -0.02, "Amount": 149.62}'
```
La respuesta tiene esta forma:
```json
{"es_fraude": 0, "probabilidad": 0.0002}
```
`es_fraude` vale 1 cuando la probabilidad supera el umbral de 0,29.

---

## 🧩 Retos técnicos resueltos

- **Codificación UTF-16 en Windows** que rompía la construcción de la imagen Docker.
- **Compatibilidad de DuckDB vía JDBC** con Apache Hop.
- **Condiciones de carrera en Airflow**, resueltas migrando a PostgreSQL + LocalExecutor con *healthchecks* y dependencias explícitas entre servicios.

## 🔭 Próximos pasos

- Cargar el modelo desde el registro de MLflow en lugar de un `.pkl`.
- Añadir tests automáticos de la API y CI con GitHub Actions.
- Reentrenamiento automático cuando el dashboard detecte drift.

---

**Autor:** Jaime Llorca Martínez · [GitHub](https://github.com/jaime570)

Datos: *Credit Card Fraud Detection*, Machine Learning Group (ULB), publicado en Kaggle.
