import requests
import sqlite3
from datetime import datetime

# CONFIGURAZIONE AGGIORNATA 2026
CITTÀ_CONFIG = {
    "Bologna": {
        "url": "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=50",
        "mapping": {"nome": "parcheggio", "liberi": "posti_liberi"}
    },
    "Firenze": {
        # Endpoint ricavato dal portale opendata.comune.fi.it che hai inviato
        "url": "https://opendata.comune.fi.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=100",
        "mapping": {"nome": "nome", "liberi": "posti_liberi"}
    },
    "Torino": {
        "url": "https://storing.5t.torino.it/fdt/extra/ParkingInformation.json",
        "tipo": "json_piatto"
    }
}

DB_NAME = "storico_parcheggi.db"

def esegui_aggiornamento():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # FIX ERRORE COLONNE: Elimina la vecchia tabella se strutturata male e la ricrea
    try:
        cursor.execute("DROP TABLE IF EXISTS storico")
        cursor.execute("CREATE TABLE storico (citta TEXT, nome TEXT, liberi INTEGER, timestamp DATETIME)")
        print("✅ Tabella resettata correttamente.")
    except Exception as e:
        print(f"Nota: {e}")
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    for citta, info in CITTÀ_CONFIG.items():
        try:
            print(f"Tentativo su {citta}...")
            r = requests.get(info["url"], headers=headers, timeout=20)
            r.raise_for_status()
            data = r.json()
            
            count = 0
            # Gestione formati (Torino è una lista, gli altri hanno 'results')
            records = data if info.get("tipo") == "json_piatto" else data.get('results', [])
            
            for rec in records:
                if info.get("tipo") == "json_piatto":
                    n, l = rec.get('name'), rec.get('free_spaces')
                else:
                    n = rec.get(info["mapping"]["nome"])
                    l = rec.get(info["mapping"]["liberi"])
                
                if n and l is not None:
                    # Inseriamo esattamente 4 valori per le 4 colonne: citta, nome, liberi, timestamp
                    cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?)", (citta, str(n), int(l), now))
                    count += 1
            
            print(f"✅ {citta}: Inseriti {count} record.")
        except Exception as e:
            print(f"❌ Errore {citta}: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    esegui_aggiornamento()
