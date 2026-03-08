"""
streamlit_app.py  —  ParkPulse | Monitoraggio Parcheggi
──────────────────────────────────────────────────────────
Città supportate in tempo reale:
  • Bologna  (3 parcheggi — API Comune di Bologna)
  • Torino   (~20 parcheggi — API 5T S.r.l.)
  • Firenze  (13 parcheggi — API Firenze Parcheggi)

Lo storico viene popolato da scraper_parcheggi.py
"""

import streamlit as st
import os
import pandas as pd
import plotly.graph_objects as go
import folium
import requests
import xml.etree.ElementTree as ET
from streamlit_folium import folium_static
from datetime import datetime
import time
import io

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="ParkPulse — Parcheggi in Tempo Reale | Bologna Torino Firenze",
    page_icon="🅿",
    layout="wide",
    initial_sidebar_state="auto",
)

LOGO_URL = "https://raw.githubusercontent.com/parkpulse/main/logo.png"
PALETTE  = ["#ff8c00", "#00c864", "#00b4ff", "#ff3c3c", "#b57fff", "#ffd700"]

# Coordinate fallback per Bologna (l'API le include già nella risposta)
COORDINATE_FALLBACK_BO = {
    "VIII Agosto":  [44.500297, 11.345368],
    "Riva Reno":    [44.501153, 11.336062],
    "Autostazione": [44.504422, 11.346514],
}

# Coordinate per Firenze (dal GeoJSON di ogni parcheggio)
# Coordinate Firenze spostate in COORDINATE_FIRENZE_FB (vedi sotto)

# Endpoint unico Firenze — restituisce lista con Id, Name, FreeSpot, Latitude, Longitude
FIRENZE_URL = "https://datastore.comune.fi.it/od/ParkFreeSpot.json"

# Capacità totale fissa per parcheggio (API non fornisce i totali)
# Chiavi usate come match parziale sul campo "Name" dell'API
FIRENZE_CAPACITA = {
    "Parterre":      630,
    "Palazzo":       480,
    "Oltrarno":      392,
    "Fortezza":      650,
    "Stazione":      600,
    "Careggi":       900,
    "Beccaria":      800,
    "Alberti":       540,
    "San Lorenzo":   165,
    "Ambrogio":      398,
    "Porta al Prato":490,
    "Pieraccini":    800,
}

# Coordinate fallback per Firenze (usate se Latitude/Longitude mancano nell'API)
COORDINATE_FIRENZE_FB = {
    "Parterre":      [43.7833, 11.2536],
    "Palazzo":       [43.7745, 11.2558],
    "Oltrarno":      [43.7658, 11.2472],
    "Fortezza":      [43.7847, 11.2478],
    "Stazione":      [43.7762, 11.2491],
    "Careggi":       [43.8067, 11.2581],
    "Beccaria":      [43.7720, 11.2706],
    "Alberti":       [43.7694, 11.2644],
    "San Lorenzo":   [43.7748, 11.2522],
    "Ambrogio":      [43.7686, 11.2619],
    "Porta al Prato":[43.7804, 11.2408],
    "Pieraccini":    [43.8058, 11.2572],
}

# Centro mappa per città
MAPPA_CENTRI = {
    "Bologna": [44.499, 11.343],
    "Torino":  [45.070, 7.686],
    "Firenze": [43.775, 11.255],
}

# ─────────────────────────────────────────────
# TURSO — lettura storico
# ─────────────────────────────────────────────
_TURSO_URL   = os.environ.get("TURSO_URL", "")
_TURSO_TOKEN = os.environ.get("TURSO_TOKEN", "")

@st.cache_data(ttl=300)
def query_storico(citta: str, data_str: str) -> pd.DataFrame:
    """Legge lo storico da Turso via HTTP API."""
    if not _TURSO_URL or not _TURSO_TOKEN:
        return pd.DataFrame()
    try:
        base = _TURSO_URL.replace("libsql://", "https://")
        sql  = "SELECT citta, nome, liberi, totali, timestamp FROM storico WHERE citta=? AND timestamp LIKE ?"
        payload = {
            "requests": [
                {"type": "execute", "stmt": {
                    "sql": sql,
                    "args": [
                        {"type": "text", "value": citta},
                        {"type": "text", "value": f"{data_str}%"},
                    ]
                }},
                {"type": "close"}
            ]
        }
        r = requests.post(
            f"{base}/v2/pipeline",
            json=payload,
            headers={"Authorization": f"Bearer {_TURSO_TOKEN}",
                     "Content-Type": "application/json"},
            timeout=10,
        )
        r.raise_for_status()
        result = r.json()
        rows_data = result["results"][0]["response"]["result"]
        cols  = [c["name"] for c in rows_data["cols"]]
        rows  = [[v["value"] for v in row] for row in rows_data["rows"]]
        return pd.DataFrame(rows, columns=cols)
    except Exception as e:
        st.warning(f"Errore lettura Turso: {e}")
        return pd.DataFrame()

