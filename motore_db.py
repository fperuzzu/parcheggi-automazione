import requests
import sqlite3
import re
from datetime import datetime

# Il tuo nuovo URL funzionante
URL_TORINO_PROXY = "https://script.google.com/macros/s/AKfycbwi1wd9cwc9qH1qlir9nTBi9gbK982e6j2O4obBgoHC0yhlmYsxWTylqZDcZvTdTII7/exec"
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
        r.raise_for_status()
        testo = r.text
        
        # Regex specifica per il formato PK_data Name="..." Free="..."
        # Il flag re.IGNORECASE gestisce eventuali variazioni maiuscole/minuscole
        matches = re.findall(r'Name\s*=\s*"([^"]+)"[^>]+Free\s*=\s*"(\d+)"', testo, re.IGNORECASE)
        
        count_to = 0
        for nome, liberi in matches:
            cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?)", ("Torino", str(nome), int(liberi), now))
            count_to += 1
            
        if count_to > 0:
            print(f"✅ Torino: Inseriti {count_to} record.")
        else:
            print("⚠️ Torino: Connessione ok, ma nessun dato trovato nel testo.")
    except Exception as e:
        print(f"❌ Errore Torino: {e}")

    # --- BOLOGNA ---
    try:
        print("📡 Recupero Bologna...")
        r = requests.get(URL_BOLOGNA, timeout=30)
        data = r.json()
        count_bo = 0
        for rec in data.get('results', []):
            n = rec.get('parcheggio')
            l = rec.get('posti_liberi')
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
