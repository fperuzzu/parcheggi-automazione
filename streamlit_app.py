import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

st.set_page_config(page_title="ParkMonitor Italia", layout="wide", page_icon="🅿️")

# Sidebar con le città funzionanti
st.sidebar.header("📍 Selezione Città")
citta_scelta = st.sidebar.selectbox("Scegli la città da monitorare:", ["Bologna", "Roma", "Bolzano"])

st.title(f"📊 Monitoraggio Parcheggi: {citta_scelta}")

def load_data(citta):
    if not os.path.exists("storico_parcheggi.db"):
        return pd.DataFrame()
    conn = sqlite3.connect("storico_parcheggi.db")
    try:
        df = pd.read_sql_query(f"SELECT * FROM storico WHERE citta = '{citta}'", conn)
    except:
        df = pd.DataFrame()
    conn.close()
    return df

df = load_data(citta_scelta)

if not df.empty:
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    parcheggio = st.selectbox("🎯 Seleziona struttura:", sorted(df['nome'].unique()))
    
    df_filtered = df[df['nome'] == parcheggio].sort_values('timestamp')
    
    # Grafico moderno ad area
    fig = px.area(df_filtered, x='timestamp', y='liberi', 
                  title=f"Posti Liberi: {parcheggio}",
                  color_discrete_sequence=['#0083B0'])
    
    fig.update_layout(xaxis=dict(fixedrange=True), yaxis=dict(fixedrange=True))
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    
    st.subheader("📝 Storico Ultime Rilevazioni")
    st.dataframe(df_filtered.tail(10).sort_values('timestamp', ascending=False), 
                 use_container_width=True, hide_index=True)
else:
    st.warning(f"⚠️ Dati per {citta_scelta} in fase di caricamento.")
    st.info("Esegui 'Run workflow' su GitHub per popolare il database.")
