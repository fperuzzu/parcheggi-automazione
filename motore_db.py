import requests
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime

DB_NAME = "storico_parcheggi.db"

def esegui_aggiornamento():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        # Struttura a 5 colonne: citta, nome, liberi, totali, timestamp
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS storico (
                citta TEXT, nome TEXT, liberi INTEGER, totali INTEGER, timestamp DATETIME
            )
        """)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # --- BOLOGNA ---
        try:
            r_bo = requests.get("https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=50", timeout=10).json()
            for rec in r_bo.get('results', []):
                # Usiamo le chiavi confermate dal tuo log di debug (Immagine 4)
                cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?, ?)", 
                             ("Bologna", rec.get('parcheggio'), rec.get('posti_liberi'), rec.get('posti_totali'), now))
            print("✅ Bologna aggiornata")
        except Exception as e: print(f"❌ Errore Bologna: {e}")

        # --- TORINO ---
        try:
            r_to = requests.get("http://opendata.5t.torino.it/get_pk", timeout=10)
            root = ET.fromstring(r_to.content)
            for pk in root.findall('Table'):
                cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?, ?)", 
                             ("Torino", pk.findtext('Name'), pk.findtext('Free'), pk.findtext('Total'), now))
            print("✅ Torino aggiornata")
        except Exception as e: print(f"❌ Errore Torino: {e}")

        # --- FIRENZE ---
        try:
            r_fi = requests.get("https://opendata.comune.fi.it/api/action/datastore_search?resource_id=07ccbe04-2041-4357-b501-8f52f3607062", timeout=10).json()
            for rec in r_fi.get('result', {}).get('records', []):
                cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?, ?)", 
                             ("Firenze", rec.get('description') or rec.get('nome'), rec.get('free_spaces') or rec.get('posti_liberi'), rec.get('total_spaces') or rec.get('posti_totali'), now))
            print("✅ Firenze aggiornata")
        except Exception as e: print(f"❌ Errore Firenze: {e}")

        conn.commit()
        conn.close()
    except Exception as e: print(f"❌ Errore DB: {e}")

def genera_pagina_web():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        # Selezioniamo l'ultimo stato per ogni parcheggio
        cursor.execute("SELECT citta, nome, liberi, totali, MAX(timestamp) FROM storico GROUP BY citta, nome")
        rows = cursor.fetchall()
        conn.close()

        html = """<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Dashboard Parcheggi</title><script src="https://cdn.plot.ly/plotly-latest.min.js"></script><style>body { font-family: sans-serif; background: #eef2f3; display: flex; flex-wrap: wrap; justify-content: center; padding: 20px; }.card { background: white; border-radius: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); margin: 10px; padding: 15px; width: 300px; text-align: center; }.city-tag { background: #3498db; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.8em; }</style></head><body>"""
        for row in rows:
            citta, nome, liberi, totali, ts = row
            # Logica bicchiere mezzo pieno
            lib = liberi if liberi is not None else 0
            tot = totali if (totali and totali > 0) else (lib + 1)
            percentuale = round(((tot - lib) / tot * 100), 1)
            div_id = f"g_{hash(nome)}"
            
            html += f'<div class="card"><span class="city-tag">{citta}</span><h2>{nome}</h2><div id="{div_id}"></div><p>Liberi: {lib} / Totali: {tot}</p></div><script>Plotly.newPlot("{div_id}", [{{type: "indicator", mode: "gauge+number", value: {percentuale}, number: {{suffix: "%"}}, gauge: {{axis: {{range: [0, 100]}}, bar: {{color: "{ "#e74c3c" if percentuale > 85 else "#2ecc71" }" }} }} }}], {{width: 250, height: 200, margin: {{t:0, b:0}}}});</script>'
        
        html += "</body></html>"
        with open("index.html", "w", encoding="utf-8") as f: f.write(html)
        print("🖥️ Dashboard generata")
    except Exception as e: print(f"❌ Errore Web: {e}")

if __name__ == "__main__":
    esegui_aggiornamento()
    genera_pagina_web()
