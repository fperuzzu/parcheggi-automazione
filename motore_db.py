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

    # --- TORINO (Diagnostica Profonda) ---
    try:
        print("📡 Recupero Torino via Proxy...")
        r = requests.get(URL_TORINO_PROXY, timeout=30)
        r.raise_for_status()
        testo = r.text
        
        # DEBUG: Stampiamo i primi 500 caratteri per capire cosa arriva davvero
        print(f"🔍 ANTEPRIMA DATI RICEVUTI: {testo[:500]}")

        # Proviamo 3 pattern diversi per catturare i dati (XML o JSON)
        patterns = [
            r'name="([^"]+)"[^>]+free_spaces="(\d+)"', # XML Standard
            r'"name":\s*"([^"]+)"[^}]+"free_spaces":\s*(\d+)', # JSON Standard
            r'stop\s+name=([^>\s]+).+free_spaces=(\d+)' # Testo sporco
        ]
        
        count_to = 0
        for p in patterns:
            matches = re.findall(p, testo, re.IGNORECASE)
            if matches:
                for nome, liberi in matches:
                    cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?)", ("Torino", str(nome), int(liberi), now))
                    count_to += 1
                break # Se troviamo dati con un pattern, ci fermiamo
        
        if count_to > 0:
            print(f"✅ Torino: Inseriti {count_to} record.")
        else:
            print("❌ Torino: Ancora nessun dato estratto. Controlla l'anteprima sopra.")
            
    except Exception as e:
        print(f"❌ Errore critico Torino: {e}")

    # --- BOLOGNA ---
    try:
        r = requests.get(URL_BOLOGNA, timeout=30)
        data = r.json()
        for rec in data.get('results', []):
            cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?)", ("Bologna", str(rec.get('parcheggio')), int(rec.get('posti_liberi')), now))
        print("✅ Bologna: Aggiornata.")
    except:
        print("❌ Errore Bologna.")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    esegui_aggiornamento()
