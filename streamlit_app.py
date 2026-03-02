import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

st.set_page_config(page_title="Monitor Parcheggi", layout="wide", page_icon="🅿️")
st.title("📊 Monitoraggio Parcheggi Italia")

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
    
    # Sidebar con selezione città
    citta_list = sorted(df_all['citta'].unique())
    citta_scelta = st.sidebar.selectbox("📍 Seleziona Città", citta_list)
    
    df_citta = df_all[df_all['citta'] == citta_scelta]
    parcheggio = st.selectbox("🎯 Seleziona Struttura", sorted(df_citta['nome'].unique()))
    
    df_plot = df_citta[df_citta['nome'] == parcheggio].sort_values('timestamp')
    
    # GESTIONE GRAFICO
    if len(df_plot) > 1:
        fig = px.line(df_plot, x='timestamp', y='liberi', markers=True, 
                      title=f"Disponibilità nel tempo: {parcheggio}")
        # Forza l'asse X a essere una linea temporale estesa
        fig.update_xaxes(type='date')
        st.plotly_chart(fig, use_container_width=True)
    else:
        # Se abbiamo un solo punto, mostriamo una metrica invece di un grafico vuoto
        st.info("📈 Dati storici in fase di accumulo. Ecco la prima rilevazione:")
        st.metric(label=f"Posti liberi a {parcheggio}", value=f"{df_plot.iloc[-1]['liberi']} posti")

    st.subheader("📋 Storico Dati")
    st.dataframe(df_plot.sort_values('timestamp', ascending=False), use_container_width=True, hide_index=True)
else:
    st.warning("⚠️ Database vuoto. Esegui il workflow su GitHub Actions per caricare i primi dati.")
