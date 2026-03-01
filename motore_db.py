import requests
import sqlite3
from datetime import datetime

# CONFIGURAZIONE TESTATA AL 01/03/2026
CITTÀ_CONFIG = {
    "Bologna": {
        "url": "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=50",
        "mapping": {"nome": "parcheggio", "liberi": "posti_liberi"}
    },
    "Milano": {
        "url": "https://dati.comune.milano.it/api/explore/v2.1/catalog/datasets/ds338_pms-disponibilita-parcheggi-pms-scambiatore-e-multipiano/records?limit=100",
        "mapping": {"nome": "nome_parcheggio", "liberi": "posti_liberi"}
    },
    "Firenze": {
        "url": "https://opendata.comune.fi.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=100",
        "mapping": {"nome": "nome", "liberi": "posti_liberi"}
    },
    "Torino": {
        "url": "https://storing.5t.torino.it/fdt/extra/ParkingInformation.json",
        "tipo": "torino"
    }
}

DB_NAME = "storico_parcheggi.db"

def esegui_aggiornamento():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS storico (citta TEXT, nome TEXT, liberi INTEGER, timestamp DATETIME)")
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Header per evitare blocchi "anti-bot" (soprattutto per Torino)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    for citta, info in CITTÀ_CONFIG.items():
        try:
            print(f"Tentativo su {citta}...")
            r = requests.get(info["url"], headers=headers, timeout=15)
            r.raise_for_status()
            data = r.json()
            
            count = 0
            # Torino restituisce una lista, gli altri comuni un oggetto con 'results'
            records = data if citta == "Torino" else data.get('results', [])
            
            for rec in records:
                if citta == "Torino":
                    nome = rec.get('name')
                    liberi = rec.get('free_spaces')
                else:
                    nome = rec.get(info["mapping"]["nome"])
                    liberi = rec.get(info["mapping"]["liberi"])
                
                if nome and liberi is not None:
                    cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?)", (citta, str(nome), int(liberi), now))
                    count += 1
            
            print(f"✅ {citta}: Inseriti {count} record.")
        except Exception as e:
            print(f"❌ Errore su {citta}: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    esegui_aggiornamento()
