import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Configurazione Pagina
st.set_page_config(page_title="PeruLabTech | Smart City", layout="wide")

# --- TRADUZIONE GIORNI ---
GIORNI = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]

# --- CSS EXPERT UI ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    .stApp { background: #0e1117; color: #e0e0e0; }
    
    /* Pulizia Sidebar */
    [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #30363d; }

    /* Badge Giorno */
    .day-badge {
        background: rgba(0, 210, 255, 0.1);
        color: #00d2ff;
        padding: 4px 12px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.9rem;
        border: 1px solid rgba(0, 210, 255, 0.3);
        margin-bottom: 20px;
        display: inline-block;
    }

    /* Card Design */
    .parking-card {
        background: #1c2128;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .city-header {
        color: #8b949e;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 4px;
    }
    .parking-name {
        color: #f0f6fc;
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 12px;
    }
    .stat-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .stat-number { font-size: 1.5rem; font-weight: 700; }
    
    /* Rimuovi margini inutili di Streamlit */
    .block-container { padding-top: 2rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI DATI ---
def get_data(selected_date):
    try:
        conn = sqlite3.connect("storico_parcheggi.db")
        date_str = selected_date.strftime('%Y-%m-%d')
        df = pd.read_sql_query(f"SELECT * FROM storico WHERE timestamp LIKE '{date_str}%'", conn)
        conn.close()
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except: return pd.DataFrame()

# --- SIDEBAR & NAVIGATION ---
LOGO_URL = "https://raw.githubusercontent.com/fperuzzu/parcheggi-automazione/main/logo.png"
st.sidebar.image(LOGO_URL, use_container_width=True)
st.sidebar.markdown("<br>", unsafe_allow_html=True)

data_scelta = st.sidebar.date_input("Seleziona Data", datetime.now())
giorno_sett = GIORNI[data_scelta.weekday()]

# --- MAIN CONTENT ---
df = get_data(data_scelta)

# Badge sottile al posto del titolo gigante
st.markdown(f"<div class='day-badge'>{giorno_sett.upper()} {data_scelta.strftime('%d.%m.%Y')}</div>", unsafe_allow_html=True)

if not df.empty:
    citta_presenti = sorted(df['citta'].unique())
    sel_citta = st.sidebar.multiselect("Città", citta_presenti, default=citta_presenti)
    df_f = df[df['citta'].isin(sel_citta)]

    # --- SEZIONE REAL TIME ---
    ultimi = df_f.sort_values('timestamp').groupby(['citta', 'nome']).last().reset_index()
    
    # Raggruppiamo per città per ordine mentale
    for citta in sel_citta:
        st.markdown(f"<div style='color:#58a6ff; font-weight:600; margin: 10px 0;'>{citta}</div>", unsafe_allow_html=True)
        c_cols = st.columns(3)
        c_data = ultimi[ultimi['citta'] == citta]
        
        for idx, row in enumerate(c_data.itertuples()):
            with c_cols[idx % 3]:
                lib = row.liberi
                tot = row.totali if (hasattr(row, 'totali') and row.totali > 0) else (lib + 20)
                perc = round(((tot - lib) / tot * 100), 1)
                color = "#3fb950" if perc < 60 else "#d29922" if perc < 85 else "#f85149"
                
                st.markdown(f"""
                    <div class="parking-card">
                        <div class="parking-name">{row.nome}</div>
                        <div class="stat-row">
                            <span class="stat-number" style="color:{color}">{lib}</span>
                            <span style="color:#8b949e; font-size:0.85rem;">liberi su {tot}</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                st.progress(min(perc/100, 1.0))

    # --- SEZIONE GRAFICO ---
    st.markdown("<br><div style='color:#8b949e; font-size:0.9rem; font-weight:600;'>TREND OCCUPAZIONE</div>", unsafe_allow_html=True)
    
    fig = go.Figure()
    max_y = 0
    
    for n in df_f['nome'].unique():
        p = df_f[df_f['nome'] == n].sort_values('timestamp')
        current_max = p['totali'].max() if ('totali' in p.columns and p['totali'].max() > 0) else p['liberi'].max()
        if current_max > max_y: max_y = current_max
        
        fig.add_trace(go.Scatter(
            x=p['timestamp'], y=p['liberi'],
            name=n,
            mode='lines',
            line=dict(width=3, shape='spline'), # Linee morbide "WOW"
            fill='tozeroy',
            hovertemplate="<b>%{y}</b> liberi<br>%{x|%H:%M}"
        ))

    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=10, b=0),
        height=450,
        font=dict(color="#8b949e", size=11),
        xaxis=dict(showgrid=False, showline=True, linecolor='#30363d'),
        yaxis=dict(
            range=[0, max_y + 10],
            gridcolor='#30363d',
            fixedrange=True
        ),
        # LEGENDA SPOSTATA SOTTO ORIZZONTALE
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.15,
            xanchor="center",
            x=0.5,
            font=dict(size=10)
        )
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

else:
    st.info("Sincronizzazione dati per la data selezionata...")

st.sidebar.markdown("<br><br><br>", unsafe_allow_html=True)
st.sidebar.caption(f"PeruLabTech Smart System • {datetime.now().year}")
