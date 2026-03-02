import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

st.set_page_config(page_title="Monitor Parcheggi", layout="wide")
st.title("📊 Monitoraggio Parcheggi Italia")

def load_data():
    if not os.path.exists("storico_parcheggi.db"):
        return pd.DataFrame()
    conn = sqlite3.connect("storico_parcheggi.db")
    df = pd.read_sql_query("SELECT * FROM storico", conn)
    conn.close()
    return df

df_all = load_data()

if not df_all.empty:
    df_all['timestamp'] = pd.to_datetime(df_all['timestamp'])
    
    citta_list = sorted(df_all['citta'].unique())
    citta_scelta = st.sidebar.selectbox("📍 Seleziona Città", citta_list)
    
    df_citta = df_all[df_all['citta'] == citta_scelta]
    parcheggio = st.selectbox("🎯 Seleziona Parcheggio", sorted(df_citta['nome'].unique()))
    
    df_plot = df_citta[df_citta['nome'] == parcheggio].sort_values('timestamp')
    
    if not df_plot.empty:
        # GRAFICO CON FIX PER PUNTO SINGOLO
        fig = px.line(df_plot, x='timestamp', y='liberi', markers=True, 
                      title=f"Disponibilità: {parcheggio}")
        
        # Se abbiamo un solo punto, allarghiamo l'asse X di 2 ore totali
        if len(df_plot) == 1:
            t_min = df_plot['timestamp'].min() - pd.Timedelta(hours=1)
            t_max = df_plot['timestamp'].max() + pd.Timedelta(hours=1)
            fig.update_xaxes(range=[t_min, t_max])
        
        st.plotly_chart(fig, use_container_width=True)
        st.metric("Posti liberi attuali", f"{df_plot.iloc[-1]['liberi']}")
        st.dataframe(df_plot.sort_values('timestamp', ascending=False), use_container_width=True)
else:
    st.warning("Database vuoto. Esegui il workflow su GitHub Actions.")
