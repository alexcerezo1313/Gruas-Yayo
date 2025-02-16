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

# --------------------------------------------------------------------
# Parámetros opcionales para Carga Intermedia Deseada
use_intermedia = st.sidebar.checkbox("Carga Intermedia Deseada")
if use_intermedia:
    target_distancia = st.sidebar.number_input("Distancia Deseada (m):", value=14.0, step=0.5)
    target_carga_intermedia = st.sidebar.number_input("Carga Intermedia Deseada (kg):", value=2420, step=100)
    # Se exige que estén dentro del ±5%
    distancia_min_allowed = target_distancia * 0.95
    distancia_max_allowed = target_distancia * 1.05
    carga_intermedia_min_allowed = target_carga_intermedia * 0.95
    carga_intermedia_max_allowed = target_carga_intermedia * 1.05

# --------------------------------------------------------------------
# Opción para asignar Stock
use_stock = st.sidebar.checkbox("Asignar Stock")
stock_dict = {}
if use_stock:
    st.sidebar.subheader("Definir Stock por Modelo")
    # Extraer modelos base únicos de la base de datos
    modelos_unicos = sorted({ base_model(grua.get("Modelo de Grúa Torre", "")) 
                               for grua in gruas_list if grua.get("Modelo de Grúa Torre") })
    for modelo in modelos_unicos:
        stock = st.sidebar.number_input(f"Stock para {modelo}:", value=0, step=1, min_value=0)
        stock_dict[modelo] = stock

# --------------------------------------------------------------------
# Función para calcular el error relativo (asumiendo que el valor >= target)
def relative_error(value, target):
    return (value - target) / target

# --------------------------------------------------------------------
# Filtrado y clasificación de candidatos
candidatos = []

if use_stock:
    # Modo CON stock asignado
    for grua in gruas_list:
        # Verificar parámetros obligatorios
        if grua.get("Pluma Instalada") is None or grua.get("Carga en Punta") is None:
            continue
        if grua["Pluma Instalada"] < target_alcance or grua["Carga en Punta"] < target_carga_punta:
            continue
        if not use_intermedia:
            # Sin carga intermedia: exigir que Distancia Específica == Pluma Instalada y Carga específica == Carga en Punta
            if grua.get("Distancia Específica") != grua.get("Pluma Instalada"):
                continue
            if grua.get("Carga específica") != grua.get("Carga en Punta"):
                continue
        else:
            # Con carga intermedia: exigir que existan y estén dentro de ±5%
            if grua.get("Distancia Específica") is None or grua.get("Carga específica") is None:
                continue
            if not (distancia_min_allowed <= grua["Distancia Específica"] <= distancia_max_allowed):
                continue
            if not (carga_intermedia_min_allowed <= grua["Carga específica"] <= carga_intermedia_max_allowed):
                continue
        # Asignar stock según modelo base
        modelo_base = base_model(grua.get("Modelo de Grúa Torre", ""))
        grua["Stock"] = stock_dict.get(modelo_base, 0)
        # Solo se incluyen si el stock es mayor a 0
        # (Si se quiere mostrar también sin stock, se incluirá pero se marcará en rojo)
        candidatos.append(grua)
    # Ordenar candidatos por stock descendente
    candidatos = sorted(candidatos, key=lambda x: x["Stock"], reverse=True)