# ─────────────────────────────────────────────
# GOOGLE ANALYTICS 4
# ─────────────────────────────────────────────
GA_ID = "G-H5D1JNW6R1"
st.markdown(f"""
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{GA_ID}', {{
    page_title: 'ParkPulse — Parcheggi in Tempo Reale',
    page_location: window.location.href
  }});

  // Traccia selezione città
  function trackCity(city) {{
    gtag('event', 'select_city', {{
      event_category: 'navigation',
      event_label: city
    }});
  }}

  // Traccia click Naviga → Google Maps
  function trackNavigate(parking, city) {{
    gtag('event', 'navigate_parking', {{
      event_category: 'engagement',
      event_label: parking + ' — ' + city
    }});
  }}

  // Traccia download CSV
  function trackDownload(city, giorni) {{
    gtag('event', 'download_csv', {{
      event_category: 'conversion',
      event_label: city + ' — ' + giorni + 'gg'
    }});
  }}

  // Traccia download PDF
  function trackPDF(city) {{
    gtag('event', 'download_pdf', {{
      event_category: 'conversion',
      event_label: city
    }});
  }}

  // Intercetta click su link "Naviga" e "Waze"
  document.addEventListener('click', function(e) {{
    var a = e.target.closest('a');
    if (!a) return;
    var href = a.href || '';
    if (href.includes('google.com/maps')) {{
      var label = a.closest('[data-parking]')?.dataset.parking || href;
      trackNavigate(label, window.__pp_city || '');
    }}
    if (href.includes('waze.com')) {{
      trackNavigate('waze', window.__pp_city || '');
    }}
    if (href.includes('paypal.me')) {{
      gtag('event', 'donate_click', {{event_category: 'monetization'}});
    }}
  }});
</script>
""", unsafe_allow_html=True)

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
[data-testid="stHeader"], [data-testid="stToolbar"] { display:none !important; }
[data-testid="stSidebar"] { background:#0f0f16 !important; border-right:1px solid #1e1e2e; }

h1,h2,h3,h4 { font-family:'Bebas Neue',sans-serif !important; letter-spacing:0.05em; }
p,span,div,label { font-family:'DM Sans',sans-serif !important; }

[data-testid="metric-container"] {
    background:#111118 !important; border:1px solid #1e1e2e !important;
    border-radius:2px !important; padding:1rem 1.2rem !important;
    transition:border-color 0.2s;
}
[data-testid="metric-container"]:hover { border-color:#ff8c00 !important; }
[data-testid="metric-container"] label {
    font-family:'DM Mono',monospace !important; font-size:0.7rem !important;
    text-transform:uppercase; letter-spacing:0.1em; color:#666 !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-family:'Bebas Neue',sans-serif !important; font-size:2.2rem !important;
    color:#e8e6e0 !important;
}
[data-testid="metric-container"] [data-testid="stMetricDelta"] {
    font-family:'DM Mono',monospace !important; font-size:0.72rem !important;
}

hr { border-color:#1e1e2e !important; margin:1.5rem 0; }
::-webkit-scrollbar { width:4px; height:4px; }
::-webkit-scrollbar-track { background:#0a0a0f; }
::-webkit-scrollbar-thumb { background:#ff8c00; border-radius:2px; }

div[data-baseweb="select"] > div,
[data-testid="stDateInput"] > div > div {
    background:#111118 !important; border:1px solid #1e1e2e !important;
    border-radius:2px !important; color:#e8e6e0 !important;
}

.section-label {
    font-family:'DM Mono',monospace; font-size:0.65rem;
    text-transform:uppercase; letter-spacing:0.15em; color:#444; margin-bottom:0.3rem;
}
.section-title {
    font-family:'Bebas Neue',sans-serif; font-size:1.8rem;
    letter-spacing:0.05em; margin:0; line-height:1;
}
.pill { display:inline-block; padding:2px 10px; border-radius:20px;
        font-family:'DM Mono',monospace; font-size:0.7rem; font-weight:500; letter-spacing:0.05em; }
.pill-green  { background:rgba(0,200,100,0.12);  color:#00c864; border:1px solid #00c86430; }
.pill-orange { background:rgba(255,160,0,0.12);  color:#ffa000; border:1px solid #ffa00030; }
.pill-red    { background:rgba(255,60,60,0.12);  color:#ff3c3c; border:1px solid #ff3c3c30; }
.city-tab { display:inline-block; padding:4px 16px; border-radius:2px; cursor:pointer;
            font-family:'DM Mono',monospace; font-size:0.75rem; letter-spacing:0.1em;
            text-transform:uppercase; margin-right:6px;
            border:1px solid #1e1e2e; color:#666; }

/* TOP BAR */
.topbar {
    display:flex; align-items:center; justify-content:space-between;
    padding:0.55rem 0 0.55rem 0; margin-bottom:0.5rem;
    border-bottom:1px solid #1a1a24;
}
.topbar-brand {
    display:flex; align-items:center; gap:10px;
}
.topbar-title {
    font-family:'DM Mono',monospace; font-size:0.85rem;
    font-weight:500; color:#e8e6e0; letter-spacing:0.06em;
}
.topbar-sub {
    font-family:'DM Mono',monospace; font-size:0.62rem;
    color:#444; letter-spacing:0.08em; margin-top:1px;
}
.topbar-time {
    font-family:'DM Mono',monospace; font-size:0.65rem; color:#444;
}

/* KPI CARDS */
.kpi-grid { display:flex; gap:12px; margin:0.8rem 0 1.2rem 0; }
.kpi-card {
    flex:1; background:#0f0f18; border:1px solid #1e1e2e;
    border-radius:4px; padding:1rem 1.2rem;
    transition:border-color 0.2s;
}
.kpi-card:hover { border-color:#ff8c0055; }
.kpi-num {
    font-family:'Bebas Neue',sans-serif; font-size:2.6rem;
    line-height:1; color:#e8e6e0; letter-spacing:0.02em;
}
.kpi-num.green  { color:#00c864; }
.kpi-num.orange { color:#ffa000; }
.kpi-num.red    { color:#ff3c3c; }
.kpi-label {
    font-family:'DM Mono',monospace; font-size:0.62rem;
    color:#555; text-transform:uppercase; letter-spacing:0.12em;
    margin-top:4px;
}

/* PARKING CARDS */
.park-grid { display:flex; flex-wrap:wrap; gap:10px; margin:0.6rem 0 1.2rem 0; }
.park-card {
    background:#0f0f18; border:1px solid #1e1e2e; border-radius:4px;
    padding:0.85rem 1rem; min-width:140px; flex:1;
    transition:border-color 0.2s, background 0.2s;
}
.park-card:hover { background:#141420; border-color:#333; }
.park-card-name {
    font-family:'DM Mono',monospace; font-size:0.68rem;
    color:#777; text-transform:uppercase; letter-spacing:0.1em;
    margin-bottom:6px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
}
.park-card-num {
    font-family:'Bebas Neue',sans-serif; font-size:2rem;
    line-height:1; margin-bottom:2px;
}
.park-card-sub {
    font-family:'DM Mono',monospace; font-size:0.65rem; color:#555;
}
.park-card-bar {
    height:2px; border-radius:1px; margin-top:8px; background:#1a1a24;
    overflow:hidden;
}
.park-card-bar-fill { height:100%; border-radius:1px; }

/* TAB BUTTONS */
[data-testid="stButton"] > button {
    font-family:'DM Mono',monospace !important;
    font-size:0.72rem !important;
    letter-spacing:0.1em !important;
    text-transform:uppercase !important;
    border-radius:3px !important;
    padding:0.3rem 0 !important;
    transition:all 0.15s !important;
}
[data-testid="stButton"] > button[kind="primary"] {
    background:#ff8c00 !important;
    border-color:#ff8c00 !important;
    color:#0a0a0f !important;
    font-weight:600 !important;
}
[data-testid="stButton"] > button[kind="secondary"] {
    background:transparent !important;
    border-color:#222230 !important;
    color:#555 !important;
}
[data-testid="stButton"] > button[kind="secondary"]:hover {
    border-color:#444 !important;
    color:#aaa !important;
}

/* HERO */
.hero-pitch {
    font-family:'DM Sans',sans-serif; font-size:0.88rem;
    color:#666; line-height:1.6; max-width:520px;
    margin-top:2px;
}
.hero-pitch b { color:#aaa; }

/* CITY CARDS */
.city-cards { display:flex; gap:8px; margin:0.4rem 0; }
.city-card {
    flex:1; padding:10px 14px; border-radius:4px; cursor:pointer;
    border:1px solid #1e1e2e; background:#0f0f18;
    transition:all 0.15s; text-align:center;
}
.city-card.active {
    border-color:#ff8c00;
    background: rgba(255,140,0,0.08);
}
.city-card:hover:not(.active) { border-color:#333; background:#141420; }
.city-card-flag { font-size:1.2rem; display:block; margin-bottom:2px; }
.city-card-name {
    font-family:'DM Mono',monospace; font-size:0.7rem;
    letter-spacing:0.1em; text-transform:uppercase;
    color:#888;
}
.city-card.active .city-card-name { color:#ff8c00; }

/* INSIGHT CARDS */
.insight-grid { display:flex; gap:10px; margin:0.6rem 0 1rem 0; }
.insight-card {
    flex:1; background:#0c0c14; border:1px solid #1a1a28;
    border-radius:4px; padding:0.8rem 1rem;
}
.insight-val {
    font-family:'Bebas Neue',sans-serif; font-size:1.6rem;
    color:#e8e6e0; line-height:1;
}
.insight-val.orange { color:#ffa000; }
.insight-val.green  { color:#00c864; }
.insight-label {
    font-family:'DM Mono',monospace; font-size:0.58rem;
    color:#444; text-transform:uppercase; letter-spacing:0.12em;
    margin-top:3px;
}

/* SIDEBAR CTA */
.cta-block {
    background:#0f0f18; border:1px solid #1e1e2e; border-radius:4px;
    padding:1rem; margin-bottom:0.8rem;
}
.cta-title {
    font-family:'DM Mono',monospace; font-size:0.68rem;
    color:#888; text-transform:uppercase; letter-spacing:0.1em;
    margin-bottom:0.5rem;
}
.cta-btn {
    display:block; width:100%; padding:8px;
    background:transparent; border:1px solid #2a2a3a;
    border-radius:3px; color:#aaa;
    font-family:'DM Mono',monospace; font-size:0.68rem;
    letter-spacing:0.08em; text-align:center;
    cursor:pointer; margin-bottom:6px;
    text-decoration:none; transition:all 0.15s;
}
.cta-btn:hover { border-color:#ff8c00; color:#ff8c00; }
.cta-btn.primary {
    background:#ff8c00; border-color:#ff8c00;
    color:#0a0a0f; font-weight:600;
}

/* ALERT soft */
.alert-soft {
    display:flex; align-items:center; gap:8px;
    background:#1a1200; border:1px solid #ffa00025;
    border-left:3px solid #ffa000;
    padding:0.5rem 0.9rem; border-radius:3px;
    margin-bottom:0.9rem;
    font-family:'DM Mono',monospace; font-size:0.72rem; color:#cc8800;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def hex_to_rgba(hex_color: str, alpha: float = 0.07) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def occ_color(pct: int) -> str:
    return "#00c864" if pct < 60 else "#ffa000" if pct < 85 else "#ff3c3c"


def aggiungi_marker(m, lat, lon, nome, occ, liberi, totali):
    color    = occ_color(occ)
    maps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}&travelmode=driving"
    popup_html = (
        f"<div style='font-family:monospace;font-size:12px;min-width:165px;line-height:1.7'>"
        f"<b style='font-size:13px'>{nome}</b><br>"
        f"<span style='color:#888'>{liberi} / {totali} posti liberi</span><br>"
        f"Occupazione: <b style='color:{color}'>{occ}%</b><br>"
        f"<a href='{maps_url}' target='_blank' "
        f"style='display:inline-block;margin-top:6px;padding:4px 10px;"
        f"background:{color}22;border:1px solid {color}66;"
        f"color:{color};text-decoration:none;border-radius:3px;"
        f"font-size:11px;font-weight:bold'>&#x1F9ED; Naviga con Maps</a>"
        f"</div>"
    )
    folium.CircleMarker(
        location=[lat, lon], radius=14,
        color=color, fill=True, fill_color=color, fill_opacity=0.25, weight=2,
        tooltip=folium.Tooltip(f"<b>{nome}</b> — {liberi} liberi · {occ}% occupato"),
        popup=folium.Popup(popup_html, max_width=230)
    ).add_to(m)
    folium.CircleMarker(
        location=[lat, lon], radius=20,
        color=color, fill=False, weight=1, opacity=0.3
    ).add_to(m)


# ─────────────────────────────────────────────
# FETCH LIVE PER CITTÀ
# ─────────────────────────────────────────────
@st.cache_data(ttl=60)
def fetch_bologna() -> pd.DataFrame:
    try:
        url  = ("https://opendata.comune.bologna.it/api/explore/v2.1/catalog/"
                "datasets/disponibilita-parcheggi-vigente/records?limit=50")
        data = requests.get(url, timeout=10).json()
        rows = []
        for rec in data.get("results", []):
            tot  = int(rec.get("posti_totali") or 0)
            lib  = int(rec.get("posti_liberi") or 0)
            nome = rec.get("parcheggio", "")
            coord = rec.get("coordinate") or {}
            lat  = coord.get("lat") or COORDINATE_FALLBACK_BO.get(nome, [44.499, 11.343])[0]
            lon  = coord.get("lon") or COORDINATE_FALLBACK_BO.get(nome, [44.499, 11.343])[1]
            if tot > 0 and nome:
                rows.append({"nome": nome, "liberi": lib, "occupati": tot - lib,
                             "totali": tot, "lat": lat, "lon": lon})
        return pd.DataFrame(rows)
    except Exception as e:
        st.warning(f"Bologna — errore API: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=60)
def fetch_torino() -> pd.DataFrame:
    # Struttura XML reale: namespace {https://simone.5t.torino.it/ns/traffic_data.xsd}
    # Dati nei tag <PK_data Name="X" Free="12" Total="200" lat="45.0" lng="7.6" .../>
    NS = "{https://simone.5t.torino.it/ns/traffic_data.xsd}"
    for url in ["https://opendata.5t.torino.it/get_pk",
                "http://opendata.5t.torino.it/get_pk"]:
        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; ParcheggiBot/1.0)",
                       "Accept": "application/xml, text/xml, */*"}
            r = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            r.raise_for_status()
            if b"<html" in r.content[:200].lower():
                continue
            root = ET.fromstring(r.content)
            rows = []
            for pk in root.iter(f"{NS}PK_data"):
                a = pk.attrib
                nome   = a.get("Name") or a.get("name")
                liberi = a.get("Free")  or a.get("free")
                totali = a.get("Total") or a.get("total")
                lat    = a.get("lat")   or a.get("Lat")
                lon    = a.get("lng")   or a.get("Lng")
                if not nome or liberi is None or totali is None:
                    continue
                try:
                    lib = int(liberi); tot = int(totali)
                    if tot > 0 and lib >= 0:
                        rows.append({"nome": nome, "liberi": lib, "occupati": tot - lib,
                                     "totali": tot,
                                     "lat": float(lat) if lat else 45.070,
                                     "lon": float(lon) if lon else 7.686})
                except (ValueError, TypeError):
                    continue
            if rows:
                return pd.DataFrame(rows)
        except Exception:
            continue
    return pd.DataFrame(columns=["nome","liberi","occupati","totali","lat","lon"])


@st.cache_data(ttl=120)
def fetch_firenze() -> pd.DataFrame:
    """Endpoint unico ParkFreeSpot.json — lista con Name, FreeSpot, Latitude, Longitude."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; ParcheggiBot/1.0)",
                   "Accept": "application/json, */*"}
        r = requests.get(FIRENZE_URL, headers=headers, timeout=15, allow_redirects=True)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return pd.DataFrame(columns=["nome","liberi","occupati","totali","lat","lon"])

    records = data if isinstance(data, list) else data.get("features", [])
    rows = []
    for rec in records:
        props = rec.get("properties", rec) if isinstance(rec, dict) else {}
        nome   = props.get("Name") or props.get("name")
        liberi = props.get("FreeSpot") or props.get("free_spot") or props.get("FREE_SLOTS")
        lat    = props.get("Latitude")  or props.get("latitude")
        lon    = props.get("Longitude") or props.get("longitude")
        if not nome or liberi is None:
            continue
        # Capacità totale da dizionario fisso (match parziale case-insensitive)
        totali = None
        for chiave, cap in FIRENZE_CAPACITA.items():
            if chiave.lower() in nome.lower():
                totali = cap
                break
        if totali is None:
            totali = max(int(liberi), 1)
        # Coordinate: usa quelle dell'API se disponibili, altrimenti fallback
        try:
            r_lat = float(lat) if lat else None
            r_lon = float(lon) if lon else None
        except (ValueError, TypeError):
            r_lat = r_lon = None
        if not r_lat or not r_lon:
            fb = next((v for k, v in COORDINATE_FIRENZE_FB.items()
                       if k.lower() in nome.lower()), [43.775, 11.255])
            r_lat, r_lon = fb[0], fb[1]
        try:
            lib = int(liberi); tot = int(totali)
            if tot > 0 and 0 <= lib <= tot:
                rows.append({"nome": nome, "liberi": lib, "occupati": tot - lib,
                             "totali": tot, "lat": r_lat, "lon": r_lon})
        except (ValueError, TypeError):
            continue
    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["nome","liberi","occupati","totali","lat","lon"])


def genera_pdf_report(citta: str, df_live: pd.DataFrame,
                      df_storico: pd.DataFrame, data_str: str) -> bytes:
    """Genera report PDF con snapshot live + trend storico."""
    buf = io.BytesIO()
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                        Table, TableStyle, HRFlowable)
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT

        doc = SimpleDocTemplate(buf, pagesize=A4,
                                leftMargin=2*cm, rightMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)

        styles = getSampleStyleSheet()
        BG     = colors.white
        ORANGE = colors.HexColor("#e07000")
        LIGHT  = colors.HexColor("#1a1a1a")
        MUTED  = colors.HexColor("#888888")
        GREEN  = colors.HexColor("#007a3d")
        RED    = colors.HexColor("#cc2200")

        title_style = ParagraphStyle("title", fontSize=22, textColor=ORANGE,
                                     spaceAfter=8, fontName="Helvetica-Bold")
        sub_style   = ParagraphStyle("sub",   fontSize=10, textColor=MUTED,
                                     spaceBefore=4, spaceAfter=14, fontName="Helvetica")
        h2_style    = ParagraphStyle("h2",    fontSize=12, textColor=LIGHT,
                                     spaceBefore=14, spaceAfter=6,
                                     fontName="Helvetica-Bold")
        cell_style  = ParagraphStyle("cell",  fontSize=9,  textColor=LIGHT,
                                     fontName="Helvetica")

        story = []

        # Header
        story.append(Paragraph("ParkPulse", title_style))
        story.append(Paragraph(
            f"Parking Report — {citta} · {data_str}", sub_style))
        story.append(HRFlowable(width="100%", thickness=0.5,
                                color=colors.HexColor("#dddddd")))
        story.append(Spacer(1, 0.4*cm))

        # Snapshot live
        if not df_live.empty:
            story.append(Paragraph("Snapshot Live", h2_style))
            tot_lib = int(df_live["liberi"].sum())
            tot_tot = int(df_live["totali"].sum())
            pct     = int((1 - tot_lib/tot_tot)*100) if tot_tot else 0

            summary_data = [
                ["Posti liberi", "Capacità totale", "Occupazione media"],
                [str(tot_lib), str(tot_tot), f"{pct}%"],
            ]
            t = Table(summary_data, colWidths=[5.5*cm, 5.5*cm, 5.5*cm])
            t.setStyle(TableStyle([
                ("BACKGROUND",  (0,0), (-1,0), colors.HexColor("#f5f5f5")),
                ("BACKGROUND",  (0,1), (-1,1), colors.white),
                ("TEXTCOLOR",   (0,0), (-1,0), MUTED),
                ("TEXTCOLOR",   (0,1), (-1,1), ORANGE),
                ("FONTNAME",    (0,0), (-1,-1), "Helvetica"),
                ("FONTSIZE",    (0,0), (-1,0), 7),
                ("FONTSIZE",    (0,1), (-1,1), 16),
                ("ALIGN",       (0,0), (-1,-1), "CENTER"),
                ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0,0), (-1,-1),
                 [colors.HexColor("#f5f5f5"), colors.white]),
                ("BOX",         (0,0), (-1,-1), 0.5, colors.HexColor("#dddddd")),
                ("INNERGRID",   (0,0), (-1,-1), 0.3, colors.HexColor("#dddddd")),
                ("TOPPADDING",  (0,0), (-1,-1), 8),
                ("BOTTOMPADDING",(0,0),(-1,-1), 8),
            ]))
            story.append(t)
            story.append(Spacer(1, 0.5*cm))

            # Tabella dettaglio parcheggi
            story.append(Paragraph("Dettaglio parcheggi", h2_style))
            rows_pdf = [["Parcheggio", "Liberi", "Totali", "Occupazione"]]
            for _, r in df_live.iterrows():
                occ = int(r["occupati"]/r["totali"]*100) if r["totali"] > 0 else 0
                col = GREEN if occ < 60 else ORANGE if occ < 85 else RED
                rows_pdf.append([
                    r["nome"], str(int(r["liberi"])),
                    str(int(r["totali"])), f"{occ}%"
                ])
            t2 = Table(rows_pdf, colWidths=[8*cm, 3*cm, 3*cm, 3*cm])
            row_colors = [colors.HexColor("#f5f5f5")]
            for _, r in df_live.iterrows():
                occ = int(r["occupati"]/r["totali"]*100) if r["totali"] > 0 else 0
                row_colors.append(colors.white)
            t2.setStyle(TableStyle([
                ("BACKGROUND",   (0,0), (-1,0), colors.HexColor("#eeeeee")),
                ("TEXTCOLOR",    (0,0), (-1,0), MUTED),
                ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
                ("FONTSIZE",     (0,0), (-1,-1), 9),
                ("TEXTCOLOR",    (0,1), (-1,-1), LIGHT),
                ("ALIGN",        (1,0), (-1,-1), "CENTER"),
                ("ROWBACKGROUNDS",(0,1),(-1,-1),
                 [colors.white, colors.HexColor("#fafafa")]),
                ("BOX",          (0,0), (-1,-1), 0.5, colors.HexColor("#dddddd")),
                ("INNERGRID",    (0,0), (-1,-1), 0.3, colors.HexColor("#e0e0e0")),
                ("TOPPADDING",   (0,0), (-1,-1), 6),
                ("BOTTOMPADDING",(0,0), (-1,-1), 6),
            ]))
            story.append(t2)

        # Storico
        if not df_storico.empty:
            story.append(Spacer(1, 0.6*cm))
            story.append(Paragraph(f"Dati storici — {data_str}", h2_style))
            df_s = df_storico.copy()
            df_s["liberi"] = pd.to_numeric(df_s["liberi"], errors="coerce")
            df_s["totali"] = pd.to_numeric(df_s["totali"], errors="coerce")
            df_s = df_s.dropna(subset=["liberi","totali"])
            if not df_s.empty:
                sommario = df_s.groupby("nome").agg(
                    media_liberi=("liberi","mean"),
                    min_liberi=("liberi","min"),
                    max_liberi=("liberi","max"),
                    rilevazioni=("liberi","count"),
                ).reset_index()
                rows_s = [["Parcheggio","Media liberi","Min","Max","Rilevazioni"]]
                for _, r in sommario.iterrows():
                    rows_s.append([
                        r["nome"],
                        f"{r['media_liberi']:.0f}",
                        f"{r['min_liberi']:.0f}",
                        f"{r['max_liberi']:.0f}",
                        str(int(r["rilevazioni"])),
                    ])
                t3 = Table(rows_s, colWidths=[7*cm,3*cm,2.5*cm,2.5*cm,2.5*cm])
                t3.setStyle(TableStyle([
                    ("BACKGROUND",   (0,0), (-1,0), colors.HexColor("#eeeeee")),
                    ("TEXTCOLOR",    (0,0), (-1,0), MUTED),
                    ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
                    ("FONTSIZE",     (0,0), (-1,-1), 9),
                    ("TEXTCOLOR",    (0,1), (-1,-1), LIGHT),
                    ("ALIGN",        (1,0), (-1,-1), "CENTER"),
                    ("ROWBACKGROUNDS",(0,1),(-1,-1),
                     [colors.white, colors.HexColor("#fafafa")]),
                    ("BOX",          (0,0), (-1,-1), 0.5, colors.HexColor("#dddddd")),
                    ("INNERGRID",    (0,0), (-1,-1), 0.3, colors.HexColor("#e0e0e0")),
                    ("TOPPADDING",   (0,0), (-1,-1), 6),
                    ("BOTTOMPADDING",(0,0), (-1,-1), 6),
                ]))
                story.append(t3)

        # Footer
        story.append(Spacer(1, 1*cm))
        story.append(HRFlowable(width="100%", thickness=0.5,
                                color=colors.HexColor("#dddddd")))
        story.append(Paragraph(
            f"ParkPulse — parkpulse.it · Generato il {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            ParagraphStyle("footer", fontSize=7, textColor=MUTED,
                           fontName="Helvetica", spaceBefore=6)
        ))

        doc.build(story)
        return buf.getvalue()

    except ImportError:
        return b""


FETCH_MAP = {
    "Bologna": fetch_bologna,
    "Torino":  fetch_torino,
    "Firenze": fetch_firenze,
}


def scarica_dataset_csv(citta: str, giorni: int = 7) -> bytes:
    """Scarica lo storico degli ultimi N giorni da Turso e restituisce CSV."""
    if not _TURSO_URL or not _TURSO_TOKEN:
        return b""
    try:
        base = _TURSO_URL.replace("libsql://", "https://")
        from datetime import timedelta
        data_inizio = (datetime.now() - timedelta(days=giorni)).strftime("%Y-%m-%d")
        sql = """
            SELECT citta, nome, liberi, totali, timestamp
            FROM storico
            WHERE citta = ? AND timestamp >= ?
            ORDER BY timestamp DESC
        """
        payload = {
            "requests": [
                {"type": "execute", "stmt": {
                    "sql": sql,
                    "args": [
                        {"type": "text", "value": citta},
                        {"type": "text", "value": data_inizio},
                    ]
                }},
                {"type": "close"}
            ]
        }
        r = requests.post(
            f"{base}/v2/pipeline",
            json=payload,
            headers={"Authorization": f"Bearer {_TURSO_TOKEN}",
                     "Content-Type": "application/json"},
            timeout=15,
        )
        r.raise_for_status()
        result = r.json()
        rows_data = result["results"][0]["response"]["result"]
        cols = [c["name"] for c in rows_data["cols"]]
        rows = [[v["value"] for v in row] for row in rows_data["rows"]]
        df = pd.DataFrame(rows, columns=cols)
        # Aggiungi colonna occupazione %
        df["liberi"]  = pd.to_numeric(df["liberi"],  errors="coerce")
        df["totali"]  = pd.to_numeric(df["totali"],  errors="coerce")
        df["occupazione_pct"] = (
            (1 - df["liberi"] / df["totali"]) * 100
        ).round(1)
        return df.to_csv(index=False).encode("utf-8")
    except Exception:
        return b""


# ─────────────────────────────────────────────
# SIDEBAR — CTA + download + caffè
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:0.5rem 0 1rem 0">
        <div style="font-family:'Bebas Neue',sans-serif;font-size:1.6rem;
                    letter-spacing:0.05em;color:#ff8c00">ParkPulse</div>
        <div style="font-family:'DM Mono',monospace;font-size:0.6rem;
                    color:#444;text-transform:uppercase;letter-spacing:0.12em">
            Italy Parking Monitor
        </div>
    </div>
    <hr style="border-color:#1a1a24;margin-bottom:1rem">
    """, unsafe_allow_html=True)

    # ── Download CSV ──
    st.markdown("""
    <div class="cta-block">
        <div class="cta-title">📥 Dataset</div>
        <div style="font-family:'DM Mono',monospace;font-size:0.6rem;
                    color:#555;margin-bottom:8px;line-height:1.6">
            Storico completo · CSV · libero<br>
            Aggiornato ogni 30 min da GitHub Actions
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Selezione città e periodo per il download
    dl_citta = st.selectbox(
        "Città", ["Bologna", "Torino", "Firenze"],
        key="dl_citta", label_visibility="collapsed"
    )
    dl_giorni = st.select_slider(
        "Periodo", options=[1, 3, 7, 14, 30],
        value=7, key="dl_giorni",
        format_func=lambda x: f"Ultimi {x} giorni"
    )

    if st.button("⬇ Scarica CSV", use_container_width=True, type="primary"):
        with st.spinner("Preparazione dataset..."):
            csv_bytes = scarica_dataset_csv(dl_citta, dl_giorni)
        if csv_bytes:
            fname = f"parkpulse_{dl_citta.lower()}_{datetime.now().strftime('%Y%m%d')}.csv"
            st.download_button(
                label=f"💾 Download {dl_citta} ({dl_giorni}gg)",
                data=csv_bytes,
                file_name=fname,
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.warning("Nessun dato disponibile per il periodo selezionato.")

    st.markdown("<hr style='border-color:#1a1a24;margin:1rem 0'>", unsafe_allow_html=True)

    # ── API Access ──
    st.markdown("""
    <div class="cta-block">
        <div class="cta-title">🔌 API Access</div>
        <div style="font-family:'DM Mono',monospace;font-size:0.6rem;
                    color:#555;margin-bottom:8px;line-height:1.6">
            Integra i dati nella tua app.<br>
            Contattaci per accesso e pricing.
        </div>
        <a class="cta-btn"
           href="mailto:info@parkpulse.it?subject=ParkPulse API Access"
           style="display:block;text-align:center;padding:7px;border:1px solid #2a2a3a;
                  border-radius:3px;color:#aaa;font-family:'DM Mono',monospace;
                  font-size:0.68rem;text-decoration:none;">
            Richiedi accesso →
        </a>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<hr style='border-color:#1a1a24;margin:1rem 0'>", unsafe_allow_html=True)

    # ── Sostieni il progetto ──
    st.markdown("""
    <div class="cta-block" style="border-color:#2a1f00">
        <div class="cta-title" style="color:#cc8800">☕ Sostieni il progetto</div>
        <div style="font-family:'DM Mono',monospace;font-size:0.6rem;
                    color:#555;margin-bottom:10px;line-height:1.7">
            ParkPulse è gratuito e open data.<br>
            Se lo trovi utile, offrimi un caffè ☕
        </div>
        <a href="https://paypal.me/parkpulse/3EUR"
           target="_blank"
           style="display:block;text-align:center;padding:9px;
                  background:linear-gradient(135deg,#ff8c00,#e67e00);
                  border-radius:3px;color:#0a0a0f;
                  font-family:'DM Mono',monospace;font-size:0.72rem;
                  font-weight:700;letter-spacing:0.08em;text-decoration:none;">
            ☕ Offrimi un caffè (3€)
        </a>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<hr style='border-color:#1a1a24;margin:1rem 0'>", unsafe_allow_html=True)

    # ── Copertura ──
    st.markdown('<div class="cta-title">📡 Copertura</div>', unsafe_allow_html=True)
    CITTA_INFO = {
        "Bologna":  {"emoji": "🅱", "n": 3},
        "Torino":   {"emoji": "🔺", "n": 36},
        "Firenze":  {"emoji": "🌸", "n": 13},
    }
    for city, info in CITTA_INFO.items():
        st.markdown(f"""
        <div style="display:flex;justify-content:space-between;align-items:center;
                    padding:5px 0;border-bottom:1px solid #111120;
                    font-family:'DM Mono',monospace;font-size:0.68rem">
            <span style="color:#888">{info['emoji']} {city}</span>
            <span style="color:#555">{info['n']} parcheggi</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div style="margin-top:1.2rem;font-family:'DM Mono',monospace;
                font-size:0.58rem;color:#2a2a3a;line-height:1.8">
        Dati aggiornati ogni 30 min<br>
        Fonti: Comune di Bologna,<br>
        5T Torino, Firenze Parcheggi<br><br>
        © ParkPulse
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HERO + SELEZIONE CITTÀ
# ─────────────────────────────────────────────
now_str = datetime.now().strftime("%d %b %Y · %H:%M")

col_hero, col_time = st.columns([5, 2])
with col_hero:
    st.markdown("""
    <div style="padding:0.2rem 0 0.6rem 0">
        <div style="display:flex;align-items:baseline;gap:10px">
            <span style="font-family:'Bebas Neue',sans-serif;font-size:1.6rem;
                         color:#ff8c00;letter-spacing:0.05em">ParkPulse</span>
            <span style="font-family:'DM Mono',monospace;font-size:0.62rem;
                         color:#333;letter-spacing:0.1em">BETA</span>
        </div>
        <div class="hero-pitch">
            Real-time parking availability in Italian cities.<br>
            <b>Monitor occupancy, spot trends, plan your route.</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_time:
    st.markdown(f"""
    <div style="text-align:right;padding-top:14px">
        <div class="topbar-time">🕐 {now_str}</div>
    </div>
    """, unsafe_allow_html=True)

# City cards — selezione visiva
if "citta_sel" not in st.session_state:
    st.session_state.citta_sel = "Bologna"

CITY_META = {
    "Bologna": {"flag": "🅱", "sub": "3 parking"},
    "Torino":  {"flag": "🔺", "sub": "36 parking"},
    "Firenze": {"flag": "🌸", "sub": "13 parking"},
}

c1, c2, c3 = st.columns(3)
_city_changed = False
for col, city in zip([c1, c2, c3], ["Bologna", "Torino", "Firenze"]):
    with col:
        active = st.session_state.citta_sel == city
        if st.button(
            f"{CITY_META[city]['flag']}  {city}  ·  {CITY_META[city]['sub']}",
            key=f"btn_{city}",
            use_container_width=True,
            type="primary" if active else "secondary",
        ):
            if st.session_state.citta_sel != city:
                st.session_state.citta_sel = city
                _city_changed = True

if _city_changed:
    # Traccia cambio città in GA4
    st.markdown(f"""
    <script>
      window.__pp_city = '{st.session_state.citta_sel}';
      if(typeof gtag !== 'undefined') trackCity('{st.session_state.citta_sel}');
    </script>
    """, unsafe_allow_html=True)
    st.rerun()

citta_sel = st.session_state.citta_sel
st.markdown("<div style='border-bottom:1px solid #1a1a24;margin:0.6rem 0 1rem 0'></div>",
            unsafe_allow_html=True)


# ─────────────────────────────────────────────
# CARICA DATI LIVE PER LA CITTÀ SELEZIONATA
# ─────────────────────────────────────────────
with st.spinner(f"Caricamento dati {citta_sel}..."):
    df_live = FETCH_MAP[citta_sel]()


# ─────────────────────────────────────────────
# BANNER DATI NON DISPONIBILI
# ─────────────────────────────────────────────
live_disponibile = not df_live.empty

if not live_disponibile:
    st.markdown(f"""
    <div style="
        background:#0f0f1a;
        border:1px solid #2a2a3e;
        border-left:3px solid #ff8c00;
        padding:1rem 1.4rem;
        border-radius:2px;
        margin-bottom:1.2rem;
        font-family:'DM Mono',monospace;
    ">
        <div style="color:#ff8c00;font-size:0.8rem;font-weight:500;letter-spacing:0.08em;
                    margin-bottom:0.3rem">
            ⚡ DATI LIVE NON DISPONIBILI — {citta_sel.upper()}
        </div>
        <div style="color:#666;font-size:0.72rem;line-height:1.6">
            L'API di {citta_sel} non è raggiungibile da Streamlit Cloud.<br>
            I dati live vengono raccolti dallo <b style="color:#888">scraper in locale</b>
            e salvati nel database storico.<br>
            Seleziona una data nel <b style="color:#888">trend storico</b> per vedere i dati raccolti.
        </div>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# KPI + ALERT
# ─────────────────────────────────────────────
if not df_live.empty:
    tot_lib  = int(df_live["liberi"].sum())
    tot_occ  = int(df_live["occupati"].sum())
    tot_tot  = int(df_live["totali"].sum())
    pct_glob = int(tot_occ / tot_tot * 100) if tot_tot > 0 else 0
    n_park   = len(df_live)
    occ_cls  = "green" if pct_glob < 60 else "orange" if pct_glob < 85 else "red"

    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-num green">{tot_lib:,}</div>
            <div class="kpi-label">Posti liberi</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-num {occ_cls}">{pct_glob}%</div>
            <div class="kpi-label">Occupazione media</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-num">{n_park}</div>
            <div class="kpi-label">Parcheggi monitorati</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-num">{tot_tot:,}</div>
            <div class="kpi-label">Capacità totale</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Insight analitici dallo storico di oggi ──
    df_oggi = query_storico(citta_sel, str(datetime.now().date()))
    if not df_oggi.empty:
        df_oggi["liberi"] = pd.to_numeric(df_oggi["liberi"], errors="coerce")
        df_oggi["totali"] = pd.to_numeric(df_oggi["totali"], errors="coerce")
        df_oggi = df_oggi.dropna(subset=["liberi", "totali"])
        df_oggi = df_oggi[df_oggi["totali"] > 0]
        if not df_oggi.empty:
            df_oggi["occ_pct"] = (1 - df_oggi["liberi"] / df_oggi["totali"]) * 100
            peak_occ   = int(df_oggi["occ_pct"].max())
            avg_occ    = int(df_oggi["occ_pct"].mean())
            n_rilevaz  = len(df_oggi["timestamp"].unique()) if "timestamp" in df_oggi.columns else "—"
            peak_cls   = "orange" if peak_occ < 85 else "red"
            avg_cls    = "green" if avg_occ < 60 else "orange"
            st.markdown(f"""
            <div class="insight-grid">
                <div class="insight-card">
                    <div class="insight-val {peak_cls}">{peak_occ}%</div>
                    <div class="insight-label">Peak occupancy oggi</div>
                </div>
                <div class="insight-card">
                    <div class="insight-val {avg_cls}">{avg_occ}%</div>
                    <div class="insight-label">Media occupazione</div>
                </div>
                <div class="insight-card">
                    <div class="insight-val">{n_rilevaz}</div>
                    <div class="insight-label">Rilevazioni oggi</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Alert soft alta occupazione
    critici = df_live[df_live.apply(
        lambda r: int(r["occupati"] / r["totali"] * 100) >= 85, axis=1
    )]
    if not critici.empty:
        for _, cr in critici.iterrows():
            occ_cr = int(cr["occupati"] / cr["totali"] * 100)
            st.markdown(f"""
            <div class="alert-soft">
                ⚠ Alta occupazione ({occ_cr}%) — <b>{cr["nome"]}</b>
                &nbsp;·&nbsp; {cr["liberi"]} posti rimasti
            </div>
            """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# TROVA PARCHEGGIO ORA
# ─────────────────────────────────────────────
if live_disponibile:
    df_sorted = df_live.copy()
    df_sorted["occ_pct"] = df_sorted.apply(
        lambda r: int(r["occupati"] / r["totali"] * 100) if r["totali"] > 0 else 100, axis=1
    )

    # 1. Più posti liberi in assoluto
    top_liberi = df_sorted.nlargest(1, "liberi").iloc[0]
    # 2. Meno occupato in percentuale (escludendo il primo se uguale)
    top_pct = df_sorted.nsmallest(1, "occ_pct").iloc[0]
    # 3. Storico ultime 2h — meno affollato mediamente
    ora_attuale = datetime.now().hour
    df_storico_oggi = query_storico(citta_sel, str(datetime.now().date()))
    top_storico_nome = None
    if not df_storico_oggi.empty:
        df_storico_oggi["liberi"] = pd.to_numeric(df_storico_oggi["liberi"], errors="coerce")
        df_storico_oggi["totali"] = pd.to_numeric(df_storico_oggi["totali"], errors="coerce")
        df_storico_oggi = df_storico_oggi.dropna(subset=["liberi","totali"])
        df_storico_oggi = df_storico_oggi[df_storico_oggi["totali"] > 0]
        if not df_storico_oggi.empty:
            df_storico_oggi["occ_pct"] = (1 - df_storico_oggi["liberi"] / df_storico_oggi["totali"]) * 100
            media_storico = df_storico_oggi.groupby("nome")["occ_pct"].mean()
            top_storico_nome = media_storico.idxmin()

    def status_emoji(occ):
        return "🟢" if occ < 60 else "🟡" if occ < 85 else "🔴"

    def maps_url(row):
        return f"https://www.google.com/maps/dir/?api=1&destination={row['lat']},{row['lon']}&travelmode=driving"

    # Probabilità oraria dallo storico
    prob_html = ""
    if not df_storico_oggi.empty and "timestamp" in df_storico_oggi.columns:
        try:
            df_storico_oggi["ora"] = pd.to_datetime(
                df_storico_oggi["timestamp"], errors="coerce"
            ).dt.hour
            ora_media = df_storico_oggi.groupby("ora").apply(
                lambda g: 100 - int(g["occ_pct"].mean())
            ).reset_index()
            ora_media.columns = ["ora", "prob_libero"]
            ore_mostra = ora_media[
                (ora_media["ora"] >= max(0, ora_attuale - 2)) &
                (ora_media["ora"] <= min(23, ora_attuale + 4))
            ].sort_values("ora")
            if not ore_mostra.empty:
                prob_items = ""
                for _, row_o in ore_mostra.iterrows():
                    ora_label = f"{int(row_o['ora']):02d}:00"
                    prob = int(row_o["prob_libero"])
                    col_p = "#00c864" if prob >= 50 else "#ffa000" if prob >= 25 else "#ff3c3c"
                    is_now = int(row_o["ora"]) == ora_attuale
                    prob_items += f"""
                    <div style="text-align:center;padding:8px 4px;
                                {'background:#ff8c0018;border-radius:4px;' if is_now else ''}">
                        <div style="font-family:'DM Mono',monospace;font-size:0.62rem;
                                    color:#555">{ora_label}{'<br><span style="color:#ff8c00;font-size:0.55rem">ORA</span>' if is_now else ''}</div>
                        <div style="font-family:'Bebas Neue',sans-serif;font-size:1.3rem;
                                    color:{col_p};line-height:1.1">{prob}%</div>
                    </div>"""
                prob_html = f"""
                <div style="margin-top:1rem;padding-top:1rem;border-top:1px solid #1a1a24">
                    <div style="font-family:'DM Mono',monospace;font-size:0.62rem;color:#555;
                                text-transform:uppercase;letter-spacing:0.12em;margin-bottom:8px">
                        📊 Probabilità di trovare posto — prossime ore
                    </div>
                    <div style="display:grid;grid-template-columns:repeat({len(ore_mostra)},1fr);gap:4px">
                        {prob_items}
                    </div>
                </div>"""
        except Exception:
            pass

    # Card suggerimenti
    suggerimenti = [
        (top_liberi, f"🏆 Più posti liberi — {int(top_liberi['liberi'])} posti disponibili"),
        (top_pct,    f"⚡ Meno affollato — {int(top_pct['occ_pct'])}% occupato"),
    ]
    if top_storico_nome and top_storico_nome in df_sorted["nome"].values:
        row_st = df_sorted[df_sorted["nome"] == top_storico_nome].iloc[0]
        suggerimenti.append((row_st, f"📈 Più stabile oggi — media migliore"))

    sugg_cards = ""
    for i, (row_s, label) in enumerate(suggerimenti):
        occ_s = int(row_s["occ_pct"])
        em    = status_emoji(occ_s)
        url   = maps_url(row_s)
        waze  = f"https://waze.com/ul?ll={row_s['lat']},{row_s['lon']}&navigate=yes"
        rank  = ["1️⃣","2️⃣","3️⃣"][i]
        sugg_cards += f"""
        <div style="background:#0f0f18;border:1px solid #1e1e2e;border-radius:8px;
                    padding:1rem 1.2rem;display:flex;align-items:center;
                    justify-content:space-between;gap:1rem;flex-wrap:wrap">
            <div>
                <div style="font-family:'DM Mono',monospace;font-size:0.6rem;
                            color:#555;text-transform:uppercase;letter-spacing:0.1em;
                            margin-bottom:4px">{rank} {label}</div>
                <div style="font-family:'DM Sans',sans-serif;font-size:1rem;
                            font-weight:600;color:#e8e6e0">{em} {row_s['nome']}</div>
                <div style="font-family:'DM Mono',monospace;font-size:0.72rem;
                            color:#666;margin-top:2px">
                    {int(row_s['liberi'])} liberi · {occ_s}% occupato
                </div>
            </div>
            <div style="display:flex;gap:8px;flex-shrink:0">
                <a href="{url}" target="_blank"
                   style="padding:8px 16px;background:#ff8c00;color:#0a0a0f;
                          border-radius:4px;text-decoration:none;
                          font-family:'DM Mono',monospace;font-size:0.72rem;
                          font-weight:700;white-space:nowrap">
                    🗺 Naviga
                </a>
                <a href="{waze}" target="_blank"
                   style="padding:8px 12px;background:#0f0f18;color:#08b3ff;
                          border:1px solid #08b3ff44;border-radius:4px;
                          text-decoration:none;font-family:'DM Mono',monospace;
                          font-size:0.72rem;white-space:nowrap">
                    Waze
                </a>
            </div>
        </div>"""

    st.markdown(f"""
    <div style="background:#080810;border:1px solid #ff8c0033;border-radius:10px;
                padding:1.2rem 1.4rem;margin-bottom:1.2rem">
        <div style="font-family:'Bebas Neue',sans-serif;font-size:1.4rem;
                    color:#ff8c00;letter-spacing:0.04em;margin-bottom:0.2rem">
            🚗 Trova Parcheggio Ora — {citta_sel}
        </div>
        <div style="font-family:'DM Mono',monospace;font-size:0.65rem;
                    color:#555;margin-bottom:1rem">
            Suggerimenti basati sulla disponibilità in tempo reale
        </div>
        <div style="display:flex;flex-direction:column;gap:10px">
            {sugg_cards}
        </div>
        {prob_html}
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<div style='border-bottom:1px solid #1a1a24;margin:0.5rem 0 1rem 0'></div>",
                unsafe_allow_html=True)


# ─────────────────────────────────────────────
# PARKING CARDS
# ─────────────────────────────────────────────
if live_disponibile:
    st.markdown('<div class="section-label" style="margin-bottom:4px">Parcheggi</div>',
                unsafe_allow_html=True)
    cards_html = '<div class="park-grid">'
    for row in df_live.itertuples():
        occ   = int(row.occupati / row.totali * 100) if row.totali > 0 else 0
        color = "#00c864" if occ < 60 else "#ffa000" if occ < 85 else "#ff3c3c"
        cards_html += f"""
        <div class="park-card" style="border-color:{color}22">
            <div class="park-card-name">{row.nome}</div>
            <div class="park-card-num" style="color:{color}">{row.liberi}</div>
            <div class="park-card-sub">{occ}% occupato · {row.totali} tot</div>
            <div class="park-card-bar">
                <div class="park-card-bar-fill"
                     style="width:{occ}%;background:{color}"></div>
            </div>
        </div>"""
    cards_html += '</div>'
    st.markdown(cards_html, unsafe_allow_html=True)
    st.markdown("<div style='border-bottom:1px solid #1a1a24;margin:1rem 0'></div>",
                unsafe_allow_html=True)


# ─────────────────────────────────────────────
# MAPPA FULL-WIDTH — protagonista
# ─────────────────────────────────────────────
if live_disponibile:
    st.markdown('<div class="section-label" style="margin-bottom:4px">Mappa live</div>',
                unsafe_allow_html=True)
    centro = MAPPA_CENTRI.get(citta_sel, [44.499, 11.343])
    m = folium.Map(
        location=centro, zoom_start=14, tiles="cartodbdark_matter",
        scrollWheelZoom=False,   # no scroll wheel hijack
        dragging=True,
    )
    # Su mobile disabilita il drag per non bloccare lo scroll della pagina
    m.options["tap"] = False
    for row in df_live.itertuples():
        occ = int(row.occupati / row.totali * 100) if row.totali > 0 else 0
        aggiungi_marker(m, row.lat, row.lon, row.nome, occ, row.liberi, row.totali)
    # Inietta CSS per evitare che la mappa catturi il touch scroll
    m.get_root().html.add_child(folium.Element("""
    <style>
    .leaflet-container {
        touch-action: pan-x pan-y !important;
    }
    @media (max-width: 768px) {
        .leaflet-container {
            touch-action: none !important;
            height: 320px !important;
        }
    }
    </style>
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        // Aggiunge un overlay tap-to-interact su mobile
        var maps = document.querySelectorAll('.leaflet-container');
        maps.forEach(function(mapEl) {
            var overlay = document.createElement('div');
            overlay.style.cssText = [
                'position:absolute','top:0','left:0','right:0','bottom:0',
                'z-index:1000','background:rgba(0,0,0,0.5)',
                'display:flex','align-items:center','justify-content:center',
                'color:#ff8c00','font-family:monospace','font-size:13px',
                'letter-spacing:0.08em','cursor:pointer','border-radius:2px',
                'backdrop-filter:blur(1px)',
            ].join(';');
            overlay.textContent = '👆 Tocca per interagire con la mappa';
            overlay.style.display = window.innerWidth <= 768 ? 'flex' : 'none';
            mapEl.style.position = 'relative';
            mapEl.appendChild(overlay);
            overlay.addEventListener('click', function() {
                overlay.style.display = 'none';
            });
        });
    });
    </script>
    """))
    folium_static(m, width=1400, height=520)
    st.markdown("<div style='border-bottom:1px solid #1a1a24;margin:0.8rem 0'></div>",
                unsafe_allow_html=True)

# BAR CHART — sotto la mappa, full-width
if live_disponibile:
    st.markdown('<div class="section-label">Occupazione attuale</div>', unsafe_allow_html=True)
    df_bar = df_live.copy()
    df_bar["pct"] = (df_bar["occupati"] / df_bar["totali"] * 100).astype(int)
    df_bar = df_bar.sort_values("pct", ascending=True)
    df_bar["liberi_label"] = df_bar.apply(
        lambda r: f"{r['nome']} — {r['liberi']} liberi", axis=1
    )
    fig_bar = go.Figure(go.Bar(
        x=list(df_bar["pct"]),
        y=list(df_bar["liberi_label"]),
        orientation="h",
        marker_color=[occ_color(p) for p in df_bar["pct"]],
        marker_line_width=0,
        text=[f"{p}%  ·  {r} liberi" for p, r in zip(df_bar["pct"], df_bar["liberi"])],
        textposition="outside",
        textfont=dict(size=11, color="#777"),
        customdata=list(df_bar["liberi"]),
    ))
    fig_bar.update_xaxes(range=[0, 120], showgrid=True, gridcolor="#1a1a24",
                         ticksuffix="%", zeroline=False, tickfont=dict(size=10, color="#555"))
    fig_bar.update_yaxes(showgrid=False, tickfont=dict(size=11, color="#bbb"))
    fig_bar.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=max(260, len(df_bar) * 38),
        margin=dict(l=10, r=80, t=10, b=10),
        bargap=0.35, showlegend=False,
    )
    st.plotly_chart(fig_bar, use_container_width=True)
    st.markdown("<div style='border-bottom:1px solid #1a1a24;margin:0.8rem 0'></div>",
                unsafe_allow_html=True)

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
        nomi_disponibili = list(df_live["nome"].unique()) if not df_live.empty else []
        parcheggio_sel = st.selectbox(
            "Parcheggio",
            options=["Tutti"] + nomi_disponibili,
            label_visibility="collapsed",
        )

df_storico = query_storico(citta_sel, str(st.session_state.data_att))

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
            name=p, mode="lines+markers",
            line=dict(color=c, width=2),
            marker=dict(size=4, color=c),
            # Niente fill — le aree colorate si sovrapponevano nascondendo le linee
        ))

    if traces:
        fig = go.Figure(data=traces)
        fig.update_xaxes(showgrid=True, gridcolor="#1a1a24", zeroline=False,
                         tickformat="%H:%M", tickfont=dict(color="#888", size=11))
        fig.update_yaxes(showgrid=True, gridcolor="#1a1a24", zeroline=False,
                         tickfont=dict(color="#888", size=11))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=360, margin=dict(l=10, r=10, t=20, b=10),
            hovermode="x unified", showlegend=True,
            legend=dict(
                bgcolor="rgba(10,10,20,0.92)",
                bordercolor="#333344",
                borderwidth=1,
                font=dict(color="#cccccc", size=12),
            ),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nessun dato storico per il parcheggio selezionato.")
else:
    st.markdown("""
    <div style="background:#111118;border:1px solid #1e1e2e;border-radius:2px;
                padding:2rem;text-align:center;
                font-family:'DM Mono',monospace;font-size:0.8rem;color:#444">
        [ STORICO IN COSTRUZIONE — nessun dato per la data selezionata ]
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# REPORT PDF
# ─────────────────────────────────────────────
st.markdown('<div class="section-label" style="margin-top:0.5rem">Report</div>',
            unsafe_allow_html=True)

col_pdf1, col_pdf2, col_pdf3 = st.columns([2, 2, 3])
with col_pdf1:
    pdf_citta = st.selectbox("Città report", ["Bologna","Torino","Firenze"],
                             key="pdf_citta", label_visibility="collapsed",
                             index=["Bologna","Torino","Firenze"].index(citta_sel))
with col_pdf2:
    genera = st.button("📄 Genera Report PDF", use_container_width=True)

if genera:
    with st.spinner("Generazione report..."):
        df_rep_live    = FETCH_MAP[pdf_citta]()
        df_rep_storico = query_storico(pdf_citta, str(datetime.now().date()))
        pdf_bytes = genera_pdf_report(
            pdf_citta, df_rep_live, df_rep_storico,
            datetime.now().strftime("%d/%m/%Y")
        )
    if pdf_bytes:
        fname_pdf = f"parkpulse_{pdf_citta.lower()}_{datetime.now().strftime('%Y%m%d')}.pdf"
        st.download_button(
            label=f"⬇ Download PDF — {pdf_citta}",
            data=pdf_bytes,
            file_name=fname_pdf,
            mime="application/pdf",
        )
    else:
        st.warning("Installa reportlab: pip install reportlab")

st.markdown("<div style='border-bottom:1px solid #1a1a24;margin:1rem 0'></div>",
            unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SEO CONTENT BLOCK
# ─────────────────────────────────────────────
SEO_CONTENT = {
    "Bologna": {
        "intro": "ParkPulse monitora in tempo reale la disponibilità dei parcheggi a Bologna. "
                 "Dati aggiornati ogni 30 minuti dalle API ufficiali del Comune di Bologna.",
        "parcheggi": [
            ("VIII Agosto", "44.500297,11.345368",
             "Il parcheggio VIII Agosto si trova in Piazza VIII Agosto, vicino alla stazione centrale di Bologna. "
             "Uno dei parcheggi più grandi del centro con oltre 600 posti. "
             "Ideale per chi arriva in treno o visita il centro storico."),
            ("Riva Reno", "44.501153,11.336062",
             "Il parcheggio Riva Reno si trova lungo l'omonima via, in posizione centrale. "
             "Ottimo punto di partenza per raggiungere piazza Maggiore a piedi."),
            ("Autostazione", "44.504422,11.346514",
             "Il parcheggio Autostazione è adiacente al terminal degli autobus di Bologna. "
             "Comodo per chi utilizza i mezzi pubblici o arriva in pullman."),
        ],
        "faq": [
            ("Dove parcheggiare a Bologna centro?",
             "I parcheggi più vicini al centro di Bologna sono VIII Agosto, Riva Reno e Autostazione. "
             "ParkPulse mostra in tempo reale quanti posti sono disponibili in ciascuno."),
            ("Quanto costa parcheggiare a Bologna?",
             "Le tariffe variano per parcheggio e fascia oraria. "
             "ParkPulse monitora la disponibilità in tempo reale — per le tariffe consulta il sito del Comune di Bologna."),
            ("A che ora è più facile trovare parcheggio a Bologna?",
             "In base ai dati storici raccolti da ParkPulse, i parcheggi di Bologna sono più liberi nelle prime ore del mattino "
             "e dopo le 20:00. Il picco di occupazione si registra tra le 10:00 e le 13:00."),
        ],
        "keywords": "parcheggi bologna, parcheggio bologna centro, posti liberi bologna oggi, "
                    "dove parcheggiare bologna, VIII agosto bologna parcheggio, "
                    "parcheggio riva reno bologna, parcheggio autostazione bologna",
    },
    "Torino": {
        "intro": "ParkPulse monitora in tempo reale la disponibilità di oltre 36 parcheggi a Torino. "
                 "Dati aggiornati ogni 30 minuti dal sistema 5T (Telematica per i Trasporti di Torino).",
        "parcheggi": [
            ("Piazza Castello", "45.0703,7.6869",
             "Il parcheggio di Piazza Castello è uno dei più centrali di Torino, "
             "a pochi passi dalla Mole Antonelliana e dai principali musei cittadini."),
            ("Porta Nuova", "45.0634,7.6782",
             "Il parcheggio Porta Nuova si trova nelle vicinanze dell'omonima stazione ferroviaria. "
             "Ideale per chi arriva in treno a Torino."),
            ("Lingotto", "45.0333,7.6667",
             "Il parcheggio Lingotto è vicino al centro commerciale e all'auditorium. "
             "Ben collegato con la metropolitana di Torino."),
        ],
        "faq": [
            ("Dove parcheggiare a Torino centro?",
             "I parcheggi più centrali di Torino monitorati da ParkPulse includono Piazza Castello, "
             "Porta Nuova e Porta Palazzo. La dashboard mostra la disponibilità in tempo reale."),
            ("Come funziona il sistema parcheggi di Torino?",
             "Torino utilizza il sistema 5T per monitorare i parcheggi cittadini. "
             "ParkPulse legge questi dati ogni 30 minuti e li visualizza in modo semplice."),
            ("A che ora è più facile trovare parcheggio a Torino?",
             "Secondo i dati storici di ParkPulse, i parcheggi di Torino sono più liberi "
             "nelle prime ore del mattino e la domenica. Il picco di occupazione è tra le 11:00 e le 13:00."),
        ],
        "keywords": "parcheggi torino, parcheggio torino centro, posti liberi torino oggi, "
                    "dove parcheggiare torino, parcheggi 5T torino, parcheggio porta nuova torino, "
                    "parcheggio piazza castello torino",
    },
    "Firenze": {
        "intro": "ParkPulse monitora in tempo reale la disponibilità di 13 parcheggi a Firenze. "
                 "Dati aggiornati ogni 30 minuti da Firenze Parcheggi S.p.A.",
        "parcheggi": [
            ("Parterre", "43.7833,11.2667",
             "Il parcheggio Parterre si trova in Piazza della Libertà, uno dei più grandi di Firenze con 630 posti. "
             "Ottimo punto di accesso al centro storico, raggiungibile a piedi in 10 minuti."),
            ("Oltrarno", "43.7667,11.2500",
             "Il parcheggio Oltrarno è situato nel quartiere omonimo, a pochi minuti da Palazzo Pitti "
             "e Piazzale Michelangelo."),
            ("Fortezza da Basso", "43.7833,11.2500",
             "Il parcheggio Fortezza da Basso si trova vicino all'omonimo complesso monumentale, "
             "comodo per visitare Santa Maria Novella e il centro."),
        ],
        "faq": [
            ("Dove parcheggiare a Firenze centro storico?",
             "I parcheggi più vicini al centro storico di Firenze sono Parterre, Palazzo dei Congressi e Oltrarno. "
             "ParkPulse mostra in tempo reale quanti posti sono liberi."),
            ("Quanto costa parcheggiare a Firenze?",
             "Le tariffe dei parcheggi di Firenze variano. Per i prezzi aggiornati consulta Firenze Parcheggi S.p.A. "
             "ParkPulse si concentra sulla disponibilità in tempo reale."),
            ("Qual è il parcheggio più vicino agli Uffizi a Firenze?",
             "I parcheggi più vicini alla Galleria degli Uffizi sono Oltrarno e Palazzo dei Congressi, "
             "entrambi monitorati da ParkPulse in tempo reale."),
        ],
        "keywords": "parcheggi firenze, parcheggio firenze centro, posti liberi firenze oggi, "
                    "dove parcheggiare firenze, parcheggio parterre firenze, parcheggio oltrarno firenze, "
                    "parcheggio fortezza da basso firenze",
    },
}

if "citta_sel" in st.session_state:
    _seo  = SEO_CONTENT.get(st.session_state.citta_sel, SEO_CONTENT["Bologna"])
    _city = st.session_state.citta_sel

    # ── Schema.org JSON-LD ──
    _schema_parkings = ", ".join(
        '{"@type":"Place","name":"' + p[0] + '","geo":{"@type":"GeoCoordinates",'
        '"latitude":"' + p[1].split(",")[0] + '","longitude":"' + p[1].split(",")[1] + '"}}'
        for p in _seo["parcheggi"]
    )
    _faq_schema = ", ".join(
        '{"@type":"Question","name":"' + q.replace('"', '') + '",'
        '"acceptedAnswer":{"@type":"Answer","text":"' + a.replace('"', '') + '"}}'
        for q, a in _seo["faq"]
    )
    _schema_html = (
        '<script type="application/ld+json">'
        '{"@context":"https://schema.org","@graph":['
        '{"@type":"WebSite","name":"ParkPulse","url":"https://parkpulse.it"},'
        '{"@type":"FAQPage","mainEntity":[' + _faq_schema + ']},'
        '{"@type":"ItemList","name":"Parcheggi ' + _city + '","itemListElement":[' + _schema_parkings + ']}'
        ']}</script>'
    )

    # ── Card parcheggi ──
    _park_cards = ""
    for p in _seo["parcheggi"]:
        _park_cards += (
            '<div style="background:#0a0a0f;border:1px solid #1a1a24;'
            'border-radius:6px;padding:0.8rem 1rem">'
            '<div style="font-family:DM Mono,monospace;font-size:0.68rem;color:#ff8c00;'
            'font-weight:600;margin-bottom:4px">🅿 ' + p[0] + '</div>'
            '<div style="font-family:DM Sans,sans-serif;font-size:0.75rem;color:#444;'
            'line-height:1.6">' + p[2] + '</div>'
            '</div>'
        )

    # ── FAQ ──
    _faq_html = ""
    for q, a in _seo["faq"]:
        _faq_html += (
            '<div style="border-bottom:1px solid #111118;padding:0.6rem 0">'
            '<div style="font-family:DM Sans,sans-serif;font-size:0.78rem;'
            'font-weight:600;color:#555;margin-bottom:2px">' + q + '</div>'
            '<div style="font-family:DM Sans,sans-serif;font-size:0.75rem;'
            'color:#3a3a3a;line-height:1.6">' + a + '</div>'
            '</div>'
        )

    _seo_block = (
        _schema_html +
        '<div style="margin-top:2rem;padding:1.5rem 0;border-top:1px solid #1a1a24">'
        '<div style="font-family:DM Mono,monospace;font-size:0.62rem;color:#333;'
        'text-transform:uppercase;letter-spacing:0.12em;margin-bottom:0.8rem">'
        'ℹ Informazioni — Parcheggi ' + _city + '</div>'
        '<p style="font-family:DM Sans,sans-serif;font-size:0.82rem;color:#444;'
        'line-height:1.7;margin-bottom:1rem">' + _seo["intro"] + '</p>'
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));'
        'gap:0.8rem;margin-bottom:1.2rem">' + _park_cards + '</div>'
        '<div style="margin-top:1rem">' + _faq_html + '</div>'
        '<div style="margin-top:1rem;font-family:DM Mono,monospace;font-size:0.58rem;color:#222">'
        + _seo["keywords"] + '</div>'
        '</div>'
    )
    st.markdown(_seo_block, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("""
<div style="font-family:'DM Mono',monospace;font-size:0.65rem;color:#333;padding-bottom:1rem">
    <div style="display:flex;flex-wrap:wrap;justify-content:space-between;
                align-items:center;gap:8px;margin-bottom:8px">
        <span>© ParkPulse</span>
        <span>
            <a href="https://opendata.comune.bologna.it" style="color:#555;text-decoration:none">Bologna</a>
            &nbsp;·&nbsp;
            <a href="https://opendata.5t.torino.it" style="color:#555;text-decoration:none">Torino</a>
            &nbsp;·&nbsp;
            <a href="https://opendata.comune.fi.it" style="color:#555;text-decoration:none">Firenze</a>
        </span>
    </div>
    <div style="text-align:center;margin-top:4px">
        <a href="https://paypal.me/parkpulse/3EUR" target="_blank"
           style="display:inline-block;color:#ff8c00;text-decoration:none;font-weight:600;
                  background:rgba(255,140,0,0.08);border:1px solid rgba(255,140,0,0.3);
                  padding:6px 20px;border-radius:3px;letter-spacing:0.06em;font-size:0.72rem;">
            ☕ Offrimi un caffè
        </a>
    </div>
</div>
""", unsafe_allow_html=True)
