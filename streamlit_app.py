import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

st.set_page_config(page_title="Analisi Parcheggi", layout="wide")
st.title("📊 Monitoraggio Storico Parcheggi")

# 1. Trova il percorso preciso del database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "storico_parcheggi.db")

def get_data():
    if os.path.exists(DB_NAME):
        try:
            conn = sqlite3.connect(DB_NAME)
            # Leggiamo tutto dalla tabella 'storico'
            df = pd.read_sql_query("SELECT * FROM storico", conn)
            conn.close()
            return df
        except Exception as e:
            st.error(f"Errore nella lettura del database: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# 2. Carica i dati
df = get_data()

# 3. Visualizzazione
if not df.empty:
    # Convertiamo la data in formato leggibile
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    st.success(f"✅ Connessione riuscita! Trovate {len(df)} righe di dati.")
    
    # Menu a tendina per scegliere il parcheggio
    lista_parcheggi = df['nome'].unique()
    parcheggio = st.selectbox("Scegli un parcheggio per vedere il grafico:", lista_parcheggi)
    
    df_filtered = df[df['nome'] == parcheggio].sort_values('timestamp')
    
    # Mostriamo il grafico solo se ci sono dati
    fig = px.line(df_filtered, x='timestamp', y='liberi', 
                  title=f"Posti liberi nel tempo: {parcheggio}",
                  markers=True) # Aggiunge i puntini così si vede anche se c'è un solo dato
    st.plotly_chart(fig, use_container_width=True)
    
    # Tabella di controllo in basso
    st.subheader("Ultimi dati registrati (Tabella)")
    st.dataframe(df_filtered.tail(10), hide_index=True)

else:
    st.info("Il file database esiste ma sembra non contenere ancora dati. Vai su GitHub Actions e clicca 'Run workflow' per popolarlo!")
