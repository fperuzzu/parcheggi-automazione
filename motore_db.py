import requests
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime

# CONFIGURAZIONE TESTATA AL 01/03/2026
CITTÀ_CONFIG = {
    "Bologna": {
        "url": "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=50",
        "tipo": "json_v2",
        "mapping": {"nome": "parcheggio", "liberi": "posti_liberi"}
    },
    "Firenze": {
        # Endpoint specifico per i record in tempo reale di Firenze
        "url": "https://opendata.comune.fi.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=100",
        "tipo": "json_v2",
        "mapping": {"nome": "nome", "liberi": "posti_liberi"}
    },
    "Torino": {
        # Usiamo l'endpoint JSON di Torino che è più stabile dell'XML
        "url": "https://storing.5t.torino.it/fdt/extra/ParkingInformation.json",
        "tipo": "json_torino"
    }
}

DB_NAME = "storico_parcheggi.db"

def esegui_aggiornamento():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS storico (citta TEXT, nome TEXT, liberi INTEGER, timestamp DATETIME)")
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Header fondamentale per simulare un browser ed evitare il blocco "403 Forbidden"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    for citta, info in CITTÀ_CONFIG.items():
        try:
            print(f"Tentativo su {citta}...")
            r = requests.get(info["url"], headers=headers, timeout=20)
            r.raise_for_status() # Blocca se c'è un errore di connessione
            
            count = 0
            data = r.json()
            
            if info["tipo"] == "json_torino":
                # Torino restituisce una lista semplice di oggetti
                for pk in data:
                    n = pk.get('name')
                    l = pk.get('free_spaces')
                    if n and l is not None:
                        cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?)", (citta, str(n), int(l), now))
                        count += 1
            else:
                # Bologna e Firenze usano il formato catalog/records
                records = data.get('results', [])
                for rec in records:
                    n = rec.get(info["mapping"]["nome"])
                    l = rec.get(info["mapping"]["liberi"])
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
