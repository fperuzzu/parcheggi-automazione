import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
import folium
import requests
from streamlit_folium import folium_static
from datetime import datetime, timedelta

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="PeruLabTech | Bologna Smart Map", layout="wide")

LOGO_URL = "https://raw.githubusercontent.com/fperuzzu/parcheggi-automazione/main/logo.png"
DB_NAME = "storico_parcheggi.db"
GIORNI_ITA = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]

# Coordinate precise dei parcheggi di Bologna
COORDINATE = {
    "Piazza VIII Agosto": [44.5011, 11.3438],
    "Riva Reno": [44.4981, 11.3353],
    "Autostazione": [44.5049, 11.3456],
    "Staveco": [44.4842, 11.3429],
    "Parcheggio Aeroporto": [44.5308, 11.2912],
    "Tanari": [44.5056, 11.3268],
    "Prati di Caprara": [44.5028, 11.3121],
    "Antistadio": [44.4925, 11.3089]
}

if 'data_attiva' not in st.session_state:
    st.session_state.data_attiva = datetime.now().date()

def sposta_giorno(delta):
    st.session_state.data_attiva += timedelta(days=delta)

# --- CSS CUSTOM (EFFETTO WOW) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Inter:wght@300;400;700&display=swap');
    .stApp { background: #0d1117; color: #e6edf3; }
    .block-container { padding-top: 5rem !important; }
    .hero-title { font-family: 'Orbitron', sans-serif; background: linear-gradient(90deg, #00d2ff, #3a7bd5); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; font-size: 2.2rem; font-weight: 700; margin-bottom: 0px; }
    .hero-sub { text-align: center; color: #8b949e; font-size: 0.7rem; letter-spacing: 2px; margin-bottom: 30px; text-transform: uppercase; }
    .parking-card { background: rgba(22, 27, 34, 0.7); border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-bottom: 10px; }
    .nav-box { text-align: center; background: rgba(255,255,255,0.03); padding: 8px; border-radius: 12px; border: 1px solid #30363d; }
    .live-dot { color: #00ff88; font-weight: bold; font-size: 0.8rem; animation: blinker 2s linear infinite; }
    @keyframes blinker { 50% { opacity: 0.3; } }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI DATI ---
def fetch_bologna_live():
    live_results = []
    try:
        url = "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=50"
        r = requests.get(url, timeout=10).json()
        for rec in r.get('results', []):
            live_results.append({
                'citta': 'Bologna', 'nome': rec.get('parcheggio'), 
                'liberi': int(rec.get('posti_liberi', 0)), 'totali': int(rec.get('posti_totali', 0)), 
                'timestamp': datetime.now()
            })
    except: pass
    return pd.DataFrame(live_results)

def load_history(date_obj):
    try:
        conn = sqlite3.connect(DB_NAME)
        query = f"SELECT * FROM storico WHERE citta = 'Bologna' AND timestamp LIKE '{date_obj.strftime('%Y-%m-%d')}%'"
        df = pd.read_sql_query(query, conn)
        conn.close()
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['totali'] = pd.to_numeric(df['totali']).fillna(0).astype(int)
            df['liberi'] = pd.to_numeric(df['liberi']).fillna(0).astype(int)
        return df
    except: return pd.DataFrame()

# --- INTERFACCIA ---
st.sidebar.image(LOGO_URL, use_container_width=True)
st.markdown("<div class='hero-title'>PERULABTECH</div>", unsafe_allow_html=True)
st.markdown("<div class='hero-sub'>Bologna Smart Parking Control</div>", unsafe_allow_html=True)

df_live = fetch_bologna_live()
df_hist = load_history(st.session_state.data_attiva)

if not df_live.empty:
    # 1. SCHEDE LIVE
    st.markdown("<div class='live-dot'>● LIVE DATA</div>", unsafe_allow_html=True)
    grid = st.columns(3)
    for i, row in enumerate(df_live.itertuples()):
        with grid[i % 3]:
            tot = row.totali if row.totali > 0 else (row.liberi + 50)
            perc_occ = (tot - row.liberi) / tot
            color = "#3fb950" if (row.liberi/tot) > 0.3 else "#d29922" if (row.liberi/tot) > 0.1 else "#f85149"
            st.markdown(f"<div class='parking-card'><small>{row.nome}</small><br><span style='font-size:1.8rem; font-weight:800; color:{color};'>{row.liberi}</span> <small>/ {tot} tot</small></div>", unsafe_allow_html=True)
            st.progress(min(max(perc_occ, 0.0), 1.0))

    # 2. MAPPA CON NUMERI (EFFETTO WOW)
    st.markdown("<br><div style='color:#8b949e; font-size:0.75rem; font-weight:600;'>POSIZIONE E NAVIGAZIONE</div>", unsafe_allow_html=True)
    m = folium.Map(location=[44.494, 11.342], zoom_start=14, tiles="cartodbpositron")
    
    for row in df_live.itertuples():
        coords = COORDINATE.get(row.nome, [44.49, 11.34])
        lib = row.liberi
        tot = row.totali if row.totali > 0 else (lib + 50)
        bg = "#3fb950" if (lib/tot) > 0.3 else "#d29922" if (lib/tot) > 0.1 else "#f85149"
        
        # Icona circolare con numero posti liberi
        icon_html = f'<div style="background:{bg}; border:2px solid white; border-radius:50%; color:white; font-weight:bold; font-size:13px; display:flex; align-items:center; justify-content:center; width:34px; height:34px; box-shadow:0 2px 5px rgba(0,0,0,0.4);">{lib}</div>'
        
        popup_html = f"<div style='font-family:sans-serif; width:150px; color:black;'><b>{row.nome}</b><br>Posti: {lib}/{tot}<br><a href='https://www.google.com/maps/dir/?api=1&destination={coords[0]},{coords[1]}' target='_blank' style='display:block; background:#238636; color:white; text-align:center; padding:8px; border-radius:5px; text-decoration:none; margin-top:8px; font-weight:bold;'>PORTAMI QUI</a></div>"
        
        folium.Marker(location=coords, popup=folium.Popup(popup_html, max_width=200), icon=folium.DivIcon(html=icon_html)).add_to(m)
    
    folium_static(m, width=1200, height=400)

    # 3. NAVIGAZIONE GIORNI (SOPRA IL GRAFICO)
    st.markdown("<br>", unsafe_allow_html=True)
    n1, n2, n3 = st.columns([1, 2, 1])
    with n1: 
        if st.button("◀ Ieri", use_container_width=True): sposta_giorno(-1)
    with n2:
        d = st.session_state.data_attiva
        st.markdown(
