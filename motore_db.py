import requests
import sqlite3
from datetime import datetime

# Configurazione delle città
SORGENTI = {
    "Bologna": {
        "url": "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=50",
        "tipo": "json_v2",
        "mapping": {"nome": "parcheggio", "liberi": "posti_liberi"}
    },
    "Milano": {
        "url": "https://dati.comune.milano.it/api/explore/v2.1/catalog/datasets/ds338_pms-disponibilita-parcheggi-pms-scambiatore-e-multipiano/records?limit=50",
        "tipo": "json_v2",
        "mapping": {"nome": "nome_parcheggio", "liberi": "posti_liberi"}
    },
    "Torino": {
        "url": "https://storing.5t.torino.it/fdt/extra/ParkingInformation.json", # Esempio API 5T
        "tipo": "json_flat",
        "mapping": {"nome": "name", "liberi": "free_spaces"}
    }
}

DB_NAME = "storico_parcheggi.db"

def aggiorna_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # AGGIUNGIAMO LA COLONNA 'citta'
    cursor.execute("CREATE TABLE IF NOT EXISTS storico (citta TEXT, nome TEXT, liberi INTEGER, timestamp DATETIME)")
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for citta, info in SORGENTI.items():
        try:
            r = requests.get(info["url"]).json()
            # Qui andrebbe un piccolo parser a seconda del 'tipo' (json_v2, json_flat, ecc.)
            # ... logica di estrazione record ...
            print(f"✅ Dati aggiornati per {citta}")
        except Exception as e:
            print(f"❌ Errore su {citta}: {e}")
            
    conn.commit()
    conn.close()
