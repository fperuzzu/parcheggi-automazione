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
        fig = px.line(df_plot, x='timestamp', y='liberi', markers=True, 
                      title=f"Disponibilità: {parcheggio}")
        
        # FIX ASSE X: Allarghiamo lo zoom se c'è poca storia
        if len(df_plot) < 5:
            t_center = df_plot['timestamp'].iloc[-1]
            fig.update_xaxes(range=[t_center - pd.Timedelta(hours=2), t_center + pd.Timedelta(hours=2)])
        
        st.plotly_chart(fig, use_container_width=True)
        
        col1, col2 = st.columns(2)
        col1.metric("Stato Attuale", f"{df_plot.iloc[-1]['liberi']} posti")
        col2.metric("Ultimo Aggiornamento", df_plot.iloc[-1]['timestamp'].strftime("%H:%M:%S"))
        
        st.dataframe(df_plot.sort_values('timestamp', ascending=False), use_container_width=True)
else:
    st.warning("Database vuoto. Esegui il workflow su GitHub Actions.")
