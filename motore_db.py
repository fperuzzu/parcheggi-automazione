import requests
import sqlite3
from datetime import datetime

# URL API Bologna v2.1
URL = "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=50"
DB_NAME = "storico_parcheggi.db"

def esegui_aggiornamento():
    try:
        r = requests.get(URL).json()
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS storico (nome TEXT, liberi INTEGER, timestamp DATETIME)")
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        count = 0
        
        for record in r.get('results', []):
            # NOMI CAMPI CORRETTI PER L'API DI BOLOGNA:
            nome = record.get('nome')
            # L'API usa 'posti_liberi' o 'stato'
            liberi = record.get('posti_liberi')
            
            if nome is not None and liberi is not None:
                cursor.execute("INSERT INTO storico VALUES (?, ?, ?)", (nome, int(liberi), now))
                count += 1
        
        conn.commit()
        conn.close()
        print(f"✅ Inseriti {count} record alle {now}")
    except Exception as e:
        print(f"❌ Errore: {e}")

if __name__ == "__main__":
    esegui_aggiornamento()
