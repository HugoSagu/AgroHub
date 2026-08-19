import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial import KDTree
from streamlit_js_eval import streamlit_js_eval
from datetime import datetime

# --- ESTÉTICA MISSION CONTROL (HUD) ---
st.set_page_config(page_title="AGRO-SCAN PRO", layout="centered")

def apply_hud_style():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
        .main { background-color: #000000; color: #00FF41; font-family: 'JetBrains Mono', monospace; }
        .stButton>button { 
            border: 2px solid #00FF41; background-color: #051405; color: #00FF41; 
            width: 100%; height: 70px; font-size: 1.2rem; font-weight: bold;
            box-shadow: 0 0 15px #00FF41; border-radius: 4px;
        }
        .stMetric { background-color: #0A0A0A; border: 1px solid #1A331A; padding: 15px; border-radius: 5px; }
        [data-testid="stMetricValue"] { color: #00FF41; font-size: 1.5rem !important; }
        .header-box { border: 2px solid #333; padding: 15px; text-align: center; margin-bottom: 20px; background: #050505; }
        .telemetry-box { 
            background-color: #050505; border: 1px dashed #00FF41; 
            padding: 10px; margin-top: 10px; font-size: 0.85rem; color: #00FF41;
        }
        .month-tag { color: #000; background-color: #00FF41; padding: 2px 10px; font-weight: bold; border-radius: 3px; }
        h3 { color: #00FF41 !important; letter-spacing: 2px; text-transform: uppercase; border-bottom: 1px solid #1A331A; }
        </style>
    """, unsafe_allow_html=True)

@st.cache_resource
def load_engine(file_path):
    df = pd.read_parquet(file_path)
    tree = KDTree(df[['lat_suelo', 'lon_suelo']].values)
    return df, tree

def get_month_name():
    meses = {1:"ENERO", 2:"FEBRERO", 3:"MARZO", 4:"ABRIL", 5:"MAYO", 6:"JUNIO", 
             7:"JULIO", 8:"AGOSTO", 9:"SEPTIEMBRE", 10:"OCTUBRE", 11:"NOVIEMBRE", 12:"DICIEMBRE"}
    return meses[datetime.now().month]

def main():
    apply_hud_style()
    nombre_mes = get_month_name()
    
    # --- HEADER ---
    st.markdown('<div class="header-box">', unsafe_allow_html=True)
    st.markdown("<h1 style='margin:0; color:#00FF41;'>📡 AGRO-SCAN PRO</h1>", unsafe_allow_html=True)
    st.markdown(f"PERIODO: <span class='month-tag'>{nombre_mes} {datetime.now().year}</span>", unsafe_allow_html=True)
    
    # Geolocalización del dispositivo
    loc = streamlit_js_eval(js_expressions="window.navigator.geolocation.getCurrentPosition(pos => pos.coords)", key="location")
    
    if loc:
        lat_gps, lon_gps = loc['latitude'], loc['longitude']
        acc_gps = loc['accuracy']
        st.success(f"SENSOR GPS: ONLINE")
    else:
        st.warning("🛰️ BUSCANDO SATÉLITES...")
        lat_gps, lon_gps, acc_gps = 19.1684, -104.6623, 0.0
    st.markdown('</div>', unsafe_allow_html=True)

    DATA_FILE = "field_app_data.parquet" 
    
    try:
        df, spatial_tree = load_engine(DATA_FILE)
    except Exception as e:
        st.error(f"DATABASE ERROR: {e}")
        return

    if st.button("EJECUTAR ESCANEO DE CAMPO"):
        with st.spinner("SINCRONIZANDO TELEMETRÍA..."):
            # Búsqueda KD-Tree
            dist, idx = spatial_tree.query([lat_gps, lon_gps])
            data = df.iloc[idx]
            
            # --- PANEL DE COORDENADAS (NUEVO) ---
            st.subheader("📍 Posicionamiento Espacial")
            col_gps, col_data = st.columns(2)
            
            with col_gps:
                st.markdown(f"""
                <div class="telemetry-box">
                    <b>GPS (TU UBICACIÓN):</b><br>
                    LAT: {lat_gps:.6f}<br>
                    LON: {lon_gps:.6f}<br>
                    PRECISIÓN: ±{acc_gps:.1f}m
                </div>
                """, unsafe_allow_html=True)
                
            with col_data:
                st.markdown(f"""
                <div class="telemetry-box">
                    <b>NODO (BASE DE DATOS):</b><br>
                    LAT: {data['lat_suelo']:.6f}<br>
                    LON: {data['lon_suelo']:.6f}<br>
                    OFFSET: {dist*111111:.1f}m
                </div>
                """, unsafe_allow_html=True)

            # --- SECCIÓN SUELO ---
            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("🛠️ Caracterización de Suelo")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("pH", f"{data['suelo_ph']:.1f}")
            c2.metric("SOC", f"{data['suelo_soc']:.1f}")
            c3.metric("ARCILLA", f"{data['suelo_arcilla_pct']:.1f}%")
            c4.metric("TWI", f"{data['topo_twi']:.1f}")
            
            # --- SECCIÓN CLIMA ---
            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader(f"📊 Análisis Climático: {nombre_mes}")
            
            metrics = [
                ("LLUVIA TOTAL", "rain_25", "rain_26", "mm", False),
                ("ESTRÉS (VPD)", "vpd_25", "vpd_26", "kPa", True),
                ("TEMP. MÁX", "temp_25", "temp_26", "°C", True),
                ("VIGOR (NDVI)", "vigor_25", "vigor_26", "idx", False)
            ]

            for label, col_25, col_26, unit, inv in metrics:
                val_25, val_26 = data[col_25], data[col_26]
                st.metric(
                    label=f"{label} (vs {nombre_mes} '25)", 
                    value=f"{val_26:.2f} {unit}", 
                    delta=f"{val_26-val_25:.2f} {unit}",
                    delta_color="inverse" if inv else "normal"
                )
                st.markdown("---")

    st.sidebar.markdown(f"### TELEMETRÍA")
    st.sidebar.code(f"LAT: {lat_gps:.4f}\nLON: {lon_gps:.4f}\nMONTH: {nombre_mes}")
    st.sidebar.info("MODO: ESCANEO ACTIVO")

if __name__ == "__main__":
    main()
