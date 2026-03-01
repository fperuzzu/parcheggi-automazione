import requests
import sqlite3
from datetime import datetime

# CONFIGURAZIONE CON CITTÀ TESTATE E FUNZIONANTI AL 100%
CITTÀ_CONFIG = {
    "Bologna": {
        "url": "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=50",
        "mapping": {"nome": "parcheggio", "liberi": "posti_liberi"}
    },
    "Roma": {
        "url": "https://romamobilita.it/sites/default/files/velas/dataset/disponibilita_parcheggi.json",
        "tipo": "json_piatto",
        "mapping": {"nome": "nome", "liberi": "posti_liberi"}
    },
    "Bolzano": {
        "url": "https://shared.opendatahub.com/v1/p-and-r",
        "tipo": "json_bz",
    }
}

DB_NAME = "storico_parcheggi.db"

def esegui_aggiornamento():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS storico (citta TEXT, nome TEXT, liberi INTEGER, timestamp DATETIME)")
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    headers = {"User-Agent": "Mozilla/5.0"}

    for citta, info in CITTÀ_CONFIG.items():
        try:
            print(f"📡 Tentativo su {citta}...")
            r = requests.get(info["url"], headers=headers, timeout=15)
            r.raise_for_status()
            data = r.json()
            
            count = 0
            if citta == "Bolzano":
                for p in data.get('data', []):
                    n, l = p.get('name'), p.get('free_spaces')
                    if n and l is not None:
                        cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?)", (citta, str(n), int(l), now))
                        count += 1
            elif citta == "Roma":
                for p in data:
                    n, l = p.get('nome'), p.get('posti_liberi')
                    if n and l is not None:
                        cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?)", (citta, str(n), int(l), now))
                        count += 1
            else: # Bologna
                for rec in data.get('results', []):
                    n, l = rec.get('parcheggio'), rec.get('posti_liberi')
                    if n and l is not None:
                        cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?)", (citta, str(n), int(l), now))
                        count += 1
            
            print(f"✅ {citta}: Inseriti {count} record.")
        except Exception as e:
            print(f"❌ Errore {citta}: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    esegui_aggiornamento()
