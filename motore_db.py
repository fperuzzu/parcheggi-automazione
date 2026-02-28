import requests
import sqlite3
from datetime import datetime

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
        
        results = r.get('results', [])
        
        # DEBUG: Stampiamo il primo record per capire come si chiamano i campi oggi
        if results:
            first_fields = results[0].get('fields', {})
            print(f"DEBUG - Campi ricevuti dall'API: {list(first_fields.keys())}")

        for record in results:
            fields = record.get('fields', {})
            
            # Prova tutte le varianti note dei nomi dei campi di Bologna
            nome = fields.get('nome') or fields.get('denominazione')
            
            # Cerca i posti liberi in diverse etichette possibili
            liberi = fields.get('posti_liberi') 
            if liberi is None:
                liberi = fields.get('posti_disponibili')
            if liberi is None:
                liberi = fields.get('stato') # A volte lo chiamano stato se è un numero

            if nome is not None and liberi is not None:
                try:
                    cursor.execute("INSERT INTO storico VALUES (?, ?, ?)", (str(nome), int(liberi), now))
                    count += 1
                except ValueError:
                    continue # Salta se 'liberi' non è un numero
        
        conn.commit()
        conn.close()
        print(f"✅ Fatto! Inseriti {count} record alle {now}")
        
    except Exception as e:
        print(f"❌ Errore durante l'esecuzione: {e}")

if __name__ == "__main__":
    esegui_aggiornamento()
