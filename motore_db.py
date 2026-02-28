import requests
import sqlite3
from datetime import datetime

# URL API Bologna v2.1 - Dataset disponibilità parcheggi
URL = "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=50"
DB_NAME = "storico_parcheggi.db"

def esegui_aggiornamento():
    try:
        # 1. Richiesta dati
        response = requests.get(URL)
        response.raise_for_status() # Genera un errore se il sito non risponde
        data = response.json()
        
        # 2. Connessione DB
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Creazione tabella se non esiste
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS storico (
                nome TEXT, 
                liberi INTEGER, 
                timestamp DATETIME
            )
        """)
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        count = 0
        
        # 3. Estrazione dati corretta per API v2.1
        # I record sono in 'results', i dati reali in 'fields'
        for record in data.get('results', []):
            fields = record.get('fields', {})
            
            nome = fields.get('nome')
            # L'API di Bologna a volte usa 'posti_liberi', a volte 'posti_disponibili'
            liberi = fields.get('posti_liberi') or fields.get('posti_disponibili')
            
            if nome is not None and liberi is not None:
                cursor.execute("INSERT INTO storico VALUES (?, ?, ?)", (nome, int(liberi), now))
                count += 1
        
        # 4. Salvataggio e chiusura
        conn.commit()
        conn.close()
        
        if count > 0:
            print(f"✅ Successo: Inseriti {count} record alle {now}")
        else:
            print("⚠️ Attenzione: Connessione riuscita ma 0 record trovati. Controlla i nomi dei campi JSON.")
            
    except Exception as e:
        print(f"❌ Errore critico: {e}")

if __
