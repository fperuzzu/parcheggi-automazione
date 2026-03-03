import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Configurazione Pagina
st.set_page_config(page_title="PeruLabTech Control Room", layout="wide", initial_sidebar_state="expanded")

# --- CSS CUSTOM PER EFFETTO WOW ---
st.markdown("""
    <style>
    /* Sfondo generale */
    .stApp {
        background: linear_gradient(135deg, #0f2027, #203a43, #2c5364);
        color: white;
    }
    
    /* Card satinate (Glassmorphism) */
    .parking-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 20px;
        transition: transform 0.3s ease;
    }
    .parking-card:hover {
        transform: translateY(-5px);
        border: 1px solid #00d2ff;
    }
    
    /* Titoli e Testi */
    h1, h2, h3 { color: #00d2ff !important; font-family: 'Inter', sans-serif; }
    .city-label { 
        font-size: 0.8rem; 
        text-transform: uppercase; 
        letter-spacing: 2px; 
        color: #888;
        margin-bottom: 5px;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: rgba(15, 32, 39, 0.8);
    }
    </style>
    """, unsafe_allow_html=True)

# --- CARICAMENTO DATI ---
def load_data():
    try:
        conn = sqlite3.connect("storico_parcheggi.db")
        df = pd.read_sql_query("SELECT * FROM storico", conn)
        conn.close()
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            # Pulizia nomi
            df['citta'] = df['citta'].fillna('Bologna')
        return df
    except:
        return pd.DataFrame()

# --- INTERFACCIA ---
# Logo e Sidebar
LOGO_URL = "https://raw.githubusercontent.com/fperuzzu/parcheggi-automazione/main/logo.png"
st.sidebar.image(LOGO_URL, use_container_width=True)
st.sidebar.markdown("<h2 style='text-align: center; color: white;'>Navigation</h2>", unsafe_allow_html=True)

df = load_data()

if not df.empty:
    citta_list = sorted(df['citta'].unique())
    sel_citta = st.sidebar.multiselect("Filtra per città", citta_list, default=citta_list)
    df_filtrato = df[df['citta'].isin(sel_citta)]

    # Header Principale
    st.markdown("<h1>🛰️ PeruLabTech Smart City Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #aaa;'>Monitoraggio flussi di sosta in tempo reale</p>", unsafe_allow_html=True)

    # --- KPI ATTUALI CON EFFETTO WOW ---
    ultimi = df_filtrato.sort_values('timestamp').groupby(['citta', 'nome']).last().reset_index()
    
    st.subheader("📍 Stato Parcheggi")
    cols = st.columns(3)
    
    for i, row in ultimi.iterrows():
        with cols[i % 3]:
            lib = row['liberi']
            tot = row['totali'] if ('totali' in row and row['totali'] > 0) else (lib + 50)
            occ_perc = round(((tot - lib) / tot * 100), 1)
            color = "#00ff88" if occ_perc < 60 else "#ffcc00" if occ_perc < 85 else "#ff4444"
            
            # HTML Custom Card
            st.markdown(f"""
                <div class="parking-card">
                    <div class="city-label">{row['citta']}</div>
                    <div style="font-size: 1.2rem; font-weight: bold; margin-bottom: 10px;">{row['nome']}</div>
                    <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                        <span style="font-size: 2rem; color: {color}; font-weight: 800;">{lib}</span>
                        <span style="color: #666; margin-bottom: 5px;">/ {tot} Liberi</span>
                    </div>
                    <div style="font-size: 0.8rem; color: #888; margin-top: 10px;">Occupazione: {occ_perc}%</div>
                </div>
            """, unsafe_allow_html=True)
            st.progress(occ_perc / 100)

    # --- STORICO CON GRAFICO AREA ---
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("📈 Analisi Trend (Ultime 24h)")
    
    ieri = datetime.now() - timedelta(hours=24)
    df_graf = df_filtrato[df_filtrato['timestamp'] > ieri].sort_values('timestamp')
    
    if not df_graf.empty:
        fig = go.Figure()
        
        for p_nome in df_graf['nome'].unique():
            p_df = df_graf[df_graf['nome'] == p_nome]
            fig.add_trace(go.Scatter(
                x=p_df['timestamp'], y=p_df['liberi'],
                mode='lines',
                name=p_nome,
                fill='tozeroy', # Effetto area sfumata
                line=dict(width=2),
                hovertemplate="<b>%{y}</b> posti liberi<br>%{x|%H:%M}"
            ))
            
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color="white"),
            xaxis=dict(showgrid=False, zeroline=False),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
            margin=dict(l=20, r=20, t=30, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("⚠️ In attesa di dati dalla rete PeruLabTech...")

st.sidebar.markdown("---")
st.sidebar.caption(f"Engine v2.0 | Last sync: {datetime.now().strftime('%H:%M:%S')}")
