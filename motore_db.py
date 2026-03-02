import requests
import sqlite3
import re
from datetime import datetime

URL_TORINO_PROXY = "https://script.google.com/macros/s/AKfycbxST_tjOBH2v3ERqb_dif6kazstQr8qZkwwKnrgGtfPkpjkqARpaiwYIq-f7epgVNz_/exec"
URL_BOLOGNA = "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=50"
DB_NAME = "storico_parcheggi.db"

def esegui_aggiornamento():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS storico (citta TEXT, nome TEXT, liberi INTEGER, timestamp DATETIME)")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # --- TORINO ---
    try:
        print("📡 Recupero Torino via Proxy...")
        r = requests.get(URL_TORINO_PROXY, timeout=30)
        testo = r.text
        
        # Regex SUPER FLESSIBILE: 
        # Cerca Name="QualsiasiCosa" seguito da Free="Numero" (ignorando cosa c'è in mezzo)
        # re.IGNORECASE serve per non sbagliare tra 'Free' e 'free'
        matches = re.findall(r'Name\s*=\s*"([^"]+)"[^>]+Free\s*=\s*"(\d+)"', testo, re.IGNORECASE)
        
        count_to = 0
        if matches:
            for nome, liberi in matches:
                cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?)", ("Torino", str(nome), int(liberi), now))
                count_to += 1
            print(f"✅ Torino: Inseriti {count_to} record.")
        else:
            print("⚠️ Torino: Nessun dato trovato con la Regex.")
            # Stampiamo i primi 1000 caratteri per vedere cosa è arrivato davvero
            print(f"🔍 DEBUG TESTO RICEVUTO: {testo[:1000]}")
            
    except Exception as e:
        print(f"❌ Errore Torino: {e}")

    # --- BOLOGNA ---
    try:
        r = requests.get(URL_BOLOGNA, timeout=30)
        data = r.json()
        for rec in data.get('results', []):
            cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?)", ("Bologna", str(rec.get('parcheggio')), int(rec.get('posti_liberi')), now))
        print("✅ Bologna: Aggiornata.")
    except: pass

    conn.commit()
    conn.close()

if __name__ == "__main__":
    esegui_aggiornamento()
