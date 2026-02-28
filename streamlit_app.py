import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

st.set_page_config(page_title="Analisi Parcheggi", layout="wide")

st.title("📊 Monitoraggio Storico Parcheggi")

DB_NAME = "storico_parcheggi.db"

# Funzione per leggere i dati dal database creato dall'automazione
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
    
    # Filtro parcheggio
    parcheggio = st.sidebar.selectbox("Seleziona Parcheggio", df['nome'].unique())
    df_filtered = df[df['nome'] == parcheggio].sort_values('timestamp')
    
    # Grafico storico
    fig = px.line(df_filtered, x='timestamp', y='liberi', 
                  title=f"Disponibilità nel tempo: {parcheggio}",
                  labels={'liberi': 'Posti Liberi', 'timestamp': 'Ora/Data'})
    st.plotly_chart(fig, use_container_width=True)
    
    # Tabella ultimi dati
    st.subheader("Ultimi rilevamenti")
    st.dataframe(df_filtered.tail(10), hide_index=True)
else:
    st.info("Il database è in fase di creazione. Attiva l'aggiornamento nelle GitHub Actions!")
