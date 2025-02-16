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

# Función auxiliar para extraer el modelo base (la parte antes de la barra "/")
def base_model(model_str):
    if model_str:
        return model_str.split("/")[0].strip()
    return ""

# --------------------------------------------------------------------
# Parámetros obligatorios
target_alcance = st.sidebar.number_input("Alcance deseado (m):", value=30.0, step=0.5)
target_carga_punta = st.sidebar.number_input("Carga en Punta (kg):", value=1000, step=100)

# Definir los rangos permitidos:
# Para Pluma Instalada: entre target y target*1.15 (ej. para 30 m, entre 30 y 34.5 m)
alcance_min = float(target_alcance)
alcance_max = target_alcance * 1.15
# Para Carga en Punta: entre target y target*1.25
carga_punta_min = float(target_carga_punta)
carga_punta_max = target_carga_punta * 1.25

# --------------------------------------------------------------------
# Parámetros opcionales para Carga Intermedia Deseada
use_intermedia = st.sidebar.checkbox("Carga Intermedia Deseada")
if use_intermedia:
    target_distancia = st.sidebar.number_input("Distancia Deseada (m):", value=14.0, step=0.5)
    target_carga_intermedia = st.sidebar.number_input("Carga Intermedia Deseada (kg):", value=2420, step=100)
    # Para los parámetros intermedios se exige un rango del target al target*1.05 (±5% - solo se aceptan valores mayores o iguales al target)
    distancia_min = float(target_distancia)
    distancia_max = target_distancia * 1.05
    carga_intermedia_min = float(target_carga_intermedia)
    carga_intermedia_max = target_carga_intermedia * 1.05

# --------------------------------------------------------------------
# Opción para asignar Stock
use_stock = st.sidebar.checkbox("Asignar Stock")
stock_dict = {}
if use_stock:
    st.sidebar.subheader("Definir Stock por Modelo")
    modelos_unicos = sorted({ base_model(grua.get("Modelo de Grúa Torre", "")) 
                               for grua in gruas_list if grua.get("Modelo de Grúa Torre") })
    for modelo in modelos_unicos:
        stock = st.sidebar.number_input(f"Stock para {modelo}:", value=0, step=1, min_value=0)
        stock_dict[modelo] = stock

# --------------------------------------------------------------------
# Función para calcular el error relativo (asumiendo value >= target)
def relative_error(value, target):
    return (value - target) / target

# --------------------------------------------------------------------
# Filtrado y clasificación de candidatos
candidatos = []

if use_stock:
    # Modo CON stock asignado
    for grua in gruas_list:
        try:
            alcance_val = float(grua.get("Pluma Instalada", 0))
            carga_val = float(grua.get("Carga en Punta", 0))
        except:
            continue
        # Filtrar: deben estar entre target y el máximo permitido
        if not (alcance_min <= alcance_val <= alcance_max):
            continue
        if not (carga_punta_min <= carga_val <= carga_punta_max):
            continue

        if not use_intermedia:
            # Sin carga intermedia: exigir que Distancia Específica == Pluma Instalada y Carga específica == Carga en Punta
            try:
                dist_val = float(grua.get("Distancia Específica", 0))
                carga_int_val = float(grua.get("Carga específica", 0))
            except:
                continue
            if dist_val != alcance_val or carga_int_val != carga_val:
                continue
        else:
            # Con carga intermedia: exigir que Distancia Específica y Carga específica estén dentro del rango [target, target*1.05]
            try:
                dist_val = float(grua.get("Distancia Específica", 0))
                carga_int_val = float(grua.get("Carga específica", 0))
            except:
                continue
            if not (distancia_min <= dist_val <= distancia_max):
                continue
            if not (carga_intermedia_min <= carga_int_val <= carga_intermedia_max):
                continue

        # Asignar stock según modelo base
        modelo_base = base_model(grua.get("Modelo de Grúa Torre", ""))
        grua["Stock"] = stock_dict.get(modelo_base, 0)
        candidatos.append(grua)
    # Ordenar candidatos por stock descendente
    candidatos = sorted(candidatos, key=lambda x: x["Stock"], reverse=True)

