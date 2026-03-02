import requests
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime

# CONFIGURAZIONE CITTÀ
CITTÀ_CONFIG = {
    "Bologna": {
        "url": "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=50",
        "tipo": "json"
    },
    "Torino": {
        "url": "http://opendata.5t.torino.it/get_pk",
        "tipo": "xml_torino"
    }
}

DB_NAME = "storico_parcheggi.db"

def esegui_aggiornamento():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # NON usiamo DROP TABLE per non perdere la cronologia del grafico
    cursor.execute("CREATE TABLE IF NOT EXISTS storico (citta TEXT, nome TEXT, liberi INTEGER, timestamp DATETIME)")
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Questi metadati fanno credere al server di Torino che siamo un vero browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/xml,application/json,text/html",
        "Accept-Language": "it-IT,it;q=0.9"
    }

    for citta, info in CITTÀ_CONFIG.items():
        try:
            print(f"📡 Tentativo su {citta}...")
            r = requests.get(info["url"], headers=headers, timeout=25)
            r.raise_for_status()
            
            count = 0
            if info["tipo"] == "xml_torino":
                # Parsing specifico per il link di Torino (XML)
                root = ET.fromstring(r.content)
                for pk in root.findall('stop'):
                    n, l = pk.get('name'), pk.get('free_spaces')
                    if n and l is not None:
                        cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?)", (citta, str(n), int(l), now))
                        count += 1
            else:
                # Parsing per Bologna (JSON)
                data = r.json()
                for rec in data.get('results', []):
                    n = rec.get('parcheggio')
                    l = rec.get('posti_liberi')
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
