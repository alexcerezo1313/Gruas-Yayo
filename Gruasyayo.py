

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

# --------------------------
# Parámetros para Alcance deseado (Pluma Instalada)
target_alcance = st.sidebar.number_input("Alcance deseado (m):", value=30.0, step=0.5)
# Rango permitido: ±15%
alcance_min_allowed = target_alcance * 0.85
alcance_max_allowed = target_alcance * 1.15

# --------------------------
# Parámetros para Carga en Punta
target_carga_punta = st.sidebar.number_input("Carga en Punta (kg):", value=1000.0, step=100.0)
# Rango permitido: ±25%
carga_punta_min_allowed = target_carga_punta * 0.75
carga_punta_max_allowed = target_carga_punta * 1.25

# --------------------------
# Filtro opcional: Carga Intermedia (renombrada)
use_intermedia = st.sidebar.checkbox("Filtrar por Carga Intermedia")
if use_intermedia:
    # Parámetro para Distancia (se compara con "Distancia Específica")
    target_distancia = st.sidebar.number_input("Distancia (m):", value=14.0, step=0.5)
    distancia_min_allowed = target_distancia * 0.95
    distancia_max_allowed = target_distancia * 1.05

    # Parámetro para Carga Intermedia (se compara con "Carga específica")
    target_carga_intermedia = st.sidebar.number_input("Carga Intermedia (kg):", value=2420.0, step=100.0)
    carga_intermedia_min_allowed = target_carga_intermedia * 0.95
    carga_intermedia_max_allowed = target_carga_intermedia * 1.05

# --------------------------
# Función para calcular el error relativo con penalty
# Si el valor es inferior al target, se suma un penalty (en este ejemplo 0.05)
def relative_error_with_penalty(value, target):
    error = abs(value - target) / target
    if value < target:
        # Penalizamos si el valor es inferior (preferimos un poco más)
        error += 0.05
    return error

# --------------------------
# Evaluamos cada grúa
candidatos = []

for grua in gruas_list:
    valid = True
    errors = {}  # Guardará el error relativo de cada parámetro
    
    # 1. Alcance (Pluma Instalada)
    val_alcance = grua.get("Pluma Instalada", None)
    if val_alcance is None or not (alcance_min_allowed <= val_alcance <= alcance_max_allowed):
        valid = False
    else:
        err_alcance = relative_error_with_penalty(val_alcance, target_alcance)
        errors["Alcance"] = err_alcance

    # 2. Carga en Punta
    val_carga_punta = grua.get("Carga en Punta", None)
    if val_carga_punta is None or not (carga_punta_min_allowed <= val_carga_punta <= carga_punta_max_allowed):
        valid = False
    else:
        err_carga_punta = relative_error_with_penalty(val_carga_punta, target_carga_punta)
        errors["Carga en Punta"] = err_carga_punta

    # 3. Si se filtra por Carga Intermedia, evaluamos los siguientes parámetros:
    if use_intermedia:
        # Distancia (Distancia Específica)
        val_distancia = grua.get("Distancia Específica", None)
        if val_distancia is None or not (distancia_min_allowed <= val_distancia <= distancia_max_allowed):
            valid = False
        else:
            err_distancia = relative_error_with_penalty(val_distancia, target_distancia)
            errors["Distancia"] = err_distancia

        # Carga Intermedia (Carga específica)
        val_carga_intermedia = grua.get("Carga específica", None)
        if val_carga_intermedia is None or not (carga_intermedia_min_allowed <= val_carga_intermedia <= carga_intermedia_max_allowed):
            valid = False
        else:
            err_carga_intermedia = relative_error_with_penalty(val_carga_intermedia, target_carga_intermedia)
            errors["Carga Intermedia"] = err_carga_intermedia

    if valid:
        total_error = sum(errors.values())
        # Se considera "Match" si TODOS los errores (con penalty) son ≤ 5%
        tipo = "Match" if all(err <= 0.05 for err in errors.values()) else "Casi Match"
        candidato = grua.copy()
        candidato["Total Error Relativo"] = total_error
        candidato["Tipo"] = tipo
        candidato.update({f"Err {k}": v for k, v in errors.items()})
        candidatos.append(candidato)

# --------------------------
# Eliminar duplicados: para cada modelo, conservar la grúa con menor error total
unique_candidates = {}
for cand in candidatos:
    modelo = cand.get("Modelo de Grúa Torre", "N/A")
    if modelo not in unique_candidates:
        unique_candidates[modelo] = cand
    else:
        if cand["Total Error Relativo"] < unique_candidates[modelo]["Total Error Relativo"]:
            unique_candidates[modelo] = cand

# Convertir los candidatos únicos a una lista y ordenar por Total Error Relativo
candidatos_unicos = list(unique_candidates.values())
candidatos_sorted = sorted(candidatos_unicos, key=lambda x: x["Total Error Relativo"])

# Seleccionar los 5 primeros resultados
resultados = candidatos_sorted[:5]

# --------------------------
# Mostrar resultados en formato de tabla
if not resultados:
    st.write("No se encontraron grúas que se asemejen a los parámetros solicitados.")
else:
    # Definir las columnas a mostrar y agregar etiquetas de unidades en el título
    columnas = ["Modelo de Grúa Torre", "Pluma Instalada (m)", "Carga en Punta (kg)"]
    if use_intermedia:
        columnas += ["Distancia Específica (m)", "Carga específica (kg)"]
    columnas += ["Tipo", "Total Error Relativo"]
    
    # Crear el DataFrame y renombrar las columnas (asumiendo que las claves originales son las de la BD)
    df = pd.DataFrame(resultados)
    df.rename(columns={
        "Pluma Instalada": "Pluma Instalada (m)",
        "Carga en Punta": "Carga en Punta (kg)",
        "Distancia Específica": "Distancia Específica (m)",
        "Carga específica": "Carga específica (kg)"
    }, inplace=True)
    df = df[columnas]
    
    # Formatear los valores:
    # - Para columnas de metros: 2 decimales.
    # - Para columnas de kg: 2 decimales y separador de miles.
    def format_val(val, unit):
        if unit == "m":
            return f"{float(val):.2f}"
        elif unit == "kg":
            # Formatea con separador de miles y 2 decimales.
            return f"{float(val):,.2f}"
        return val

    # Usamos st.dataframe con estilo para aplicar formato a cada columna
    fmt_dict = {}
    # Identificamos columnas según unidad
    for col in df.columns:
        if "(m)" in col:
            fmt_dict[col] = lambda x: f"{x:.2f}"
        elif "(kg)" in col:
            fmt_dict[col] = lambda x: f"{x:,.2f}"
    
    st.header("Opciones encontradas")
    
    # Función para colorear las filas según el tipo
    def color_rows(row):
        if row["Tipo"] == "Match":
            return ['background-color: lightgreen'] * len(row)
        elif row["Tipo"] == "Casi Match":
            return ['background-color: lightyellow'] * len(row)
        else:
            return [''] * len(row)
    
    st.dataframe(df.style.format(fmt_dict).apply(color_rows, axis=1))
