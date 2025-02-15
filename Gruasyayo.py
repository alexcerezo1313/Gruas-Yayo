import streamlit as st
import json
import pandas as pd

# Función para cargar la base de datos desde el archivo JSON
@st.cache_data
def load_data(json_file):
    with open(json_file, "r", encoding="utf-8") as f:
        return json.load(f)

# Cargar datos (se asume que el JSON se llama "gruas_data.json")
data = load_data("gruas_data.json")
# La lista de grúas está en la clave "Hoja1"
gruas_list = data.get("Hoja1", [])

st.title("Selector de Grúas Tore")

st.sidebar.header("Filtros de búsqueda")

# --- Intervalos para los filtros principales ---
# Pluma Instalada (en metros)
pluma_min = st.sidebar.number_input("Pluma Instalada Mínima (m):", value=30.0, step=0.5)
pluma_max = st.sidebar.number_input("Pluma Instalada Máxima (m):", value=50.0, step=0.5)

# Carga en Punta (en kg)
carga_punta_min = st.sidebar.number_input("Carga en Punta Mínima (kg):", value=1000.0, step=100.0)
carga_punta_max = st.sidebar.number_input("Carga en Punta Máxima (kg):", value=2500.0, step=100.0)

# ¿Filtrar también por datos a distancia específica?
use_especifica = st.sidebar.checkbox("Filtrar por carga a distancia específica")
if use_especifica:
    distancia_min = st.sidebar.number_input("Distancia Específica Mínima (m):", value=10.0, step=0.5)
    distancia_max = st.sidebar.number_input("Distancia Específica Máxima (m):", value=20.0, step=0.5)
    carga_espec_min = st.sidebar.number_input("Carga Específica Mínima (kg):", value=1000.0, step=100.0)
    carga_espec_max = st.sidebar.number_input("Carga Específica Máxima (kg):", value=2500.0, step=100.0)

# Tolerancias fijas
tol_metros = 5.0   # tolerancia en metros
tol_kg = 100.0     # tolerancia en kg

# Función que evalúa un campo:
# Devuelve 0 si el valor está dentro del intervalo,
# devuelve la desviación (diferencia al límite) si se sale pero dentro de la tolerancia,
# y devuelve None si se sale por más de la tolerancia.
def check_field(value, lower, upper, tol):
    if lower <= value <= upper:
        return 0.0
    elif value < lower:
        dev = lower - value
        if dev <= tol:
            return dev
        else:
            return None
    else:  # value > upper
        dev = value - upper
        if dev <= tol:
            return dev
        else:
            return None

# Listas para guardar los candidatos
matches = []      # candidatos que cumplen el intervalo en todos los campos
almost_matches = []  # candidatos que se salen en algún campo pero dentro de la tolerancia

# Iteramos sobre cada grúa
for grua in gruas_list:
    total_deviation = 0.0
    valid = True  # indica que el campo cumple o está dentro de tolerancia
    # Evaluamos "Pluma Instalada"
    val_pluma = grua.get("Pluma Instalada", 0)
    dev = check_field(val_pluma, pluma_min, pluma_max, tol_metros)
    if dev is None:
        valid = False
    else:
        total_deviation += dev

    # Evaluamos "Carga en Punta"
    val_carga_punta = grua.get("Carga en Punta", 0)
    dev2 = check_field(val_carga_punta, carga_punta_min, carga_punta_max, tol_kg)
    if dev2 is None:
        valid = False
    else:
        total_deviation += dev2

    # Si se filtra por datos de distancia específica, evaluamos esos campos
    if use_especifica:
        val_dist = grua.get("Distancia Específica", None)
        val_carga_esp = grua.get("Carga específica", None)
        if val_dist is None or val_carga_esp is None:
            valid = False
        else:
            dev3 = check_field(val_dist, distancia_min, distancia_max, tol_metros)
            dev4 = check_field(val_carga_esp, carga_espec_min, carga_espec_max, tol_kg)
            if dev3 is None or dev4 is None:
                valid = False
            else:
                total_deviation += dev3 + dev4

    # Solo consideramos el registro si es válido (está dentro del rango o dentro de tolerancia en cada campo)
    if valid:
        # Definimos el tipo: "Match" si no hubo desviación en ningún campo; "Casi Match" si hubo alguna desviación
        tipo = "Match" if total_deviation == 0.0 else "Casi Match"
        # Agregamos el registro junto con su desviación total y tipo
        candidate = grua.copy()
        candidate["Deviación Total"] = total_deviation
        candidate["Tipo"] = tipo
        if tipo == "Match":
            matches.append(candidate)
        else:
            almost_matches.append(candidate)

# Seleccionamos las 5 primeras opciones que ajustan (si hay más, se podría ordenar por otro criterio; aquí se usa el orden original)
matches_sorted = matches[:5]

# Para casi match, si existen, seleccionamos la que tenga la menor desviación total
almost_candidate = None
if almost_matches:
    almost_matches_sorted = sorted(almost_matches, key=lambda x: x["Deviación Total"])
    almost_candidate = almost_matches_sorted[0]

# Combinamos resultados: las 5 matches y, si existe, la casi match (se muestra aparte)
resultados = m
