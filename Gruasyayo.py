import streamlit as st
import json

# Función para cargar la base de datos desde un archivo JSON
@st.cache_data
def load_data(json_file):
    with open(json_file, "r", encoding="utf-8") as f:
        return json.load(f)

# Cargar la base de datos. Se asume que el JSON se llama "gruas_data.json"
data = load_data("gruas_data.json")

# Extraemos la lista de grúas que se encuentra en la clave "Hoja1"
gruas_list = data.get("Hoja1", [])

st.title("Selector de Grúas Tore")

st.sidebar.header("Filtros de búsqueda")

# Filtro para la longitud mínima de la pluma instalada (en metros)
pluma_req = st.sidebar.number_input("Longitud mínima de pluma (m):", min_value=0.0, value=30.0, step=0.5)

# Filtro para la carga mínima en punta (kg)
carga_punta_req = st.sidebar.number_input("Carga mínima en punta (kg):", min_value=0.0, value=1000.0, step=100.0)

# Opción para filtrar por carga a distancia específica
use_especifica = st.sidebar.checkbox("Filtrar por carga a distancia específica")

if use_especifica:
    # Estos valores de ejemplo se pueden ajustar
    distancia_req = st.sidebar.number_input("Distancia específica requerida (m):", min_value=0.0, value=14.0, step=0.5)
    carga_especifica_req = st.sidebar.number_input("Carga específica mínima (kg):", min_value=0.0, value=2420.0, step=100.0)

st.header("Resultados de la búsqueda")

# Lista para almacenar las grúas que cumplan los requisitos
resultados = []

for grua in gruas_list:
    # Se utilizan las claves exactas según el JSON ("Pluma Instalada", "Carga en Punta", etc.)
    if grua.get("Pluma Instalada", 0) < pluma_req:
        continue
    if grua.get("Carga en Punta", 0) < carga_punta_req:
        continue
    if use_especifica:
        # Validamos que existan los datos de distancia y carga específica
        if grua.get("Distancia Específica") is None or grua.get("Carga específica") is None:
            continue
        # Se verifica que la distancia sea exactamente la requerida
        if grua["Distancia Específica"] != distancia_req:
            continue
        # Se verifica que la carga específica sea al menos la requerida
        if grua["Carga específica"] < carga_especifica_req:
            continue
    resultados.append(grua)

if resultados:
    for idx, grua in enumerate(resultados, start=1):
        st.write(f"### Grúa {idx}")
        st.write(f"**Modelo:** {grua.get('Modelo de Grúa Torre', 'N/A')}")
        st.write(f"**Pluma Instalada:** {grua.get('Pluma Instalada', 'N/A')} m")
        st.write(f"**Carga en Punta:** {grua.get('Carga en Punta', 'N/A')} kg")
        st.write(f"**Distancia Específica:** {grua.get('Distancia Específica', 'N/A')} m")
        st.write(f"**Carga específica:** {grua.get('Carga específica', 'N/A')} kg")
        st.markdown("---")
else:
    st.write("No se encontraron grúas que cumplan los requisitos.")
