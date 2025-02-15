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
# Título (corrigiendo "Torre")
st.title("Selector de Grúas Torre")

st.sidebar.header("Filtros de búsqueda")

# --- Parámetros de búsqueda ---

# 1. Alcance deseado (Pluma Instalada)
target_alcance = st.sidebar.number_input("Alcance deseado (m):", value=30.0, step=0.5)
# Tolerancia máxima permitida: ±15%
alcance_min_allowed = target_alcance * 0.85
alcance_max_allowed = target_alcance * 1.15

# 2. Carga en Punta
target_carga_punta = st.sidebar.number_input("Carga en Punta (kg):", value=1000.0, step=100.0)
# Tolerancia máxima permitida: ±25%
carga_punta_min_allowed = target_carga_punta * 0.75
carga_punta_max_allowed = target_carga_punta * 1.25

# 3. Filtro opcional: Carga Intermedia
use_intermedia = st.sidebar.checkbox("Filtrar por Carga Intermedia")
if use_intermedia:
    # Distancia: Se acepta únicamente si está entre el 95% y el 105% del valor deseado
    target_distancia = st.sidebar.number_input("Distancia (m):", value=14.0, step=0.5)
    distancia_min_allowed = target_distancia * 0.95
    distancia_max_allowed = target_distancia * 1.05

    # Carga Intermedia: Se acepta únicamente si está entre el 95% y el 105% del valor deseado
    target_carga_intermedia = st.sidebar.number_input("Carga Intermedia (kg):", value=2420.0, step=100.0)
    carga_intermedia_min_allowed = target_carga_intermedia * 0.95
    carga_intermedia_max_allowed = target_carga_intermedia * 1.05

# --------------------------
# Función para calcular el error relativo
# Retorna el error relativo (valor absoluto dividido por el target)
def relative_error(value, target):
    return abs(value - target) / target

# --------------------------
# Evaluamos cada grúa
# Solo se aceptan aquellas que estén dentro de los rangos máximos permitidos.
# Luego se calcula la suma de los errores relativos para todos los parámetros.
# Se asigna el tipo:
#   - "Match" (verde) si TODOS los parámetros tienen un error relativo <= 5%
#   - "Casi Match" (amarillo) si alguno supera el 5%
candidatos = []

for grua in gruas_list:
    valid = True
    errors = {}  # Para guardar el error relativo de cada parámetro

    # 1. Alcance (Pluma Instalada)
    val_alcance = grua.get("Pluma Instalada", None)
    if val_alcance is None or not (alcance_min_allowed <= val_alcance <= alcance_max_allowed):
        valid = False
    else:
        err_alcance = relative_error(val_alcance, target_alcance)
        errors["Alcance"] = err_alcance

    # 2. Carga en Punta
    val_carga_punta = grua.get("Carga en Punta", None)
    if val_carga_punta is None or not (carga_punta_min_allowed <= val_carga_punta <= carga_punta_max_allowed):
        valid = False
    else:
        err_carga_punta = relative_error(val_carga_punta, target_carga_punta)
        errors["Carga en Punta"] = err_carga_punta

    # 3. Si se filtra por carga intermedia, evaluamos esos parámetros
    if use_intermedia:
        # Distancia (Distancia Específica)
        val_distancia = grua.get("Distancia Específica", None)
        if val_distancia is None or not (distancia_min_allowed <= val_distancia <= distancia_max_allowed):
            valid = False
        else:
            err_distancia = relative_error(val_distancia, target_distancia)
            errors["Distancia"] = err_distancia

        # Carga Intermedia (Carga específica)
        val_carga_intermedia = grua.get("Carga específica", None)
        if val_carga_intermedia is None or not (carga_intermedia_min_allowed <= val_carga_intermedia <= carga_intermedia_max_allowed):
            valid = False
        else:
            err_carga_intermedia = relative_error(val_carga_intermedia, target_carga_intermedia)
            errors["Carga Intermedia"] = err_carga_intermedia

    # Si la grúa pasó todos los filtros, se considera candidata
    if valid:
        # Suma de errores relativos
        total_error = sum(errors.values())
        # Se determina el tipo: si todos los errores son <= 5% (0.05), es "Match"
        # De lo contrario, es "Casi Match"
        tipo = "Match" if all(err <= 0.05 for err in errors.values()) else "Casi Match"
        candidato = grua.copy()
        candidato["Total Error Relativo"] = total_error
        candidato["Tipo"] = tipo
        # También guardamos cada error para posibles visualizaciones (opcional)
        candidato.update({f"Err {k}": v for k, v in errors.items()})
        candidatos.append(candidato)

# Ordenamos los candidatos por la suma de errores relativos (de menor a mayor)
candidatos_sorted = sorted(candidatos, key=lambda x: x["Total Error Relativo"])

# Seleccionamos los 5 primeros resultados
resultados = candidatos_sorted[:5]

# --------------------------
# Mostrar resultados en formato de tabla
if not resultados:
    st.write("No se encontraron grúas que se asemejen a los parámetros solicitados.")
else:
    # Creamos un DataFrame con las columnas de interés.
    # Se muestran los parámetros básicos y el tipo.
    columnas = ["Modelo de Grúa Torre", "Pluma Instalada", "Carga en Punta"]
    if use_intermedia:
        columnas += ["Distancia Específica", "Carga específica"]
    columnas += ["Tipo", "Total Error Relativo"]
    df = pd.DataFrame(resultados)[columnas]

    st.header("Opciones encontradas")

    # Función para colorear: verde para "Match", amarillo para "Casi Match"
    def color_rows(row):
        if row["Tipo"] == "Match":
            return ['background-color: lightgreen'] * len(row)
        elif row["Tipo"] == "Casi Match":
            return ['background-color: lightyellow'] * len(row)
        else:
            return [''] * len(row)

    st.dataframe(df.style.apply(color_rows, axis=1))

