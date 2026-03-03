import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
import folium
from streamlit_folium import folium_static
from datetime import datetime, timedelta

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="PeruLabTech | Smart City", layout="wide")

# Costanti
LOGO_URL = "https://raw.githubusercontent.com/fperuzzu/parcheggi-automazione/main/logo.png"
DB_NAME = "storico_parcheggi.db"
GIORNI_ITA = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]

# --- DATABASE COORDINATE ---
COORDINATE = {
    "Piazza VIII Agosto": [44.500, 11.344],
    "Riva Reno": [44.498, 11.336],
    "Autostazione": [44.505, 11.345],
    "Bolzano": [45.074, 7.666],
    "Vittorio Veneto": [45.063, 7.689],
    "Fortezza Fiera": [43.782, 11.248],
    "Stazione Binario 16": [43.785, 11.245],
    "Parcheggio Aeroporto": [44.530, 11.290]
}

# --- NAVIGAZIONE GIORNI (Session State) ---
if 'data_attiva' not in st.session_state:
    st.session_state.data_attiva = datetime.now().date()

def sposta_giorno(delta):
    st.session_state.data_attiva += timedelta(days=delta)

# --- CSS CUSTOM (EFFETTO WOW & MOBILE) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Inter:wght@300;400;700&display=swap');
    
    .stApp { background: #0d1117; color: #e6edf3; }
    .block-container { padding-top: 0.5rem !important; }

    /* Titolo Futuristico */
    .hero-title {
        font-family: 'Orbitron', sans-serif;
        background: linear-gradient(90deg, #00d2ff, #3a7bd5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0px;
        letter-spacing: 2px;
    }
    .hero-sub {
        text-align: center; font-family: 'Inter', sans-serif;
        color: #8b949e; font-size: 0.7rem; letter-spacing: 2px;
        margin-bottom: 20px; text-transform: uppercase;
    }

    /* Card Stile Tech */
    .parking-card {
        background: rgba(22, 27, 34, 0.7);
        border: 1px solid #30363d;
        border-radius: 12px; padding: 16px; margin-bottom: 10px;
    }
    .parking-name { color: #f0f6fc; font-size: 1.05rem; font-weight: 700; }
    .stat-val { font-size: 1.8rem; font-weight: 800; }
    
    /* Navigatore sopra il grafico */
    .nav-box {
        text-align: center; background: rgba(255,255,255,0.03);
        padding: 8px; border-radius: 12px; border: 1px solid #30363d;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CARICAMENTO E PULIZIA DATI ---
def load_clean_data(date_obj):
    try:
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query(f"SELECT * FROM storico WHERE timestamp LIKE '{date_obj.strftime('%Y-%m-%d')}%'", conn)
        conn.close()
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['totali'] = pd.to_numeric(df['totali'], errors='coerce').fillna(0).astype(int)
            df['liberi'] = pd.to_numeric(df['liberi'], errors='coerce').fillna(0).astype(int)
        return df
    except: return pd.DataFrame()

# --- HEADER ---
st.markdown("<div class='hero-title'>PERULABTECH</div>", unsafe_allow_html=True)
st.markdown("<div class='hero-sub'>Smart City Control Room</div>", unsafe_allow_html=True)

# Sidebar
st.sidebar.image(LOGO_URL, use_container_width=True)
st.sidebar.markdown("---")

df = load_clean_data(st.session_state.data_attiva)

if not df.empty:
    citta_sel = st.sidebar.multiselect("Città", sorted(df['citta'].unique()), default=list(df['citta'].unique()))
    df_f = df[df['citta'].isin(citta_sel)]
    
    # --- 1. LIVE CARDS ---
    ultimi = df_f.sort_values('timestamp').groupby(['citta', 'nome']).last().reset_index()
    st.markdown("<div style='color:#8b949e; font-size:0.75rem; font-weight:600; letter-spacing:1px; margin-bottom:10px;'>LIVE STATUS</div>", unsafe_allow_html=True)
    
    grid = st.columns(3)
    for i, row in enumerate(ultimi.itertuples()):
        with grid[i % 3]:
            lib = row.liberi
            tot = row.totali if row.totali > 0 else (lib + 20)
            perc_occ = min(max((tot - lib) / tot, 0.0), 1.0)
            color = "#3fb950" if (lib/tot) > 0.4 else "#d29922" if (lib/tot) > 0.15 else "#f85149"
            
            st.markdown(f"""
                <div class="parking-card">
                    <div style="color:#8b949e; font-size:0.65rem; text-transform:uppercase;">{row.citta}</div>
                    <div class="parking-name">{row.nome}</div>
                    <div style="display:flex; justify-content:space-between; align-items:baseline; margin-top:5px;">
                        <span class="stat-val" style="color:{color};">{lib}</span>
                        <span style="color:#8b949e; font-size:0.8rem;">/ {tot} totali</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            st.progress(perc_occ)

    # --- 2. MAPPA CON LINK RIPRISTINATI ---
    st.markdown("<br><div style='color:#8b949e; font-size:0.75rem; font-weight:600; letter-spacing:1px; margin-bottom:10px;'>GEOSPATIAL VIEW & NAV</div>", unsafe_allow_html=True)
    m = folium.Map(location=[44.494, 11.342], zoom_start=12, tiles="cartodbpositron")
    
    for row in ultimi.itertuples():
        coords = COORDINATE.get(row.nome, [44.49, 11.34])
        nav_url = f"https://www.google.com/maps/dir/?api=1&destination={coords[0]},{coords[1]}"
        
        # Popup HTML ripristinato
        popup_content = f"""
        <div style='font-family:sans-serif; width:160px; color:black;'>
            <b style='font-size:14px;'>{row.nome}</b><br>
            <span style='color:#666;'>Liberi: {row.liberi} / {row.totali}</span><br>
            <a href='{nav_url}' target='_blank' style='display:block; background:#238636; color:white; text-align:center; padding:8px; border-radius:5px; text-decoration:none; margin-top:8px; font-weight:bold;'>PORTAMI QUI</a>
        </div>
        """
        folium.Marker(
            location=coords, 
            popup=folium.Popup(popup_content, max_width=200),
            icon=folium.Icon(color='blue' if row.liberi > 10 else 'red', icon='car', prefix='fa')
        ).add_to(m)
    
    folium_static(m, width=1000, height=350)

    # --- 3. NAVIGATORE SPOSTATO SOPRA IL GRAFICO ---
    st.markdown("<br>", unsafe_allow_html=True)
    nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
    with nav_col1:
        if st.button("◀ Ieri", use_container_width=True): sposta_giorno(-1)
    with nav_col2:
        data_att = st.session_state.data_attiva
        st.markdown(f"""
            <div class='nav-box'>
                <div style='color:#00d2ff; font-weight:bold; font-size:1.1rem;'>{GIORNI_ITA[data_att.weekday()].upper()}</div>
                <div style='color:#8b949e; font-size:0.85rem;'>{data_att.strftime('%d %B %Y')}</div>
            </div>
        """, unsafe_allow_html=True)
    with nav_col3:
        if st.button("Domani ▶", use_container_width=True): sposta_giorno(1)

    # --- 4. GRAFICO TREND ---
    st.markdown("<div style='color:#8b949e; font-size:0.75rem; font-weight:600; letter-spacing:1px; margin-top:10px;'>DAILY OCCUPANCY TREND</div>", unsafe_allow_html=True)
    
    fig = go.Figure()
    max_y = df_f['totali'].max() if df_f['totali'].max() > 0 else df_f['liberi'].max()
    
    for nome in df_f['nome'].unique():
        p_data = df_f[df_f['nome'] == nome].sort_values('timestamp')
        fig.add_trace(go.Scatter(
            x=p_data['timestamp'], y=p_data['liberi'], name=nome,
            mode='lines', line=dict(width=3, shape='spline'), fill='tozeroy'
        ))

    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=10, b=0), height=400,
        xaxis=dict(showgrid=False, color="#8b949e"),
        yaxis=dict(gridcolor='#30363d', color="#8b949e", range=[0, max_y + 15], fixedrange=True),
        legend=dict(
            orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5, 
            font=dict(color="#f0f6fc", size=10), bgcolor="rgba(0,0,0,0)"
        )
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

else:
    st.markdown("<br>", unsafe_allow_html=True)
    # Anche se non ci sono dati, permettiamo di navigare
    nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
    with nav_col1:
        if st.button("◀ Ieri", use_container_width=True): sposta_giorno(-1)
    with nav_col2:
        data_att = st.session_state.data_attiva
        st.markdown(f"<div class='nav-box'><div style='color:#00d2ff;'>{GIORNI_ITA[data_att.weekday()].upper()}</div><div>{data_att.strftime('%d %B %Y')}</div></div>", unsafe_allow_html=True)
    with nav_col3:
        if st.button("Domani ▶", use_container_width=True): sposta_giorno(1)
    st.warning(f"Nessun dato registrato per questa data.")
