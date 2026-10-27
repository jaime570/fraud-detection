import joblib
import pandas as pd

UMBRAL = 0.29
MODELO_PATH = 'src/modelo_xgboost.pkl'

modelo = joblib.load(MODELO_PATH)

def predecir(datos: dict) -> dict:
    df = pd.DataFrame([datos])
    probabilidad = modelo.predict_proba(df)[0][1]
    es_fraude = int(probabilidad >= UMBRAL)
    
    return {
        'es_fraude': es_fraude,
        'probabilidad': round(float(probabilidad), 4)
    }