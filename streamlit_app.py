import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
import folium
import requests
from streamlit_folium import folium_static
from datetime import datetime, timedelta

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# CONFIG
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
st.set_page_config(
    page_title="PeruLabTech | Parcheggi Bologna",
    layout="wide",
    initial_sidebar_state="collapsed"
)

LOGO_URL = "https://raw.githubusercontent.com/fperuzzu/parcheggi-automazione/main/logo.png"
DB_NAME = "storico_parcheggi.db"

COORDINATE = {
    "Piazza VIII Agosto": [44.5011, 11.3438],
    "Riva Reno":          [44.4981, 11.3353],
    "Autostazione":       [44.5049, 11.3456],
    "Staveco":            [44.4842, 11.3429],
    "Parcheggio Aeroporto": [44.5308, 11.2912],
    "Tanari":             [44.5056, 11.3268],
}

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# GLOBAL CSS
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;600&display=swap');

/* Reset & base */
html, body, [data-testid="stAppViewContainer"] {
    background-color: #0a0a0f !important;
    color: #e8e6e0 !important;
}
[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(ellipse 80% 50% at 20% 10%, rgba(255,140,0,0.06) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 80% 80%, rgba(0,180,255,0.04) 0%, transparent 60%),
        #0a0a0f;
}
[data-testid="stHeader"], [data-testid="stToolbar"] { display: none !important; }
[data-testid="stSidebar"] { background: #0f0f16 !important; border-right: 1px solid #1e1e2e; }

/* Typography */
h1,h2,h3,h4 { font-family: 'Bebas Neue', sans-serif !important; letter-spacing: 0.05em; }
p, span, div, label { font-family: 'DM Sans', sans-serif !important; }
code, .mono { font-family: 'DM Mono', monospace !important; }

/* Metric cards */
[data-testid="metric-container"] {
    background: #111118 !important;
    border: 1px solid #1e1e2e !important;
    border-radius: 2px !important;
    padding: 1rem 1.2rem !important;
    transition: border-color 0.2s;
}
[data-testid="metric-container"]:hover { border-color: #ff8c00 !important; }
[data-testid="metric-container"] label {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.7rem !important;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #666 !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-family: 'Bebas Neue', sans-serif !important;
    font-size: 2.2rem !important;
    color: #e8e6e0 !important;
}
[data-testid="metric-container"] [data-testid="stMetricDelta"] {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.72rem !important;
}

/* Dividers */
hr { border-color: #1e1e2e !important; margin: 1.5rem 0; }

/* Plotly chart bg */
.js-plotly-plot .plotly { background: transparent !important; }

/* Selectbox / date_input */
[data-testid="stSelectbox"] > div > div,
[data-testid="stDateInput"] > div > div {
    background: #111118 !important;
    border: 1px solid #1e1e2e !important;
    border-radius: 2px !important;
    color: #e8e6e0 !important;
}

/* Alert boxes */
[data-testid="stAlert"] {
    background: #111118 !important;
    border: 1px solid #ff8c00 !important;
    border-radius: 2px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.8rem !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #0a0a0f; }
::-webkit-scrollbar-thumb { background: #ff8c00; border-radius: 2px; }

/* Section label */
.section-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: #444;
    margin-bottom: 0.3rem;
}
.section-title {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.8rem;
    letter-spacing: 0.05em;
    margin: 0;
    line-height: 1;
}
.pill {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-family: 'DM Mono', monospace;
    font-size: 0.7rem;
    font-weight: 500;
    letter-spacing: 0.05em;
}
.pill-green  { background: rgba(0,200,100,0.12); color: #00c864; border: 1px solid #00c86430; }
.pill-orange { background: rgba(255,160,0,0.12); color: #ffa000; border: 1px solid #ffa00030; }
.pill-red    { background: rgba(255,60,60,0.12);  color: #ff3c3c; border: 1px solid #ff3c3c30; }
</style>
""", unsafe_allow_html=True)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# DATA FETCH
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@st.cache_data(ttl=60)
def fetch_live():
    try:
        url = "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=20"
        r = requests.get(url, timeout=10).json()
        data = []
        for rec in r.get("results", []):
            tot = int(rec.get("posti_totali", 0))
            lib = int(rec.get("posti_liberi", 0))
            if tot > 0:
                data.append({
                    "nome":      rec.get("parcheggio"),
                    "liberi":    lib,
                    "occupati":  tot - lib,
                    "totali":    tot,
                    "timestamp": datetime.now(),
                })
        return pd.DataFrame(data)
    except Exception as e:
        st.warning(f"Errore nel recupero dati live: {e}")
        return pd.DataFrame()


df_live = fetch_live()


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# HEADER
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
col_logo, col_title, col_stats = st.columns([1, 5, 3])

with col_logo:
    st.image(LOGO_URL, width=56)

with col_title:
    now_str = datetime.now().strftime("%d %b %Y  â€”  %H:%M")
    st.markdown(f"""
    <div class="section-label">Sistema di monitoraggio urbano</div>
    <div class="section-title">PARCHEGGI BOLOGNA</div>
    <div style="font-family:'DM Mono',monospace;font-size:0.7rem;color:#555;margin-top:4px">
        Aggiornato {now_str}
    </div>
    """, unsafe_allow_html=True)

with col_stats:
    if not df_live.empty:
        tot_lib  = df_live["liberi"].sum()
        tot_occ  = df_live["occupati"].sum()
        tot_tot  = df_live["totali"].sum()
        pct_glob = int(tot_occ / tot_tot * 100) if tot_tot > 0 else 0
        pill_cls = "pill-green" if pct_glob < 60 else "pill-orange" if pct_glob < 85 else "pill-red"
        st.markdown(f"""
        <div style="text-align:right;padding-top:8px">
            <div style="font-family:'Bebas Neue',sans-serif;font-size:3rem;line-height:1;color:#e8e6e0">
                {tot_lib:,}
                <span style="font-size:1rem;color:#555;font-family:'DM Mono',monospace"> posti liberi</span>
            </div>
            <span class="pill {pill_cls}" style="margin-top:4px">{pct_glob}% OCCUPATO</span>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# ALERT SOGLIE
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if not df_live.empty:
    critici = df_live[df_live.apply(
        lambda r: int((r["occupati"] / r["totali"]) * 100) >= 85, axis=1
    )]
    if not critici.empty:
        nomi = ", ".join(critici["nome"].tolist())
        st.markdown(f"""
        <div style="
            background:#1a0a0a;border:1px solid #ff3c3c33;border-left:3px solid #ff3c3c;
            padding:0.7rem 1rem;border-radius:2px;margin-bottom:1rem;
            font-family:'DM Mono',monospace;font-size:0.78rem;color:#ff7070
        ">
            âš ï¸ &nbsp; ALTA OCCUPAZIONE â†’ {nomi}
        </div>
        """, unsafe_allow_html=True)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# CARDS METRICHE
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
st.markdown('<div class="section-label">DisponibilitÃ  in tempo reale</div>', unsafe_allow_html=True)

if not df_live.empty:
    cols = st.columns(len(df_live))
    for i, row in enumerate(df_live.itertuples()):
        occ = int((row.occupati / row.totali) * 100) if row.totali > 0 else 0
        pill_cls = "pill-green" if occ < 60 else "pill-orange" if occ < 85 else "pill-red"
        delta_color = "normal" if occ < 60 else "off" if occ < 85 else "inverse"
        with cols[i]:
            st.metric(
                label=row.nome,
                value=row.liberi,
                delta=f"{occ}% occupato",
                delta_color=delta_color
            )
else:
    st.info("Nessun dato live disponibile al momento.")

st.markdown("<hr>", unsafe_allow_html=True)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# MAPPA
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
st.markdown('<div class="section-label">Distribuzione geografica</div>', unsafe_allow_html=True)
st.markdown('<div class="section-title" style="margin-bottom:0.8rem">MAPPA PARCHEGGI</div>', unsafe_allow_html=True)

m = folium.Map(
    location=[44.499, 11.343],
    zoom_start=14,
    tiles="cartodbdark_matter"
)

# Build lookup for occupancy
occ_map = {}
if not df_live.empty:
    for row in df_live.itertuples():
        occ_map[row.nome] = int((row.occupati / row.totali) * 100) if row.totali > 0 else 0

for nome, coords in COORDINATE.items():
    occ = occ_map.get(nome, 0)
    color = "#00c864" if occ < 60 else "#ffa000" if occ < 85 else "#ff3c3c"
    liberi = occ_map.get(nome, "N/D")

    folium.CircleMarker(
        location=coords,
        radius=14,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.25,
        weight=2,
        tooltip=folium.Tooltip(f"<b>{nome}</b><br>Occupazione: {occ}%"),
        popup=folium.Popup(
            f"""<div style='font-family:monospace;font-size:12px;min-width:140px'>
            <b>{nome}</b><br>
            Occupazione: <b style='color:{color}'>{occ}%</b>
            </div>""",
            max_width=200
        )
    ).add_to(m)

    # Pulse ring
    folium.CircleMarker(
        location=coords,
        radius=20,
        color=color,
        fill=False,
        weight=1,
        opacity=0.3,
    ).add_to(m)

folium_static(m, width=1100, height=420)

st.markdown("<hr>", unsafe_allow_html=True)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# GRAFICO OCCUPAZIONE ATTUALE (bar)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if not df_live.empty:
    st.markdown('<div class="section-label">Snapshot attuale</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title" style="margin-bottom:0.8rem">OCCUPAZIONE PER PARCHEGGIO</div>', unsafe_allow_html=True)

    df_sorted = df_live.copy()
    df_sorted["pct"] = (df_sorted["occupati"] / df_sorted["totali"] * 100).astype(int)
    df_sorted = df_sorted.sort_values("pct", ascending=True)

    colors = ["#00c864" if p < 60 else "#ffa000" if p < 85 else "#ff3c3c"
              for p in df_sorted["pct"]]

    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        x=df_sorted["pct"],
        y=df_sorted["nome"],
        orientation="h",
        marker_color=colors,
        marker_line_width=0,
        text=[f"{p}%" for p in df_sorted["pct"]],
        textposition="outside",
        textfont=dict(family="DM Mono", size=11, color="#888"),
    ))
    fig_bar.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Mono", color="#888"),
        xaxis=dict(
            range=[0, 115],
            showgrid=True,
            gridcolor="#1e1e2e",
            ticksuffix="%",
            zeroline=False,
            tickfont=dict(size=10),
        ),
        yaxis=dict(
            showgrid=False,
            tickfont=dict(family="DM Sans", size=12, color="#bbb"),
        ),
        margin=dict(l=10, r=40, t=10, b=10),
        height=260,
        bargap=0.35,
        showlegend=False,
    )
    st.plotly_chart(fig_bar, use_container_width=True)
    st.markdown("<hr>", unsafe_allow_html=True)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# TREND STORICO
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
st.markdown('<div class="section-label">Dati storici</div>', unsafe_allow_html=True)

col_title2, col_filters = st.columns([3, 4])
with col_title2:
    st.markdown('<div class="section-title">TREND STORICO</div>', unsafe_allow_html=True)

with col_filters:
    f_col1, f_col2 = st.columns(2)
    with f_col1:
        if "data_att" not in st.session_state:
            st.session_state.data_att = datetime.now().date()
        data_sel = st.date_input(
            "Data",
            value=st.session_state.data_att,
            label_visibility="collapsed"
        )
        st.session_state.data_att = data_sel
    with f_col2:
        parcheggio_sel = st.selectbox(
            "Parcheggio",
            options=["Tutti"] + list(COORDINATE.keys()),
            label_visibility="collapsed"
        )

conn = sqlite3.connect(DB_NAME)
df_storico = pd.read_sql_query(
    f"SELECT * FROM storico WHERE timestamp LIKE '{st.session_state.data_att}%'", conn
)
conn.close()

if not df_storico.empty:
    df_storico["timestamp"] = pd.to_datetime(df_storico["timestamp"])

    nomi_da_mostrare = (
        df_storico["nome"].unique()
        if parcheggio_sel == "Tutti"
        else [parcheggio_sel]
    )

    PALETTE = ["#ff8c00", "#00c864", "#00b4ff", "#ff3c3c", "#b57fff", "#ffd700"]

    fig = go.Figure()
    for idx, p in enumerate(nomi_da_mostrare):
        d = df_storico[df_storico["nome"] == p]
        if d.empty:
            continue
        c = PALETTE[idx % len(PALETTE)]
        fig.add_trace(go.Scatter(
            x=d["timestamp"],
            y=d["liberi"],
            name=p,
            mode="lines",
            line=dict(color=c, width=2),
            fill="tozeroy",
            fillcolor=c.replace("#", "rgba(") + ",0.05)".replace("rgba(", "rgba(")
                if "#" in c else c,
            hovertemplate="<b>%{fullData.name}</b><br>%{x|%H:%M}<br>Liberi: %{y}<extra></extra>",
        ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Mono", color="#666", size=11),
        xaxis=dict(
            showgrid=True,
            gridcolor="#1a1a24",
            zeroline=False,
            tickformat="%H:%M",
            tickfont=dict(size=10),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#1a1a24",
            zeroline=False,
            title="Posti liberi",
            titlefont=dict(size=10, color="#444"),
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor="#1e1e2e",
            borderwidth=1,
            font=dict(size=10),
        ),
        margin=dict(l=10, r=10, t=20, b=10),
        height=360,
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.markdown("""
    <div style="
        background:#111118;border:1px solid #1e1e2e;border-radius:2px;
        padding:2rem;text-align:center;
        font-family:'DM Mono',monospace;font-size:0.8rem;color:#444
    ">
        [ STORICO IN COSTRUZIONE â€” nessun dato per la data selezionata ]
    </div>
    """, unsafe_allow_html=True)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# FOOTER
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("""
<div style="
    display:flex;justify-content:space-between;align-items:center;
    font-family:'DM Mono',monospace;font-size:0.65rem;color:#333;
    padding-bottom:1rem
">
    <span>Â© PERULABTECH â€” Sistema di monitoraggio parcheggi Bologna</span>
    <span>Dati: <a href="https://opendata.comune.bologna.it" style="color:#555;text-decoration:none">
        opendata.comune.bologna.it
    </a></span>
</div>
""", unsafe_allow_html=True)
