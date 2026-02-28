import requests
import sqlite3
from datetime import datetime

# URL dei parcheggi di Bologna
URL = "https://bologna.opendatasoft.com/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=30"
DB_NAME = "storico_parcheggi.db"

def esegui_aggiornamento():
    try:
        r = requests.get(URL).json()
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Crea la tabella se non esiste
        cursor.execute("CREATE TABLE IF NOT EXISTS storico (nome TEXT, liberi INTEGER, timestamp DATETIME)")
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Inserisce i nuovi dati
        for record in r.get('results', []):
            nome = record.get('nome')
            liberi = record.get('posti_liberi')
            if nome is not None and liberi is not None:
                cursor.execute("INSERT INTO storico VALUES (?, ?, ?)", (nome, liberi, now))
        
        conn.commit()
        conn.close()
        print(f"Aggiornamento completato alle {now}")
    except Exception as e:
        print(f"Errore: {e}")

if __name__ == "__main__":
    esegui_aggiornamento()
