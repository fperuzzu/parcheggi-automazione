import requests
import sqlite3
from datetime import datetime

# L'unica certezza: Bologna
URL_BOLOGNA = "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=50"
DB_NAME = "storico_parcheggi.db"

def esegui_aggiornamento():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Creiamo la tabella se non esiste
    cursor.execute("CREATE TABLE IF NOT EXISTS storico (citta TEXT, nome TEXT, liberi INTEGER, timestamp DATETIME)")
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        print("📡 Recupero Bologna...")
        r = requests.get(URL_BOLOGNA, timeout=20)
        r.raise_for_status()
        data = r.json()
        
        count = 0
        for rec in data.get('results', []):
            nome = rec.get('parcheggio')
            liberi = rec.get('posti_liberi')
            
            if nome and liberi is not None:
                cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?)", ("Bologna", str(nome), int(liberi), now))
                count += 1
        
        print(f"✅ Bologna: Inseriti {count} record.")
        
    except Exception as e:
        print(f"❌ Errore Bologna: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    esegui_aggiornamento()
