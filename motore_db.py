import requests
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime
import re

URL_TORINO_PROXY = "https://script.google.com/macros/s/AKfycbxST_tjOBH2v3ERqb_dif6kazstQr8qZkwwKnrgGtfPkpjkqARpaiwYIq-f7epgVNz_/exec"
URL_BOLOGNA = "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=50"

DB_NAME = "storico_parcheggi.db"

def esegui_aggiornamento():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS storico (citta TEXT, nome TEXT, liberi INTEGER, timestamp DATETIME)")
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # --- TORINO (con Pulizia Dati) ---
    try:
        print("📡 Recupero Torino via Proxy...")
        r = requests.get(URL_TORINO_PROXY, timeout=30)
        r.raise_for_status()
        
        # Pulizia: rimuoviamo eventuali dichiarazioni XML duplicate o spazi strani
        xml_data = r.text.strip()
        if not xml_data.startswith('<'):
             xml_data = xml_data[xml_data.find('<'):]
             
        root = ET.fromstring(xml_data)
        count_to = 0
        for pk in root.findall('.//stop'): # Cerca in tutto l'albero
            n, l = pk.get('name'), pk.get('free_spaces')
            if n and l is not None:
                cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?)", ("Torino", str(n), int(l), now))
                count_to += 1
        print(f"✅ Torino: Inseriti {count_to} record.")
    except Exception as e:
        print(f"❌ Errore Torino (XML): {e}")

    # --- BOLOGNA ---
    try:
        print("📡 Recupero Bologna...")
        r = requests.get(URL_BOLOGNA, timeout=30)
        r.raise_for_status()
        data = r.json()
        count_bo = 0
        for rec in data.get('results', []):
            n, l = rec.get('parcheggio'), rec.get('posti_liberi')
            if n and l is not None:
                cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?)", ("Bologna", str(n), int(l), now))
                count_bo += 1
        print(f"✅ Bologna: Inseriti {count_bo} record.")
    except Exception as e:
        print(f"❌ Errore Bologna: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    esegui_aggiornamento()
