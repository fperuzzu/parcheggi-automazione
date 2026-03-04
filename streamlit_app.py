import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
import folium
import requests
from streamlit_folium import folium_static
from datetime import datetime, timedelta

# --- CONFIGURAZIONE PREMIUM ---
st.set_page_config(page_title="PeruLabTech | Control", layout="wide", initial_sidebar_state="collapsed")

# Logo ufficiale (Usa il tuo file se caricato su GitHub)
LOGO_URL = "https://raw.githubusercontent.com/fperuzzu/parcheggi-automazione/main/logo.png"
DB_NAME = "storico_parcheggi.db"
GIORNI_ITA = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]

COORDINATE = {
    "Piazza VIII Agosto": [44.5011, 11.3438], "Riva Reno": [44.4981, 11.3353],
    "Autostazione": [44.5049, 11.3456], "Staveco": [44.4842, 11.3429],
    "Parcheggio Aeroporto": [44.5308, 11.2912], "Tanari": [44.5056, 11.3268]
}

# --- CSS HACKING (CONSUMER LOOK) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Inter:wght@300;400;600;800&display=swap');
    
    .stApp { background-color: #050505; color: #ffffff; font-family: 'Inter', sans-serif; }
    .block-container { padding-top: 2rem !important; max-width: 1100px; }

    /* Header Identity */
    .header-container {
        display: flex; justify-content: space-between; align-items: center;
        padding: 20px; background: rgba(255,255,255,0.02);
        border-radius: 20px; border: 1px solid rgba(255,255,255,0.05);
        margin-bottom: 30px;
    }
    .logo-text { font-family: 'Orbitron', sans-serif; font-size: 1.4rem; color: #00d2ff; letter-spacing: 2px; }
    .global-kpi-box { text-align: right; }
    .global-number { font-size: 2.2rem; font-weight: 800; color: #fff; line-height: 1; }
    .global-label { font-size: 0.7rem; color: #00ff88; text-transform: uppercase; letter-spacing: 1px; }

    /* Custom Progress Bar (Alto Contrasto) */
    .progress-container {
        width: 100%; background-color: #1a1a1a; border-radius: 10px;
        height: 8px; margin-top: 10px; overflow: hidden;
    }
    .progress-fill { height: 100%; border-radius: 10px; transition: width 0.5s ease-in-out; }
    
    /* Card Style */
    .p-card {
        background: #0f0f0f; border: 1px solid #1a1a1a;
        border-radius: 18px; padding: 22px; margin-bottom: 15px;
    }
    .p-name { font-size: 0.8rem; font-weight: 600; color: #555; text-transform: uppercase; }
    .p-stat { font-size: 2.2rem; font-weight: 800; margin: 2px 0; }
    .p-perc { font-size: 0.75rem; font-weight: 400; color: #888; }
    </style>
    """, unsafe_allow_html=True)

def fetch_data_live():
    try:
        url = "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=20"
        r = requests.get(url, timeout=10).json()
        return pd.DataFrame([{'nome': rec.get('parcheggio'), 'liberi': int(rec.get('posti_liberi', 0)), 'totali': int(rec.get('posti_totali', 0)), 'timestamp': datetime.now()} for rec in r.get('results', [])])
    except: return pd.DataFrame()

# --- HEADER RENDER ---
df_live = fetch_data_live()
posti_tot = df_live['liberi'].sum() if not df_live.empty else 0

st.markdown(f"""
    <div class="header-container">
        <div style="display: flex; align-items: center; gap: 15px;">
            <img src="{LOGO_URL}" width="50">
            <div class="logo-text">PERULABTECH</div>
        </div>
        <div class="global-kpi-box">
            <div class="global-label">Disponibilità Totale</div>
            <div class="global-number">{posti_tot}</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- CARDS RENDER ---
if not df_live.empty:
    cols = st.columns(3)
    for idx, row in enumerate(df_live.itertuples()):
        with cols[idx % 3]:
            tot = row.totali if row.totali > 0 else (row.liberi + 100)
            occ_perc = int(((tot - row.liberi) / tot) * 100)
            # Logica colori semantici ad alto contrasto
            color = "#00ff88" if occ_perc < 60 else "#ffcc00" if occ_perc < 85 else "#ff3333"
            
            st.markdown(f"""
                <div class="p-card">
                    <div class="p-name">{row.nome}</div>
                    <div class="p-stat" style="color:{color};">{row.liberi}</div>
                    <div style="display:flex; justify-content:space-between;">
                        <span class="p-perc">Occupato: {occ_perc}%</span>
                        <span class="p-perc">Tot: {tot}</span>
                    </div>
                    <div class="progress-container">
                        <div class="progress-fill" style="width: {occ_perc}%; background-color: {color}; box-shadow: 0 0 10px {color}66;"></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

# --- MAPPA DARK ---
st.markdown("<br>", unsafe_allow_html=True)
m = folium.Map(location=[44.495, 11.343], zoom_start=14, tiles="cartodbdark_matter")
for row in df_live.itertuples():
    coords = COORDINATE.get(row.nome, [44.49, 11.34])
    occ = int(((row.totali - row.liberi) / (row.totali or 100)) * 100)
    c = "#00ff88" if occ < 60 else "#ff3333"
    icon = f'<div style="background:{c}; border:2px solid #fff; border-radius:50%; width:32px; height:32px; display:flex; align-items:center; justify-content:center; color:#000; font-weight:800; font-size:12px; box-shadow: 0 0 15px {c};">{row.liberi}</div>'
    folium.Marker(location=coords, icon=folium.DivIcon(html=icon)).add_to(m)
folium_static(m, width=1100, height=400)

# --- TREND ---
st.markdown("<br>### Trend Storico Analitico", unsafe_allow_html=True)
if 'data_att' not in st.session_state: st.session_state.data_att = datetime.now().date()
c1, c2, c3 = st.columns([1,2,1])
with c1: 
    if st.button("◀ IERI"): st.session_state.data_att -= timedelta(days=1); st.rerun()
with c2:
    st.markdown(f"<div style='text-align:center; background:#111; padding:10px; border-radius:10px;'>{GIORNI_ITA[st.session_state.data_att.weekday()]} {st.session_state.data_att}</div>", unsafe_allow_html=True)
with c3:
    if st.button("DOMANI ▶"): st.session_state.data_att += timedelta(days=1); st.rerun()

# Grafico pulito spline
try:
    conn = sqlite3.connect(DB_NAME)
    df_h = pd.read_sql_query(f"SELECT * FROM storico WHERE timestamp LIKE '{st.session_state.data_att}%'", conn)
    conn.close()
    if not df_h.empty:
        df_h['timestamp'] = pd.to_datetime(df_h['timestamp'])
        fig = go.Figure()
        for p in df_h['nome'].unique()[:3]:
            d = df_h[df_h['nome'] == p]
            fig.add_trace(go.Scatter(x=d['timestamp'], y=d['liberi'], name=p, line=dict(width=4, shape='spline')))
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="#555"), margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)
except: st.info("Dati storici in aggiornamento...")
