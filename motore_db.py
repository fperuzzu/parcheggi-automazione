import requests
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime

# CONFIGURAZIONE CITTÀ CON ENDPOINT TESTATI (MARZO 2026)
CITTÀ_CONFIG = {
    "Bologna": {
        "url": "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=50",
        "tipo": "opendatasoft"
    },
    "Firenze": {
        # Endpoint ricavato dal portale che hai fotografato
        "url": "https://opendata.comune.fi.it/api/explore/v2.1/catalog/datasets/firenze-parcheggi-disponibilita-posti-real-time/records?limit=100",
        "tipo": "opendatasoft"
    },
    "Pisa": {
        "url": "https://opendata.comune.pisa.it/api/explore/v2.1/catalog/datasets/pisa-disponibilita-parcheggi-pisa-scambiatore-e-multipiano/records?limit=50",
        "tipo": "opendatasoft"
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
    # Ripariamo la tabella se corrotta (errore 5 colonne vs 4 valori)
    cursor.execute("DROP TABLE IF EXISTS storico")
    cursor.execute("CREATE TABLE storico (citta TEXT, nome TEXT, liberi INTEGER, timestamp DATETIME)")
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    for citta, info in CITTÀ_CONFIG.items():
        try:
            print(f"--- DEBUG {citta.upper()} ---")
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
                        n = rec.get('parcheggio') or rec.get('nome') or rec.get('nome_parcheggio')
                        l = rec.get('posti_liberi')
                        if n and l is not None:
                            cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?)", (citta, str(n), int(l), now))
                            count += 1
                print(f"✅ {citta}: Inseriti {count} record.")
        except Exception as e:
            print(f"❌ Errore {citta}: {str(e)[:100]}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    aggiorna()
