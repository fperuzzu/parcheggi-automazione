import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
import folium
from streamlit_folium import folium_static
from datetime import datetime, timedelta

# Configurazione Pagina
st.set_page_config(page_title="PeruLabTech | Smart City", layout="wide")

# --- DATABASE COORDINATE (MAPPING) ---
COORDINATE = {
    "Piazza VIII Agosto": [44.500, 11.344],
    "Riva Reno": [44.498, 11.336],
    "Autostazione": [44.505, 11.345],
    "Bolzano": [45.074, 7.666],
    "Vittorio Veneto": [45.063, 7.689],
    "Fortezza Fiera": [43.782, 11.248],
    "Stazione Binario 16": [43.785, 11.245]
}

# --- CSS EXPERT UI (MOBILE OPTIMIZED) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: #0d1117; color: #e6edf3; }
    
    /* FIX MOBILE: Rimosso spazio bianco in alto */
    .block-container { padding-top: 0rem !important; padding-bottom: 1rem !important; }
    
    .day-badge {
        background: rgba(0, 210, 255, 0.1); color: #58a6ff;
        padding: 5px 12px; border-radius: 8px; font-weight: 600;
        font-size: 0.8rem; border: 1px solid rgba(88, 166, 255, 0.2);
        margin-top: 10px; margin-bottom: 20px; display: inline-block;
    }

    .parking-card {
        background: #161b22; border: 1px solid #30363d;
        border-radius: 12px; padding: 18px; margin-bottom: 10px;
    }
    .parking-name { color: #f0f6fc; font-size: 1.1rem; font-weight: 700; margin-bottom: 5px; }
    .stat-main { font-size: 1.8rem; font-weight: 800; color: #00d2ff; }
    .stat-sub { color: #8b949e; font-size: 0.85rem; }
    
    .nav-btn {
        display: block; background: #238636; color: white !important;
        text-align: center; padding: 10px; border-radius: 6px;
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
data_scelta = st.sidebar.date_input("Seleziona Giorno", datetime.now())

df = get_data(data_scelta)

# --- HEADER ---
st.markdown(f"<div class='day-badge'>PERULABTECH MONITORING • {data_scelta.strftime('%d.%m.%Y')}</div>", unsafe_allow_html=True)

if not df.empty:
    citta_presenti = sorted(df['citta'].unique())
    sel_citta = st.sidebar.multiselect("Filtra Città", citta_presenti, default=citta_presenti)
    df_f = df[df['citta'].isin(sel_citta)]
    
    # --- 1. SCHEDE DATI (BICCHIERE MEZZO PIENO) ---
    ultimi = df_f.sort_values('timestamp').groupby(['citta', 'nome']).last().reset_index()
    
    st.markdown("<div style='color:#8b949e; font-size:0.8rem; font-weight:600; margin-bottom:10px;'>STATO ATTUALE</div>", unsafe_allow_html=True)
    
    cols = st.columns(3)
    for idx, row in enumerate(ultimi.itertuples()):
        with cols[idx % 3]:
            lib = row.liberi
            tot = row.totali if (hasattr(row, 'totali') and row.totali > 0) else (lib + 20)
            
            # Calcolo occupazione per la barra (il bicchiere si riempie man mano che i posti finiscono)
            occupati = tot - lib
            perc_occ = (occupati / tot) if tot > 0 else 0
            
            # Colore dinamico per il numero dei liberi
            color_stat = "#3fb950" if (lib/tot) > 0.4 else "#d29922" if (lib/tot) > 0.15 else "#f85149"
            
            st.markdown(f"""
                <div class="parking-card">
                    <div style="color:#8b949e; font-size:0.7rem; text-transform:uppercase;">{row.citta}</div>
                    <div class="parking-name">{row.nome}</div>
                    <div style="display: flex; justify-content: space-between; align-items: baseline;">
                        <span class="stat-main" style="color:{color_stat};">{lib}</span>
                        <span class="stat-sub">liberi su {tot}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            st.progress(min(max(perc_occ, 0.0), 1.0))

    # --- 2. MAPPA SMART (SPOSTATA DOPO LE SCHEDE) ---
    st.markdown("<br><div style='color:#8b949e; font-size:0.8rem; font-weight:600; margin-bottom:10px;'>MAPPA NAVIGAZIONE</div>", unsafe_allow_html=True)
    
    m = folium.Map(location=[44.494, 11.342], zoom_start=12, tiles="cartodbpositron")
    
    for row in ultimi.itertuples():
        coords = COORDINATE.get(row.nome, [44.49, 11.34])
        nav_url = f"https://www.google.com/maps/dir/?api=1&destination={coords[0]},{coords[1]}"
        
        popup_html = f"""
        <div style='font-family:sans-serif; width:160px;'>
            <b style='font-size:14px;'>{row.nome}</b><br>
            <span style='color:#666;'>Liberi: {row.liberi}</span><br>
            <a href='{nav_url}' target='_blank' class='nav-btn' style='color:white; background:#238636; padding:8px; display:block; text-align:center; border-radius:5px; text-decoration:none; margin-top:8px;'>NAVIGA ORA</a>
        </div>
        """
        folium.Marker(
            location=coords, 
            popup=folium.Popup(popup_html, max_width=200),
            icon=folium.Icon(color='blue' if row.liberi > 10 else 'red', icon='car', prefix='fa')
        ).add_to(m)
    
    folium_static(m, width=700, height=350)

    # --- 3. GRAFICO TREND ---
    st.markdown("<br><div style='color:#8b949e; font-size:0.8rem; font-weight:600;'>TREND GIORNALIERO</div>", unsafe_allow_html=True)
    
    fig = go.Figure()
    max_val = 0
    for n in df_f['nome'].unique():
        p = df_f[df_f['nome'] == n].sort_values('timestamp')
        current_max = p['totali'].max() if 'totali' in p.columns else p['liberi'].max()
        if current_max > max_val: max_val = current_max
        
        fig.add_trace(go.Scatter(
            x=p['timestamp'], y=p['liberi'], name=n, 
            mode='lines', line=dict(width=3, shape='spline'), fill='tozeroy'
        ))

    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=10, b=0), height=350,
        xaxis=dict(showgrid=False, color="#8b949e"),
        yaxis=dict(gridcolor='#30363d', color="#8b949e", range=[0, max_val + 10]),
        legend=dict(
            orientation="h", yanchor="top", y=-0.25, xanchor="center", x=0.5, 
            font=dict(color="#f0f6fc", size=10) # Legenda chiara e leggibile
        )
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

else:
    st.info("Nessun dato trovato per questa data. Controlla lo storico dei giorni precedenti.")
