import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

st.set_page_config(page_title="ParkMonitor Pro", layout="wide", page_icon="🅿️")

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
    
    # Sidebar dinamica: mostra solo le città che hanno dati nel DB
    citta_list = sorted(df_all['citta'].unique())
    citta_scelta = st.sidebar.selectbox("📍 Seleziona Città", citta_list)
    
    df_citta = df_all[df_all['citta'] == citta_scelta]
    parcheggio = st.selectbox("🎯 Seleziona Parcheggio", sorted(df_citta['nome'].unique()))
    
    df_plot = df_citta[df_citta['nome'] == parcheggio].sort_values('timestamp')
    
    # GESTIONE GRAFICO (Evita la barra fissa)
    if len(df_plot) > 1:
        fig = px.line(df_plot, x='timestamp', y='liberi', markers=True, 
                      title=f"Andamento: {parcheggio}")
        # Forza l'asse X a comportarsi come una linea temporale
        fig.update_xaxes(type='date')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📈 Dati storici in accumulo. Ecco la prima rilevazione effettuata:")
        st.metric(f"Posti Liberi a {parcheggio}", f"{df_plot.iloc[-1]['liberi']} posti")

    st.subheader("📋 Log Dati")
    st.dataframe(df_plot.sort_values('timestamp', ascending=False), use_container_width=True, hide_index=True)
else:
    st.warning("Database in attesa di dati. Avvia il workflow su GitHub Actions.")
