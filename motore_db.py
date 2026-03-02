import requests
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime

# CONFIGURAZIONE TESTATA SUI PORTALI CHE HAI TROVATO
CITTÀ_CONFIG = {
    "Bologna": {
        "url": "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=50",
        "tipo": "json"
    },
    "Firenze": {
        "url": "https://opendata.comune.fi.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=100",
        "tipo": "json"
    },
    "Torino": {
        "url": "http://opendata.5t.torino.it/get_pk",
        "tipo": "xml_torino"
    }
}

DB_NAME = "storico_parcheggi.db"

def aggiorna():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Crea la tabella con 4 colonne se non esiste
    cursor.execute("CREATE TABLE IF NOT EXISTS storico (citta TEXT, nome TEXT, liberi INTEGER, timestamp DATETIME)")
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Header fondamentale per bypassare i blocchi dei server di Torino e Firenze
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    for citta, info in CITTÀ_CONFIG.items():
        print(f"--- TENTATIVO {citta.upper()} ---")
        try:
            r = requests.get(info["url"], headers=headers, timeout=25)
            print(f"Status: {r.status_code}")
            
            if r.status_code == 200:
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
                        n = rec.get('parcheggio') or rec.get('nome')
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
    aggiorna()
