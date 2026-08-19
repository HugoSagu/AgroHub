import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial import KDTree
from streamlit_js_eval import streamlit_js_eval

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
        [data-testid="stMetricValue"] { color: #00FF41; font-size: 1.8rem !important; }
        [data-testid="stMetricDelta"] svg { fill: #00FF41 !important; }
        .header-box { border: 2px solid #333; padding: 15px; text-align: center; margin-bottom: 20px; background: #050505; }
        h3 { color: #00FF41 !important; letter-spacing: 2px; text-transform: uppercase; border-bottom: 1px solid #1A331A; padding-bottom: 5px; }
        </style>
    """, unsafe_allow_html=True)

# --- MOTOR DE BÚSQUEDA ESPACIAL ---
@st.cache_resource
def load_engine(file_path):
    # Carga eficiente de Parquet
    df = pd.read_parquet(file_path)
    # Indexamos por las columnas de tu archivo: lat_suelo y lon_suelo
    tree = KDTree(df[['lat_suelo', 'lon_suelo']].values)
    return df, tree

def main():
    apply_hud_style()
    
    st.markdown('<div class="header-box">', unsafe_allow_html=True)
    st.markdown("<h1 style='margin:0; color:#00FF41;'>📡 AGRO-SCAN PRO</h1>", unsafe_allow_html=True)
    
    # Obtención de coordenadas GPS en tiempo real
    loc = streamlit_js_eval(js_expressions="window.navigator.geolocation.getCurrentPosition(pos => pos.coords)", key="location")
    
    if loc:
        lat_gps, lon_gps = loc['latitude'], loc['longitude']
        st.success(f"GPS LOCK: {lat_gps:.5f}, {lon_gps:.5f} (Acc: ±{loc['accuracy']:.1f}m)")
    else:
        st.warning("🛰️ BUSCANDO SATÉLITES... (Activa el GPS)")
        lat_gps, lon_gps = 19.1684, -104.6623 # Coordenadas de referencia
    st.markdown('</div>', unsafe_allow_html=True)

    # El archivo debe llamarse así en tu carpeta:
    DATA_FILE = "field_app_data.parquet" 
    
    try:
        df, spatial_tree = load_engine(DATA_FILE)
    except Exception as e:
        st.error(f"DATABASE ERROR: {e}")
        return

    if st.button("EJECUTAR ESCANEO GEORREFERENCIADO"):
        with st.spinner("PROCESANDO MALLA DE DATOS..."):
            # Búsqueda instantánea del punto más cercano
            dist, idx = spatial_tree.query([lat_gps, lon_gps])
            data = df.iloc[idx]
            
            # --- SECCIÓN 1: SUELO (Variables estáticas) ---
            st.subheader("🛠️ Propiedades del Suelo")
            c1, c2 = st.columns(2)
            c3, c4 = st.columns(2)
            
            c1.metric("pH", f"{data['suelo_ph']:.2f}")
            c2.metric("CARBONO (SOC)", f"{data['suelo_soc']:.1f}")
            c3.metric("ARCILLA", f"{data['suelo_arcilla_pct']:.1f}%")
            c4.metric("TOPO TWI", f"{data['topo_twi']:.2f}")
            
            # --- SECCIÓN 2: COMPARATIVA CLIMÁTICA (2025 vs 2026) ---
            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("📊 Comparativa Ciclo 25 vs 26")
            
            # Definimos las métricas según tus columnas reales
            # (Etiqueta, Col_2025, Col_2026, Unidad, Invertir_Color)
            metrics = [
                ("LLUVIA TOTAL", "rain_25", "rain_26", "mm", False),
                ("ESTRÉS TÉRMICO (VPD)", "vpd_25", "vpd_26", "kPa", True),
                ("TEMP. MÁXIMA", "temp_25", "temp_26", "°C", True),
                ("VIGOR VEGETATIVO (NDVI)", "vigor_25", "vigor_26", "idx", False)
            ]

            for label, col_25, col_26, unit, inv in metrics:
                val_25 = data[col_25]
                val_26 = data[col_26]
                diff = val_26 - val_25
                
                # Diseño de la métrica comparativa
                st.metric(
                    label=f"{label} (vs {val_25:.2f} {unit} en 2025)", 
                    value=f"{val_26:.2f} {unit}", 
                    delta=f"{diff:.2f} {unit}",
                    delta_color="inverse" if inv else "normal"
                )
                st.markdown("---")

    st.sidebar.markdown("### SYSTEM LOG")
    st.sidebar.info("Modo: Análisis Interanual")
    st.sidebar.caption("v2.1 Build: Parquet_Engine")

if __name__ == "__main__":
    main()
