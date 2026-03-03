import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="PeruLabTech Control Room", layout="wide")

# --- TRADUZIONE GIORNI IN ITALIANO ---
GIORNI = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]

# --- CSS WOW ---
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #0f2027, #203a43, #2c5364); color: white; }
    .parking-card {
        background: rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(15px);
        border-radius: 15px; padding: 20px;
        border: 1px solid rgba(255, 255, 255, 0.2); margin-bottom: 20px;
    }
    .city-label { color: #00d2ff; font-size: 0.75rem; text-transform: uppercase; font-weight: bold; }
    .parking-name { color: #ffffff !important; font-size: 1.3rem; font-weight: 800; margin: 5px 0; }
    .day-highlight { 
        background: #00d2ff; color: #0f2027; padding: 5px 15px; 
        border-radius: 10px; font-weight: bold; font-size: 1.2rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CARICAMENTO DATI ---
def load_full_data(selected_date):
    try:
        conn = sqlite3.connect("storico_parcheggi.db")
        # Carichiamo i dati del giorno scelto (da mezzanotte a mezzanotte)
        date_str = selected_date.strftime('%Y-%m-%d')
        query = f"SELECT * FROM storico WHERE timestamp LIKE '{date_str}%'"
        df = pd.read_sql_query(query, conn)
        conn.close()
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except: return pd.DataFrame()

# --- SIDEBAR ---
LOGO_URL = "https://raw.githubusercontent.com/fperuzzu/parcheggi-automazione/main/logo.png"
st.sidebar.image(LOGO_URL, use_container_width=True)

st.sidebar.header("📅 Archivio Storico")
data_scelta = st.sidebar.date_input("Scegli un giorno", datetime.now())
giorno_sett = GIORNI[data_scelta.weekday()]

# --- LOGICA APP ---
df = load_full_data(data_scelta)

st.markdown(f"<h1>🛰️ PeruLabTech Dashboard</h1>", unsafe_allow_html=True)
st.markdown(f"<span class='day-highlight'>📅 {giorno_sett} {data_scelta.strftime('%d/%m/%Y')}</span>", unsafe_allow_html=True)

if not df.empty:
    citta_list = sorted(df['citta'].unique())
    sel_citta = st.sidebar.multiselect("Filtra Città", citta_list, default=citta_list)
    df_f = df[df['citta'].isin(sel_citta)]

    # --- CARD STATO ATTUALE (O ULTIMO DATO DEL GIORNO SCELTO) ---
    st.write("")
    ultimi = df_f.sort_values('timestamp').groupby(['citta', 'nome']).last().reset_index()
    cols = st.columns(3)
    
    for i, row in ultimi.iterrows():
        with cols[i % 3]:
            lib = row['liberi']
            tot = row['totali'] if ('totali' in row and row['totali'] > 0) else (lib + 20)
            perc = round(((tot - lib) / tot * 100), 1)
            
            st.markdown(f"""
                <div class="parking-card">
                    <div class="city-label">{row['citta']}</div>
                    <div class="parking-name">{row['nome']}</div>
                    <div style="display:flex; justify-content:space-between; align-items:baseline;">
                        <span style="font-size:1.8rem; font-weight:bold; color:#00ff88;">{lib}</span>
                        <span style="color:#ccc;">/ {tot} Totali</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            st.progress(min(perc/100, 1.0))

    # --- GRAFICO CON SCALA FISSA ---
    st.divider()
    st.subheader(f"📈 Analisi Flussi - {giorno_sett}")
    
    if not df_f.empty:
        fig = go.Figure()
        max_y = 0
        
        for n in df_f['nome'].unique():
            p = df_f[df_f['nome'] == n]
            current_max = p['totali'].max() if ('totali' in p.columns and p['totali'].max() > 0) else p['liberi'].max()
            if current_max > max_y: max_y = current_max
            
            fig.add_trace(go.Scatter(
                x=p['timestamp'], y=p['liberi'], 
                name=n, fill='tozeroy', line=dict(width=2),
                hovertemplate="<b>%{y}</b> liberi<br>%{x|%H:%M}"
            ))
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color="white"),
            height=500,
            # --- SCALA FISSA ---
            yaxis=dict(
                range=[0, max_y + 10], # La scala resta ferma basandosi sul parcheggio più grande
                gridcolor='rgba(255,255,255,0.05)',
                fixedrange=True # Impedisce lo zoom accidentale su mobile
            ),
            xaxis=dict(showgrid=False)
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.warning(f"Nessun dato presente per {giorno_sett} {data_scelta.strftime('%d/%m/%Y')}. Ricorda che lo storico è iniziato da quando abbiamo attivato il nuovo database.")
