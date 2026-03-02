import requests
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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
    cursor.execute("CREATE TABLE IF NOT EXISTS storico (citta TEXT, nome TEXT, liberi INTEGER, timestamp DATETIME)")
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Configurazione Sessione Professionale
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    # Questo set di dati è quello "pronto" che imita Chrome al 100%
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/xml,application/json,text/html,application/xhtml+xml",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8",
        "Referer": "https://www.google.it/",
        "DNT": "1"
    })

    for citta, info in CITTÀ_CONFIG.items():
        try:
            print(f"📡 Tentativo 'Human-Like' su {citta}...")
            r = session.get(info["url"], timeout=30)
            r.raise_for_status()
            
            count = 0
            if info["tipo"] == "xml_torino":
                root = ET.fromstring(r.content)
                for pk in root.findall('stop'):
                    n, l = pk.get('name'), pk.get('free_spaces')
                    if n and l is not None:
                        cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?)", (citta, str(n), int(l), now))
                        count += 1
            else:
                data = r.json()
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
