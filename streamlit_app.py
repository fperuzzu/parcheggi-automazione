import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

# Configurazione Pagina
st.set_page_config(page_title="ParkMonitor Italia", layout="wide", page_icon="🅿️")

# Sidebar per la selezione della città
st.sidebar.header("Impostazioni")
citta_scelta = st.sidebar.selectbox(
    "🏙️ Seleziona Città", 
    ["Bologna", "Milano", "Torino", "Firenze"]
)

st.title(f"📊 Analisi Parcheggi: {citta_scelta}")
st.markdown(f"Monitoraggio in tempo reale e storico della disponibilità a **{citta_scelta}**.")

def load_data(citta):
    if not os.path.exists("storico_parcheggi.db"):
        return pd.DataFrame()
    
    conn = sqlite3.connect("storico_parcheggi.db")
    # Filtriamo i dati direttamente via SQL per velocità
    query = f"SELECT * FROM storico WHERE citta = '{citta}'"
    try:
        df = pd.read_sql_query(query, conn)
    except:
        df = pd.DataFrame()
    conn.close()
    return df

# Caricamento dati
df = load_data(citta_scelta)

if not df.empty:
    # Formattazione dati
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Selezione Parcheggio
    lista_parcheggi = sorted(df['nome'].unique())
    parcheggio = st.selectbox("🎯 Scegli un parcheggio per il dettaglio:", lista_parcheggi)
    
    # Filtro e Grafico
    df_filtered = df[df['nome'] == parcheggio].sort_values('timestamp')
    
    fig = px.line(
        df_filtered, 
        x='timestamp', 
        y='liberi', 
        title=f"Posti liberi nel tempo: {parcheggio}",
        labels={'liberi': 'Posti Liberi', 'timestamp': 'Data e Ora'},
        markers=True
    )
    
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
    
    # Tabella riassuntiva
    st.subheader("📋 Ultimi dati rilevati")
    st.dataframe(df_filtered.tail(15).sort_values('timestamp', ascending=False), use_container_width=True, hide_index=True)

else:
    st.warning(f"⚠️ Al momento non ci sono dati per {citta_scelta}. L'aggiornamento automatico caricherà i dati a breve.")
    st.info("💡 Se hai appena aggiornato il codice, vai su GitHub Actions e clicca su 'Run workflow' per popolare il database.")

# Sidebar Credit & Monetizzazione (Simulata)
st.sidebar.markdown("---")
st.sidebar.write("☕ **Ti piace il progetto?**")
st.sidebar.button("Offrimi un caffè")
st.sidebar.caption("Supporta i costi di mantenimento dei dati.")
