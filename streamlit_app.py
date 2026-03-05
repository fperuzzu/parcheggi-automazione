import streamlit as st
import sqlite3
import pandas as pd
import folium
from streamlit_folium import st_folium
import requests
from datetime import datetime

DB_NAME = "storico_parcheggi.db"

st.set_page_config(page_title="Parcheggi Live", layout="wide")
st.markdown("<h1 style='text-align:center;'>🚗 Parcheggi Live</h1>", unsafe_allow_html=True)

# ---------------------------
# FUNZIONE LIVE PER TUTTI I COMUNI
# ---------------------------
def fetch_live():
    results = []

    # Bologna
    try:
        url_bo = "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=20"
        r_bo = requests.get(url_bo, timeout=10).json()
        for rec in r_bo.get('results', []):
            results.append({
                "citta": "Bologna",
                "nome": rec.get('parcheggio'),
                "liberi": int(rec.get('posti_liberi', 0)),
                "totali": int(rec.get('posti_totali', 0))
            })
    except:
        st.warning("Bologna LIVE non disponibile → uso ultimo storico")

    # Firenze
    try:
        url_fi = "https://servizi.comune.fi.it/opendata/parcheggi.json"
        headers = {"User-Agent": "Mozilla/5.0"}
        r_fi = requests.get(url_fi, headers=headers, timeout=10)
        r_fi.raise_for_status()
        for p in r_fi.json():
            results.append({
                "citta": "Firenze",
                "nome": p.get("nome"),
                "liberi": int(p.get("posti_liberi", 0)),
                "totali": int(p.get("posti_totali", 0))
            })
    except:
        st.warning("Firenze LIVE non disponibile → uso ultimo storico")

    return results

# ---------------------------
# FETCH STORICO DAL DB
# ---------------------------
def fetch_last_from_db():
    try:
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query(
            "SELECT * FROM storico WHERE timestamp = (SELECT MAX(timestamp) FROM storico)",
            conn
        )
        conn.close()
        return df
    except:
        return pd.DataFrame()

# ---------------------------
# DATI LIVE O STORICO
# ---------------------------
live_data = fetch_live()
if live_data:
    df_live = pd.DataFrame(live_data)
else:
    st.warning("Nessun dato LIVE disponibile, uso ultimo dato storico")
    df_live = fetch_last_from_db()

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
# MAPPA
# ---------------------------
COORDINATE = {
    # Bologna
    "Piazza VIII Agosto": [44.5011, 11.3438], "Riva Reno": [44.4981, 11.3353],
    "Autostazione": [44.5049, 11.3456], "Staveco": [44.4842, 11.3429],
    "Parcheggio Aeroporto": [44.5308, 11.2912], "Tanari": [44.5056, 11.3268],
    # Firenze (esempio)
    "S. Ambrogio": [43.7705, 11.2638], "Beccaria": [43.7693, 11.2724],
    "Alberti": [43.7662, 11.2847], "Parterre": [43.7870, 11.2560],
    "Stazione SMN": [43.7769, 11.2486]
}

m = folium.Map(location=[44.495, 11.343], zoom_start=13, tiles="cartodbdark_matter")
if not df_live.empty:
    for _, row in df_live.iterrows():
        nome = row["nome"]
        liberi = row["liberi"]
        totali = row["totali"]
        coords = COORDINATE.get(nome, [44.49, 11.34])
        colore = "green" if liberi > totali*0.4 else "orange" if liberi > totali*0.2 else "red"
        folium.CircleMarker(
            location=coords,
            radius=10,
            popup=f"{nome} ({row['citta']})<br>Liberi: {liberi}/{totali}",
            color=colore,
            fill=True,
            fill_opacity=0.7
        ).add_to(m)
st_folium(m, width=1200, height=500)

# ---------------------------
# TABELLA DETTAGLIO
# ---------------------------
st.subheader("Dettaglio Parcheggi")
st.dataframe(df_live, use_container_width=True)
