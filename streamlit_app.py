import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. Configurazione Pagina (Mobile First)
st.set_page_config(page_title="PeruLabTech Smart Parking", page_icon="🅿️", layout="centered")

# 2. Iniezione CSS per Stile iOS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, sans-serif;
        background-color: #F2F2F7;
    }
    
    /* Nascondi header Streamlit */
    header {visibility: hidden;}
    
    /* Header Stile iPhone */
    .ios-title {
        font-size: 34px;
        font-weight: 800;
        letter-spacing: -1px;
        color: #000000;
        margin-bottom: 5px;
    }
    .ios-subtitle {
        font-size: 13px;
        font-weight: 600;
        color: #8E8E93;
        text-transform: uppercase;
        margin-bottom: 25px;
    }

    /* Card iOS */
    .stMetric {
        background: white;
        border-radius: 20px;
        padding: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    
    /* Bottoni e Slider */
    .stSlider > div > div > div > div {
        background-color: #007AFF;
    }
    
    .main-card {
        background: white;
        border-radius: 25px;
        padding: 25px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08);
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. Funzioni di Caricamento Dati
def get_data():
    conn = sqlite3.connect("storico_parcheggi.db")
    df = pd.read_sql_query("SELECT * FROM storico ORDER BY timestamp DESC", conn)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    conn.close()
    return df

# Header
st.markdown('<div class="ios-subtitle">PeruLabTech Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="ios-title">Smart Parking</div>', unsafe_allow_html=True)

try:
    df = get_data()
    
    # --- SEZIONE REAL TIME ---
    st.markdown("### 📍 Stato Attuale")
    ultimo_aggiornamento = df['timestamp'].iloc[0]
    df_now = df[df['timestamp'] == ultimo_aggiornamento]
    
    # Colonne per i parcheggi principali
    cols = st.columns(2)
    for i, (index, row) in enumerate(df_now.head(4).iterrows()):
        with cols[i % 2]:
            st.metric(label=row['nome'], value=f"{row['liberi']} p.", 
                      delta_color="normal")

    st.markdown("---")

    # --- SEZIONE STORICA (ANALISI) ---
    st.markdown("### 📈 Analisi Storica")
    
    with st.container():
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        
        selected_parking = st.selectbox("Seleziona Parcheggio", df['nome'].unique())
        ore_slider = st.slider("Visualizza ultime ore", 1, 48, 12)
        
        limit_time = datetime.now() - timedelta(hours=ore_slider)
        df_filtered = df[(df['nome'] == selected_parking) & (df['timestamp'] > limit_time)]
        
        # Grafico in stile Apple Health (pulito, senza griglie pesanti)
        fig = px.line(df_filtered, x='timestamp', y='liberi', 
                      render_mode='svg',
                      labels={'liberi': 'Posti Liberi', 'timestamp': 'Orario'})
        
        fig.update_traces(line_color='#007AFF', line_width=4)
        fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=20, b=0),
            height=300,
