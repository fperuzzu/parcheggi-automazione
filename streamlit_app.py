import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

st.set_page_config(page_title="Analisi Parcheggi", layout="wide")
st.title("📊 Monitoraggio Storico Parcheggi")

# Forza il percorso assoluto del database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "storico_parcheggi.db")

def get_data():
    # Se il file esiste, lo apriamo
    if os.path.exists(DB_NAME):
        try:
            conn = sqlite3.connect(DB_NAME)
            df = pd.read_sql_query("SELECT * FROM storico", conn)
            conn.close()
            return df
        except Exception as e:
            st.error(f"Errore tecnico nel database: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

df = get_data()