else:
    # Modo SIN stock: aplicar criterios de error para alcance y carga en punta
    for grua in gruas_list:
        try:
            alcance_val = float(grua.get("Pluma Instalada", 0))
            carga_val = float(grua.get("Carga en Punta", 0))
        except:
            continue
        # Filtrar: solo se aceptan grúas cuyo alcance esté entre target y target*1.15
        # y cuya carga esté entre target y target*1.25
        if not (alcance_min <= alcance_val <= alcance_max):
            continue
        if not (carga_punta_min <= carga_val <= carga_punta_max):
            continue

        # Calcular errores relativos
        err_alcance = relative_error(alcance_val, target_alcance)
        err_carga = relative_error(carga_val, target_carga_punta)
        # Si alguno supera el 15% (0.15) se descarta
        if err_alcance > 0.15 or err_carga > 0.15:
            continue
        total_error = err_alcance + err_carga

        if use_intermedia:
            try:
                dist_val = float(grua.get("Distancia Específica", 0))
                carga_int_val = float(grua.get("Carga específica", 0))
            except:
                continue
            if not (distancia_min <= dist_val <= distancia_max):
                continue
            if not (carga_intermedia_min <= carga_int_val <= carga_intermedia_max):
                continue
            err_dist = relative_error(dist_val, target_distancia)
            err_carga_int = relative_error(carga_int_val, target_carga_intermedia)
            if err_dist > 0.15 or err_carga_int > 0.15:
                continue
            total_error += (err_dist + err_carga_int)
            grua["_errors"] = {"Alcance": err_alcance, "Carga en Punta": err_carga,
                               "Distancia": err_dist, "Carga Intermedia": err_carga_int}
        else:
            grua["_errors"] = {"Alcance": err_alcance, "Carga en Punta": err_carga}
        grua["Total Error"] = total_error
        # Definir Tipo según los errores (solo en modo SIN stock)
        if err_alcance <= 0.05 and err_carga <= 0.05:
            grua["Tipo"] = "Match"
        else:
            grua["Tipo"] = "Casi Match"
        candidatos.append(grua)
    # Ordenar candidatos por Total Error (menor primero)
    candidatos = sorted(candidatos, key=lambda x: x["Total Error"])

# --------------------------------------------------------------------
# Eliminar duplicados: conservar para cada modelo base el candidato con mejor criterio
candidatos_unicos = {}
for cand in candidatos:
    modelo = base_model(cand.get("Modelo de Grúa Torre", ""))
    if modelo not in candidatos_unicos:
        candidatos_unicos[modelo] = cand
    else:
        if use_stock:
            if cand["Stock"] > candidatos_unicos[modelo]["Stock"]:
                candidatos_unicos[modelo] = cand
        else:
            if cand["Total Error"] < candidatos_unicos[modelo]["Total Error"]:
                candidatos_unicos[modelo] = cand

candidatos_filtrados = list(candidatos_unicos.values())
resultados = candidatos_filtrados[:5]

# --------------------------------------------------------------------
# Preparar la tabla de resultados
if not resultados:
    st.write("No se encontraron grúas que se ajusten a los parámetros solicitados.")
else:
    # Definir columnas a mostrar:
    # Siempre se muestran: Modelo, Pluma Instalada y Carga en Punta.
    columnas = ["Modelo de Grúa Torre", "Pluma Instalada (m)", "Carga en Punta (kg)"]
    if use_intermedia:
        columnas += ["Distancia Específica (m)", "Carga específica (kg)"]
    if use_stock:
        columnas += ["Stock"]
    
    # En modo SIN stock agregamos columnas auxiliares para estilo (Total Error y Tipo) que luego se ocultan
    cols_aux = []
    if not use_stock:
        cols_aux = ["Total Error", "Tipo"]

    # Función para formatear cada fila:
    def formatea_fila(grua):
        fila = {}
        fila["Modelo de Grúa Torre"] = grua.get("Modelo de Grúa Torre", "")
        fila["Pluma Instalada (m)"] = f"{float(grua.get('Pluma Instalada', 0)):.2f}"
        fila["Carga en Punta (kg)"] = f"{int(round(float(grua.get('Carga en Punta', 0)))):,d}"
        if use_intermedia:
            fila["Distancia Específica (m)"] = f"{float(grua.get('Distancia Específica', 0)):.2f}"
            fila["Carga específica (kg)"] = f"{int(round(float(grua.get('Carga específica', 0)))):,d}"
        if use_stock:
            stock_val = grua.get("Stock", 0)
            if stock_val > 0:
                fila["Stock"] = stock_val
            else:
                fila["Stock"] = "No hay stock"
        if not use_stock:
            fila["Total Error"] = f"{grua.get('Total Error', 0):.3f}"
            fila["Tipo"] = grua.get("Tipo", "")
        return fila

    df = pd.DataFrame([formatea_fila(g) for g in resultados])
    columnas_final = columnas + cols_aux
    df = df[columnas_final]
    
    # --------------------------------------------------------------------
    # Función para colorear filas según criterios:
    # - En modo CON stock: si "Stock" es "No hay stock", la fila se pinta de rojo.
    # - En modo SIN stock: se pinta de verde si "Tipo" es "Match", de amarillo si "Tipo" es "Casi Match".
    def color_rows(row):
        if use_stock:
            if row["Stock"] == "No hay stock":
                return ['background-color: red'] * len(row)
            else:
                return [''] * len(row)
        else:
            if row["Tipo"] == "Match":
                return ['background-color: lightgreen'] * len(row)
            elif row["Tipo"] == "Casi Match":
                return ['background-color: lightyellow'] * len(row)
            else:
                return [''] * len(row)
    
    styled_df = df.style.apply(color_rows, axis=1)
    if not use_stock:
        styled_df = styled_df.hide_columns(cols_aux)
    
    st.header("Opciones encontradas")
    st.dataframe(styled_df)

