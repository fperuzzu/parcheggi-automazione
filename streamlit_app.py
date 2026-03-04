import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
import folium
import requests
from streamlit_folium import folium_static
from datetime import datetime, timedelta

# --- CONFIGURAZIONE PREMIUM ---
st.set_page_config(page_title="PeruLabTech Control", layout="wide", initial_sidebar_state="collapsed")

LOGO_URL = "https://raw.githubusercontent.com/fperuzzu/parcheggi-automazione/main/logo.png"
DB_NAME = "storico_parcheggi.db"
GIORNI_ITA = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]

COORDINATE = {
    "Piazza VIII Agosto": [44.5011, 11.3438], "Riva Reno": [44.4981, 11.3353],
    "Autostazione": [44.5049, 11.3456], "Staveco": [44.4842, 11.3429],
    "Parcheggio Aeroporto": [44.5308, 11.2912], "Tanari": [44.5056, 11.3268]
}

# --- CSS HACKING (TESLA STYLE) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    
    /* Reset Streamlit */
    .stApp { background-color: #050505; color: #ffffff; font-family: 'Inter', sans-serif; }
    .block-container { padding-top: 2rem !important; max-width: 1200px; }
    [data-testid="stHeader"] { background: rgba(0,0,0,0); }
    
    /* Header Minimal */
    .brand-box { display: flex; align-items: center; gap: 10px; margin-bottom: 20px; }
    .kpi-main { font-size: 2.5rem; font-weight: 800; color: #ffffff; letter-spacing: -1px; line-height: 1; }
    .kpi-sub { font-size: 0.9rem; color: #888; font-weight: 400; }
    
    /* Glassmorphism Cards */
    .p-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px; padding: 20px; margin-bottom: 15px;
        transition: transform 0.2s ease;
    }
    .p-name { font-size: 0.85rem; font-weight: 600; color: #888; text-transform: uppercase; letter-spacing: 1px; }
    .p-stat { font-size: 1.8rem; font-weight: 700; margin: 5px 0; }
    .p-perc { font-size: 0.8rem; font-weight: 500; }
    
    /* Custom Progress Bar */
    .stProgress > div > div > div > div { background-color: #222; border-radius: 10px; }
    
    /* Pills Navigation */
    .stButton > button {
        background: #111; border: 1px solid #222; color: #eee;
        border-radius: 50px; padding: 0.5rem 1.5rem; font-weight: 600;
        transition: all 0.3s;
    }
    .stButton > button:hover { border-color: #00d2ff; color: #00d2ff; background: #00d2ff1a; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGICA DATI ---
def fetch_data_live():
    try:
        url = "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=20"
        r = requests.get(url, timeout=10).json()
        data = []
        for rec in r.get('results', []):
            data.append({
                'nome': rec.get('parcheggio'),
                'liberi': int(rec.get('posti_liberi', 0)),
                'totali': int(rec.get('posti_totali', 0)),
                'timestamp': datetime.now()
            })
        return pd.DataFrame(data)
    except: return pd.DataFrame()

# --- UI RENDER ---

# 1. HEADER (Brand ridotto + KPI)
col_logo, col_kpi = st.columns([1, 4])
with col_logo:
    st.image(LOGO_URL, width=120)

df_live = fetch_data_live()
if not df_live.empty:
    posti_tot_liberi = df_live['liberi'].sum()
    with col_kpi:
        st.markdown(f"""
            <div style="text-align: right;">
                <div class="kpi-main">{posti_tot_liberi}</div>
                <div class="kpi-sub">Posti liberi ora in città • <span style="color:#00ff88;">Sistema Operativo</span></div>
            </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# 2. CARDS (Tesla Style)
if not df_live.empty:
    cols = st.columns(3)
    for idx, row in enumerate(df_live.itertuples()):
        with cols[idx % 3]:
            tot = row.totali if row.totali > 0 else (row.liberi + 100)
            occ_perc = int(((tot - row.liberi) / tot) * 100)
            
            # Colore semantico basato su % occupazione
            status_color = "#00ff88" if occ_perc < 60 else "#ffcc00" if occ_perc < 85 else "#ff4b4b"
            
            st.markdown(f"""
                <div class="p-card">
                    <div class="p-name">{row.nome}</div>
                    <div class="p-stat" style="color:{status_color};">{row.liberi}</div>
                    <div class="p-perc" style="color:#666;">Occupato al {occ_perc}%</div>
                </div>
            """, unsafe_allow_html=True)
            st.progress(occ_perc / 100)

# 3. MAPPA (Dark Matter Style)
st.markdown("<br>", unsafe_allow_html=True)
m = folium.Map(location=[44.495, 11.343], zoom_start=14, tiles="cartodbdark_matter")
for row in df_live.itertuples():
    coords = COORDINATE.get(row.nome, [44.49, 11.34])
    occ_perc = int(((row.totali - row.liberi) / (row.totali or 100)) * 100)
    bg = "#00ff88" if occ_perc < 60 else "#ff4b4b"
    
    icon_html = f'<div style="background:{bg}; border:2px solid white; border-radius:50%; width:30px; height:30px; display:flex; align-items:center; justify-content:center; color:black; font-weight:bold; font-size:11px;">{row.liberi}</div>'
    folium.Marker(location=coords, icon=folium.DivIcon(html=icon_html)).add_to(m)

folium_static(m, width=1200, height=450)

# 4. TREND (Insight Storytelling)
st.markdown("### Trend & Insight")
# Gestione navigazione giorni
if 'data_attiva' not in st.session_state: st.session_state.data_attiva = datetime.now().date()
c_nav1, c_nav2, c_nav3 = st.columns([1,2,1])
with c_nav1: 
    if st.button("◀ IERI"): st.session_state.data_attiva -= timedelta(days=1); st.rerun()
with c_nav2:
    st.markdown(f"<div class='nav-box'><b>{GIORNI_ITA[st.session_state.data_attiva.weekday()].upper()}</b><br>{st.session_state.data_attiva}</div>", unsafe_allow_html=True)
with c_nav3:
    if st.button("DOMANI ▶"): st.session_state.data_attiva += timedelta(days=1); st.rerun()

# Grafico pulito (Una città, Insight intelligenti)
# [Qui carichiamo lo storico dal DB per brevità assumo df_hist caricato]
try:
    conn = sqlite3.connect(DB_NAME)
    df_h = pd.read_sql_query(f"SELECT * FROM storico WHERE timestamp LIKE '{st.session_state.data_attiva}%'", conn)
    conn.close()
    
    if not df_h.empty:
        df_h['timestamp'] = pd.to_datetime(df_h['timestamp'])
        fig = go.Figure()
        # Visualizziamo solo la media o il parcheggio principale per non fare confusione
        for p_nome in df_h['nome'].unique()[:3]: # Solo i primi 3 per chiarezza
            p_data = df_h[df_h['nome'] == p_nome]
            fig.add_trace(go.Scatter(x=p_data['timestamp'], y=p_data['liberi'], name=p_nome, line=dict(width=3, shape='spline')))
            
            # Insight: Massimo e Minimo
            max_p = p_data.loc[p_data['liberi'].idxmax()]
            fig.add_annotation(x=max_p['timestamp'], y=max_p['liberi'], text="Massima disp.", showarrow=True, arrowhead=1)

        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=0,b=0), font=dict(color="#888"))
        st.plotly_chart(fig, use_container_width=True)
except:
    st.info("Caricamento dati storici...")

