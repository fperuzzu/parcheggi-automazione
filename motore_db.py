import requests
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime

# CONFIGURAZIONE API AGGIORNATA
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
        "url": "http://opendata.5t.torino.it/get_pk",
        "tipo": "xml"
    }
}

DB_NAME = "storico_parcheggi.db"

def esegui_aggiornamento():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Assicuriamoci che la tabella sia corretta
    cursor.execute("CREATE TABLE IF NOT EXISTS storico (citta TEXT, nome TEXT, liberi INTEGER, timestamp DATETIME)")
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for citta, info in CITTÀ_CONFIG.items():
        try:
            print(f"Tentativo su {citta}...")
            r = requests.get(info["url"], timeout=20)
            r.raise_for_status()
            
            count = 0
            if info.get("tipo") == "xml":
                # Logica per TORINO (XML)
                root = ET.fromstring(r.content)
                for pk in root.findall('stop'):
                    nome = pk.get('name')
                    liberi = pk.get('free_spaces')
                    if nome and liberi is not None:
                        cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?)", (citta, str(nome), int(liberi), now))
                        count += 1
            else:
                # Logica per JSON (Bologna, Milano, Firenze)
                data = r.json()
                records = data.get('results', [])
                for rec in records:
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
