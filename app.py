import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial import KDTree
from streamlit_js_eval import streamlit_js_eval
import datetime

# --- CONFIGURACIÓN DE INTERFAZ NAVIGATOR ---
st.set_page_config(page_title="AGRO-SCAN NAVIGATOR", layout="centered")

def apply_navigator_style():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
        .main { background-color: #000000; color: #FFFFFF; font-family: 'JetBrains Mono', monospace; }
        
        .stButton>button { 
            border: 1px solid #FF5F1F; background-color: #1A0F0A; color: #FF5F1F; 
            width: 100%; height: 50px; font-weight: bold; border-radius: 2px;
            letter-spacing: 2px; text-transform: uppercase; margin-top: 10px;
        }
        .header-box { border: 1px solid #333; padding: 20px; text-align: center; background: #050505; margin-bottom: 10px; }
        .telemetry-card { background: #0A0A0A; border: 1px solid #222; padding: 15px; margin-bottom: 10px; }
        
        /* Estilo para Títulos de Sección */
        .section-header { 
            color: #FF5F1F; font-size: 1.2rem; font-weight: bold; 
            border-bottom: 1px solid #FF5F1F; padding-bottom: 5px; margin-top: 20px;
            text-transform: uppercase; letter-spacing: 2px;
        }
        
        [data-testid="stMetricValue"] { color: #FF5F1F !important; font-size: 1.5rem !important; }
        .stNumberInput label { color: #FF5F1F !important; }
        </style>
    """, unsafe_allow_html=True)

def decimal_to_dms(deg, is_lat=True):
    direction = ("N" if deg >= 0 else "S") if is_lat else ("E" if deg >= 0 else "W")
    deg = abs(deg)
    d = int(deg)
    m = int((deg - d) * 60)
    s = round((deg - d - m/60) * 3600, 2)
    return f"{direction} {d}°{m:02d}'{s:05.2f}\""

@st.cache_resource
def load_spatial_engine(file_path):
    df = pd.read_parquet(file_path).dropna(subset=['lat_suelo', 'lon_suelo'])
    tree = KDTree(df[['lat_suelo', 'lon_suelo']].values)
    return df, tree

def main():
    apply_navigator_style()
    
    st.markdown('<div class="header-box">', unsafe_allow_html=True)
    st.markdown("<h1 style='margin:0; color:#FF5F1F; letter-spacing:3px;'>MISSION NAVIGATOR</h1>", unsafe_allow_html=True)
    st.markdown("<span style='color:#888;'>SISTEMA DE ANÁLISIS JULIO 25/26</span>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # --- SELECTOR DE MODO ---
    modo_gps = st.radio("SISTEMA DE POSICIONAMIENTO", ["Satélite (Auto)", "Manual (Override)"], horizontal=True)

    lat_now, lon_now = 20.6825, -103.3830 # Guadalajara Default

    if modo_gps == "Satélite (Auto)":
        loc = streamlit_js_eval(js_expressions="navigator.geolocation.getCurrentPosition(pos => pos.coords, err => console.log(err), {enableHighAccuracy:true, timeout:10000})", key="gps_auto")
        if loc:
            lat_now, lon_now = loc['latitude'], loc['longitude']
            st.success(f"✅ SEÑAL SATELITAL ACTIVA")
        else:
            st.warning("⚠️ SENSOR GPS INACTIVO / BUSCANDO...")
    else:
        st.info("⌨️ INGRESE COORDENADAS DEL DISPOSITIVO FÍSICO")
        c1, c2 = st.columns(2)
        lat_now = c1.number_input("Latitud", value=20.682554, format="%.6f")
        lon_now = c2.number_input("Longitud", value=-103.383093, format="%.6f")

    # --- TELEMETRÍA BOX ---
    st.markdown(f"""
        <div class="telemetry-card">
            <table style="width:100%; color: #CCC;">
                <tr><td>Latitud</td><td style="text-align:right;">{decimal_to_dms(lat_now, True)}</td></tr>
                <tr><td>Longitud</td><td style="text-align:right;">{decimal_to_dms(lon_now, False)}</td></tr>
                <tr><td>Altitud</td><td style="text-align:right;">1543m</td></tr>
            </table>
        </div>
    """, unsafe_allow_html=True)

    DATA_FILE = "field_app_data.parquet"
    try:
        df, tree = load_spatial_engine(DATA_FILE)
    except:
        st.error("DATABASE OFFLINE")
        return

    if st.button("🚀 EJECUTAR ESCANEO DE CAMPO"):
        with st.spinner("PROCESANDO DATOS..."):
            dist, idx = tree.query(np.array([lat_now, lon_now]))
            data = df.iloc[idx]
            
            st.markdown('<div class="section-header">🛠️ Caracterización de Suelo</div>', unsafe_allow_html=True)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("pH", f"{data['suelo_ph']:.1f}")
            c2.metric("SOC", f"{data['suelo_soc']:.1f}")
            c3.metric("ARCILLA", f"{data['suelo_arcilla_pct']:.1f}%")
            c4.metric("TWI", f"{data['topo_twi']:.1f}")

            st.markdown('<div class="section-header">📊 Salud Climática (JULIO)</div>', unsafe_allow_html=True)
            clima = [("LLUVIA", "rain_25", "rain_26", "mm", False),
                     ("ESTRÉS (VPD)", "vpd_25", "vpd_26", "kPa", True),
                     ("TEMP MÁX", "temp_25", "temp_26", "°C", True),
                     ("VIGOR (NDVI)", "vigor_25", "vigor_26", "idx", False)]

            for label, c25, c26, unit, inv in clima:
                v25, v26 = data[c25], data[c26]
                st.metric(label=f"{label} (JUL '26 vs '25)", value=f"{v26:.2f} {unit}", 
                          delta=f"{v26-v25:.2f} {unit}", delta_color="inverse" if inv else "normal")
                st.markdown("---")
            
            st.caption(f"Nodo más cercano a {dist*111.1:.2f} km")

if __name__ == "__main__":
    main()
