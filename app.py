import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial import KDTree
from streamlit_js_eval import streamlit_js_eval
from datetime import datetime

# --- CONFIGURACIÓN UI ---
st.set_page_config(page_title="AGRO-SCAN PRO", layout="centered")

def apply_hud_style():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
        .main { background-color: #000000; color: #00FF41; font-family: 'JetBrains Mono', monospace; }
        .stButton>button { 
            border: 2px solid #00FF41; background-color: #051405; color: #00FF41; 
            width: 100%; height: 60px; font-weight: bold; border-radius: 4px; box-shadow: 0 0 10px #00FF41;
        }
        .header-box { border: 2px solid #333; padding: 15px; text-align: center; background: #050505; margin-bottom: 10px;}
        .telemetry-box { background: #0A0A0A; border: 1px solid #00FF41; padding: 10px; font-size: 0.8rem; color: #00FF41; border-radius: 4px;}
        .month-tag { color: #000; background-color: #00FF41; padding: 2px 8px; font-weight: bold; border-radius: 3px; }
        </style>
    """, unsafe_allow_html=True)

@st.cache_resource
def load_engine(file_path):
    df = pd.read_parquet(file_path)
    tree = KDTree(df[['lat_suelo', 'lon_suelo']].values)
    return df, tree

def main():
    apply_hud_style()
    nombre_mes = {1:"ENERO", 2:"FEBRERO", 3:"MARZO", 4:"ABRIL", 5:"MAYO", 6:"JUNIO", 
                  7:"JULIO", 8:"AGOSTO", 9:"SEPTIEMBRE", 10:"OCTUBRE", 11:"NOVIEMBRE", 12:"DICIEMBRE"}[datetime.now().month]

    st.markdown('<div class="header-box">', unsafe_allow_html=True)
    st.markdown("<h1 style='margin:0; color:#00FF41;'>📡 AGRO-SCAN PRO</h1>", unsafe_allow_html=True)
    st.markdown(f"MODO: <span class='month-tag'>{nombre_mes} '25/'26</span>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # --- LÓGICA DE GPS REFORZADA ---
    st.sidebar.header("CONFIGURACIÓN GPS")
    modo_gps = st.sidebar.radio("MODO DE UBICACIÓN", ["Automático (Sensor)", "Manual (Override)"])

    lat_final, lon_final, acc_final = 0.0, 0.0, 0.0

    if modo_gps == "Automático (Sensor)":
        # Forzamos High Accuracy mediante JS
        loc = streamlit_js_eval(
            js_expressions="navigator.geolocation.getCurrentPosition(pos => pos.coords, err => console.log(err), {enableHighAccuracy:true, timeout:5000, maximumAge:0})", 
            key="gps_engine"
        )
        if loc:
            lat_final, lon_final, acc_final = loc['latitude'], loc['longitude'], loc['accuracy']
            st.sidebar.success(f"✅ Satélite Lock: ±{acc_final:.1f}m")
        else:
            st.sidebar.warning("⌛ Obteniendo señal...")
            # Fallback a un punto central si no hay señal
            lat_final, lon_final = 19.1684, -104.6623
    else:
        # Modo manual para cuando el GPS falla
        lat_final = st.sidebar.number_input("Latitud Manual", value=19.168446, format="%.6f")
        lon_final = st.sidebar.number_input("Longitud Manual", value=-104.662370, format="%.6f")
        acc_final = 0.0

    # --- PROCESAMIENTO ---
    DATA_FILE = "field_app_data.parquet"
    try:
        df, spatial_tree = load_engine(DATA_FILE)
    except:
        st.error("DATABASE NOT FOUND")
        return

    if st.button("ESCANEAR POSICIÓN ACTUAL"):
        dist, idx = spatial_tree.query([lat_final, lon_final])
        data = df.iloc[idx]
        
        # Panel de Coordenadas
        st.subheader("📍 Telemetría")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f'<div class="telemetry-box"><b>GPS ACTUAL</b><br>LAT: {lat_final:.6f}<br>LON: {lon_final:.6f}</div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="telemetry-box"><b>NODO DATA</b><br>LAT: {data["lat_suelo"]:.6f}<br>LON: {data["lon_suelo"]:.6f}</div>', unsafe_allow_html=True)

        # Resultados de Suelo
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("🛠️ Caracterización de Suelo")
        cols = st.columns(4)
        cols[0].metric("pH", f"{data['suelo_ph']:.1f}")
        cols[1].metric("SOC", f"{data['suelo_soc']:.1f}")
        cols[2].metric("ARCILLA", f"{data['suelo_arcilla_pct']:.1f}%")
        cols[3].metric("TWI", f"{data['topo_twi']:.1f}")

        # Comparativa Climática
        st.subheader(f"📊 Clima: {nombre_mes}")
        m_list = [("Lluvia", "rain_25", "rain_26", "mm", False),
                  ("VPD", "vpd_25", "vpd_26", "kPa", True),
                  ("Temp", "temp_25", "temp_26", "°C", True),
                  ("NDVI", "vigor_25", "vigor_26", "idx", False)]

        for label, c25, c26, unit, inv in m_list:
            v25, v26 = data[c25], data[c26]
            st.metric(label=f"{label} ('26 vs '25)", value=f"{v26:.2f} {unit}", 
                      delta=f"{v26-v25:.2f}", delta_color="inverse" if inv else "normal")
            st.markdown("---")

if __name__ == "__main__":
    main()
