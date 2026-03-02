import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

st.set_page_config(page_title="ParkMonitor Italia", layout="wide", page_icon="🅿️")

st.title("🅿️ Monitoraggio Parcheggi Italia")

def load_data():
    if not os.path.exists("storico_parcheggi.db"):
        return pd.DataFrame()
    conn = sqlite3.connect("storico_parcheggi.db")
    try:
        df = pd.read_sql_query("SELECT * FROM storico", conn)
    except:
        df = pd.DataFrame()
    conn.close()
    return df

df_all = load_data()

if not df_all.empty:
    df_all['timestamp'] = pd.to_datetime(df_all['timestamp'])
    
    # Sidebar dinamica basata sui dati reali nel DB
    citta_list = sorted(df_all['citta'].unique())
    citta_scelta = st.sidebar.selectbox("📍 Seleziona Città", citta_list)
    
    df_citta = df_all[df_all['citta'] == citta_scelta]
    parcheggio = st.selectbox("🎯 Seleziona Parcheggio", sorted(df_citta['nome'].unique()))
    
    df_plot = df_citta[df_citta['nome'] == parcheggio].sort_values('timestamp')
    
    # LOGICA GRAFICO: Serve almeno 2 punti per una linea
    if len(df_plot) > 1:
        fig = px.line(df_plot, x='timestamp', y='liberi', 
                      title=f"Andamento Posti Liberi: {parcheggio}",
                      markers=True)
        # Forza l'asse X a mostrare un intervallo temporale sensato
        fig.update_xaxes(type='date')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📈 Dati insufficienti per il grafico. L'app ha bisogno di almeno due rilevazioni (attendi il prossimo aggiornamento tra 30 minuti).")
        st.metric("Posti liberi attuali", df_plot.iloc[0]['liberi'] if not df_plot.empty else "N/A")

    st.subheader("📋 Storico Dati")
    st.dataframe(df_plot.sort_values('timestamp', ascending=False), use_container_width=True, hide_index=True)
else:
    st.warning("Database in fase di popolamento. Attendi il primo ciclo di GitHub Actions.")
