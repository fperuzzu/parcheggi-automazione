import requests
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime

CITTÀ_CONFIG = {
    "Bologna": {
        "url": "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=50",
        "tipo": "json_v2",
        "mapping": {"nome": "parcheggio", "liberi": "posti_liberi"}
    },
    "Milano": {
        "url": "https://dati.comune.milano.it/api/explore/v2.1/catalog/datasets/ds338_pms-disponibilita-parcheggi-pms-scambiatore-e-multipiano/records?limit=100",
        "tipo": "json_v2",
        "mapping": {"nome": "nome_parcheggio", "liberi": "posti_liberi"}
    },
    "Firenze": {
        "url": "https://opendata.comune.fi.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=100",
        "tipo": "json_v2",
        "mapping": {"nome": "nome", "liberi": "posti_liberi"}
    },
    "Torino": {
        "url": "http://opendata.5t.torino.it/get_pk",
        "tipo": "xml_5t"
    }
}

DB_NAME = "storico_parcheggi.db"

def esegui_aggiornamento():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS storico (citta TEXT, nome TEXT, liberi INTEGER, timestamp DATETIME)")
    try:
        cursor.execute("SELECT citta FROM storico LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE storico ADD COLUMN citta TEXT DEFAULT 'Bologna'")
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for citta, info in CITTÀ_CONFIG.items():
        try:
            r = requests.get(info["url"], timeout=20)
            if info["tipo"] == "json_v2":
                records = r.json().get('results', [])
                for rec in records:
                    n = rec.get(info["mapping"]["nome"])
                    l = rec.get(info["mapping"]["liberi"])
                    if n and l is not None:
                        cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?)", (citta, str(n), int(l), now))
            elif info["tipo"] == "xml_5t":
                root = ET.fromstring(r.content)
                for pk in root.findall('stop'):
                    n = pk.get('name')
                    l = pk.get('free_spaces')
                    if n and l is not None:
                        cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?)", (citta, str(n), int(l), now))
        except Exception as e:
            print(f"Errore su {citta}: {e}")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    esegui_aggiornamento()
