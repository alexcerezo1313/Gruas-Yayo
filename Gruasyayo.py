import streamlit as st
import json
import pandas as pd

# --------------------------
# Función para cargar el JSON
@st.cache_data
def load_data(json_file):
    with open(json_file, "r", encoding="utf-8") as f:
        return json.load(f)

# Cargar datos; se asume que el JSON se llama "gruas_data.json" y la lista se encuentra en la clave "Hoja1"
data = load_data("gruas_data.json")
gruas_list = data.get("Hoja1", [])

# --------------------------
# Título con "Torre" correctamente escrito
st.title("Selector de Grúas Torre")

st.sidebar.header("Filtros de búsqueda")

# 1. Alcance deseado (Pluma Instalada)
target_alcance = st.sidebar.number_input("Alcance deseado (m):", value=30.0, step=0.5)
# El rango primario es ±15%
alcance_pct = 0.15
alcance_lower = target_alcance * (1 - alcance_pct)
alcance_upper = target_alcance * (1 + alcance_pct)
# Extensión adicional absoluta para casi match: ±5 m
alcance_extra = 5.0

# 2. Carga en Punta
target_carga_punta = st.sidebar.number_input("Carga en Punta (kg):", value=1000.0, step=100.0)
# Rango primario: ±25%
carga_punta_pct = 0.25
carga_punta_lower = target_carga_punta * (1 - carga_punta_pct)
carga_punta_upper = target_carga_punta * (1 + carga_punta_pct)
# Extensión adicional absoluta: ±100 kg
carga_punta_extra = 100.0

# 3. Filtro opcional: Carga Intermedia
use_intermedia = st.sidebar.checkbox("Filtrar por Carga Intermedia")
if use_intermedia:
    # Para la Distancia (se compara con "Distancia Específica")
    target_distancia = st.sidebar.number_input("Distancia (m):", value=14.0, step=0.5)
    distancia_pct = 0.05
    distancia_lower = target_distancia * (1 - distancia_pct)
    distancia_upper = target_distancia * (1 + distancia_pct)
    # Extensión extra: ±5 m
    distancia_extra = 5.0

    # Para la Carga Intermedia (se compara con "Carga específica")
    target_carga_intermedia = st.sidebar.number_input("Carga Intermedia (kg):", value=2420.0, step=100.0)
    carga_intermedia_pct = 0.05
    carga_intermedia_lower = target_carga_intermedia * (1 - carga_intermedia_pct)
    carga_intermedia_upper = target_carga_intermedia * (1 + carga_intermedia_pct)
    # Extensión extra: ±100 kg
    carga_intermedia_extra = 100.0

# --------------------------
# Función para evaluar un campo.
# Recibe: valor, límite inferior primario, límite superior primario y extra (valor absoluto adicional)
# Devuelve:
#   - 0 si está dentro del rango primario.
#   - La desviación (valor que excede el límite primario) si está fuera pero dentro del rango extendido.
#   - None si se excede el rango extendido.
def check_param(value, primary_lower, primary_upper, extra):
    if primary_lower <= value <= primary_upper:
        return 0.0  # sin desviación
    elif value < primary_lower:
        deviation = primary_lower - value
        if deviation <= extra:
            return deviation
        else:
            return None
    else:  # value > primary_upper
        deviation = value - primary_upper
        if deviation <= extra:
            return deviation
        else:
            return None

# --------------------------
# Evaluamos cada grúa y clasificamos
matches = []       # candidatos que cumplen en todos los parámetros (con desviación 0 en cada campo)
almost_matches = []  # candidatos que tienen al menos una desviación > 0 pero están dentro del rango extendido en TODOS

for grua in gruas_list:
    total_deviation = 0.0
    valid = True  # indica que la grúa está dentro de los rangos extendidos en todos los parámetros

    # Campo: Alcance deseado (Pluma Instalada)
    val_alcance = grua.get("Pluma Instalada", None)
    if val_alcance is None:
        valid = False
    else:
        dev_alcance = check_param(val_alcance, alcance_lower, alcance_upper, alcance_extra)
        if dev_alcance is None:
            valid = False
        else:
            total_deviation += dev_alcance

    # Campo: Carga en Punta
    val_carga_punta = grua.get("Carga en Punta", None)
    if val_carga_punta is None:
        valid = False
    else:
        dev_carga_punta = check_param(val_carga_punta, carga_punta_lower, carga_punta_upper, carga_punta_extra)
        if dev_carga_punta is None:
            valid = False
        else:
            total_deviation += dev_carga_punta

    # Si se filtra por carga intermedia, evaluar los campos correspondientes
    if use_intermedia:
        # Campo: Distancia (Distancia Específica)
        val_distancia = grua.get("Distancia Específica", None)
        if val_distancia is None:
            valid = False
        else:
            dev_distancia = check_param(val_distancia, distancia_lower, distancia_upper, distancia_extra)
            if dev_distancia is None:
                valid = False
            else:
                total_deviation += dev_distancia

        # Campo: Carga Intermedia (Carga específica)
        val_carga_intermedia = grua.get("Carga específica", None)
        if val_carga_intermedia is None:
            valid = False
        else:
            dev_carga_intermedia = check_param(val_carga_intermedia, carga_intermedia_lower, carga_intermedia_upper, carga_intermedia_extra)
            if dev_carga_intermedia is None:
                valid = False
            else:
                total_deviation += dev_carga_intermedia

    # Solo consideramos la grúa si pasó en TODOS los campos
    if valid:
        # Si la desviación total es 0, es un "Match"
        tipo = "Match" if total_deviation == 0.0 else "Casi Match"
        candidate = grua.copy()
        candidate["Deviación Total"] = total_deviation
        candidate["Tipo"] = tipo
        if tipo == "Match":
            matches.append(candidate)
        else:
            almost_matches.append(candidate)

# --------------------------
# Seleccionar los resultados:
# Se muestran las 5 primeras grúas que son "Match" y, adicionalmente, la "Casi Match" con menor desviación (si existe)
matches_sorted = matches[:5]

almost_candidate = None
if almost_matches:
    almost_matches_sorted = sorted(almost_matches, key=lambda x: x["Deviación Total"])
    almost_candidate = almost_matches_sorted[0]

# Se combinan los resultados: 5 matches y la casi match (si existe)
resultados = matches_sorted.copy()
if almost_candidate:
    resultados.append(almost_candidate)

# --------------------------
# Mostrar resultados en formato de tabla
if not resultados:
    st.write("No se encontraron grúas que se ajusten (ni casi) a los parámetros solicitados.")
else:
    # Convertir resultados a DataFrame; se muestran las columnas relevantes.
    df = pd.DataFrame(resultados)
    columnas = ["Modelo de Grúa Torre", "Pluma Instalada", "Carga en Punta"]
    if use_intermedia:
        columnas += ["Distancia Específica", "Carga específica"]
    columnas += ["Tipo", "Deviación Total"]
    df = df[columnas]

    st.header("Opciones encontradas")

    # Función para aplicar estilos: verde para Match y amarillo para Casi Match.
    def color_rows(row):
        if row["Tipo"] == "Match":
            return ['background-color: lightgreen'] * len(row)
        elif row["Tipo"] == "Casi Match":
            return ['background-color: lightyellow'] * len(row)
        else:
            return [''] * len(row)

    st.dataframe(df.style.apply(color_rows, axis=1))

