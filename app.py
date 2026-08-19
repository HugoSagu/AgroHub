import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial import KDTree
from streamlit_js_eval import get_geolocation
import datetime

# 1. CONFIGURACIÓN E INICIALIZACIÓN
st.set_page_config(page_title="AGRO-SCAN NAVIGATOR", layout="centered")

if "location" not in st.session_state:
    st.session_state.location = None

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
        .section-header { 
            color: #FF5F1F; font-size: 1.2rem; font-weight: bold; 
            border-bottom: 1px solid #FF5F1F; padding-bottom: 5px; margin-top: 20px;
            text-transform: uppercase; letter-spacing: 2px;
        }
        [data-testid="stMetricValue"] { color: #FF5F1F !important; font-size: 1.5rem !important; }
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

    # --- LÓGICA DE CAPTURA GPS ---
    if st.button("🔄 SINCRONIZAR SENSOR SATELITAL"):
        st.session_state.location = None  # Reset para nueva lectura
        st.rerun()

    if st.session_state.location is None:
        # Obtenemos ubicación con timeout y alta precisión
        loc = get_geolocation()
        if loc and 'coords' in loc:
            st.session_state.location = {
                "lat": loc['coords']['latitude'],
                "lon": loc['coords']['longitude'],
                "alt": loc['coords'].get('altitude', 0)
            }
            st.rerun()
        else:
            st.warning("⚠️ BUSCANDO SEÑAL GPS... Asegúrate de estar en exterior y con permisos activos.")
            # Ubicación manual por si falla el sensor
            with st.expander("⌨️ Ingreso Manual de Emergencia"):
                c1, c2 = st.columns(2)
                m_lat = c1.number_input("Latitud", value=20.6825, format="%.6f")
                m_lon = c2.number_input("Longitud", value=-103.3830, format="%.6f")
                if st.button("FIJAR COORDENADAS MANUALES"):
                    st.session_state.location = {"lat": m_lat, "lon": m_lon, "alt": 0}
                    st.rerun()

    # --- DESPLIEGUE DE TELEMETRÍA ---
    if st.session_state.location:
        lat_now = st.session_state.location['lat']
        lon_now = st.session_state.location['lon']
        alt_now = st.session_state.location['alt'] if st.session_state.location['alt'] else 0

        st.markdown(f"""
            <div class="telemetry-card">
                <table style="width:100%; color: #CCC; font-family: monospace;">
                    <tr><td>Latitud</td><td style="text-align:right;">{decimal_to_dms(lat_now, True)}</td></tr>
                    <tr><td>Longitud</td><td style="text-align:right;">{decimal_to_dms(lon_now, False)}</td></tr>
                    <tr><td>Altitud</td><td style="text-align:right;">{alt_now:.1f} m</td></tr>
                </table>
            </div>
        """, unsafe_allow_html=True)

        # --- BÚSQUEDA EN BASE DE DATOS ---
        DATA_FILE = "field_app_data.parquet"
        try:
            df, tree = load_spatial_engine(DATA_FILE)
        except:
            st.error("DATABASE OFFLINE")
            return

        if st.button("🚀 EJECUTAR ESCANEO DE CAMPO"):
            with st.spinner("PROCESANDO..."):
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
                
                st.caption(f"Nodo detectado a {dist*111.1:.2f} km")

if __name__ == "__main__":
    main()
