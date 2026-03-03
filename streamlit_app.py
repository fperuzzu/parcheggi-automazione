import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import os

st.set_page_config(page_title="PeruLabTech Smart Parking", layout="wide")

st.markdown("""
<style>
body {
    background-color: #0e1117;
}
.metric-card {
    background: linear-gradient(135deg, #1f2937, #111827);
    padding: 20px;
    border-radius: 15px;
}
</style>
""", unsafe_allow_html=True)

st.title("🚀 PERULABTECH SMART PARKING CONTROL ROOM")

def load_data():
    if not os.path.exists("storico_parcheggi.db"):
        return pd.DataFrame()
    conn = sqlite3.connect("storico_parcheggi.db")
    df = pd.read_sql_query("SELECT * FROM storico", conn)
    conn.close()
    return df

df_all = load_data()

if not df_all.empty:

    df_all['timestamp'] = pd.to_datetime(df_all['timestamp'])

    citta_list = sorted(df_all['citta'].unique())
    citta_scelta = st.sidebar.selectbox("📍 Città", citta_list)

    df_citta = df_all[df_all['citta'] == citta_scelta]
    parcheggio = st.sidebar.selectbox("🎯 Parcheggio", sorted(df_citta['nome'].unique()))

    df_plot = df_citta[df_citta['nome'] == parcheggio].sort_values('timestamp')

    if not df_plot.empty:

        ultimo = df_plot.iloc[-1]['liberi']

        if len(df_plot) > 1:
            precedente = df_plot.iloc[-2]['liberi']
            delta = ultimo - precedente
        else:
            delta = 0

        capacita = df_plot['liberi'].max()
        occupazione = round((1 - ultimo / capacita) * 100, 1)

        col1, col2, col3 = st.columns(3)

        col1.metric("🚗 Posti Liberi", int(ultimo), delta)
        col2.metric("📊 Occupazione %", f"{occupazione}%")
        col3.metric("📈 Trend", "↓" if delta < 0 else "↑")

        st.markdown("---")

        # Grafico Area
        fig = px.area(
            df_plot,
            x='timestamp',
            y='liberi',
            title=f"Andamento disponibilità - {parcheggio}",
        )

        fig.update_layout(
            template="plotly_dark",
            xaxis_title="Data/Ora",
            yaxis_title="Posti Liberi",
        )

        fig.add_hline(
            y=50,
            line_dash="dash",
            line_color="red",
            annotation_text="Soglia Critica"
        )

        st.plotly_chart(fig, use_container_width=True)

        # Gauge
        gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=occupazione,
            title={'text': "Occupazione %"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "#00ff99"},
                'steps': [
                    {'range': [0, 50], 'color': "green"},
                    {'range': [50, 80], 'color': "orange"},
                    {'range': [80, 100], 'color': "red"},
                ],
            }
        ))

        gauge.update_layout(template="plotly_dark")

        st.plotly_chart(gauge, use_container_width=True)

        # Insight automatico
        media = int(df_plot['liberi'].mean())
        minimo = int(df_plot['liberi'].min())

        st.info(f"""
        🧠 Insight automatico:
        Media posti liberi: {media}
        Minimo registrato: {minimo}
        Variazione ultima rilevazione: {delta}
        """)

else:
    st.warning("Database vuoto.")
