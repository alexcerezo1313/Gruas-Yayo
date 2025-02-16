import streamlit as st
import json
import pandas as pd

# --------------------------
# Mostrar el logo en la parte superior del Sidebar
st.sidebar.image("logo.png", width=200)

st.title("Selector de Grúas Torre")
st.sidebar.header("Filtros de búsqueda")

# --------------------------
# Cargar datos desde JSON
@st.cache_data
def load_data(json_file):
    with open(json_file, "r", encoding="utf-8") as f:
        return json.load(f)

data = load_data("gruas_data.json")
gruas_list = data.get("Hoja1", [])

# --------------------------
# Parámetros obligatorios
target_alcance = st.sidebar.number_input("Alcance deseado (m):", value=30.0, step=0.5)
target_carga_punta = st.sidebar.number_input("Carga en Punta (kg):", value=1000, step=100)

# --------------------------
# Parámetros opcionales para carga intermedia
use_intermedia = st.sidebar.checkbox("Carga Intermedia Deseada")
if use_intermedia:
    target_distancia = st.sidebar.number_input("Distancia Deseada (m):", value=14.0, step=0.5)
    target_carga_intermedia = st.sidebar.number_input("Carga Intermedia Deseada (kg):", value=2420, step=100)
    # Para estos parámetros se aceptan solo valores dentro de ±5%
    distancia_min_allowed = target_distancia * 0.95
    distancia_max_allowed = target_distancia * 1.05
    carga_intermedia_min_allowed = target_carga_intermedia * 0.95
    carga_intermedia_max_allowed = target_carga_intermedia * 1.05

# --------------------------
# Función para calcular el error relativo
def relative_error(value, target):
    return abs(value - target) / target

# --------------------------
# Filtrado y cálculo de error según el modo de búsqueda

candidatos = []

for grua in gruas_list:
    # Aseguramos que existan los parámetros obligatorios
    if grua.get("Pluma Instalada") is None or grua.get("Carga en Punta") is None:
        continue

    # Modo CON carga intermedia: se prioriza que la carga específica (a una distancia) sea lo más similar posible
    if use_intermedia:
        # Requerimos que alcance y carga en punta sean al menos los deseados (o mayores)
        if grua["Pluma Instalada"] < target_alcance or grua["Carga en Punta"] < target_carga_punta:
            continue
        # Requerimos que los parámetros opcionales estén dentro de ±5%
        if grua.get("Distancia Específica") is None or grua.get("Carga específica") is None:
            continue
        if not (distancia_min_allowed <= grua["Distancia Específica"] <= distancia_max_allowed):
            continue
        if not (carga_intermedia_min_allowed <= grua["Carga específica"] <= carga_intermedia_max_allowed):
            continue

        # Calcular errores:
        # Para alcance y carga en punta, se calcula el exceso relativo (cuánto más ofrecen respecto al target)
        error_alcance = (grua["Pluma Instalada"] - target_alcance) / target_alcance
        error_carga_punta = (grua["Carga en Punta"] - target_carga_punta) / target_carga_punta
        # Para los parámetros opcionales se calcula el error relativo (idealmente cercano a 0)
        error_distancia = relative_error(grua["Distancia Específica"], target_distancia)
        error_carga_intermedia = relative_error(grua["Carga específica"], target_carga_intermedia)
        # Para ordenar, damos prioridad a la suma de los errores de los parámetros opcionales,
        # y luego añadimos el exceso de los obligatorios.
        total_optional_error = error_distancia + error_carga_intermedia
        total_primary_error = error_alcance + error_carga_punta
        total_error = total_optional_error + total_primary_error

        # Definir el tipo: si todos los errores son ≤5% (0.05), es "Match"; de lo contrario, "Casi Match"
        tipo = "Match" if (error_distancia <= 0.05 and error_carga_intermedia <= 0.05 and error_alcance <= 0.05 and error_carga_punta <= 0.05) else "Casi Match"

        candidato = grua.copy()
        candidato["Error Alcance"] = error_alcance
        candidato["Error Carga Punta"] = error_carga_punta
        candidato["Error Distancia"] = error_distancia
        candidato["Error Carga Intermedia"] = error_carga_intermedia
        candidato["Total Error"] = total_error
        candidato["Tipo"] = tipo
        candidatos.append(candidato)

    # Modo SIN carga intermedia: se usan tolerancias amplias (±15% para alcance y ±25% para carga en punta)
    else:
        # Rechazamos si los parámetros no están dentro del rango permitido o si son menores al requerido
        if not (target_alcance * 0.85 <= grua["Pluma Instalada"] <= target_alcance * 1.15):
            continue
        if grua["Pluma Instalada"] < target_alcance:
            continue
        if not (target_carga_punta * 0.75 <= grua["Carga en Punta"] <= target_carga_punta * 1.25):
            continue
        if grua["Carga en Punta"] < target_carga_punta:
            continue

        error_alcance = (grua["Pluma Instalada"] - target_alcance) / target_alcance
        error_carga_punta = (grua["Carga en Punta"] - target_carga_punta) / target_carga_punta
        total_error = error_alcance + error_carga_punta
        tipo = "Match" if (error_alcance <= 0.05 and error_carga_punta <= 0.05) else "Casi Match"

        candidato = grua.copy()
        candidato["Error Alcance"] = error_alcance
        candidato["Error Carga Punta"] = error_carga_punta
        candidato["Total Error"] = total_error
        candidato["Tipo"] = tipo
        candidatos.append(candidato)

