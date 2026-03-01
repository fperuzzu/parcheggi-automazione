import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os
from datetime import datetime

# --- CONFIGURAZIONE PROFESSIONALE ---
st.set_page_config(
    page_title="ParkMonitor Pro | Italia",
    page_icon="🅿️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- STILE CSS PERSONALIZZATO (Look & Feel Professionale) ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .stPlotlyChart { background-color: #ffffff; border-radius: 12px; padding: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    h1 { color: #1e293b; font-weight: 800; }
    .sidebar-text { font-size: 14px; color: #64748b; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGICA CARICAMENTO DATI ---
def load_data(citta):
    if not os.path.exists("storico_parcheggi.db"):
        return pd.DataFrame()
    conn = sqlite3.connect("storico_parcheggi.db")
    query = f"SELECT * FROM storico WHERE citta = '{citta}'"
    try:
        df = pd.read_sql_query(query, conn)
    except:
        df = pd.DataFrame()
    conn.close()
    return df

# --- SIDEBAR MODERNA ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2991/2991231.png", width=80) # Icona placeholder
    st.title("Navigation")
    citta_scelta = st.selectbox("🏙️ Seleziona Città", ["Bologna", "Milano", "Torino", "Firenze"])
    st.markdown("---")
    st.markdown("<p class='sidebar-text'>ParkMonitor Pro v2.0<br>Aggiornamenti ogni 30 min</p>", unsafe_allow_html=True)
    st.link_button("☕ Supporta il Progetto", "https://www.buymeacoffee.com")

# --- DASHBOARD PRINCIPALE ---
df = load_data(citta_scelta)

if not df.empty:
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    lista_parcheggi = sorted(df['nome'].unique())
    
    col_t1, col_t2 = st.columns([2, 1])
    with col_t1:
        st.title(f"Dashboard {citta_scelta}")
    with col_t2:
        parcheggio = st.selectbox("🎯 Seleziona Struttura", lista_parcheggi)

    # Filtro dati
    df_p = df[df['nome'] == parcheggio].sort_values('timestamp')
    
    if not df_p.empty:
        # --- SEZIONE METRICHE (KPI CARDS) ---
        ultimo_dato = df_p.iloc[-1]
        precedente = df_p.iloc[-2] if len(df_p) > 1 else ultimo_dato
        delta_posti = int(ultimo_dato['liberi'] - precedente['liberi'])

        m1, m2, m3 = st.columns(3)
        m1.metric("Posti Attuali", f"{ultimo_dato['liberi']}", delta=f"{delta_posti} vs 30m fa")
        m2.metric("Stato", "Disponibile" if ultimo_dato['liberi'] > 10 else "Quasi Pieno", 
                  delta_color="normal" if ultimo_dato['liberi'] > 10 else "inverse")
        m3.metric("Ultimo Check", ultimo_dato['timestamp'].strftime("%H:%M"))

        st.markdown("### 📈 Andamento Occupazione")
        
        # --- GRAFICO AREA PROFESSIONALE ---
        fig = px.area(df_p, x='timestamp', y='liberi',
                      color_discrete_sequence=['#3b82f6'], # Blu moderno
                      labels={'liberi': 'Posti Disponibili', 'timestamp': 'Orario'})
        
        fig.update_layout(
            margin=dict(l=20, r=20, t=20, b=20),
            paper_bgcolor="white",
            plot_bgcolor="white",
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)

        # --- TABELLA E DETTAGLI ---
        with st.expander("📂 Visualizza Dati Storici Completi"):
            st.dataframe(df_p.sort_values('timestamp', ascending=False), 
                         use_container_width=True, hide_index=True)
    else:
        st.info("Nessun dato disponibile per questo parcheggio.")
else:
    st.error(f"Nessun dato trovato per {citta_scelta}. Verifica l'Action su GitHub.")
