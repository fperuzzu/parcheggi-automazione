import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

st.set_page_config(page_title="Analisi Parcheggi", layout="wide")
st.title("📊 Monitoraggio Storico Parcheggi")

# Debug: Vediamo cosa vede l'app nella sua cartella
st.write("File presenti nel sistema:", os.listdir("."))

DB_NAME = "storico_parcheggi.db"

def get_data():
    if os.path.exists(DB_NAME):
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query("SELECT * FROM storico", conn)
        conn.close()
        return df
    return pd.DataFrame()

df = get_data()

if not df.empty:
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    parcheggio = st.sidebar.selectbox("Seleziona Parcheggio", df['nome'].unique())
    df_filtered = df[df['nome'] == parcheggio].sort_values('timestamp')
    
    fig = px.line(df_filtered, x='timestamp', y='liberi', title=f"Disponibilità: {parcheggio}")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df_filtered.tail(10))
else:
    st.info(f"Database '{DB_NAME}' non trovato. Controlla i nomi dei file su GitHub.")
