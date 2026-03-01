import requests
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime

DB_NAME = "storico_parcheggi.db"

def esegui_aggiornamento():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Tabella aggiornata con la colonna 'totali'
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS storico (
                citta TEXT,
                nome TEXT, 
                liberi INTEGER, 
                totali INTEGER,
                timestamp DATETIME
            )
        """)
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # --- BOLOGNA ---
        try:
            url_bo = "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=50"
            r_bo = requests.get(url_bo, timeout=10).json()
            for rec in r_bo.get('results', []):
                nome = rec.get('parcheggio')
                liberi = rec.get('posti_liberi')
                totali = rec.get('posti_totali') # Bologna fornisce i totali
                if nome and liberi is not None:
                    cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?, ?)", 
                                 ("Bologna", str(nome), int(liberi), totali, now))
            print("✅ Bologna aggiornata")
        except Exception as e:
            print(f"❌ Errore Bologna: {e}")

        # --- TORINO ---
        try:
            url_to = "http://opendata.5t.torino.it/get_pk"
            r_to = requests.get(url_to, timeout=10)
            root = ET.fromstring(r_to.content)
            for pk in root.findall('Table'):
                nome = pk.findtext('Name')
                liberi = pk.findtext('Free')
                totali = pk.findtext('Total') # Torino (5T) fornisce i totali
                if nome and liberi is not None:
                    cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?, ?)", 
                                 ("Torino", str(nome), int(liberi), int(totali) if totali else None, now))
            print("✅ Torino aggiornata")
        except Exception as e:
            print(f"❌ Errore Torino: {e}")

        # --- FIRENZE ---
        try:
            url_fi = "https://opendata.comune.fi.it/api/action/datastore_search?resource_id=07ccbe04-2041-4357-b501-8f52f3607062"
            r_fi = requests.get(url_fi, timeout=10).json()
            records = r_fi.get('result', {}).get('records', [])
            for rec in records:
                nome = rec.get('description') or rec.get('nome')
                liberi = rec.get('free_spaces') or rec.get('posti_liberi')
                totali = rec.get('total_spaces') or rec.get('posti_totali') # Firenze varia, cerchiamo entrambi
                if nome and liberi is not None:
                    cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?, ?)", 
                                 ("Firenze", str(nome), int(liberi), int(totali) if totali else None, now))
            print("✅ Firenze aggiornata")
        except Exception as e:
            print(f"❌ Errore Firenze: {e}")

        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"❌ Errore generale Database: {e}")

if __name__ == "__main__":
    esegui_aggiornamento()
