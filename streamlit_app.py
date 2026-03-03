import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
import folium
from streamlit_folium import folium_static
from datetime import datetime, timedelta

# Configurazione Pagina
st.set_page_config(page_title="PeruLabTech | Smart City", layout="wide")

# --- TRADUZIONE GIORNI ---
GIORNI = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]

# --- GESTIONE STATO DELLA DATA (NAVIGAZIONE FRECCE) ---
if 'data_attiva' not in st.session_state:
    st.session_state.data_attiva = datetime.now().date()

def cambia_giorno(delta):
    st.session_state.data_attiva += timedelta(days=delta)

# --- CSS EXPERT UI ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Inter:wght@300;600&display=swap');
    
    .stApp { background: #0d1117; color: #e6edf3; }
    .block-container { padding-top: 0rem !important; }

    /* Titolo Stilizzato */
    .main-title {
        font-family: 'Orbitron', sans-serif;
        background: linear-gradient(90deg, #00d2ff, #3a7bd5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.2rem;
        font-weight: 700;
        text-align: center;
        margin-top: 10px;
        letter-spacing: 2px;
    }
    .sub-title {
        font-family: 'Inter', sans-serif;
        text-align: center;
        color: #8b949e;
        font-size: 0.8rem;
        margin-bottom: 20px;
        text-transform: uppercase;
    }

    /* Navigatore Giorni */
    .nav-container {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 20px;
        margin-bottom: 30px;
        background: rgba(255,255,255,0.03);
        padding: 10px;
        border-radius: 50px;
        border: 1px solid rgba(255,255,255,0.1);
    }
    .day-display {
        text-align: center;
        min-width: 150px;
    }
    .day-name { color: #00d2ff; font-weight: 700; font-size: 1.1rem; }
    .day-date { color: #8b949e; font-size: 0.8rem; }

    /* Cards */
    .parking-card {
        background: #161b22; border: 1px solid #30363d;
        border-radius: 12px; padding: 18px; margin-bottom: 10px;
    }
    .parking-name { color: #f0f6fc; font-size: 1rem; font-weight: 700; }
    .stat-main { font-size: 1.6rem; font-weight: 800; }
    </style>
    """, unsafe_allow_html=True)

# --- CARICAMENTO DATI ---
def get_data(selected_date):
    try:
        conn = sqlite3.connect("storico_parcheggi.db")
        date_str = selected_date.strftime('%Y-%m-%d')
        df = pd.read_sql_query(f"SELECT * FROM storico WHERE timestamp LIKE '{date_str}%'", conn)
        conn.close()
        if not df.empty: df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except: return pd.DataFrame()

# --- HEADER STILIZZATO ---
st.markdown("<div class='main-title'>PERULABTECH</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>Smart City Parking Control Room</div>", unsafe_allow_html=True)

# --- NAVIGATORE A FRECCE ---
col_prev, col_day, col_next = st.columns([1, 2, 1])

with col_prev:
    st.markdown("<div style='text-align:right;'>", unsafe_allow_html=True)
    if st.button("◀ Prev"):
        cambia_giorno(-1)
    st.markdown("</div>", unsafe_allow_html=True)

with col_day:
    curr_date = st.session_state.data_attiva
    giorno_sett = GIORNI[curr_date.weekday()]
    st.markdown(f"""
        <div class="day-display">
            <div class="day-name">{giorno_sett.upper()}</div>
            <div class="day-date">{curr_date.strftime('%d %B %Y')}</div>
        </div>
    """, unsafe_allow_html=True)

with col_next:
    if st.button("Next ▶"):
        cambia_giorno(1)

# --- LOGICA DATI ---
df = get_data(st.session_state.data_attiva)

if not df.empty:
    citta_presenti = sorted(df['citta'].unique())
    sel_citta = st.sidebar.multiselect("Città", citta_presenti, default=citta_presenti)
    df_f = df[df['citta'].isin(sel_citta)]
    
    # 1. SCHEDE REAL TIME (BICCHIERE MEZZO PIENO)
    ultimi = df_f.sort_values('timestamp').groupby(['citta', 'nome']).last().reset_index()
    
    st.markdown("<br><div style='color:#8b949e; font-size:0.7rem; font-weight:600;'>LIVE STATUS</div>", unsafe_allow_html=True)
    cols = st.columns(3)
    for idx, row in enumerate(ultimi.itertuples()):
        with cols[idx % 3]:
            lib = row.liberi
            tot = row.totali if (hasattr(row, 'totali') and row.totali > 0) else (lib + 20)
            perc_occ = (tot - lib) / tot if tot > 0 else 0
            color = "#3fb950" if (lib/tot) > 0.4 else "#d29922" if (lib/tot) > 0.15 else "#f85149"
            
            st.markdown(f"""
                <div class="parking-card">
                    <div style="color:#8b949e; font-size:0.7rem; text-transform:uppercase;">{row.citta}</div>
                    <div class="parking-name">{row.nome}</div>
                    <div style="display: flex; justify-content: space-between; align-items: baseline;">
                        <span class="stat-main" style="color:{color};">{lib}</span>
                        <span style="color:#8b949e; font-size:0.8rem;">/ {tot} totali</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            st.progress(min(max(perc_occ, 0.0), 1.0))

    # 2. MAPPA
    st.markdown("<br><div style='color:#8b949e; font-size:0.7rem; font-weight:600;'>SPATIAL VIEW</div>", unsafe_allow_html=True)
    m = folium.Map(location=[44.494, 11.342], zoom_start=12, tiles="cartodbpositron")
    for row in ultimi.itertuples():
        # Qui potresti aggiungere un dizionario coordinate come visto prima
        folium.Marker(location=[44.49, 11.34], popup=f"{row.nome}: {row.liberi} liberi").add_to(m)
    folium_static(m, width=1000, height=300)

    # 3. GRAFICO TREND (SCALA FISSA E LEGENDA WOW)
    st.markdown("<br><div style='color:#8b949e; font-size:0.7rem; font-weight:600;'>24H OCCUPANCY TREND</div>", unsafe_allow_html=True)
    fig = go.Figure()
    max_val = df_f['totali'].max() if 'totali' in df_f.columns else df_f['liberi'].max()
    
    for n in df_f['nome'].unique():
        p = df_f[df_f['nome'] == n].sort_values('timestamp')
        fig.add_trace(go.Scatter(
            x=p['timestamp'], y=p['liberi'], name=n, 
            mode='lines', line=dict(width=3, shape='spline'), fill='tozeroy'
        ))

    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=10, b=0), height=350,
        xaxis=dict(showgrid=False, color="#8b949e"),
        yaxis=dict(gridcolor='#30363d', color="#8b949e", range=[0, (max_val or 100) + 20]),
        legend=dict(
            orientation="h", yanchor="top", y=-0.25, xanchor="center", x=0.5, 
            font=dict(color="#f0f6fc", size=10)
        )
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
else:
    st.warning(f"Nessun dato archiviato per {st.session_state.data_attiva.strftime('%d/%m/%Y')}")

st.sidebar.image(LOGO_URL, use_container_width=True)
