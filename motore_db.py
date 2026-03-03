import requests
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime

DB_NAME = "storico_parcheggi.db"

def migra_db(conn):
    cursor = conn.cursor()
    try:
        # Proviamo ad aggiungere la colonna 'totali' se non esiste
        cursor.execute("ALTER TABLE storico ADD COLUMN totali INTEGER")
        # Proviamo ad aggiungere la colonna 'citta' se non esiste (per sicurezza)
        cursor.execute("ALTER TABLE storico ADD COLUMN citta TEXT")
        conn.commit()
        print("🔧 Database aggiornato con successo (migrazione completata).")
    except sqlite3.OperationalError:
        # Se l'errore è "duplicate column name", va bene così, significa che ci sono già
        pass

def esegui_aggiornamento():
    conn = sqlite3.connect(DB_NAME)
    migra_db(conn) # <--- Questo salva i tuoi dati vecchi e sistema l'errore
    
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # --- BOLOGNA ---
    try:
        r_bo = requests.get("https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=50", timeout=15).json()
        for rec in r_bo.get('results', []):
            cursor.execute("INSERT INTO storico (citta, nome, liberi, totali, timestamp) VALUES (?, ?, ?, ?, ?)", 
                         ("Bologna", rec.get('parcheggio'), rec.get('posti_liberi'), rec.get('posti_totali'), now))
        print("✅ Bologna aggiornata")
    except Exception as e: print(f"❌ Errore Bologna: {e}")

    # --- TORINO (5T) ---
    try:
        r_to = requests.get("http://opendata.5t.torino.it/get_pk", timeout=15)
        root = ET.fromstring(r_to.content)
        for pk in root.findall('Table'):
            cursor.execute("INSERT INTO storico (citta, nome, liberi, totali, timestamp) VALUES (?, ?, ?, ?, ?)", 
                         ("Torino", pk.findtext('Name'), pk.findtext('Free'), pk.findtext('Total'), now))
        print("✅ Torino aggiornata")
    except Exception as e: print(f"❌ Errore Torino: {e}")

    # --- FIRENZE ---
    try:
        r_fi = requests.get("https://opendata.comune.fi.it/api/action/datastore_search?resource_id=07ccbe04-2041-4357-b501-8f52f3607062", timeout=15).json()
        for rec in r_fi.get('result', {}).get('records', []):
            cursor.execute("INSERT INTO storico (citta, nome, liberi, totali, timestamp) VALUES (?, ?, ?, ?, ?)", 
                         ("Firenze", rec.get('description') or rec.get('nome'), rec.get('free_spaces') or rec.get('posti_liberi'), rec.get('total_spaces') or rec.get('posti_totali'), now))
        print("✅ Firenze aggiornata")
    except Exception as e: print(f"❌ Errore Firenze: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    esegui_aggiornamento()
