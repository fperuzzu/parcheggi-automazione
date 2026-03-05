import streamlit as st
import sqlite3
import pandas as pd
import folium
from streamlit_folium import st_folium
import requests
from datetime import datetime

DB_NAME = "storico_parcheggi.db"

st.set_page_config(page_title="Parcheggi Firenze", layout="wide")
st.markdown("<h1 style='text-align:center;'>🚗 Parcheggi Firenze</h1>", unsafe_allow_html=True)

# ---------------------------
# FUNZIONI LIVE
# ---------------------------
def live_firenze():
    url = "https://servizi.comune.fi.it/opendata/parcheggi.json"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        results = []
        for p in data:
            results.append({
                "citta": "Firenze",
                "nome": p.get("nome"),
                "liberi": p.get("posti_liberi"),
                "totali": p.get("posti_totali")
            })
        return results
    except Exception as e:
        print("Errore Firenze LIVE:", e)
        return []

# ---------------------------
# FETCH STORICO DB
# ---------------------------
def fetch_from_db():
    try:
        conn = sqlite3.connect(DB_NAME)
        last_ts = pd.read_sql_query(
            "SELECT MAX(timestamp) as ts FROM storico WHERE citta='Firenze'",
            conn
        )['ts'][0]
        if not last_ts:
            conn.close()
            return pd.DataFrame()
        df = pd.read_sql_query(
            f"SELECT nome, liberi, totali, timestamp FROM storico WHERE citta='Firenze' AND timestamp='{last_ts}'",
            conn
        )
        conn.close()
        return df
    except Exception as e:
        st.error(f"Errore lettura DB: {e}")
        return pd.DataFrame()

# ---------------------------
# PREPARA DATI
# ---------------------------
live_data = live_firenze()
if live_data:
    df_live = pd.DataFrame(live_data)
else:
    st.warning("LIVE non disponibile → uso ultimo dato storico")
    df_live = fetch_from_db()

# ---------------------------
# KPI
# ---------------------------
col1, col2 = st.columns(2)
posti_tot = int(df_live['liberi'].sum()) if not df_live.empty else 0
posti_complessivi = int(df_live['totali'].sum()) if not df_live.empty else 0
percentuale = round((posti_tot / posti_complessivi) * 100, 1) if posti_complessivi > 0 else 0
col1.metric("Posti Liberi Totali", posti_tot)
col2.metric("Occupazione Media %", percentuale)

st.divider()

# ---------------------------
# MAPPA Firenze
# ---------------------------
COORDINATE = {
    "S. Ambrogio": [43.7705, 11.2638],
    "Beccaria": [43.7693, 11.2724],
    "Alberti": [43.7662, 11.2847],
    "Parterre": [43.7870, 11.2560],
    "Stazione SMN": [43.7769, 11.2486]
}

m = folium.Map(location=[43.77, 11.25], zoom_start=14, tiles="cartodbdark_matter")
if not df_live.empty:
    for _, row in df_live.iterrows():
        nome = row["nome"]
        liberi = row["liberi"]
        totali = row["totali"]
        if nome in COORDINATE:
            lat, lon = COORDINATE[nome]
            colore = "green" if liberi > totali * 0.4 else "orange" if liberi > totali * 0.2 else "red"
            folium.CircleMarker(
                location=[lat, lon],
                radius=10,
                popup=f"{nome}<br>Liberi: {liberi}/{totali}",
                color=colore,
                fill=True,
                fill_opacity=0.7
            ).add_to(m)
st_folium(m, width=1200, height=500)

# ---------------------------
# Tabella dettaglio
# ---------------------------
st.subheader("Dettaglio Parcheggi")
st.dataframe(df_live, use_container_width=True)
