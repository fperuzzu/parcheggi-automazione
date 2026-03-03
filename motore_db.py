import requests
import sqlite3
from datetime import datetime

URL_BOLOGNA = "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=50"
DB_NAME = "storico_parcheggi.db"

def esegui_aggiornamento():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS storico (
        citta TEXT,
        nome TEXT,
        liberi INTEGER,
        timestamp DATETIME,
        PRIMARY KEY (citta, nome, timestamp)
    )
    """)

    now_dt = datetime.now()
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")

    try:
        r = requests.get(URL_BOLOGNA, timeout=20)
        r.raise_for_status()
        data = r.json()

        count = 0

        for rec in data.get('results', []):
            nome = rec.get('parcheggio', 'N/D')
            liberi = rec.get('posti_liberi', 0)

            cursor.execute("""
            INSERT OR IGNORE INTO storico VALUES (?, ?, ?, ?)
            """, ("Bologna", nome, liberi, now_str))

            count += 1

        conn.commit()
        print(f"✅ Inseriti {count} record")

    except Exception as e:
        print(f"Errore: {e}")

    finally:
        conn.close()

if __name__ == "__main__":
    esegui_aggiornamento()
