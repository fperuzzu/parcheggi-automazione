import requests
import sqlite3
from datetime import datetime

DB_NAME = "storico_parcheggi.db"

# ---------------------------
# Creazione DB se non esiste
# ---------------------------
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

# ---------------------------
# FETCH LIVE FIRENZE
# ---------------------------
url_firenze = "https://servizi.comune.fi.it/opendata/parcheggi.json"
headers = {"User-Agent": "Mozilla/5.0"}

try:
    r = requests.get(url_firenze, headers=headers, timeout=10)
    r.raise_for_status()
    data = r.json()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    saved = 0

    for p in data:
        nome = p.get("nome")
        liberi = p.get("posti_liberi")
        totali = p.get("posti_totali")
        if nome and liberi is not None and totali is not None:
            cursor.execute(
                "INSERT INTO storico (citta,nome,liberi,totali,timestamp) VALUES (?, ?, ?, ?, ?)",
                ("Firenze", nome, int(liberi), int(totali), now)
            )
            saved += 1
    conn.commit()
    print(f"✅ Salvati {saved} record Firenze nel DB")

except Exception as e:
    print(f"❌ Errore Firenze LIVE: {e}")

conn.close()
