import requests
import sqlite3
from datetime import datetime

# Usiamo l'API v2.0 che è più stabile per la lettura diretta dei record
URL = "https://opendata.comune.bologna.it/api/records/1.0/search/?dataset=disponibilita-parcheggi-vigente&rows=50"
DB_NAME = "storico_parcheggi.db"

def esegui_aggiornamento():
    try:
        response = requests.get(URL)
        data = response.json()
        
        # In v2.0 i dati sono sotto 'records'
        records = data.get('records', [])
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS storico (nome TEXT, liberi INTEGER, timestamp DATETIME)")
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        count = 0
        
        for item in records:
            # In v2.0 i dati sono dentro 'fields' direttamente nel record
            fields = item.get('fields', {})
            nome = fields.get('nome')
            liberi = fields.get('posti_liberi')
            
            if nome is not None and liberi is not None:
                cursor.execute("INSERT INTO storico VALUES (?, ?, ?)", (str(nome), int(liberi), now))
                count += 1
        
        conn.commit()
        conn.close()
        print(f"✅ Successo! Inseriti {count} record alle {now}")
        
    except Exception as e:
        print(f"❌ Errore: {e}")

if __name__ == "__main__":
    esegui_aggiornamento()
