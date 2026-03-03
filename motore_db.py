import requests
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

DB_NAME = "storico_parcheggi.db"

def esegui_aggiornamento():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS storico (
            citta TEXT, nome TEXT, liberi INTEGER, totali INTEGER, timestamp DATETIME
        )
    """)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # --- BOLOGNA ---
    try:
        r_bo = requests.get("https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=50", timeout=15).json()
        for rec in r_bo.get('results', []):
            cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?, ?)", 
                         ("Bologna", rec.get('parcheggio'), rec.get('posti_liberi'), rec.get('posti_totali'), now))
        print("✅ Bologna aggiornata")
    except Exception as e: print(f"❌ Errore Bologna: {e}")

    # --- TORINO (5T) ---
    try:
        r_to = requests.get("http://opendata.5t.torino.it/get_pk", timeout=15)
        root = ET.fromstring(r_to.content)
        for pk in root.findall('Table'):
            nome = pk.findtext('Name')
            liberi = pk.findtext('Free')
            totali = pk.findtext('Total')
            if nome and liberi is not None:
                cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?, ?)", ("Torino", nome, int(liberi), int(totali) if totali else None, now))
        print("✅ Torino aggiornata")
    except Exception as e: print(f"❌ Errore Torino: {e}")

    # --- FIRENZE ---
    try:
        # Usiamo l'endpoint specifico per i parcheggi in tempo reale
        r_fi = requests.get("https://opendata.comune.fi.it/api/action/datastore_search?resource_id=07ccbe04-2041-4357-b501-8f52f3607062", timeout=15).json()
        for rec in r_fi.get('result', {}).get('records', []):
            nome = rec.get('description') or rec.get('nome')
            liberi = rec.get('free_spaces') or rec.get('posti_liberi')
            totali = rec.get('total_spaces') or rec.get('posti_totali')
            if nome and liberi is not None:
                cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?, ?)", ("Firenze", nome, int(liberi), int(totali) if totali else None, now))
        print("✅ Firenze aggiornata")
    except Exception as e: print(f"❌ Errore Firenze: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    esegui_aggiornamento()
