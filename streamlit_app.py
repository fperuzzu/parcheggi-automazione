import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
import folium
import requests
from streamlit_folium import folium_static
from datetime import datetime, timedelta

st.set_page_config(page_title="PeruLabTech | Control", layout="wide")

LOGO_URL = "https://raw.githubusercontent.com/fperuzzu/parcheggi-automazione/main/logo.png"

DB_NAME = "storico_parcheggi.db"

GIORNI_ITA = ["Lunedì","Martedì","Mercoledì","Giovedì","Venerdì","Sabato","Domenica"]

COORDINATE = {
"Piazza VIII Agosto":[44.5011,11.3438],
"Riva Reno":[44.4981,11.3353],
"Autostazione":[44.5049,11.3456],
"Staveco":[44.4842,11.3429],
"Parcheggio Aeroporto":[44.5308,11.2912],
"Tanari":[44.5056,11.3268]
}

def fetch_live():

    try:

        url="https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=20"

        r=requests.get(url,timeout=10).json()

        data=[]

        for rec in r.get("results",[]):

            data.append({

                "nome":rec.get("parcheggio"),

                "liberi":int(rec.get("posti_liberi",0)),

                "totali":int(rec.get("posti_totali",0)),

                "timestamp":datetime.now()

            })

        return pd.DataFrame(data)

    except:

        return pd.DataFrame()


df_live=fetch_live()

posti_tot=df_live["liberi"].sum() if not df_live.empty else 0


st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center">

<div style="display:flex;align-items:center;gap:10px">

<img src="{LOGO_URL}" width="50">

<h2>PERULABTECH</h2>

</div>

<h2>{posti_tot}</h2>

</div>
""",unsafe_allow_html=True)


if not df_live.empty:

    cols=st.columns(3)

    for i,row in enumerate(df_live.itertuples()):

        with cols[i%3]:

            occ=int(((row.totali-row.liberi)/row.totali)*100)

            color="green" if occ<60 else "orange" if occ<85 else "red"

            st.metric(row.nome,row.liberi,f"{occ}% occupato")


m=folium.Map(location=[44.495,11.343],zoom_start=14,tiles="cartodbdark_matter")

for row in df_live.itertuples():

    coords=COORDINATE.get(row.nome,[44.49,11.34])

    folium.Marker(coords,popup=row.nome).add_to(m)

folium_static(m,width=1100,height=400)


st.subheader("Trend storico")

if "data_att" not in st.session_state:

    st.session_state.data_att=datetime.now().date()

conn=sqlite3.connect(DB_NAME)

df=pd.read_sql_query(

f"SELECT * FROM storico WHERE timestamp LIKE '{st.session_state.data_att}%'",conn)

conn.close()

if not df.empty:

    df["timestamp"]=pd.to_datetime(df["timestamp"])

    fig=go.Figure()

    for p in df["nome"].unique()[:3]:

        d=df[df["nome"]==p]

        fig.add_trace(go.Scatter(

        x=d["timestamp"],

        y=d["liberi"],

        name=p,

        mode="lines"

        ))

    st.plotly_chart(fig,use_container_width=True)

else:

    st.info("Storico in costruzione")
