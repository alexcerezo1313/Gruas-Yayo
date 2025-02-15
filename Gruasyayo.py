import streamlit as st
import json

# Función para cargar la base de datos desde un archivo JSON
@st.cache_data
def load_data(json_file):
    with open(json_file, "r", encoding="utf-8") as f:
        return json.load(f)

# Cargar la base de datos (ajusta el nombre y la ruta del archivo según corresponda)
data = load_data("gruas_data.json")

st.title("Selector de Grúas Tore")

st.sidebar.header("Filtros de búsqueda")

# Filtro para la longitud de pluma instalada
pluma_req = st.sidebar.number_input("Longitud de pluma requerida (m):", min_value=0.0, value=40.0, step=0.5)

# Filtro para la carga en punta
carga_punta_req = st.sidebar.number_input("Carga en punta requerida (kg):", min_value=0.0, value=1000.0, step=100.0)

# Opción para filtrar por carga a distancia específica
use_especifica = st.sidebar.checkbox("Filtrar por carga a distancia específica")

if use_especifica:
    distancia_req = st.sidebar.number_input("Distancia específica requerida (m):", min_value=0.0, value=25.0, step=0.5)
    carga_especifica_req = st.sidebar.number_input("Carga en distancia específica requerida (kg):", min_value=0.0, value=2000.0, step=100.0)

st.header("Resultados de la búsqueda")

# Lista para almacenar las grúas que cumplan los requisitos
resultados = []

for grua in data:
    # Verificar la longitud de la pluma instalada
    if grua.get("pluma_instalada", 0) < pluma_req:
        continue

    # Verificar la carga en punta
    if grua.get("carga_punta", 0) < carga_punta_req:
        continue

    # Si se activa el filtro por distancia específica, se valida la existencia de esos datos
    if use_especifica:
        # Verificar que el registro cuente con los datos de distancia y carga específicas
        if grua.get("distancia_especifica") is None or grua.get("carga_especifica") is None:
            continue

        # En este ejemplo se asume que la distancia específica del registro debe coincidir con la ingresada
        if grua["distancia_especifica"] != distancia_req:
            continue

        # Y que la carga específica registrada debe ser igual o mayor a la requerida
        if grua["carga_especifica"] < carga_especifica_req:
            continue

    # Si se cumplen todos los filtros, se añade el registro a los resultados
    resultados.append(grua)

# Mostrar resultados
if resultados:
    for idx, grua in enumerate(resultados, start=1):
        st.write(f"### Grúa {idx}")
        st.write(f"**Pluma instalada:** {grua.get('pluma_instalada', 'N/A')} m")
        st.write(f"**Carga en punta:** {grua.get('carga_punta', 'N/A')} kg")
        # Se muestran los datos específicos si existen
        if grua.get("distancia_especifica") is not None and grua.get("carga_especifica") is not None:
            st.write(f"**Distancia específica:** {grua.get('distancia_especifica')} m")
            st.write(f"**Carga específica:** {grua.get('carga_especifica')} kg")
        st.markdown("---")
else:
    st.write("No se encontraron grúas que cumplan los requisitos.")
