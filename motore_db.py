import requests
import sqlite3
from datetime import datetime

# URL API Bologna v2.1
URL = "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=50"
DB_NAME = "storico_parcheggi.db"

def esegui_aggiornamento():
    try:
        # Recupero dati
        r = requests.get(URL).json()
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Creazione tabella
        cursor.execute("CREATE TABLE IF NOT EXISTS storico (nome TEXT, liberi INTEGER, timestamp DATETIME)")
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        count = 0
        
        # CICLO CORRETTO: Entriamo in 'results' e poi in 'fields'
        for record in r.get('results', []):
            fields = record.get('fields', {})
            nome = fields.get('nome')
            liberi = fields.get('posti_liberi')
            
            if nome is not None and liberi is not None:
                cursor.execute("INSERT INTO storico VALUES (?, ?, ?)", (nome, int(liberi), now))
                count += 1
        
        conn.commit()
        conn.close()
        print(f"✅ Inseriti {count} record alle {now}")
        
    except Exception as e:
        print(f"❌ Errore: {e}")

# LA RIGA 57 INCRIMINATA (Corretta con i due punti :)
if __name__ == "__main__":
    esegui_aggiornamento()
