import requests
import sqlite3
from datetime import datetime

# URL TESTATI E CORRETTI PER IL 2026
CITTÀ_CONFIG = {
    "Bologna": {
        "url": "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=50",
        "mapping": {"nome": "parcheggio", "liberi": "posti_liberi"}
    },
    "Firenze": {
        # Questo è l'endpoint reale che alimenta il portale v2.1 che hai fotografato
        "url": "https://opendata.comune.fi.it/api/explore/v2.1/catalog/datasets/firenze-parcheggi-disponibilita-posti-real-time/records?limit=100",
        "mapping": {"nome": "nome", "liberi": "posti_liberi"}
    },
    "Torino": {
        # Cambiato protocollo e host per evitare il blocco DNS di 5T
        "url": "http://storing.5t.torino.it/fdt/extra/ParkingInformation.json",
        "tipo": "json_piatto"
    }
}

DB_NAME = "storico_parcheggi.db"

def esegui_aggiornamento():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Assicuriamoci che la tabella sia pronta
    cursor.execute("CREATE TABLE IF NOT EXISTS storico (citta TEXT, nome TEXT, liberi INTEGER, timestamp DATETIME)")
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Header per far credere al server che siamo un browser umano
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    for citta, info in CITTÀ_CONFIG.items():
        try:
            print(f"📡 Connessione a {citta}...")
            r = requests.get(info["url"], headers=headers, timeout=15)
            r.raise_for_status()
            data = r.json()
            
            count = 0
            # Gestione formati differenti
            records = data if info.get("tipo") == "json_piatto" else data.get('results', [])
            
            for rec in records:
                if info.get("tipo") == "json_piatto":
                    n, l = rec.get('name'), rec.get('free_spaces')
                else:
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
