import streamlit as st
import json
import pandas as pd

# --------------------------------------------------------------------
# Mostrar el logo en la parte superior del Sidebar
st.sidebar.image("logo.png", width=200)

st.title("Selector de Grúas Torre")
st.sidebar.header("Filtros de búsqueda")

# --------------------------------------------------------------------
# Cargar datos desde JSON
@st.cache_data
def load_data(json_file):
    with open(json_file, "r", encoding="utf-8") as f:
        return json.load(f)

data = load_data("gruas_data.json")
gruas_list = data.get("Hoja1", [])

# Función auxiliar para extraer el modelo base (parte antes de la barra '/')
def base_model(model_str):
    if model_str:
        return model_str.split("/")[0].strip()
    return ""

# --------------------------------------------------------------------
# Parámetros obligatorios (siempre)
target_alcance = st.sidebar.number_input("Alcance deseado (m):", value=30.0, step=0.5)
target_carga_punta = st.sidebar.number_input("Carga en Punta (kg):", value=1000, step=100)

# --------------------------------------------------------------------
# Parámetros opcionales para Carga Intermedia Deseada
use_intermedia = st.sidebar.checkbox("Carga Intermedia Deseada")
if use_intermedia:
    target_distancia = st.sidebar.number_input("Distancia Deseada (m):", value=14.0, step=0.5)
    target_carga_intermedia = st.sidebar.number_input("Carga Intermedia Deseada (kg):", value=2420, step=100)
    # Para estos parámetros se exige ±5%
    distancia_min_allowed = target_distancia * 0.95
    distancia_max_allowed = target_distancia * 1.05
    carga_intermedia_min_allowed = target_carga_intermedia * 0.95
    carga_intermedia_max_allowed = target_carga_intermedia * 1.05

# --------------------------------------------------------------------
# Opción para Stock
use_stock = st.sidebar.checkbox("Asignar Stock")
stock_dict = {}
if use_stock:
    st.sidebar.subheader("Definir Stock por Modelo")
    # Extraer modelos base únicos de la base de datos
    modelos_unicos = sorted({ base_model(grua.get("Modelo de Grúa Torre", "")) for grua in gruas_list if grua.get("Modelo de Grúa Torre") })
    for modelo in modelos_unicos:
        stock = st.sidebar.number_input(f"Stock para {modelo}:", value=0, step=1, min_value=0)
        stock_dict[modelo] = stock

# --------------------------------------------------------------------
# Función para calcular el error relativo (en modo con carga intermedia)
def relative_error(value, target):
    return abs(value - target) / target

# --------------------------------------------------------------------
# Filtrado de candidatos
candidatos = []

for grua in gruas_list:
    # Verificar que existan los parámetros obligatorios
    if grua.get("Pluma Instalada") is None or grua.get("Carga en Punta") is None:
        continue

    # Si se usa stock, descartar candidatos cuyo modelo (base) tenga stock 0 o no asignado
    if use_stock:
        modelo_base = base_model(grua.get("Modelo de Grúa Torre", ""))
        if stock_dict.get(modelo_base, 0) <= 0:
            continue

    # Modo CON carga intermedia
    if use_intermedia:
        # Requerir que alcance y carga en punta sean mayores o iguales a lo solicitado
        if grua["Pluma Instalada"] < target_alcance or grua["Carga en Punta"] < target_carga_punta:
            continue
        # Requerir que existan los parámetros intermedios y estén dentro de ±5%
        if grua.get("Distancia Específica") is None or grua.get("Carga específica") is None:
            continue
        if not (distancia_min_allowed <= grua["Distancia Específica"] <= distancia_max_allowed):
            continue
        if not (carga_intermedia_min_allowed <= grua["Carga específica"] <= carga_intermedia_max_allowed):
            continue

        # Calcular errores relativos:
        error_alcance = (grua["Pluma Instalada"] - target_alcance) / target_alcance  # cuanto _extra_ ofrece
        error_carga_punta = (grua["Carga en Punta"] - target_carga_punta) / target_carga_punta
        error_distancia = relative_error(grua["Distancia Específica"], target_distancia)
        error_carga_intermedia = relative_error(grua["Carga específica"], target_carga_intermedia)
        total_error = error_alcance + error_carga_punta + error_distancia + error_carga_intermedia

        candidato = grua.copy()
        candidato["Total Error"] = total_error  # para ordenar
        candidato["Error Distancia"] = error_distancia
        candidato["Error Carga Intermedia"] = error_carga_intermedia
        # En este modo se mantiene la información de intermedios para mostrar en tabla
        candidatos.append(candidato)

    # Modo SIN carga intermedia:
    else:
        # Solo usar grúas donde Distancia Específica == Pluma Instalada y Carga específica == Carga en Punta
        if grua.get("Distancia Específica") != grua.get("Pluma Instalada"):
            continue
        if grua.get("Carga específica") != grua.get("Carga en Punta"):
            continue
        # Además, se requiere que la grúa tenga al menos los valores requeridos
        if grua["Pluma Instalada"] < target_alcance or grua["Carga en Punta"] < target_carga_punta:
            continue
        # En modo sin intermedia no se calcula error; se puede asignar un valor base (por ejemplo, 0)
        candidato = grua.copy()
        candidatos.append(candidato)