# --------------------------
# Eliminar duplicados: de cada modelo ("Modelo de Grúa Torre") se conserva el candidato con menor error total
candidatos_unicos = {}
for cand in candidatos:
    modelo = cand.get("Modelo de Grúa Torre")
    if modelo is None:
        continue
    if modelo not in candidatos_unicos or cand["Total Error"] < candidatos_unicos[modelo]["Total Error"]:
        candidatos_unicos[modelo] = cand

candidatos_filtrados = list(candidatos_unicos.values())

# Ordenar candidatos según el total error (en modo intermedia se da prioridad a los errores opcionales)
candidatos_ordenados = sorted(candidatos_filtrados, key=lambda x: x["Total Error"])

# Seleccionar los 5 primeros resultados
resultados = candidatos_ordenados[:5]

# --------------------------
# Mostrar resultados en formato de tabla
if not resultados:
    st.write("No se encontraron grúas que se ajusten a los parámetros solicitados.")
else:
    # Se preparan las columnas a mostrar.
    # Se incluyen unidades en el título y se formatean:
    # - Los valores en m con 2 decimales.
    # - Los valores en kg sin decimales y con separador de miles.
    columnas = ["Modelo de Grúa Torre", "Pluma Instalada (m)", "Carga en Punta (kg)"]
    if use_intermedia:
        columnas += ["Distancia Específica (m)", "Carga específica (kg)"]
    columnas += ["Tipo", "Total Error"]

    # Convertir a DataFrame y renombrar columnas según lo deseado:
    df = pd.DataFrame(resultados)
    # Crear un nuevo DataFrame con las columnas de interés y formatear
    def format_row(row):
        return {
            "Modelo de Grúa Torre": row.get("Modelo de Grúa Torre", ""),
            "Pluma Instalada (m)": f"{row.get('Pluma Instalada', 0):.2f}",
            "Carga en Punta (kg)": f"{int(round(row.get('Carga en Punta', 0))):,d}"
        }
    df_formatted = pd.DataFrame([format_row(r) for _, r in df.iterrows()])

    if use_intermedia:
        def format_optional(row):
            return {
                "Distancia Específica (m)": f"{row.get('Distancia Específica', 0):.2f}",
                "Carga específica (kg)": f"{int(round(row.get('Carga específica', 0))):,d}"
            }
        df_opt = pd.DataFrame([format_optional(r) for _, r in df.iterrows()])
        df_formatted = pd.concat([df_formatted, df_opt], axis=1)

    df_formatted["Tipo"] = df["Tipo"]
    df_formatted["Total Error"] = df["Total Error"].apply(lambda x: f"{x:.3f}")

    st.header("Opciones encontradas")
    
    # Función para colorear las filas según el tipo
    def color_rows(row):
        if row["Tipo"] == "Match":
            return ['background-color: lightgreen'] * len(row)
        elif row["Tipo"] == "Casi Match":
            return ['background-color: lightyellow'] * len(row)
        else:
            return [''] * len(row)
    
    st.dataframe(df_formatted.style.apply(color_rows, axis=1))
