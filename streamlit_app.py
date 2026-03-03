import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
import folium
from streamlit_folium import folium_static
from datetime import datetime, timedelta

# --- CONFIGURAZIONE E COSTANTI ---
st.set_page_config(page_title="PeruLabTech | Smart City", layout="wide")

# Definiamo il logo subito per evitare NameError
LOGO_URL = "https://raw.githubusercontent.com/fperuzzu/parcheggi-automazione/main/logo.png"
DB_NAME = "storico_parcheggi.db"
GIORNI = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]

# --- GESTIONE STATO DATA (NAVIGAZIONE) ---
if 'data_attiva' not in st.session_state:
    st.session_state.data_attiva = datetime.now().date()

def cambia_giorno(delta):
    st.session_state.data_attiva += timedelta(days=delta)

# --- CSS CUSTOM (EFFETTO WOW & MOBILE FIX) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Inter:wght@400;700&display=swap');
    
    .stApp { background: #0d1117; color: #e6edf3; }
    
    /* Rimuove lo spazio bianco in alto su mobile */
    .block-container { padding-top: 1rem !important; }

    /* Titolo Cyberpunk */
    .hero-title {
        font-family: 'Orbitron', sans-serif;
        background: linear-gradient(90deg, #00d2ff, #3a7bd5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 5px;
        letter-spacing: 3px;
    }
    
    .hero-sub {
        text-align: center;
        font-family: 'Inter', sans-serif;
        color: #8b949e;
        font-size: 0.8rem;
        letter-spacing: 2px;
        margin-bottom: 20px;
    }

    /* Card Satinate */
    .parking-card {
        background: rgba(22, 27, 34, 0.8);
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 10px;
    }
    
    /* Navigatore Giorni */
    .date-nav {
        display: flex;
        justify-content: center;
        align-items: center;
        background: #161b22;
        padding: 10px;
        border-radius: 50px;
        border: 1px solid #30363d;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI DATI ---
def get_data(selected_date):
    try:
        conn = sqlite3.connect(DB_NAME)
        date_str = selected_date.strftime('%Y-%m-%d')
        df = pd.read_sql_query(f"SELECT * FROM storico WHERE timestamp LIKE '{date_str}%'", conn)
        conn.close()
        if not df.empty: df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except: return pd.DataFrame()

# --- SIDEBAR ---
st.sidebar.image(LOGO_URL, use_container_width=True)
st.sidebar.markdown("---")
st.sidebar.write("⚡ **PeruLabTech** Smart Systems")

# --- LAYOUT PRINCIPALE ---
st.markdown("<div class='hero-title'>PERULABTECH</div>", unsafe_allow_html=True)
st.markdown("<div class='hero-sub'>SMART CITY CONTROL CENTER</div>", unsafe_allow_html=True)

# Navigazione Giorno
c1, c2, c3 = st.columns([1, 2, 1])
with c1: 
    if st.button("◀ Giorno Prec."): cambia_giorno(-1)
with c2:
    g_nome = GIORNI[st.session_state.data_attiva.weekday()]
    st.markdown(f"<div style='text-align:center;'><b style='color:#00d2ff; font-size:1.2rem;'>{g_nome.upper()}</b><br><small>{st.session_state.data_attiva.strftime('%d %m %Y')}</small></div>", unsafe_allow_html=True)
with c3:
    if st.button("Giorno Succ. ▶"): cambia_giorno(1)

df = get_data(st.session_state.data_attiva)

if not df.empty:
    citta_list = sorted(df['citta'].unique())
    sel_citta = st.sidebar.multiselect("Filtra Città", citta_list, default=citta_list)
    df_f = df[df['citta'].isin(sel_citta)]

    # --- SCHEDE REAL TIME (BICCHIERE MEZZO PIENO) ---
    ultimi = df_f.sort_values('timestamp').groupby(['citta', 'nome']).last().reset_index()
    
    st.markdown("<br><div style='color:#8b949e; font-size:0.8rem; font-weight:600; margin-bottom:10px;'>LIVE CAPACITY</div>", unsafe_allow_html=True)
    cols = st.columns(3)
    
    for idx, row in enumerate(ultimi.itertuples()):
        with cols[idx % 3]:
            lib = row.liberi
            tot = row.totali if (hasattr(row, 'totali') and row.totali > 0) else (lib + 20)
            # Logica bicchiere: calcolo occupazione per la barra
            perc_occ = (tot - lib) / tot if tot > 0 else 0
            color = "#3fb950" if (lib/tot) > 0.4 else "#d29922" if (lib/tot) > 0.15 else "#f85149"
            
            st.markdown(f"""
                <div class="parking-card">
                    <div style="color:#8b949e; font-size:0.7rem;">{row.citta}</div>
                    <div style="color:#fff; font-weight:700; font-size:1.1rem;">{row.nome}</div>
                    <div style="display:flex; justify-content:space-between; align-items:baseline; margin-top:10px;">
                        <span style="font-size:1.8rem; font-weight:800; color:{color};">{lib}</span>
                        <span style="color:#8b949e; font-size:0.8rem;">liberi su {tot}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            st.progress(min(max(perc_occ, 0.0), 1.0))

    # --- MAPPA SOTTO LE SCHEDE ---
    st.markdown("<br>", unsafe_allow_html=True)
    # Esempio centro su Bologna
    m = folium.Map(location=[44.494, 11.342], zoom_start=13, tiles="cartodbpositron")
    folium_static(m, width=1000, height=300)

    # --- GRAFICO TREND (SCALA FISSA & LEGENDA CHIARA) ---
    st.markdown("<br><div style='color:#8b949e; font-size:0.8rem; font-weight:600;'>OCCUPANCY TREND (24H)</div>", unsafe_allow_html=True)
    
    fig = go.Figure()
    # Troviamo il massimo valore per fissare l'asse Y
    max_y = df_f['totali'].max() if 'totali' in df_f.columns else df_f['liberi'].max()

    for n in df_f['nome'].unique():
        p = df_f[df_f['nome'] == n].sort_values('timestamp')
        fig.add_trace(go.Scatter(
            x=p['timestamp'], y=p['liberi'], name=n,
            mode='lines', line=dict(width=3, shape='spline'), fill='tozeroy'
        ))

    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=10, b=0), height=400,
        xaxis=dict(showgrid=False, color="#8b949e"),
        yaxis=dict(gridcolor='#30363d', color="#8b949e", range=[0, (max_y or 100) + 20], fixedrange=True),
        # LEGENDA CHIARA (BIANCA) SOTTO IL GRAFICO
        legend=dict(
            orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5,
            font=dict(color="#f0f6fc", size=10),
            bgcolor="rgba(0,0,0,0)"
        )
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

else:
    st.info(f"Nessun dato trovato per {GIORNI[st.session_state.data_attiva.weekday()]} {st.session_state.data_attiva.strftime('%d/%m/%Y')}")
