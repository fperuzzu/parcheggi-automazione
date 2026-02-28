import requests
import sqlite3
from datetime import datetime

URL = "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=50"
DB_NAME = "storico_parcheggi.db"

def esegui_aggiornamento():
    try:
        r = requests.get(URL).json()
        results = r.get('results', [])
        
        if not results:
            print("⚠️ L'API ha restituito una lista vuota!")
            return

        # --- DIAGNOSTICA: STAMPIAMO COSA C'È DENTRO ---
        first_record_fields = results[0].get('fields', {})
        print(f"DEBUG - Struttura dati ricevuta: {first_record_fields}")
        # ----------------------------------------------

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS storico (nome TEXT, liberi INTEGER, timestamp DATETIME)")
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        count = 0
        
        for record in results:
            fields = record.get('fields', {})
            
            # Proviamo a indovinare i nomi più comuni
            nome = fields.get('nome') or fields.get('denominazione') or fields.get('testo')
            liberi = fields.get('posti_liberi') or fields.get('posti_disponibili') or fields.get('valore')
            
            if nome is not None and liberi is not None:
                cursor.execute("INSERT INTO storico VALUES (?, ?, ?)", (str(nome), int(liberi), now))
                count += 1
        
        conn.commit()
        conn.close()
        print(f"✅ Risultato finale: Inseriti {count} record.")
        
    except Exception as e:
        print(f"❌ Errore: {e}")

if __name__ == "__main__":
    esegui_aggiornamento()
