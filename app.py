import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial import KDTree
from streamlit_js_eval import streamlit_js_eval

# --- CONFIGURACIÓN DE INTERFAZ HUD ---
st.set_page_config(page_title="AGRO-SCAN PRO", layout="centered")

def apply_hud_style():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
        .main { background-color: #000000; color: #00FF41; font-family: 'JetBrains Mono', monospace; }
        .stButton>button { 
            border: 2px solid #00FF41; background-color: #051405; color: #00FF41; 
            width: 100%; height: 70px; font-size: 1.2rem; font-weight: bold;
            box-shadow: 0 0 15px #00FF41; border-radius: 2px;
        }
        .stMetric { background-color: #0A0A0A; border: 1px solid #1A331A; padding: 10px; border-radius: 5px; }
        [data-testid="stMetricValue"] { color: #00FF41; font-size: 1.6rem !important; }
        .data-card { 
            border-left: 4px solid #00FF41; background: #0A0A0A; padding: 12px; 
            margin-bottom: 8px; border-radius: 0 5px 5px 0;
        }
        .header-box { border: 2px solid #333; padding: 15px; text-align: center; margin-bottom: 20px; background: #050505; }
        h3 { color: #00FF41 !important; letter-spacing: 2px; border-bottom: 1px solid #1A331A; }
        </style>
    """, unsafe_allow_html=True)

@st.cache_resource
def load_data_and_tree(file_path):
    if file_path.endswith('.parquet'):
        df = pd.read_parquet(file_path)
    else:
        df = pd.read_csv(file_path)
    tree = KDTree(df[['lat_suelo', 'lon_suelo']].values)
    return df, tree

def main():
    apply_hud_style()
    st.markdown('<div class="header-box">', unsafe_allow_html=True)
    st.markdown("<h1 style='margin:0;'>📡 AGRO-SCAN PRO</h1>", unsafe_allow_html=True)
    
    loc = streamlit_js_eval(js_expressions="window.navigator.geolocation.getCurrentPosition(pos => pos.coords)", key="location")
    
    if loc:
        lat_gps, lon_gps = loc['latitude'], loc['longitude']
        st.success(f"LOCALIZADO: {lat_gps:.5f}, {lon_gps:.5f}")
    else:
        st.warning("⚠️ ESPERANDO GPS...")
        lat_gps, lon_gps = 19.1684, -104.6623 
    st.markdown('</div>', unsafe_allow_html=True)

    DATA_FILE = "field_app_data.csv" 
    
    try:
        df, spatial_tree = load_data_and_tree(DATA_FILE)
    except:
        st.error("ARCHIVO 'field_app_data.csv' NO DETECTADO. CARGALO A COLAB.")
        return

    if st.button("INICIAR ESCANEO DE CAMPO"):
        dist, idx = spatial_tree.query([lat_gps, lon_gps])
        data = df.iloc[idx]
        
        st.subheader("🛠️ CARACTERIZACIÓN DE SUELO")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("pH", f"{data['suelo_ph']:.1f}")
        c2.metric("SOC", f"{data['suelo_soc']:.1f}")
        c3.metric("ARCILLA", f"{data['suelo_arcilla_pct']:.1f}%")
        c4.metric("TWI", f"{data['topo_twi']:.1f}")
        
        st.subheader("📊 COMPARATIVA CLIMÁTICA (25 vs 26)")
        metrics = [
            ("LLUVIA", "rain_25", "rain_26", "mm", False),
            ("ESTRÉS (VPD)", "vpd_25", "vpd_26", "kPa", True),
            ("TEMP MÁX", "temp_25", "temp_26", "°C", True),
            ("VIGOR (NDVI)", "vigor_25", "vigor_26", "idx", False)
        ]

        for label, col_25, col_26, unit, inv in metrics:
            val_25, val_26 = data[col_25], data[col_26]
            st.metric(label=f"{label} (vs 2025)", value=f"{val_26:.2f} {unit}", 
                      delta=f"{val_26-val_25:.2f}", delta_color="inverse" if inv else "normal")

if __name__ == "__main__":
    main()
