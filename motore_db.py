import requests
import sqlite3
from datetime import datetime

# URL aggiornato per l'API v2.1 di Bologna
URL = "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-storico/records?limit=50"
DB_NAME = "storico_parcheggi.db"

def esegui_aggiornamento():
    try:
        response = requests.get(URL)
        r = response.json()
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Crea la tabella se non esiste
        cursor.execute("CREATE TABLE IF NOT EXISTS storico (nome TEXT, liberi INTEGER, timestamp DATETIME)")
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        count = 0
        
        # Estraiamo i dati dai risultati
        for record in r.get('results', []):
            # L'API di Bologna usa spesso questi nomi campi:
            nome = record.get('nome')
            # Proviamo a prendere 'posti_liberi' o 'occupazione' a seconda di cosa risponde l'API
            liberi = record.get('posti_liberi') if record.get('posti_liberi') is not None else record.get('valore')
            
            if nome is not None and liberi is not None:
                cursor.execute("INSERT INTO storico VALUES (?, ?, ?)", (nome, int(liberi), now))
                count += 1
        
        conn.commit()
        conn.close()
        print(f"✅ Aggiornamento completato: inseriti {count} record alle {now}")
        
    except Exception as e:
        print(f"❌ Errore durante l'aggiornamento: {e}")

if __name__ == "__main__":
    esegui_aggiornamento()
