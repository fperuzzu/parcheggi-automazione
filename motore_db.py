import requests
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime
import re

URL_TORINO_PROXY = "https://script.google.com/macros/s/AKfycbxST_tjOBH2v3ERqb_dif6kazstQr8qZkwwKnrgGtfPkpjkqARpaiwYIq-f7epgVNz_/exec"
URL_BOLOGNA = "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=50"
DB_NAME = "storico_parcheggi.db"

def pulisci_xml(testo):
    # Rimuove caratteri illegali che rompono l'XML (invalid tokens)
    testo = re.sub(r'[^\x09\x0A\x0D\x20-\x7E\x85\xA0-\xFF]', '', testo)
    # Protegge le ampersand (&) se non sono già codificate
    testo = testo.replace(' & ', ' &amp; ')
    return testo

def esegui_aggiornamento():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS storico (citta TEXT, nome TEXT, liberi INTEGER, timestamp DATETIME)")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # --- TORINO ---
    try:
        print("📡 Recupero Torino via Proxy...")
        r = requests.get(URL_TORINO_PROXY, timeout=30)
        r.raise_for_status()
        
        # Pulizia e ricerca tag iniziale
        testo = pulisci_xml(r.text)
        inizio = testo.find('<pk_information')
        if inizio != -1:
            testo = testo[inizio:]
        
        # Carichiamo i dati
        root = ET.fromstring(testo)
        count_to = 0
        for pk in root.iter('stop'):
            n = pk.get('name')
            l = pk.get('free_spaces')
            if n and l is not None:
                cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?)", ("Torino", str(n), int(l), now))
                count_to += 1
        print(f"✅ Torino: Inseriti {count_to} record.")
    except Exception as e:
        print(f"❌ Errore Torino (XML Cleanup): {e}")

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
