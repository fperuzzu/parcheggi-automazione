import requests
import sqlite3
from datetime import datetime

# CONFIGURAZIONE CITTÀ CON API APERTE E TESTATE
CITTÀ_CONFIG = {
    "Bologna": {
        "url": "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=50",
        "tipo": "json_v2"
    },
    "Venezia": {
        "url": "https://portale.comune.venezia.it/sites/default/files/opendata/parcheggi_smart.json",
        "tipo": "json_venezia"
    }
}

DB_NAME = "storico_parcheggi.db"

def esegui_aggiornamento():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Crea la tabella se non esiste (senza resettare tutto ogni volta, così i grafici crescono)
    cursor.execute("CREATE TABLE IF NOT EXISTS storico (citta TEXT, nome TEXT, liberi INTEGER, timestamp DATETIME)")
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    headers = {"User-Agent": "Mozilla/5.0"}

    for citta, info in CITTÀ_CONFIG.items():
        try:
            print(f"📡 Recupero dati per {citta}...")
            r = requests.get(info["url"], headers=headers, timeout=15)
            r.raise_for_status()
            data = r.json()
            
            count = 0
            if info["tipo"] == "json_venezia":
                for p in data:
                    n, l = p.get('nome'), p.get('posti_liberi')
                    if n and l is not None:
                        cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?)", (citta, str(n), int(l), now))
                        count += 1
            elif info["tipo"] == "json_v2":
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
