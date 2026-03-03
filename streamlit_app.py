import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="PeruLabTech Control Room", layout="wide")

# CSS Migliorato: Nomi parcheggi in evidenza e contrasto elevato
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #0f2027, #203a43, #2c5364); color: white; }
    .parking-card {
        background: rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(15px);
        border-radius: 15px;
        padding: 20px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        margin-bottom: 20px;
    }
    .city-label { color: #00d2ff; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1.5px; font-weight: bold; }
    .parking-name { color: #ffffff !important; font-size: 1.4rem; font-weight: 800; margin: 5px 0 15px 0; line-height: 1.2; }
    .stat-val { font-size: 1.8rem; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# Logo
LOGO_URL = "https://raw.githubusercontent.com/fperuzzu/parcheggi-automazione/main/logo.png"
st.sidebar.image(LOGO_URL, use_container_width=True)

def load_data():
    try:
        conn = sqlite3.connect("storico_parcheggi.db")
        df = pd.read_sql_query("SELECT * FROM storico", conn)
        conn.close()
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['citta'] = df['citta'].fillna('Bologna')
        return df
    except: return pd.DataFrame()

df = load_data()

if not df.empty:
    sel_citta = st.sidebar.multiselect("Filtra Città", sorted(df['citta'].unique()), default=list(df['citta'].unique()))
    df_f = df[df['citta'].isin(sel_citta)]

    st.markdown("<h1>🛰️ PeruLabTech Smart City Dashboard</h1>", unsafe_allow_html=True)

    # Griglia Card
    ultimi = df_f.sort_values('timestamp').groupby(['citta', 'nome']).last().reset_index()
    cols = st.columns(3)
    
    for i, row in ultimi.iterrows():
        with cols[i % 3]:
            lib = row['liberi']
            tot = row['totali'] if ('totali' in row and row['totali'] > 0) else (lib + 20)
            perc = round(((tot - lib) / tot * 100), 1)
            col_bar = "#00ff88" if perc < 60 else "#f39c12" if perc < 85 else "#ff4d4d"
            
            # HTML Card con NOME BEN VISIBILE
            st.markdown(f"""
                <div class="parking-card">
                    <div class="city-label">{row['citta']}</div>
                    <div class="parking-name">{row['nome']}</div>
                    <div style="display: flex; justify-content: space-between; align-items: baseline;">
                        <span class="stat-val" style="color:{col_bar}">{lib}</span>
                        <span style="color: #ccc;">/ {tot} Posti Liberi</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            st.progress(perc / 100)

    # Storico Area Chart
    st.subheader("📈 Trend Occupazione (24h)")
    ieri = datetime.now() - timedelta(hours=24)
    df_g = df_f[df_f['timestamp'] > ieri].sort_values('timestamp')
    if not df_g.empty:
        fig = go.Figure()
        for n in df_g['nome'].unique():
            p = df_g[df_g['nome'] == n]
            fig.add_trace(go.Scatter(x=p['timestamp'], y=p['liberi'], name=n, fill='tozeroy', line=dict(width=2)))
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white"), height=450)
        st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("In attesa di dati sincronizzati...")