else:
    # Modo SIN stock: usar criterios de error
    for grua in gruas_list:
        # Verificar existencia de parámetros obligatorios
        if grua.get("Pluma Instalada") is None or grua.get("Carga en Punta") is None:
            continue
        if grua["Pluma Instalada"] < target_alcance or grua["Carga en Punta"] < target_carga_punta:
            continue
        # Calcular error relativo para alcance y carga en punta
        err_alcance = relative_error(grua["Pluma Instalada"], target_alcance)
        err_carga = relative_error(grua["Carga en Punta"], target_carga_punta)
        # Rechazar si alguno supera 15%
        if err_alcance > 0.15 or err_carga > 0.15:
            continue
        total_error = err_alcance + err_carga
        # Si se usa carga intermedia, evaluar esos parámetros
        if use_intermedia:
            if grua.get("Distancia Específica") is None or grua.get("Carga específica") is None:
                continue
            if grua["Distancia Específica"] < target_distancia or grua["Carga específica"] < target_carga_intermedia:
                continue
            err_dist = relative_error(grua["Distancia Específica"], target_distancia)
            err_carga_int = relative_error(grua["Carga específica"], target_carga_intermedia)
            if err_dist > 0.15 or err_carga_int > 0.15:
                continue
            total_error += (err_dist + err_carga_int)
            # Almacenar errores individuales
            grua["_errors"] = {"Alcance": err_alcance, "Carga en Punta": err_carga,
                               "Distancia": err_dist, "Carga Intermedia": err_carga_int}
        else:
            grua["_errors"] = {"Alcance": err_alcance, "Carga en Punta": err_carga}
        grua["Total Error"] = total_error
        # Determinar Tipo: si TODOS los errores son ≤ 0.05 se marca "Match" (verde); si alguno supera 0.05 (pero todos ≤ 0.15) se marca "Casi Match" (amarillo)
        if use_intermedia:
            if (grua["_errors"]["Alcance"] <= 0.05 and grua["_errors"]["Carga en Punta"] <= 0.05 and
                grua["_errors"]["Distancia"] <= 0.05 and grua["_errors"]["Carga Intermedia"] <= 0.05):
                grua["Tipo"] = "Match"
            else:
                grua["Tipo"] = "Casi Match"
        else:
            if grua["_errors"]["Alcance"] <= 0.05 and grua["_errors"]["Carga en Punta"] <= 0.05:
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
        # En modo con stock, conservar el que tenga mayor stock;
        # en modo sin stock, conservar el que tenga menor Total Error.
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
    # Siempre: Modelo, Pluma Instalada y Carga en Punta.
    columnas = ["Modelo de Grúa Torre", "Pluma Instalada (m)", "Carga en Punta (kg)"]
    if use_intermedia:
        columnas += ["Distancia Específica (m)", "Carga específica (kg)"]
    if use_stock:
        columnas += ["Stock"]

    # Función para formatear cada fila
    def formatea_fila(grua):
        fila = {}
        fila["Modelo de Grúa Torre"] = grua.get("Modelo de Grúa Torre", "")
        fila["Pluma Instalada (m)"] = f"{grua.get('Pluma Instalada', 0):.2f}"
        fila["Carga en Punta (kg)"] = f"{int(round(grua.get('Carga en Punta', 0))):,d}"
        if use_intermedia:
            fila["Distancia Específica (m)"] = f"{grua.get('Distancia Específica', 0):.2f}"
            fila["Carga específica (kg)"] = f"{int(round(grua.get('Carga específica', 0))):,d}"
        if use_stock:
            stock_val = grua.get("Stock", 0)
            if stock_val > 0:
                fila["Stock"] = stock_val
            else:
                fila["Stock"] = "No hay stock"
        # En modo sin stock se NO mostramos Total Error ni Tipo (estos se usan solo para estilizar)
        if not use_stock:
            fila["Total Error"] = f"{grua.get('Total Error', 0):.3f}"
            fila["Tipo"] = grua.get("Tipo", "")
        return fila

    # En modo sin stock incluiremos columnas auxiliares "Total Error" y "Tipo" para el estilo y luego las ocultamos.
    cols_aux = []
    if not use_stock:
        cols_aux = ["Total Error", "Tipo"]

    df = pd.DataFrame([formatea_fila(g) for g in resultados])
    # Reordenar las columnas para visualización
    columnas_final = columnas + cols_aux
    df = df[columnas_final]

    # --------------------------------------------------------------------
    # Función para aplicar estilos a las filas
    def color_rows(row):
        if use_stock:
            # Si se usa stock: si la columna "Stock" dice "No hay stock", fila roja.
            if row["Stock"] == "No hay stock":
                return ['background-color: red'] * len(row)
            else:
                return [''] * len(row)
        else:
            # Sin stock: usar la columna "Tipo" para colorear
            if row["Tipo"] == "Match":
                return ['background-color: lightgreen'] * len(row)
            elif row["Tipo"] == "Casi Match":
                return ['background-color: lightyellow'] * len(row)
            else:
                return [''] * len(row)

    # Aplicar estilo y, en modo sin stock, ocultar las columnas auxiliares
    styled_df = df.style.apply(color_rows, axis=1)
    if not use_stock:
        styled_df = styled_df.hide_columns(cols_aux)

    st.header("Opciones encontradas")
    st.dataframe(styled_df)
