import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial import KDTree
from streamlit_js_eval import streamlit_js_eval
from datetime import datetime

# --- ESTÉTICA DE INSTRUMENTACIÓN (AVIONICS HUD) ---
st.set_page_config(page_title="AGRO-SCAN NAVIGATOR", layout="centered")

def apply_navigator_style():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');
        
        .main { background-color: #000000; color: #FFFFFF; font-family: 'Inter', sans-serif; }
        
        /* Estilo de Botón de Escaneo */
        .stButton>button { 
            border: 1px solid #FF5F1F; background-color: #1A0F0A; color: #FF5F1F; 
            width: 100%; height: 60px; font-weight: bold; border-radius: 0px;
            letter-spacing: 2px; transition: 0.3s;
        }
        .stButton>button:hover { background-color: #FF5F1F; color: #000; }

        /* Contenedor de Brújula y Telemetría */
        .compass-header {
            text-align: center; border: 1px solid #333; padding: 20px;
            background: radial-gradient(circle, #1a1a1a 0%, #000000 100%);
            margin-bottom: 20px; border-radius: 5px;
        }
        
        .coordinate-label { color: #888; font-size: 1.1rem; text-align: left; }
        .coordinate-value { color: #FFFFFF; font-size: 1.2rem; font-family: monospace; text-align: right; }
        
        /* Tarjetas de Datos */
        .data-card {
            border-left: 3px solid #FF5F1F; background-color: #0A0A0A;
            padding: 15px; margin: 10px 0;
        }
        
        [data-testid="stMetricValue"] { color: #FF5F1F !important; font-family: monospace; }
        [data-testid="stMetricLabel"] { color: #AAA !important; text-transform: uppercase; }
        hr { border: 0.5px solid #333; }
        </style>
    """, unsafe_allow_html=True)

# --- HELPER: CONVERSIÓN A DMS (Como en tu foto) ---
def decimal_to_dms(deg, is_lat=True):
    direction = ""
    if is_lat:
        direction = "N" if deg >= 0 else "S"
    else:
        direction = "E" if deg >= 0 else "W"
    
    deg = abs(deg)
    d = int(deg)
    m = int((deg - d) * 60)
    s = round((deg - d - m/60) * 3600, 2)
    return f"{direction} {d}°{m:02d}'{s:05.2f}\""

def main():
    apply_navigator_style()
    
    # --- HEADER: SIMULACIÓN DE BRÚJULA ---
    st.markdown("""
        <div class="compass-header">
            <svg width="150" height="150" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="45" fill="none" stroke="#333" stroke-width="1"/>
                <circle cx="50" cy="50" r="35" fill="none" stroke="#FF5F1F" stroke-width="0.5" stroke-dasharray="2,2"/>
                <text x="47" y="12" fill="#FF5F1F" font-size="8" font-weight="bold">N</text>
                <text x="88" y="53" fill="#888" font-size="8">E</text>
                <text x="47" y="95" fill="#888" font-size="8">S</text>
                <text x="5" y="53" fill="#888" font-size="8">W</text>
                <path d="M50 20 L55 50 L50 80 L45 50 Z" fill="#FF5F1F" opacity="0.8"/>
            </svg>
            <h2 style='color:#FF5F1F; margin:10px 0 0 0;'>MISSION NAVIGATOR</h2>
        </div>
    """, unsafe_allow_html=True)

    # --- OBTENER POSICIÓN ---
    loc = streamlit_js_eval(js_expressions="navigator.geolocation.getCurrentPosition(pos => pos.coords, err => console.log(err), {enableHighAccuracy:true})", key="gps")
    
    lat_val, lon_val = (20.174966, -102.222761) # Fallback (Jalisco/Michoacán)
    if loc:
        lat_val, lon_val = loc['latitude'], loc['longitude']

    # --- DISPLAY COORDENADAS ESTILO FOTO ---
    st.markdown(f"""
        <div style="background:#0A0A0A; padding:15px; border-radius:5px; border:1px solid #222;">
            <table style="width:100%">
                <tr>
                    <td class="coordinate-label">Latitud</td>
                    <td class="coordinate-value">{decimal_to_dms(lat_val, True)}</td>
                </tr>
                <tr>
                    <td class="coordinate-label">Longitud</td>
                    <td class="coordinate-value">{decimal_to_dms(lon_val, False)}</td>
                </tr>
                <tr>
                    <td class="coordinate-label">Altitud</td>
                    <td class="coordinate-value">1543m</td>
                </tr>
            </table>
        </div>
    """, unsafe_allow_html=True)

    st.write("") # Espaciador

    # --- DATA ENGINE ---
    DATA_PATH = "field_app_data.parquet"
    try:
        df = pd.read_parquet(DATA_PATH)
        tree = KDTree(df[['lat_suelo', 'lon_suelo']].values)
    except:
        st.error("DATABASE NOT LINKED")
        return

    if st.button("EJECUTAR ESCANEO SENSOR"):
        with st.spinner("SINCRO-MALLA..."):
            dist, idx = tree.query([lat_val, lon_val])
            data = df.iloc[idx]
            
            # --- SECCIÓN SUELO ---
            st.subheader("🛠️ SUELO (EDACOLOGÍA)")
            c1, c2 = st.columns(2)
            with c1:
                st.metric("PH", f"{data['suelo_ph']:.2f}")
                st.metric("ARCILLA", f"{data['suelo_arcilla_pct']:.1f}%")
            with c2:
                st.metric("SOC", f"{data['suelo_soc']:.1f}")
                st.metric("TWI", f"{data['topo_twi']:.2f}")

            st.divider()

            # --- SECCIÓN CLIMA ---
            st.subheader(f"📊 CLIMA {datetime.now().strftime('%B').upper()}")
            
            m_list = [
                ("LLUVIA", "rain_25", "rain_26", "mm"),
                ("ESTRÉS (VPD)", "vpd_25", "vpd_26", "kPa"),
                ("TEMP MÁX", "temp_25", "temp_26", "°C"),
                ("VIGOR (NDVI)", "vigor_25", "vigor_26", "idx")
            ]

            for label, c25, c26, unit in m_list:
                v25, v26 = data[c25], data[c26]
                st.metric(label=f"{label} (ACTUAL)", value=f"{v26:.2f} {unit}", 
                          delta=f"{v26-v25:.2f} vs 2025")

    st.sidebar.markdown("### SYSTEM LOG")
    st.sidebar.caption("NAVIGATOR MODE ACTIVE")
    st.sidebar.code(f"LAT: {lat_val}\nLON: {lon_val}")

if __name__ == "__main__":
    main()
