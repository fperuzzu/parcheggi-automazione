import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

st.set_page_config(page_title="Monitor Parcheggi", layout="wide")

st.title("🅿️ Monitoraggio Parcheggi Italia")

def get_data():
    if not os.path.exists("storico_parcheggi.db"):
        return pd.DataFrame()
    conn = sqlite3.connect("storico_parcheggi.db")
    try:
        df = pd.read_sql_query("SELECT * FROM storico", conn)
    except:
        df = pd.DataFrame()
    conn.close()
    return df

df_full = get_data()

if not df_full.empty:
    # Sidebar dinamica
    citta_disponibili = sorted(df_full['citta'].unique())
    citta_scelta = st.sidebar.selectbox("📍 Seleziona Città", citta_disponibili)
    
    df = df_full[df_full['citta'] == citta_scelta]
    
    # Selettore Parcheggio
    parcheggio = st.selectbox("🎯 Scegli Parcheggio", sorted(df['nome'].unique()))
    
    df_plot = df[df['nome'] == parcheggio].sort_values('timestamp')
    
    if not df_plot.empty:
        fig = px.line(df_plot, x='timestamp', y='liberi', title=f"Posti liberi a {parcheggio}")
        st.plotly_chart(fig, use_container_width=True)
        st.table(df_plot.tail(5))
else:
    st.error("Database vuoto. Attendi il completamento di GitHub Actions.")
