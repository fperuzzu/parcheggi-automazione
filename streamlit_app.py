import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="PeruLabTech - Monitoraggio Parcheggi", layout="wide")

# Logo PeruLabTech
LOGO_URL = "https://raw.githubusercontent.com/fperuzzu/parcheggi-automazione/main/logo.png"
st.sidebar.image(LOGO_URL, use_container_width=True)
st.sidebar.markdown("---")

DB_NAME = "storico_parcheggi.db"

def load_data():
    try:
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query("SELECT * FROM storico", conn)
        conn.close()
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except:
        return pd.DataFrame()

st.title("🚗 Dashboard Parcheggi PeruLabTech")

df = load_data()

if not df.empty:
    # Filtro città
    citta_list = sorted(df['citta'].unique())
    sel_citta = st.sidebar.multiselect("Seleziona Città", citta_list, default=citta_list)
    df_filtrato = df[df['citta'].isin(sel_citta)]

    # STATO ATTUALE
    st.subheader("📍 Situazione Attuale (Bicchiere mezzo pieno)")
    ultimi = df_filtrato.sort_values('timestamp').groupby(['citta', 'nome']).last().reset_index()
    
    cols = st.columns(3)
    for i, row in ultimi.iterrows():
        with cols[i % 3]:
            lib = row['liberi']
            tot = row['totali'] if row['totali'] and row['totali'] > 0 else (lib + 20)
            occ_perc = round(((tot - lib) / tot * 100), 1)
            
            st.metric(label=f"{row['citta']} - {row['nome']}", 
                      value=f"{lib} / {tot} LIBERI", 
                      delta=f"{occ_perc}% Occupato", delta_color="inverse")
            st.progress(min(max(occ_perc/100, 0.0), 1.0))

    # STORICO
    st.divider()
    st.subheader("📈 Storico ultime 24 ore")
    ieri = datetime.now() - timedelta(hours=24)
    df_graf = df_filtrato[df_filtrato['timestamp'] > ieri]
    
    if not df_graf.empty:
        fig = px.line(df_graf, x='timestamp', y='liberi', color='nome', facet_row='citta',
                      height=600, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Nessun dato trovato. Verifica GitHub Actions.")
