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
        
        /* Botones HUD */
        .stButton>button { 
            border: 1px solid #FF5F1F; background-color: #1A0F0A; color: #FF5F1F; 
            width: 100%; height: 60px; font-weight: bold; border-radius: 2px;
            letter-spacing: 2px; text-transform: uppercase;
        }
        .stButton>button:hover { background-color: #FF5F1F; color: #000; box-shadow: 0 0 20px #FF5F1F; }

        /* Contenedores de Telemetría */
        .header-box { border: 1px solid #333; padding: 20px; text-align: center; background: #050505; margin-bottom: 20px; }
        .telemetry-card { 
            background: #0A0A0A; border: 1px solid #222; padding: 15px; 
            margin-bottom: 10px; font-size: 0.9rem;
        }
        .label-orange { color: #FF5F1F; font-weight: bold; text-transform: uppercase; font-size: 0.75rem; }
        
        /* Métricas */
        [data-testid="stMetricValue"] { color: #FF5F1F !important; font-size: 1.7rem !important; }
        [data-testid="stMetricLabel"] { color: #888 !important; }
        h3 { color: #FF5F1F !important; border-bottom: 1px solid #333; padding-bottom: 10px; letter-spacing: 2px; }
        </style>
    """, unsafe_allow_html=True)

# --- HELPERS TÉCNICOS ---
def decimal_to_dms(deg, is_lat=True):
    direction = ("N" if deg >= 0 else "S") if is_lat else ("E" if deg >= 0 else "W")
    deg = abs(deg)
    d = int(deg)
    m = int((deg - d) * 60)
    s = round((deg - d - m/60) * 3600, 2)
    return f"{direction} {d}°{m:02d}'{s:05.2f}\""

@st.cache_resource
def load_spatial_engine(file_path):
    df = pd.read_parquet(file_path)
    # Limpieza: Asegurar que lat/lon sean numéricos y no nulos
    df = df.dropna(subset=['lat_suelo', 'lon_suelo'])
    tree = KDTree(df[['lat_suelo', 'lon_suelo']].values)
    return df, tree

def main():
    apply_navigator_style()
    
    # --- HEADER ---
    st.markdown('<div class="header-box">', unsafe_allow_html=True)
    st.markdown("<h1 style='margin:0; color:#FF5F1F; letter-spacing:5px;'>MISSION NAVIGATOR</h1>", unsafe_allow_html=True)
    st.markdown("<span style='color:#888;'>SISTEMA DE MONITOREO GEORREFERENCIADO</span>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # --- LÓGICA DE GPS ROBUSTO ---
    # Intentamos obtener ubicación (Auto + Botón Manual)
    st.write("")
    if st.button("🔄 SINCRONIZAR SENSOR SATELITAL"):
        # Forzamos High Accuracy con un timeout largo de 15 segundos
        loc = streamlit_js_eval(
            js_expressions="navigator.geolocation.getCurrentPosition(pos => pos.coords, err => console.log(err), {enableHighAccuracy:true, timeout:15000, maximumAge:0})", 
            key="gps_manual"
        )
    else:
        loc = streamlit_js_eval(
            js_expressions="navigator.geolocation.getCurrentPosition(pos => pos.coords, err => console.log(err), {enableHighAccuracy:true, timeout:5000, maximumAge:0})", 
            key="gps_auto"
        )

    # Coordenadas de respaldo (GDL) si el GPS falla
    lat_now, lon_now, acc_now = 20.6825, -103.3830, 0

    if loc:
        lat_now = loc['latitude']
        lon_now = loc['longitude']
        acc_now = loc['accuracy']
        st.success(f"✅ CONEXIÓN SATELITAL ACTIVA (Precisión: ±{acc_now:.1f}m)")
    else:
        st.warning("⚠️ SENSOR GPS INACTIVO / BUSCANDO SEÑAL...")

    # --- PANEL DE TELEMETRÍA (Estética de la foto) ---
    st.markdown(f"""
        <div class="telemetry-card">
            <table style="width:100%; border-collapse: collapse;">
                <tr>
                    <td style="color:#888;">Latitud</td>
                    <td style="text-align:right; font-family:monospace;">{decimal_to_dms(lat_now, True)}</td>
                </tr>
                <tr>
                    <td style="color:#888;">Longitud</td>
                    <td style="text-align:right; font-family:monospace;">{decimal_to_dms(lon_now, False)}</td>
                </tr>
                <tr>
                    <td style="color:#888;">Altitud</td>
                    <td style="text-align:right; font-family:monospace;">1543m</td>
                </tr>
            </table>
        </div>
    """, unsafe_allow_html=True)

    # --- CARGA DE DATOS ---
    DATA_FILE = "field_app_data.parquet"
    try:
        df, tree = load_spatial_engine(DATA_FILE)
    except Exception as e:
        st.error(f"DATABASE OFFLINE: {e}")
        return

    # --- ACCIÓN DE ESCANEO ---
    st.write("")
    if st.button("🚀 EJECUTAR ESCANEO DE CAMPO"):
        with st.spinner("SINCRO-MALLA EN CURSO..."):
            # Búsqueda KD-Tree [Lat, Lon]
            dist, idx = tree.query(np.array([lat_now, lon_now]))
            data = df.iloc[idx]
            
            # --- RESULTADOS: SUELO ---
            st.subheader("🛠️ Caracterización de Suelo")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("pH", f"{data['suelo_ph']:.1f}")
            c2.metric("SOC", f"{data['suelo_soc']:.1f}")
            c3.metric("ARCILLA", f"{data['suelo_arcilla_pct']:.1f}%")
            c4.metric("TWI", f"{data['topo_twi']:.1f}")

            # --- RESULTADOS: CLIMA JULIO ---
            st.write("")
            st.subheader("📊 Salud Climática: JULIO")
            
            clima_cols = [
                ("LLUVIA", "rain_25", "rain_26", "mm", False),
                ("ESTRÉS (VPD)", "vpd_25", "vpd_26", "kPa", True),
                ("TEMP MÁX", "temp_25", "temp_26", "°C", True),
                ("VIGOR (NDVI)", "vigor_25", "vigor_26", "idx", False)
            ]

            for label, col25, col26, unit, inv in clima_cols:
                val25, val26 = data[col25], data[col26]
                diff = val26 - val25
                st.metric(
                    label=f"{label} (JULIO '26 vs '25)", 
                    value=f"{val26:.2f} {unit}", 
                    delta=f"{diff:.2f} {unit}",
                    delta_color="inverse" if inv else "normal"
                )
                st.markdown("---")
            
            # Info de proximidad para confianza del usuario
            st.caption(f"Nodo de datos más cercano a {dist*111.1:.2f} km de tu posición.")

    # --- FOOTER ---
    st.sidebar.markdown("### SYSTEM LOG")
    st.sidebar.code(f"MODE: NAVIGATOR\nTARGET: JULIO_CORE\nGPS_STATUS: {'LOCK' if loc else 'WAIT'}")
    st.sidebar.markdown("---")
    st.sidebar.info("Utilice el botón de Sincronizar bajo cielo despejado para máxima precisión.")

if __name__ == "__main__":
    main()
