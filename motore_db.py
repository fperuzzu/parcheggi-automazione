import requests
import sqlite3
from datetime import datetime

# URL API Bologna - Dataset Parcheggi
URL = "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=50"
DB_NAME = "storico_parcheggi.db"

def esegui_aggiornamento():
    try:
        print("--- Inizio Aggiornamento Dati ---")
        r = requests.get(URL).json()
        records = r.get('results', [])
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Creiamo la tabella con i campi giusti
        cursor.execute("CREATE TABLE IF NOT EXISTS storico (nome TEXT, liberi INTEGER, timestamp DATETIME)")
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        count = 0
        
        for record in records:
            # Basandoci sul tuo log, i dati sono DIRETTAMENTE nel record
            # Non bisogna usare .get('fields')
            nome = record.get('parcheggio') # <--- Nel log si chiama "parcheggio"
            liberi = record.get('posti_liberi') # <--- Nel log si chiama "posti_liberi"
            
            if nome is not None and liberi is not None:
                cursor.execute("INSERT INTO storico VALUES (?, ?, ?)", (str(nome), int(liberi), now))
                count += 1
        
        conn.commit()
        conn.close()
        print(f"✅ Successo! Inseriti {count} record alle {now}")
        
    except Exception as e:
        print(f"❌ Errore critico: {e}")

if __name__ == "__main__":
    esegui_aggiornamento()
