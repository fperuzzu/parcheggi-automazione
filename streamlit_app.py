import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="Monitoraggio Parcheggi", layout="wide")

DB_NAME = "storico_parcheggi.db"

def load_data():
    conn = sqlite3.connect(DB_NAME)
    # Carichiamo le ultime 24 ore di dati
    query = "SELECT * FROM storico WHERE timestamp > ?"
    ieri = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    df = pd.read_sql_query(query, conn, params=(ieri,))
    conn.close()
    return df

st.title("🚗 Dashboard Parcheggi Multi-Città")
st.markdown("Dati in tempo reale da **Bologna, Torino e Firenze** (Bicchiere mezzo pieno)")

try:
    df = load_data()
    
    if not df.empty:
        # Filtro per Città
        citta_scelta = st.sidebar.multiselect("Seleziona Città", options=df['citta'].unique(), default=df['citta'].unique())
        df_filtrato = df[df['citta'].isin(citta_scelta)]

        # --- SEZIONE INDICATORI (ULTIMO DATO) ---
        st.subheader("📍 Stato Attuale")
        cols = st.columns(3)
        
        # Prendiamo l'ultimo record per ogni parcheggio
        ultimi = df_filtrato.sort_values('timestamp').groupby(['citta', 'nome']).last().reset_index()
        
        for i, row in ultimi.iterrows():
            col_idx = i % 3
            with cols[col_idx]:
                liberi = row['liberi']
                totali = row['totali'] if row['totali'] else (liberi + 10)
                occupazione = round(((totali - liberi) / totali * 100), 1)
                
                st.metric(label=f"{row['citta']} - {row['nome']}", 
                          value=f"{liberi} liberi", 
                          delta=f"{occupazione}% occupato", delta_color="inverse")
                st.progress(occupazione / 100)

        # --- SEZIONE STORICO (GRAFICO) ---
        st.divider()
        st.subheader("📈 Storico ultime 24 ore")
        
        # Creazione grafico con Plotly
        fig = px.line(df_filtrato, x='timestamp', y='liberi', color='nome',
                      title="Andamento posti liberi",
                      labels={'liberi': 'Posti Liberi', 'timestamp': 'Orario', 'nome': 'Parcheggio'},
                      template="plotly_white")
        
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("Nessun dato trovato nel database. Aspetta il prossimo aggiornamento dello script!")

except Exception as e:
    st.error(f"Errore nel caricamento dei dati: {e}")
    st.info("Assicurati che il file 'storico_parcheggi.db' sia presente nel repository.")

st.sidebar.info(f"Ultimo controllo: {datetime.now().strftime('%H:%M:%S')}")
