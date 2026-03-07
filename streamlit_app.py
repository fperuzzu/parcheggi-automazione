import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
import folium
import requests
from streamlit_folium import folium_static
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="PeruLabTech | Parcheggi Bologna",
    layout="wide",
    initial_sidebar_state="collapsed"
)

LOGO_URL = "https://raw.githubusercontent.com/fperuzzu/parcheggi-automazione/main/logo.png"
DB_NAME  = "storico_parcheggi.db"

COORDINATE = {
    "Piazza VIII Agosto":    [44.5011, 11.3438],
    "Riva Reno":             [44.4981, 11.3353],
    "Autostazione":          [44.5049, 11.3456],
    "Staveco":               [44.4842, 11.3429],
    "Parcheggio Aeroporto":  [44.5308, 11.2912],
    "Tanari":                [44.5056, 11.3268],
}

PALETTE = ["#ff8c00", "#00c864", "#00b4ff", "#ff3c3c", "#b57fff", "#ffd700"]

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;600&display=swap');

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

h1,h2,h3,h4 { font-family: 'Bebas Neue', sans-serif !important; letter-spacing: 0.05em; }
p, span, div, label { font-family: 'DM Sans', sans-serif !important; }

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

hr { border-color: #1e1e2e !important; margin: 1.5rem 0; }
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #0a0a0f; }
::-webkit-scrollbar-thumb { background: #ff8c00; border-radius: 2px; }

[data-testid="stSelectbox"] > div > div,
[data-testid="stDateInput"] > div > div {
    background: #111118 !important;
    border: 1px solid #1e1e2e !important;
    border-radius: 2px !important;
    color: #e8e6e0 !important;
}

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
.pill { display:inline-block; padding:2px 10px; border-radius:20px;
        font-family:'DM Mono',monospace; font-size:0.7rem; font-weight:500; letter-spacing:0.05em; }
.pill-green  { background:rgba(0,200,100,0.12);  color:#00c864; border:1px solid #00c86430; }
.pill-orange { background:rgba(255,160,0,0.12);  color:#ffa000; border:1px solid #ffa00030; }
.pill-red    { background:rgba(255,60,60,0.12);   color:#ff3c3c; border:1px solid #ff3c3c30; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def hex_to_rgba(hex_color: str, alpha: float = 0.07) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


@st.cache_data(ttl=60)
def fetch_live() -> pd.DataFrame:
    try:
        url = ("https://opendata.comune.bologna.it/api/explore/v2.1/catalog/"
               "datasets/disponibilita-parcheggi-vigente/records?limit=50")
        r = requests.get(url, timeout=10).json()
        rows = []
        for rec in r.get("results", []):
            tot = int(rec.get("posti_totali") or 0)
            lib = int(rec.get("posti_liberi") or 0)
            if tot > 0:
                rows.append({
                    "nome":     rec.get("parcheggio", ""),
                    "liberi":   lib,
                    "occupati": tot - lib,
                    "totali":   tot,
                })
        return pd.DataFrame(rows)
    except Exception as e:
        st.warning(f"Errore dati live: {e}")
        return pd.DataFrame()


# ─────────────────────────────────────────────
# LIVE DATA
# ─────────────────────────────────────────────
df_live = fetch_live()


# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
col_logo, col_title, col_stats = st.columns([1, 5, 3])

with col_logo:
    st.image(LOGO_URL, width=56)

with col_title:
    now_str = datetime.now().strftime("%d %b %Y  —  %H:%M")
    st.markdown(f"""
    <div class="section-label">Sistema di monitoraggio urbano</div>
    <div class="section-title">PARCHEGGI BOLOGNA</div>
    <div style="font-family:'DM Mono',monospace;font-size:0.7rem;color:#555;margin-top:4px">
        Aggiornato {now_str}
    </div>
    """, unsafe_allow_html=True)

with col_stats:
    if not df_live.empty:
        tot_lib  = int(df_live["liberi"].sum())
        tot_occ  = int(df_live["occupati"].sum())
        tot_tot  = int(df_live["totali"].sum())
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


# ─────────────────────────────────────────────
# ALERT
# ─────────────────────────────────────────────
if not df_live.empty:
    critici = df_live[
        df_live.apply(lambda r: int(r["occupati"] / r["totali"] * 100) >= 85, axis=1)
    ]
    if not critici.empty:
        nomi = ", ".join(critici["nome"].tolist())
        st.markdown(f"""
        <div style="background:#1a0a0a;border:1px solid #ff3c3c33;border-left:3px solid #ff3c3c;
                    padding:0.7rem 1rem;border-radius:2px;margin-bottom:1rem;
                    font-family:'DM Mono',monospace;font-size:0.78rem;color:#ff7070">
            ⚠️ &nbsp; ALTA OCCUPAZIONE → {nomi}
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# METRIC CARDS
# ─────────────────────────────────────────────
st.markdown('<div class="section-label">Disponibilità in tempo reale</div>', unsafe_allow_html=True)

if not df_live.empty:
    cols = st.columns(len(df_live))
    for i, row in enumerate(df_live.itertuples()):
        occ = int(row.occupati / row.totali * 100) if row.totali > 0 else 0
        delta_color = "normal" if occ < 60 else "off" if occ < 85 else "inverse"
        with cols[i]:
            st.metric(label=row.nome, value=row.liberi,
                      delta=f"{occ}% occupato", delta_color=delta_color)
else:
    st.info("Nessun dato live disponibile.")

st.markdown("<hr>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# MAPPA
# ─────────────────────────────────────────────
st.markdown('<div class="section-label">Distribuzione geografica</div>', unsafe_allow_html=True)
st.markdown('<div class="section-title" style="margin-bottom:0.8rem">MAPPA PARCHEGGI</div>', unsafe_allow_html=True)

occ_map = {}
if not df_live.empty:
    for row in df_live.itertuples():
        occ_map[row.nome] = int(row.occupati / row.totali * 100) if row.totali > 0 else 0

m = folium.Map(location=[44.499, 11.343], zoom_start=14, tiles="cartodbdark_matter")

for nome, coords in COORDINATE.items():
    occ   = occ_map.get(nome, 0)
    color = "#00c864" if occ < 60 else "#ffa000" if occ < 85 else "#ff3c3c"
    folium.CircleMarker(
        location=coords, radius=14,
        color=color, fill=True, fill_color=color, fill_opacity=0.25, weight=2,
        tooltip=folium.Tooltip(f"<b>{nome}</b><br>Occupazione: {occ}%"),
        popup=folium.Popup(
            f"<div style='font-family:monospace;font-size:12px'>"
            f"<b>{nome}</b><br>Occupazione: <b style='color:{color}'>{occ}%</b></div>",
            max_width=200
        )
    ).add_to(m)
    folium.CircleMarker(
        location=coords, radius=20,
        color=color, fill=False, weight=1, opacity=0.3
    ).add_to(m)

folium_static(m, width=1100, height=420)
st.markdown("<hr>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# BAR CHART OCCUPAZIONE
# ─────────────────────────────────────────────
if not df_live.empty:
    st.markdown('<div class="section-label">Snapshot attuale</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title" style="margin-bottom:0.8rem">OCCUPAZIONE PER PARCHEGGIO</div>',
                unsafe_allow_html=True)

    df_bar = df_live.copy()
    df_bar["pct"] = (df_bar["occupati"] / df_bar["totali"] * 100).astype(int)
    df_bar = df_bar.sort_values("pct", ascending=True)

    bar_colors = ["#00c864" if p < 60 else "#ffa000" if p < 85 else "#ff3c3c"
                  for p in df_bar["pct"]]

    fig_bar = go.Figure(go.Bar(
        x=list(df_bar["pct"]),
        y=list(df_bar["nome"]),
        orientation="h",
        marker_color=bar_colors,
        marker_line_width=0,
        text=[f"{p}%" for p in df_bar["pct"]],
        textposition="outside",
        textfont=dict(size=11, color="#888"),
    ))
    fig_bar.update_xaxes(range=[0, 115], showgrid=True, gridcolor="#1e1e2e",
                         ticksuffix="%", zeroline=False, tickfont=dict(size=10))
    fig_bar.update_yaxes(showgrid=False, tickfont=dict(size=12, color="#bbb"))
    fig_bar.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=260,
        margin=dict(l=10, r=40, t=10, b=10),
        bargap=0.35,
        showlegend=False,
    )
    st.plotly_chart(fig_bar, use_container_width=True)
    st.markdown("<hr>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# TREND STORICO
# ─────────────────────────────────────────────
st.markdown('<div class="section-label">Dati storici</div>', unsafe_allow_html=True)

col_t, col_f = st.columns([3, 4])
with col_t:
    st.markdown('<div class="section-title">TREND STORICO</div>', unsafe_allow_html=True)
with col_f:
    fc1, fc2 = st.columns(2)
    with fc1:
        if "data_att" not in st.session_state:
            st.session_state.data_att = datetime.now().date()
        data_sel = st.date_input("Data", value=st.session_state.data_att,
                                 label_visibility="collapsed")
        st.session_state.data_att = data_sel
    with fc2:
        parcheggio_sel = st.selectbox(
            "Parcheggio",
            options=["Tutti"] + list(COORDINATE.keys()),
            label_visibility="collapsed"
        )

try:
    conn = sqlite3.connect(DB_NAME)
    df_storico = pd.read_sql_query(
        "SELECT * FROM storico WHERE timestamp LIKE ?", conn,
        params=(f"{st.session_state.data_att}%",)
    )
    conn.close()
except Exception as e:
    df_storico = pd.DataFrame()
    st.warning(f"Errore lettura DB: {e}")

if not df_storico.empty:
    df_storico["timestamp"] = pd.to_datetime(df_storico["timestamp"])
    df_storico["liberi"]    = pd.to_numeric(df_storico["liberi"], errors="coerce")

    nomi = (list(df_storico["nome"].unique())
            if parcheggio_sel == "Tutti" else [parcheggio_sel])

    traces = []
    for idx, p in enumerate(nomi):
        d = df_storico[df_storico["nome"] == p].dropna(subset=["liberi"])
        if d.empty:
            continue
        c = PALETTE[idx % len(PALETTE)]
        traces.append(go.Scatter(
            x=list(d["timestamp"]),
            y=list(d["liberi"].astype(int)),
            name=p,
            mode="lines",
            line=dict(color=c, width=2),
            fill="tozeroy",
            fillcolor=hex_to_rgba(c, 0.07),
        ))

    if traces:
        fig = go.Figure(data=traces)
        fig.update_xaxes(showgrid=True, gridcolor="#1a1a24",
                         zeroline=False, tickformat="%H:%M")
        fig.update_yaxes(showgrid=True, gridcolor="#1a1a24", zeroline=False)
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=360,
            margin=dict(l=10, r=10, t=20, b=10),
            hovermode="x unified",
            showlegend=True,
            legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#1e1e2e", borderwidth=1),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nessun dato per il parcheggio selezionato in questa data.")
else:
    st.markdown("""
    <div style="background:#111118;border:1px solid #1e1e2e;border-radius:2px;
                padding:2rem;text-align:center;
                font-family:'DM Mono',monospace;font-size:0.8rem;color:#444">
        [ STORICO IN COSTRUZIONE — nessun dato per la data selezionata ]
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("""
<div style="display:flex;justify-content:space-between;align-items:center;
            font-family:'DM Mono',monospace;font-size:0.65rem;color:#333;padding-bottom:1rem">
    <span>© PERULABTECH — Sistema di monitoraggio parcheggi Bologna</span>
    <span>Dati: <a href="https://opendata.comune.bologna.it" style="color:#555;text-decoration:none">
        opendata.comune.bologna.it
    </a></span>
</div>
""", unsafe_allow_html=True)
