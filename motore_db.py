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

    # --- TORINO (Metodo Regex - Ignora XML rotto) ---
    try:
        print("📡 Recupero Torino via Proxy (Metodo Text-Search)...")
        r = requests.get(URL_TORINO_PROXY, timeout=30)
        r.raise_for_status()
        testo = r.text

        # Cerchiamo tutti i blocchi <stop name="..." ... free_spaces="...">
        # Questa Regex estrae i dati anche se l'XML è malformato
        pattern = r'name="([^"]+)"[^>]+free_spaces="(\d+)"'
        matches = re.findall(pattern, testo)
        
        count_to = 0
        for nome, liberi in matches:
            cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?)", ("Torino", str(nome), int(liberi), now))
            count_to += 1
        
        if count_to > 0:
            print(f"✅ Torino: Inseriti {count_to} record (Regex Mode).")
        else:
            print("⚠️ Torino: Nessun dato trovato nel testo ricevuto.")
            
    except Exception as e:
        print(f"❌ Errore Torino (Regex): {e}")

    # --- BOLOGNA (Metodo JSON - Già funzionante) ---
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
