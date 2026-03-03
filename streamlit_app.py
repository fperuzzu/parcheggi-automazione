import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
import folium
from streamlit_folium import folium_static
from datetime import datetime, timedelta

# Configurazione Pagina
st.set_page_config(page_title="PeruLabTech Control Room", layout="wide")

# --- DATABASE COORDINATE (MAPPING) ---
# Ho inserito le coordinate dei principali parcheggi. Se ne mancano, basterà aggiungerli qui.
COORDINATE = {
    "Piazza VIII Agosto": [44.500, 11.344],
    "Riva Reno": [44.498, 11.336],
    "Autostazione": [44.505, 11.345],
    "Bolzano": [45.074, 7.666],
    "Vittorio Veneto": [45.063, 7.689],
    "Fortezza Fiera": [43.782, 11.248],
    "Stazione Binario 16": [43.785, 11.245],
    "Parcheggio Aeroporto": [44.530, 11.290] # Esempio
}

# --- CSS EXPERT UI (MOBILE OPTIMIZED) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: #0d1117; color: #e6edf3; }
    
    /* FIX MOBILE: Rimosso spazio bianco in alto */
    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }
    
    .day-badge {
        background: rgba(0, 210, 255, 0.15); color: #58a6ff;
        padding: 5px 12px; border-radius: 8px; font-weight: 600;
        font-size: 0.8rem; border: 1px solid rgba(88, 166, 255, 0.3);
        margin-bottom: 15px; display: inline-block;
    }

    .parking-card {
        background: #161b22; border: 1px solid #30363d;
        border-radius: 12px; padding: 15px; margin-bottom: 10px;
    }
    .parking-name { color: #f0f6fc; font-size: 1rem; font-weight: 600; margin-bottom: 8px; }
    .stat-number { font-size: 1.6rem; font-weight: 700; }
    
    /* Bottone Navigatore */
    .nav-btn {
        display: block; background: #238636; color: white !important;
        text-align: center; padding: 8px; border-radius: 6px;
        text-decoration: none; font-weight: bold; margin-top: 10px;
    }
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

# --- SIDEBAR ---
LOGO_URL = "https://raw.githubusercontent.com/fperuzzu/parcheggi-automazione/main/logo.png"
st.sidebar.image(LOGO_URL, use_container_width=True)
data_scelta = st.sidebar.date_input("Archivio", datetime.now())

df = get_data(data_scelta)

# --- HEADER ---
st.markdown(f"<div class='day-badge'>🛰️ PERULABTECH • {data_scelta.strftime('%d.%m.%Y')}</div>", unsafe_allow_html=True)

if not df.empty:
    citta_presenti = sorted(df['citta'].unique())
    sel_citta = st.sidebar.multiselect("Città", citta_presenti, default=citta_presenti)
    df_f = df[df['citta'].isin(sel_citta)]
    
    # --- MAPPA INTERATTIVA (WOW) ---
    st.markdown("<div style='color:#8b949e; font-size:0.8rem; font-weight:600; margin-bottom:10px;'>MAPPA SMART NAVIGATION</div>", unsafe_allow_html=True)
    
    # Centro mappa dinamico
    center = [44.494, 11.342] # Default Bologna
    m = folium.Map(location=center, zoom_start=12, tiles="cartodbpositron", control_scale=True)
    
    ultimi = df_f.sort_values('timestamp').groupby(['citta', 'nome']).last().reset_index()
    
    for row in ultimi.itertuples():
        coords = COORDINATE.get(row.nome, [44.49, 11.34]) # Fallback su Bologna centro
        lib = row.liberi
        tot = row.totali if (hasattr(row, 'totali') and row.totali > 0) else (lib + 20)
        perc = (tot - lib) / tot * 100
        color = 'green' if perc < 60 else 'orange' if perc < 85 else 'red'
        
        # Link Google Maps
        nav_url = f"https://www.google.com/maps/dir/?api=1&destination={coords[0]},{coords[1]}"
        
        popup_html = f"""
        <div style='font-family:sans-serif; width:180px;'>
            <b>{row.nome}</b><br>
            Liberi: {lib} / {tot}<br>
            <a href='{nav_url}' target='_blank' class='nav-btn' style='color:white; background:#238636; padding:5px; display:block; text-align:center; border-radius:5px; text-decoration:none; margin-top:5px;'>GO NAVIGATORE</a>
        </div>
        """
        folium.Marker(location=coords, popup=folium.Popup(popup_html, max_width=200),
                      icon=folium.Icon(color=color, icon='info-sign')).add_to(m)
    
    folium_static(m, width=700, height=350) # Dimensioni ottimizzate

    # --- CARDS ---
    st.markdown("<br>", unsafe_allow_html=True)
    cols = st.columns(len(ultimi) if len(ultimi) < 4 else 3)
    for idx, row in enumerate(ultimi.itertuples()):
        with cols[idx % 3]:
            perc = round(((row.totali - row.liberi) / row.totali * 100), 1) if row.totali > 0 else 0
            color = "#3fb950" if perc < 60 else "#d29922" if perc < 85 else "#f85149"
            st.markdown(f"""
                <div class="parking-card">
                    <div style="color:#8b949e; font-size:0.7rem;">{row.citta}</div>
                    <div class="parking-name">{row.nome}</div>
                    <div class="stat-number" style="color:{color}">{row.liberi}</div>
                </div>
            """, unsafe_allow_html=True)

    # --- GRAFICO (FIX COLORI LEGENDA) ---
    st.markdown("<br><div style='color:#8b949e; font-size:0.8rem; font-weight:600;'>TREND OCCUPAZIONE</div>", unsafe_allow_html=True)
    
    fig = go.Figure()
    for n in df_f['nome'].unique():
        p = df_f[df_f['nome'] == n].sort_values('timestamp')
        fig.add_trace(go.Scatter(x=p['timestamp'], y=p['liberi'], name=n, mode='lines', line=dict(width=3, shape='spline'), fill='tozeroy'))

    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=10, b=0), height=400,
        xaxis=dict(showgrid=False, color="#8b949e"),
        yaxis=dict(gridcolor='#30363d', color="#8b949e"),
        # FIX LEGENDA: Testo chiaro e posizione inferiore
        legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5, font=dict(color="#f0f6fc", size=10))
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

else:
    st.info("Inizializzazione PeruLabTech Cloud... Seleziona una data con dati presenti.")
