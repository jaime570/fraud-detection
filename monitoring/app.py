"""
Dashboard de monitorización del modelo de fraude.

Compara los datos de referencia (entrenamiento) contra los datos
"actuales" (simulación de producción) usando Evidently AI, y muestra
el reporte de drift dentro de una app de Streamlit.
"""

import pandas as pd
import streamlit as st
from evidently import Report
from evidently.presets import DataDriftPreset

st.set_page_config(page_title="Monitorización - Fraude Bancario", layout="wide")

st.title("📊 Monitorización del modelo de detección de fraude")
st.markdown(
    "Comparativa entre los datos de **referencia** (entrenamiento) y los "
    "datos **actuales** (simulación de producción), para detectar *data "
    "drift* — cambios en la distribución de las variables que podrían "
    "degradar el rendimiento del modelo."
)

referencia = pd.read_csv("monitoring/referencia.csv")
actual = pd.read_csv("monitoring/actual.csv")

st.subheader("Vista previa de los datos")
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Referencia (entrenamiento)**")
    st.dataframe(referencia.head())
with col2:
    st.markdown("**Actual (producción simulada)**")
    st.dataframe(actual.head())

st.subheader("Reporte de Data Drift")

with st.spinner("Generando reporte de drift..."):
    report = Report([DataDriftPreset()])
    resultado = report.run(reference_data=referencia, current_data=actual)

st.components.v1.html(resultado.get_html_str(as_iframe=False), height=1200, scrolling=True)