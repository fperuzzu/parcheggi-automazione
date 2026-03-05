import requests
import sqlite3
import pandas as pd
from datetime import datetime

DB_NAME = "storico_parcheggi.db"

# ---------------------------
# Creazione DB se non esiste
# ---------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS storico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            citta TEXT,
            nome TEXT,
            liberi INTEGER,
            totali INTEGER,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

# ---------------------------
# Fetch dati LIVE Firenze
# ---------------------------
def fetch_firenze_live():
    url = "https://servizi.comune.fi.it/opendata/parcheggi.json"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        records = []
        for p in data:
            nome = p.get("nome")
            liberi = p.get("posti_liberi")
            totali = p.get("posti_totali")
            if nome and liberi is not None and totali is not None:
                records.append({
                    "citta": "Firenze",
                    "nome": nome,
                    "liberi": int(liberi),
                    "totali": int(totali),
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
        return pd.DataFrame(records)
    except Exception as e:
        print(f"❌ Errore Firenze LIVE: {e}")
        return pd.DataFrame()

# ---------------------------
# Salvataggio su DB
# ---------------------------
def save_to_db(df):
    if df.empty:
        print("⚠ Nessun dato da salvare")
        return
    conn = sqlite3.connect(DB_NAME)
    df.to_sql("storico", conn, if_exists="append", index=False)
    conn.close()
    print(f"✅ Salvati {len(df)} record Firenze")

# ---------------------------
# MAIN
# ---------------------------
if __name__ == "__main__":
    init_db()
    df = fetch_firenze_live()
    save_to_db(df)

    # Debug verifica
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM storico WHERE citta='Firenze'")
    count = cursor.fetchone()[0]
    print(f"📊 Record Firenze nel DB: {count}")
    conn.close()
