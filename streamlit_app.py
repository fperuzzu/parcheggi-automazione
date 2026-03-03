import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import os

# --------------------------------------------------
# CONFIGURAZIONE PAGINA
# --------------------------------------------------

st.set_page_config(
    page_title="PeruLabTech Smart Parking",
    layout="centered"
)

# --------------------------------------------------
# STILE CUSTOM (Mobile Friendly)
# --------------------------------------------------

st.markdown("""
<style>
.block-container {
    padding-top: 1.2rem;
    padding-bottom: 1rem;
}

.big-title {
    font-size: 26px;
    font-weight: 700;
    margin-bottom: 10px;
}

.section-divider {
    margin-top: 20px;
    margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class='big-title'>🚀 PERULABTECH SMART PARKING</div>
""", unsafe_allow_html=True)

# --------------------------------------------------
# CARICAMENTO DATI
# --------------------------------------------------

def load_data():
    if not os.path.exists("storico_parcheggi.db"):
        return pd.DataFrame()

    conn = sqlite3.connect("storico_parcheggi.db")
    df = pd.read_sql_query("SELECT * FROM storico", conn)
    conn.close()
    return df


df_all = load_data()

# --------------------------------------------------
# APP
# --------------------------------------------------

if not df_all.empty:

    df_all['timestamp'] = pd.to_datetime(df_all['timestamp'])

    # Selezione città
    citta = st.selectbox(
        "📍 Città",
        sorted(df_all['citta'].unique())
    )

    df_citta = df_all[df_all['citta'] == citta]

    # Selezione parcheggio
    parcheggio = st.selectbox(
        "🎯 Parcheggio",
        sorted(df_citta['nome'].unique())
    )

    df_plot = df_citta[df_citta['nome'] == parcheggio].sort_values('timestamp')

    if not df_plot.empty:

        ultimo = df_plot.iloc[-1]['liberi']

        if len(df_plot) > 1:
            precedente = df_plot.iloc[-2]['liberi']
            delta = int(ultimo - precedente)
        else:
            delta = 0

        capacita = df_plot['liberi'].max()
        occupazione = round((1 - ultimo / capacita) * 100, 1)

        # -------------------------
        # KPI MOBILE STACKED
        # -------------------------

        st.metric("🚗 Posti Liberi", int(ultimo), delta)
        st.metric("📊 Occupazione %", f"{occupazione}%")

        trend_label = "📈 In aumento" if delta > 0 else "📉 In calo"
        st.metric("Trend", trend_label)

        st.divider()

        # -------------------------
        # GRAFICO AREA
        # -------------------------

        fig = px.area(
            df_plot,
            x='timestamp',
            y='liberi'
        )

        fig.update_layout(
            template="plotly_white",
            height=350,
            margin=dict(l=10, r=10, t=30, b=10),
            xaxis_title="",
            yaxis_title="Posti Liberi"
        )

        st.plotly_chart(fig, use_container_width=True)

        # -------------------------
        # GAUGE OCCUPAZIONE
        # -------------------------

        gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=occupazione,
            title={'text': "Occupazione %"},
            gauge={
                'axis': {'range': [0, 100]},
                'steps': [
                    {'range': [0, 50], 'color': "green"},
                    {'range': [50, 80], 'color': "orange"},
                    {'range': [80, 100], 'color': "red"},
                ],
            }
        ))

        gauge.update_layout(
            height=260,
            margin=dict(l=20, r=20, t=30, b=20)
        )

        st.plotly_chart(gauge, use_container_width=True)

        # -------------------------
        # INSIGHT AUTOMATICO
        # -------------------------

        media = int(df_plot['liberi'].mean())
        minimo = int(df_plot['liberi'].min())

        st.divider()

        st.info(f"""
🧠 Insight automatico:

• Media posti liberi: {media}  
• Minimo registrato: {minimo}  
• Ultima variazione: {delta}
        """)

else:
    st.warning("Database vuoto. Esegui prima lo script di aggiornamento.")
