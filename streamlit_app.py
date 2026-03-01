import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

st.set_page_config(page_title="ParkMonitor Italia", layout="wide")

# Menu laterale per la città
citta_scelta = st.sidebar.selectbox("🏙️ Seleziona Città", ["Bologna", "Milano", "Torino", "Firenze"])

st.title(f"📊 Stato Parcheggi: {citta_scelta}")

def load_data(citta):
    if not os.path.exists("storico_parcheggi.db"):
        return pd.DataFrame()
    conn = sqlite3.connect("storico_parcheggi.db")
    # Filtriamo i dati solo per la città selezionata
    query = f"SELECT * FROM storico WHERE citta = '{citta}'"
    try:
        df = pd.read_sql_query(query, conn)
    except:
        df = pd.DataFrame()
    conn.close()
    return df

df = load_data(citta_scelta)

if not df.empty:
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    parcheggio = st.selectbox("Scegli un parcheggio:", sorted(df['nome'].unique()))
    
    df_filtered = df[df['nome'] == parcheggio].sort_values('timestamp')
    fig = px.line(df_filtered, x='timestamp', y='liberi', title=f"Posti liberi a {parcheggio}")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df_filtered.tail(10), hide_index=True)
else:
    st.info(f"Nessun dato ancora disponibile per {citta_scelta}. Attendi il prossimo aggiornamento automatico!")
