import requests
import sqlite3
import json
from datetime import datetime

URL = "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=5"
DB_NAME = "storico_parcheggi.db"

def esegui_aggiornamento():
    try:
        print(f"--- Inizio Debug API Bologna ---")
        response = requests.get(URL)
        data = response.json()
        
        results = data.get('results', [])
        
        if not results:
            print("⚠️ L'API ha restituito 'results' vuoto. Ecco il JSON completo ricevuto:")
            print(json.dumps(data, indent=2))
            return

        # STAMPA IL PRIMO RECORD COMPLETO PER VEDERE I NOMI DEI CAMPI
        print("🔍 ANALISI PRIMO RECORD RICEVUTO:")
        print(json.dumps(results[0], indent=2))
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS storico (nome TEXT, liberi INTEGER, timestamp DATETIME)")
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        count = 0
        
        for record in results:
            fields = record.get('fields', {})
            # Qui proveremo a estrarre i dati basandoci su quello che vedremo nel log
            # Per ora usiamo un metodo generico per non far fallire lo script
            nome = fields.get('nome') or fields.get('denominazione')
            liberi = fields.get('posti_disponibili') or fields.get('posti_liberi')
            
            if nome and liberi is not None:
                cursor.execute("INSERT INTO storico VALUES (?, ?, ?)", (str(nome), int(liberi), now))
                count += 1
        
        conn.commit()
        conn.close()
        print(f"--- Fine Debug: Inseriti {count} record ---")
            
    except Exception as e:
        print(f"❌ Errore durante il debug: {e}")

if __name__ == "__main__":
    esegui_aggiornamento()
