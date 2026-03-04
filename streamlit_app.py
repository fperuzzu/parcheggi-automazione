import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
import folium
import requests
from streamlit_folium import folium_static
from datetime import datetime, timedelta

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="PeruLabTech | Bologna Smart Map", layout="wide")

# Costanti Globali
LOGO_URL = "https://raw.githubusercontent.com/fperuzzu/parcheggi-automazione/main/logo.png"
DB_NAME = "storico_parcheggi.db"
GIORNI_ITA = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]

# Mapping Coordinate Bologna
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

# --- GESTIONE NAVIGAZIONE DATA ---
if 'data_attiva' not in st.session_state:
    st.session_state.data_attiva = datetime.now().date()

def sposta_giorno(delta):
    st.session_state.data_attiva += timedelta(days=delta)

# --- CSS CUSTOM (EFFETTO WOW & MOBILE FIX) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Inter:wght@300;400;700&display=swap');
    
    .stApp { background: #0d1117; color: #e6edf3; }
    
    /* Padding superiore per evitare coperture su smartphone */
    .block-container { padding-top: 5.5rem !important; }

    .hero-title {
        font-family: 'Orbitron', sans-serif;
        background: linear-gradient(90deg, #00d2ff, #3a7bd5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center; font-size: 2.2rem; font-weight: 700;
        margin-bottom: 0px; letter-spacing: 2px;
    }
    
    .hero-sub {
        text-align: center; color: #8b949e; font-family: 'Inter', sans-serif;
        font-size: 0.7rem; letter-spacing: 2px; margin-bottom: 30px; text-transform: uppercase;
    }

    .parking-card {
        background: rgba(22, 27, 34, 0.7);
        border: 1px solid #30363d;
        border-radius: 12px; padding: 18px; margin-bottom: 10px;
    }
    
    .nav-box {
        text-align: center; background: rgba(255,255,255,0.03);
        padding: 10px; border-radius: 15px; border: 1px solid #30363d;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI DI RECUPERO DATI ---
def fetch_bologna_live():
    try:
        url = "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=50"
        r = requests.get(url, timeout=10).json()
        live_data = []
        for rec in r.get('results', []):
            live_data.append({
                'citta': 'Bologna',
                'nome': rec.get('parcheggio'),
                'liberi': int(rec.get('posti_liberi', 0)),
                'totali': int(rec.get('posti_totali', 0)),
                'timestamp': datetime.now()
            })
        return pd.DataFrame(live_data)
    except:
        return pd.DataFrame()

def load_history(date_obj):
    try:
        conn = sqlite3.connect(DB_NAME)
        query = f"SELECT * FROM storico WHERE citta = 'Bologna' AND timestamp LIKE '{date_obj.strftime('%Y-%m-%d')}%'"
        df = pd.read_sql_query(query, conn)
        conn.close()
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['totali'] = pd.to_numeric(df['totali'], errors='coerce').fillna(0).astype(int)
            df['liberi'] = pd.to_numeric(df['liberi'], errors='coerce').fillna(0).astype(int)
        return df
    except:
        return pd.DataFrame()

# --- COSTRUZIONE INTERFACCIA ---
st.sidebar.image(LOGO_URL, use_container_width=True)
st.sidebar.markdown("---")

st.markdown("<div class='hero-title'>PERULABTECH</div>", unsafe_allow_html=True)
st.markdown("<div class='hero-sub'>Bologna Smart Parking System</div>", unsafe_allow_html=True)

# Caricamento Dati (Live + Storico)
df_live = fetch_bologna_live()
df_hist = load_history(st.session_state.data_attiva)

if not df_live.empty:
    # 1. SCHEDE LIVE (Effetto Bicchiere Mezzo Pieno)
    st.markdown("<div style='color:#00ff88; font-weight:bold; font-size:0.8rem; margin-bottom:10px;'>● LIVE STATUS</div>", unsafe_allow_html=True)
    grid = st.columns(3)
    for idx, row in enumerate(df_live.itertuples()):
        with grid[idx % 3]:
            lib = row.liberi
            tot = row.totali if row.totali > 0 else (lib + 50)
            # Calcolo Occupazione per barra progresso
            perc_occ = min(max((tot - lib) / tot, 0.0), 1.0)
            # Colore numero basato su disponibilità
            ratio = lib / tot if tot > 0 else 0
            color_stat = "#3fb950" if ratio > 0.35 else "#d29922" if ratio > 0.12 else "#f85149"
            
            st.markdown(f"""
                <div class="parking-card">
                    <div style="color:#8b949e; font-size:0.7rem; text-transform:uppercase;">Bologna</div>
                    <div style="color:#fff; font-weight:700; font-size:1.05rem; margin-bottom:8px;">{row.nome}</div>
                    <div style="display:flex; justify-content:space-between; align-items:baseline;">
                        <span style="font-size:1.8rem; font-weight:800; color:{color_stat};">{lib}</span>
                        <span style="color:#8b949e; font-size:0.8rem;">/ {tot} totali</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            st.progress(perc_occ)

    # 2. MAPPA CON NUMERI IN TEMPO REALE
    st.markdown("<br><div style='color:#8b949e; font-size:0.75rem; font-weight:600;'>POSIZIONE E NAVIGAZIONE</div>", unsafe_allow_html=True)
    m = folium.Map(location=[44.495, 11.343], zoom_start=14, tiles="cartodbpositron")
    
    for row in df_live.itertuples():
        coords = COORDINATE.get(row.nome, [44.49, 11.34])
        lib = row.liberi
        tot = row.totali if row.totali > 0 else (lib + 50)
        # Colore cerchietto mappa
        ratio = lib / tot if tot > 0 else 0
        bg_m = "#3fb950" if ratio > 0.35 else "#d29922" if ratio > 0.12 else "#f85149"
        
        # Icona con numero
        icon_html = f'''<div style="background:{bg_m}; border:2px solid white; border-radius:50%; color:white; font-weight:bold; font-size:13px; display:flex; align-items:center; justify-content:center; width:34px; height:34px; box-shadow:0 2px 5px rgba(0,0,0,0.4);">{lib}</div>'''
        
        popup_html = f"""
        <div style='font-family:sans-serif; width:160px; color:black;'>
            <b style='font-size:14px;'>{row.nome}</b><br>
            Disponibili: {lib} / {tot}<br>
            <a href='http://maps.google.com/?q={coords[0]},{coords[1]}' target='_blank' style='display:block; background:#238636; color:white; text-align:center; padding:8px; border-radius:5px; text-decoration:none; margin-top:8px; font-weight:bold;'>PORTAMI QUI</a>
        </div>
        """
        folium.Marker(location=coords, popup=folium.Popup(popup_html, max_width=200), icon=folium.DivIcon(html=icon_html)).add_to(m)
    
    folium_static(m, width=1200, height=400)

    # 3. NAVIGAZIONE GIORNI (SOPRA IL GRAFICO)
    st.markdown("<br>", unsafe_allow_html=True)
    n1, n2, n3 = st.columns([1, 2, 1])
    with n1: 
        if st.button("◀ Ieri", use_container_width=True): sposta_giorno(-1)
    with n2:
        d_att = st.session_state.data_attiva
        st.markdown(f"<div class='nav-box'><b style='color:#00d2ff;'>{GIORNI_ITA[d_att.weekday()].upper()}</b><br><small>{d_att.strftime('%d %m %Y')}</small></div>", unsafe_allow_html=True)
    with n3: 
        if st.button("Domani ▶", use_container_width=True): sposta_giorno(1)

    # 4. GRAFICO TREND (LIVE + STORICO)
    st.markdown("<br><div style='color:#8b949e; font-size:0.75rem; font-weight:600;'>TREND GIORNALIERO (STORICO + LIVE)</div>", unsafe_allow_html=True)
    fig = go.Figure()
    
    for nome in df_live['nome'].unique():
        h_data = df_hist[df_hist['nome'] == nome].sort_values('timestamp')
        l_point = df_live[df_live['nome'] == nome]
        
        # Se guardiamo oggi, attacchiamo il dato live alla fine della linea
        if st.session_state.data_attiva == datetime.now().date() and not l_point.empty:
            h_data = pd.concat([h_data, l_point])
            
        if not h_data.empty:
            fig.add_trace(go.Scatter(
                x=h_data['timestamp'], y=h_data['liberi'], name=nome,
                mode='lines', line=dict(width=3, shape='spline'), fill='tozeroy'
            ))

    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=10, b=0), height=400, font=dict(color="#8b949e"),
        xaxis=dict(showgrid=False), yaxis=dict(gridcolor='#30363d'),
        legend=dict(orientation="h", yanchor="top", y=-0.25, xanchor="center", x=0.5, font=dict(color="#f0f6fc", size=10))
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

else:
    st.warning("⚠️ Connessione al server Open Data di Bologna non riuscita. Ricarica la pagina.")