# --------------------------------------------------------------------
# Si se usa stock, ordenar primero por stock (descendente) y luego por total error (si se calculó)
if use_stock:
    for cand in candidatos:
        modelo_base = base_model(cand.get("Modelo de Grúa Torre", ""))
        cand["Stock"] = stock_dict.get(modelo_base, 0)
    # Ordenar: mayor stock primero; si modo intermedia, usar total error como segundo criterio
    if use_intermedia:
        candidatos = sorted(candidatos, key=lambda x: (-x["Stock"], x["Total Error"]))
    else:
        candidatos = sorted(candidatos, key=lambda x: -x["Stock"])
else:
    # Si no se usa stock, si modo intermedia se ordena por total error; de lo contrario, mantener orden original
    if use_intermedia:
        candidatos = sorted(candidatos, key=lambda x: x["Total Error"])

# Eliminar duplicados: para cada modelo base se conserva el candidato con mejor criterio (menor error o mayor stock)
candidatos_unicos = {}
for cand in candidatos:
    modelo = base_model(cand.get("Modelo de Grúa Torre", ""))
    if modelo not in candidatos_unicos:
        candidatos_unicos[modelo] = cand
    else:
        # En modo con intermedia, ya están ordenados por stock y error; en modo sin intermedia, por stock o se puede elegir el primero.
        pass

candidatos_filtrados = list(candidatos_unicos.values())

# Seleccionar los 5 primeros resultados
resultados = candidatos_filtrados[:5]

# --------------------------------------------------------------------
# Preparar la tabla de resultados
if not resultados:
    st.write("No se encontraron grúas que se ajusten a los parámetros solicitados.")
else:
    # Definir las columnas a mostrar:
    # Siempre se muestran: Modelo, Pluma Instalada y Carga en Punta.
    # Solo se muestran las columnas de intermedios si se usa ese modo.
    columnas = ["Modelo de Grúa Torre", "Pluma Instalada (m)", "Carga en Punta (kg)"]
    if use_intermedia:
        columnas += ["Distancia Específica (m)", "Carga específica (kg)"]

    # Crear DataFrame con los resultados y formatear los valores:
    def formatea_fila(grua):
        fila = {}
        fila["Modelo de Grúa Torre"] = grua.get("Modelo de Grúa Torre", "")
        fila["Pluma Instalada (m)"] = f"{grua.get('Pluma Instalada', 0):.2f}"
        fila["Carga en Punta (kg)"] = f"{int(round(grua.get('Carga en Punta', 0))):,d}"
        if use_intermedia:
            fila["Distancia Específica (m)"] = f"{grua.get('Distancia Específica', 0):.2f}"
            fila["Carga específica (kg)"] = f"{int(round(grua.get('Carga específica', 0))):,d}"
        return fila

    df = pd.DataFrame([formatea_fila(g) for g in resultados], columns=columnas)
    
    st.header("Opciones encontradas")
    st.dataframe(df)

