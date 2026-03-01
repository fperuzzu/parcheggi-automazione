import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

st.set_page_config(page_title="ParkMonitor Italia", layout="wide")

# Sidebar per la scelta città
citta = st.sidebar.selectbox("🏙️ Scegli la città", ["Bologna", "Milano", "Torino"])

st.title(f"📊 Monitoraggio Parcheggi: {citta}")

def load_data(citta_scelta):
    conn = sqlite3.connect("storico_parcheggi.db")
    query = f"SELECT * FROM storico WHERE citta = '{citta_scelta}'"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

df = load_data(citta)

if not df.empty:
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    parcheggio = st.selectbox("Seleziona parcheggio:", df['nome'].unique())
    
    df_filtered = df[df['nome'] == parcheggio].sort_values('timestamp')
    fig = px.line(df_filtered, x='timestamp', y='liberi', title=f"Disponibilità a {parcheggio}")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning(f"Ancora nessun dato per {citta}. Lancia l'azione su GitHub!")
