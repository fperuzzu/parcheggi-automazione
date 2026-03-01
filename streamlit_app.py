import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

# 1. Configurazione della pagina
st.set_page_config(page_title="ParkMonitor Italia", layout="wide", page_icon="🅿️")

# --- BARRA LATERALE (SIDEBAR) ---
st.sidebar.header("📍 Menu di Navigazione")
citta_scelta = st.sidebar.selectbox(
    "Scegli la città da monitorare:", 
    ["Bologna", "Milano", "Torino", "Firenze"]
)

st.sidebar.markdown("---")
st.sidebar.write("☕ **Ti piace l'app?**")
st.sidebar.markdown("[Offrimi un caffè](https://www.buymeacoffee.com)")
# --------------------------------

st.title(f"📊 Analisi Parcheggi: {citta_scelta}")

def load_data(citta):
    if not os.path.exists("storico_parcheggi.db"):
        return pd.DataFrame()
    
    conn = sqlite3.connect("storico_parcheggi.db")
    query = f"SELECT * FROM storico WHERE citta = '{citta}'"
    try:
        df = pd.read_sql_query(query, conn)
    except:
        # Fallback se il db non è ancora stato aggiornato con la colonna citta
        df = pd.read_sql_query("SELECT * FROM storico", conn)
        df['citta'] = 'Bologna'
        df = df[df['citta'] == citta]
    conn.close()
    return df

df = load_data(citta_scelta)

if not df.empty:
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    lista_parcheggi = sorted(df['nome'].unique())
    parcheggio = st.selectbox("🎯 Seleziona un parcheggio specifico:", lista_parcheggi)
    
    df_filtered = df[df['nome'] == parcheggio].sort_values('timestamp')
    
    if not df_filtered.empty:
        fig = px.line(df_filtered, x='timestamp', y='liberi', 
                      title=f"Disponibilità posti: {parcheggio}",
                      labels={'liberi': 'Posti Liberi', 'timestamp': 'Orario'},
                      markers=True)
        
        fig.update_layout(hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("📋 Storico rilevazioni")
        st.dataframe(df_filtered.tail(20).sort_values('timestamp', ascending=False), 
                     use_container_width=True, hide_index=True)
else:
    st.warning(f"⚠️ Nessun dato trovato per {citta_scelta}.")
    st.info("💡 Vai su GitHub Actions e clicca 'Run workflow' per scaricare i primi dati delle altre città!")
