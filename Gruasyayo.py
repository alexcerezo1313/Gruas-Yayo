

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
    # Se exige que estén dentro del ±5%
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
    # Extraer modelos base únicos
    modelos_unicos = sorted({ base_model(grua.get("Modelo de Grúa Torre", "")) for grua in gruas_list if grua.get("Modelo de Grúa Torre") })
    for modelo in modelos_unicos:
        stock = st.sidebar.number_input(f"Stock para {modelo}:", value=0, step=1, min_value=0)
        stock_dict[modelo] = stock

# --------------------------------------------------------------------
# Función para calcular el error relativo
def relative_error(value, target):
    return (value - target) / target  # asumiendo value >= target

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
        # Si no se usa carga intermedia, exigir que:
        # Distancia Específica == Pluma Instalada y Carga específica == Carga en Punta
        if not use_intermedia:
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
        candidatos.append(grua)
    # Ordenar candidatos por stock descendente
    candidatos = sorted(candidatos, key=lambda x: x["Stock"], reverse=True)
else:
    # Modo SIN stock: usar criterios de desviación para alcance y carga en punta (y opcionalmente para intermedios)
    for grua in gruas_list:
        # Verificar parámetros obligatorios
        if grua.get("Pluma Instalada") is None or grua.get("Carga en Punta") is None:
            continue
        if grua["Pluma Instalada"] < target_alcance or grua["Carga en Punta"] < target_carga_punta:
            continue
        # Calcular errores relativos (se asume que el valor es mayor o igual al target)
        err_alcance = relative_error(grua["Pluma Instalada"], target_alcance)
        err_carga = relative_error(grua["Carga en Punta"], target_carga_punta)
        # Descartar si alguno excede el 15%
        if err_alcance > 0.15 or err_carga > 0.15:
            continue
        total_error = err_alcance + err_carga
        # Si se usa carga intermedia, procesar también esos parámetros
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
            grua["_errors"] = {
                "Alcance": err_alcance,
                "Carga en Punta": err_carga,
                "Distancia": err_dist,
                "Carga Intermedia": err_carga_int
            }
        else:
            grua["_errors"] = {
                "Alcance": err_alcance,
                "Carga en Punta": err_carga
            }
        grua["Total Error"] = total_error
        candidatos.append(grua)
    # Ordenar candidatos por total error (menor primero)
    candidatos = sorted(candidatos, key=lambda x: x["Total Error"])

# --------------------------------------------------------------------
# Eliminar duplicados: conservar para cada modelo base el candidato con mejor criterio
candidatos_unicos = {}
for cand in candidatos:
    modelo = base_model(cand.get("Modelo de Grúa Torre", ""))
    if modelo not in candidatos_unicos:
        candidatos_unicos[modelo] = cand
    else:
        # Si ya existe, conservar el que tenga menor total error (o mayor stock, en modo stock)
        if use_stock:
            if cand["Stock"] > candidatos_unicos[modelo]["Stock"]:
                candidatos_unicos[modelo] = cand
        else:
            if cand["Total Error"] < candidatos_unicos[modelo]["Total Error"]:
                candidatos_unicos[modelo] = cand

candidatos_filtrados = list(candidatos_unicos.values())

# Seleccionar los 5 primeros resultados
resultados = candidatos_filtrados[:5]

# --------------------------------------------------------------------
# Preparar la tabla de resultados y estilos
if not resultados:
    st.write("No se encontraron grúas que se ajusten a los parámetros solicitados.")
else:
    # Definir columnas a mostrar:
    # Siempre se muestran: Modelo, Pluma Instalada y Carga en Punta.
    # Si se usa carga intermedia, se muestran también Distancia Específica y Carga específica.
    columnas = ["Modelo de Grúa Torre", "Pluma Instalada (m)", "Carga en Punta (kg)"]
    if use_intermedia:
        columnas += ["Distancia Específica (m)", "Carga específica (kg)"]
    # Si se usa stock, agregar columna Stock
    if use_stock:
        columnas += ["Stock"]

    # Función para formatear una fila (los valores en m con 2 decimales y en kg sin decimales con separador de miles)
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
        return fila

    df = pd.DataFrame([formatea_fila(g) for g in resultados], columns=columnas)
    
    st.header("Opciones encontradas")
    
    # Definir función para colorear filas según los criterios:
    # - En modo con stock: si el valor de Stock es "No hay stock", la fila se colorea de rojo.
    # - En modo sin stock: se usan los errores calculados (_errors) para alcance y carga obligatoria (y opcional si aplica):
    #       si TODOS los errores son ≤5% => verde (Match),
    #       si alguno está entre >5% y ≤15% => amarillo (Casi Match).
    def color_rows(row):
        # En modo con stock
        if use_stock:
            if row["Stock"] == "No hay stock":
                return ['background-color: red'] * len(row)
            else:
                return [''] * len(row)
        else:
            # En modo sin stock, recuperamos el candidato original para obtener los errores (_errors)
            # Como DataFrame ya no tiene esos valores, usamos el total error para distinguir:
            # Se reconstruye la información de errores a partir de "Total Error" en cada candidato.
            # Aquí usaremos que si Total Error (sumado de alcance y carga obligatoria, y opcional si aplica)
            # es <= 0.05* (número de parámetros) se marca verde, si >0.05 pero <=0.15*(número de parámetros) se marca amarillo.
            # Para este ejemplo, definamos:
            #   n = 2 si no hay intermedia, n = 4 si hay intermedia.
            n = 4 if use_intermedia else 2
            # Se obtiene el valor total error (ya calculado en el candidato) y se asume que se guardó con 3 decimales.
            total_error = float(row["Total Error"]) if "Total Error" in row and row["Total Error"] != "" else 0.0
            # Como no tenemos la distribución exact, usaremos:
            #   Si total_error <= 0.05*n: verde; si total_error <= 0.15*n: amarillo; de lo contrario, se descarta (no debería aparecer).
            if total_error <= 0.05 * n:
                return ['background-color: lightgreen'] * len(row)
            elif total_error <= 0.15 * n:
                return ['background-color: lightyellow'] * len(row)
            else:
                return [''] * len(row)
    
    # En modo sin stock, como no incluimos las columnas "Total Error" ni "Tipo", agregamos temporalmente esa
    # información para el estilo. Para ello, creamos un DataFrame auxiliar.
    if not use_stock:
        # Reconstruir un DataFrame auxiliar con la información de errores a partir de la lista de candidatos filtrados
        df_aux = pd.DataFrame()
        for cand in candidatos_filtrados[:5]:
            n = 4 if use_intermedia else 2
            total_err = cand.get("Total Error", 0)
            df_aux = df_aux.append({"Total Error": f"{total_err:.3f}"}, ignore_index=True)
        # Agregamos esa columna a df temporalmente para usarla en el estilo
        df["Total Error"] = df_aux["Total Error"]
        styled_df = df.style.apply(color_rows, axis=1)
        # Luego quitamos la columna auxiliar de visualización si se desea.
        styled_df = styled_df.hide_columns(["Total Error"])
    else:
        styled_df = df.style.apply(color_rows, axis=1)
    
    st.dataframe(styled_df)
