import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

st.set_page_config(page_title="ParkMonitor Italia", layout="wide", page_icon="🅿️")

# MENU LATERALE - Clicca la freccia > in alto a sinistra per vederlo
st.sidebar.header("📍 Navigazione")
citta_scelta = st.sidebar.selectbox(
    "Scegli la città:", 
    ["Bologna", "Milano", "Torino", "Firenze"]
)

st.title(f"📊 Parcheggi: {citta_scelta}")

def load_data(citta):
    if not os.path.exists("storico_parcheggi.db"):
        return pd.DataFrame()
    conn = sqlite3.connect("storico_parcheggi.db")
    query = f"SELECT * FROM storico WHERE citta = '{citta}'"
    try:
        df = pd.read_sql_query(query, conn)
    except:
        df = pd.read_sql_query("SELECT * FROM storico", conn)
        df['citta'] = 'Bologna'
        df = df[df['citta'] == citta]
    conn.close()
    return df

df = load_data(citta_scelta)

if not df.empty:
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    parcheggio = st.selectbox("🎯 Seleziona parcheggio:", sorted(df['nome'].unique()))
    df_filtered = df[df['nome'] == parcheggio].sort_values('timestamp')
    
    fig = px.line(df_filtered, x='timestamp', y='liberi', title=f"Posti liberi: {parcheggio}", markers=True)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df_filtered.tail(15).sort_values('timestamp', ascending=False), use_container_width=True, hide_index=True)
else:
    st.warning(f"Dati per {citta_scelta} in caricamento. Lancia 'Run workflow' su GitHub per accelerare.")
