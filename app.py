import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial import KDTree
from streamlit_js_eval import get_geolocation
import datetime

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="AGRO-SCAN NAVIGATOR", layout="wide")

if "location" not in st.session_state:
    st.session_state.location = None

# 2. ESTILO CSS HUD MAIZAL (DISEÑO SOLICITADO)
def apply_maiz_hud_style():
    corn_bg = "https://upload.wikimedia.org/wikipedia/commons/3/32/Corn_field_in_Slovenia.jpg"
    
    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=JetBrains+Mono&display=swap');
        
        .stApp {{
            background: linear-gradient(rgba(0,0,0,0.5), rgba(0,0,0,0.7)), url("{corn_bg}");
            background-size: cover;
            background-attachment: fixed;
            color: #FFFFFF;
            font-family: 'Inter', sans-serif;
        }}
        
        /* Paneles Estilo Glassmorphism */
        .hud-panel {{
            background: rgba(15, 15, 15, 0.85);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 12px;
            backdrop-filter: blur(10px);
            margin-bottom: 15px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.8);
        }}
        
        /* Dial Central Aeroespacial */
        .dial-container {{
            display: flex; justify-content: center; align-items: center; padding: 10px 0;
        }}
        .central-dial {{
            width: 250px; height: 250px;
            border: 6px solid #FF5F1F;
            border-radius: 50%;
            display: flex; flex-direction: column;
            justify-content: center; align-items: center;
            background: rgba(0,0,0,0.7);
            box-shadow: 0 0 40px rgba(255, 95, 31, 0.5);
        }}
        .dial-header {{ color: #888; font-size: 0.75rem; letter-spacing: 2px; text-transform: uppercase; }}
        .dial-value {{ color: #FFF; font-size: 1.1rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }}

        /* Botones HUD */
        .stButton>button {{
            background: linear-gradient(90deg, #FF5F1F 0%, #E64A19 100%) !important;
            color: white !important;
            border: none !important;
            width: 100%;
            height: 55px;
            font-weight: 800;
            font-size: 1.1rem;
            letter-spacing: 2px;
            border-radius: 5px;
            text-transform: uppercase;
            box-shadow: 0 5px 15px rgba(255, 95, 31, 0.4);
        }}
        
        .status-pill {{
            background: #00C853; color: black; padding: 3px 10px;
            border-radius: 4px; font-weight: 800; font-size: 0.7rem;
            text-transform: uppercase;
        }}
        
        [data-testid="stMetricValue"] {{ color: #FF5F1F !important; font-family: 'JetBrains Mono', monospace; font-size: 1.6rem !important; }}
        [data-testid="stMetricLabel"] {{ color: #AAA !important; font-weight: 600; text-transform: uppercase; font-size: 0.8rem; }}
        </style>
    """, unsafe_allow_html=True)

# Lógica de DMS
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
    apply_maiz_hud_style()
    
    # --- HEADER ---
    st.markdown("<p style='text-align:center; color:#FF5F1F; letter-spacing:5px; margin-bottom:0; font-weight:bold; font-size:1.5rem;'>MISSION NAVIGATOR</p>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#888; font-size:0.85rem; margin-top:2px;'>SISTEMA DE ANÁLISIS GEORREFERENCIADO | JULIO 25/26</p>", unsafe_allow_html=True)
    st.markdown("<hr style='margin:15px auto; width:40%; opacity:0.2;'>", unsafe_allow_html=True)
    
    # --- LÓGICA FUNCIONAL: SINCRONIZACIÓN GPS ---
    if st.button("🔄 SINCRONIZAR SENSOR SATELITAL"):
        st.session_state.location = None
        st.rerun()

    if st.session_state.location is None:
        loc = get_geolocation()
        if loc and 'coords' in loc:
            st.session_state.location = {
                "lat": loc['coords']['latitude'],
                "lon": loc['coords']['longitude'],
                "alt": loc['coords'].get('altitude', 0),
                "acc": loc['coords'].get('accuracy', 0.98)
            }
            st.rerun()
        else:
            st.warning("⚠️ BUSCANDO SEÑAL GPS... Asegúrate de otorgar permisos en el navegador.")
            with st.expander("⌨️ Ingreso Manual de Emergencia"):
                c1, c2 = st.columns(2)
                m_lat = c1.number_input("Latitud", value=20.6825, format="%.6f")
                m_lon = c2.number_input("Longitud", value=-103.3830, format="%.6f")
                if st.button("FIJAR COORDENADAS MANUALES"):
                    st.session_state.location = {"lat": m_lat, "lon": m_lon, "alt": 1693.0, "acc": 0.0}
                    st.rerun()

    # --- DESPLIEGUE HUD (3 COLUMNAS) ---
    if st.session_state.location:
        lat_now = st.session_state.location['lat']
        lon_now = st.session_state.location['lon']
        alt_now = st.session_state.location['alt'] if st.session_state.location['alt'] else 1693.0
        acc_now = st.session_state.location.get('acc', 0.98)

        col_izq, col_cen, col_der = st.columns([1, 1.2, 1])
        
        with col_izq:
            st.markdown(f"""
                <div class="hud-panel">
                    <p style="color:#888; font-size:0.8rem; margin:0;">Conectividad Satelital</p>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:5px;">
                        <span style="color:#00C853; font-weight:bold;">ACTIVA</span>
                        <span class="status-pill">OK</span>
                    </div>
                    <hr style="opacity:0.1; margin:15px 0;">
                    <p style="color:#888; font-size:0.8rem; margin:0;">Precisión Horizontal</p>
                    <p style="font-family:monospace; margin:0; font-size:1.1rem; color:#FF5F1F;">{acc_now:.2f} m</p>
                </div>
            """, unsafe_allow_html=True)

        with col_cen:
            st.markdown(f"""
                <div class="dial-container">
                    <div class="central-dial">
                        <span class="dial-header">Latitud</span>
                        <span class="dial-value">{decimal_to_dms(lat_now, True)}</span>
                        <span class="dial-value">{decimal_to_dms(lon_now, False)}</span>
                        <span class="dial-header" style="margin-top:12px;">Altitud</span>
                        <span class="dial-value">{alt_now:.1f}m</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with col_der:
            st.markdown("""
                <div class="hud-panel">
                    <p style="color:#888; font-size:0.8rem; margin:0;">Puntos de Interés</p>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:5px;">
                        <span style="color:#FFF; font-weight:bold;">Precisión Nodo</span>
                        <span class="status-pill" style="background:#FF5F1F; color:white;">ÉXITO</span>
                    </div>
                    <hr style="opacity:0.1; margin:15px 0;">
                    <p style="color:#888; font-size:0.8rem; margin:0;">Alertas de Zona</p>
                    <p style="color:#00C853; font-weight:bold; margin:0;">SISTEMA ESTABLE</p>
                </div>
            """, unsafe_allow_html=True)

        # --- MOTOR DE BÚSQUEDA ---
        DATA_FILE = "field_app_data.parquet"
        try:
            df, tree = load_spatial_engine(DATA_FILE)
        except:
            st.error("BASE DE DATOS NO DETECTADA")
            return

        if st.button("🛰️ EJECUTAR ESCANEO DE CAMPO"):
            with st.spinner("ANALIZANDO MALLA GEOGRÁFICA..."):
                dist, idx = tree.query(np.array([lat_now, lon_now]))
                data = df.iloc[idx]
                
                # --- RESULTADOS ---
                r_col1, r_col2 = st.columns(2)
                
                with r_col1:
                    st.markdown('<div class="hud-panel">', unsafe_allow_html=True)
                    st.markdown("<p style='color:#FF5F1F; font-weight:bold; letter-spacing:1px; border-bottom:1px solid #333; padding-bottom:5px;'>🛠️ CARACTERIZACIÓN DE SUELO</p>", unsafe_allow_html=True)
                    m1, m2 = st.columns(2)
                    m1.metric("pH Suelo", f"{data['suelo_ph']:.1f}")
                    m2.metric("SOC (Carbono)", f"{data['suelo_soc']:.1f}")
                    m3, m4 = st.columns(2)
                    m3.metric("Arcilla %", f"{data['suelo_arcilla_pct']:.1f}%")
                    m4.metric("TWI (Humedad)", f"{data['topo_twi']:.1f}")
                    st.markdown('</div>', unsafe_allow_html=True)

                with r_col2:
                    st.markdown('<div class="hud-panel">', unsafe_allow_html=True)
                    st.markdown("<p style='color:#FF5F1F; font-weight:bold; letter-spacing:1px; border-bottom:1px solid #333; padding-bottom:5px;'>📊 SALUD CLIMÁTICA (JULIO)</p>", unsafe_allow_html=True)
                    
                    c_m1, c_m2 = st.columns(2)
                    c_m1.metric("Lluvia", f"{data['rain_26']:.1f} mm", f"{data['rain_26']-data['rain_25']:.1f} vs '25")
                    c_m2.metric("Estrés VPD", f"{data['vpd_26']:.2f} kPa", f"{data['vpd_26']-data['vpd_25']:.2f}", delta_color="inverse")
                    
                    c_m3, c_m4 = st.columns(2)
                    c_m3.metric("Temp Máx", f"{data['temp_26']:.1f} °C", f"{data['temp_26']-data['temp_25']:.1f}", delta_color="inverse")
                    c_m4.metric("Vigor NDVI", f"{data['vigor_26']:.2f}", f"{data['vigor_26']-data['vigor_25']:.2f}")
                    st.markdown('</div>', unsafe_allow_html=True)

                st.caption(f"Distancia al nodo: {dist*111.1:.2f} km")

if __name__ == "__main__":
    main()
