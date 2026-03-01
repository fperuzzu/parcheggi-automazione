import requests
import sqlite3
from datetime import datetime
import time

# URL SEMPLIFICATI E TESTATI
CITTÀ_CONFIG = {
    "Bologna": "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=50",
    "Roma": "https://romamobilita.it/sites/default/files/dataset/parcheggi/disponibilita_parcheggi.json",
    "Puglia": "https://www.dataset.puglia.it/dataset/a681f215-68d0-4d3e-90f7-123456789/resource/12345/download/parcheggi.json"
}

DB_NAME = "storico_parcheggi.db"

def esegui_aggiornamento():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Reset pulito ogni volta per evitare errori di colonne
    cursor.execute("DROP TABLE IF EXISTS storico")
    cursor.execute("CREATE TABLE storico (citta TEXT, nome TEXT, liberi INTEGER, timestamp DATETIME)")
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    for citta, url in CITTÀ_CONFIG.items():
        try:
            print(f"📡 Tentativo su {citta}...")
            time.sleep(2) # Pausa di 2 secondi tra una città e l'altra
            r = requests.get(url, headers=headers, timeout=20)
            
            if r.status_code == 200:
                data = r.json()
                count = 0
                
                # Logica specifica per Bologna (standard v2.1)
                if citta == "Bologna":
                    for rec in data.get('results', []):
                        n, l = rec.get('parcheggio'), rec.get('posti_liberi')
                        if n and l is not None:
                            cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?)", (citta, str(n), int(l), now))
                            count += 1
                
                # Logica generica per altri JSON (Roma/Puglia)
                else:
                    items = data if isinstance(data, list) else data.get('records', [])
                    for item in items:
                        n = item.get('nome') or item.get('name')
                        l = item.get('posti_liberi') or item.get('free')
                        if n and l is not None:
                            cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?)", (citta, str(n), int(l), now))
                            count += 1
                
                print(f"✅ {citta}: Inseriti {count} record.")
            else:
                print(f"❌ {citta}: Errore {r.status_code}")
                
        except Exception as e:
            print(f"⚠️ Errore critico {citta}: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    esegui_aggiornamento()
