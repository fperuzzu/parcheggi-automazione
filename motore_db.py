import requests
import sqlite3
from datetime import datetime

# URL API Bologna - Dataset Parcheggi
URL = "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=50"
DB_NAME = "storico_parcheggi.db"

def esegui_aggiornamento():
    try:
        r = requests.get(URL).json()
        records = r.get('results', [])
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS storico (nome TEXT, liberi INTEGER, timestamp DATETIME)")
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        count = 0
        
        for record in records:
            fields = record.get('fields', {})
            
            # --- CORREZIONE NOMI CAMPI ---
            # L'API attuale usa 'nome' e 'posti_disponibili'
            nome = fields.get('nome')
            liberi = fields.get('posti_disponibili') # <--- Cambiato da posti_liberi
            
            # Se non trova 'posti_disponibili', prova 'posti_liberi' (vecchio stile)
            if liberi is None:
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
