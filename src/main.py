from fastapi import FastAPI
from src.schemas import TransaccionEntrada, PrediccionSalida
from src.modelo import predecir

app = FastAPI(title='API Detección de Fraude')

@app.get('/')
def root():
    return {'mensaje': 'API de detección de fraude activa'}

@app.post('/predecir', response_model=PrediccionSalida)
def predecir_fraude(transaccion: TransaccionEntrada):
    datos = transaccion.model_dump()
    resultado = predecir(datos)
    return resultado
