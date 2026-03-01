import requests
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

DB_NAME = "storico_parcheggi.db"

def esegui_aggiornamento():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
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
                cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?, ?)", 
                             ("Bologna", rec.get('parcheggio'), rec.get('posti_liberi'), rec.get('posti_totali'), now))
        except: print("❌ Errore Bologna")

        # --- TORINO ---
        try:
            r_to = requests.get("http://opendata.5t.torino.it/get_pk", timeout=10)
            root = ET.fromstring(r_to.content)
            for pk in root.findall('Table'):
                cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?, ?)", 
                             ("Torino", pk.findtext('Name'), pk.findtext('Free'), pk.findtext('Total'), now))
        except: print("❌ Errore Torino")

        # --- FIRENZE ---
        try:
            r_fi = requests.get("https://opendata.comune.fi.it/api/action/datastore_search?resource_id=07ccbe04-2041-4357-b501-8f52f3607062", timeout=10).json()
            for rec in r_fi.get('result', {}).get('records', []):
                cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?, ?)", 
                             ("Firenze", rec.get('description') or rec.get('nome'), rec.get('free_spaces') or rec.get('posti_liberi'), rec.get('total_spaces') or rec.get('posti_totali'), now))
        except: print("❌ Errore Firenze")

        conn.commit()
        conn.close()
    except Exception as e: print(f"❌ Errore DB: {e}")

def genera_pagina_web():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # 1. Prendiamo l'ultimo dato per i tachimetri
        cursor.execute("SELECT citta, nome, liberi, totali, MAX(timestamp) FROM storico GROUP BY citta, nome")
        ultimi_dati = cursor.fetchall()

        html = """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Dashboard Parcheggi Storico</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            body { font-family: sans-serif; background: #f0f2f5; padding: 20px; text-align: center; }
            .container { display: flex; flex-wrap: wrap; justify-content: center; }
            .card { background: white; border-radius: 15px; margin: 15px; padding: 20px; width: 450px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
            .city-tag { background: #007bff; color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.8em; }
            .charts-grid { display: block; }
        </style></head><body>
        <h1>📊 Monitoraggio Parcheggi (Real-time + Storico 24h)</h1>
        <div class="container">"""

        for row in ultimi_dati:
            citta, nome, liberi, totali, ts = row
            lib = liberi if liberi is not None else 0
            tot = totali if (totali and totali > 0) else (lib + 1)
            percentuale = round(((tot - lib) / tot * 100), 1)
            
            # 2. Recuperiamo lo storico delle ultime 24 ore per questo specifico parcheggio
            ieri = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("SELECT liberi, timestamp FROM storico WHERE nome = ? AND timestamp > ? ORDER BY timestamp ASC", (nome, ieri))
            storico_rows = cursor.fetchall()
            
            x_time = [r[1].split(" ")[1][:5] for r in storico_rows] # Solo HH:MM
            y_liberi = [r[0] for r in storico_rows]

            div_gauge = f"g_{hash(nome)}"
            div_line = f"l_{hash(nome)}"

            html += f"""
            <div class="card">
                <span class="city-tag">{citta}</span>
                <h2>{nome}</h2>
                <div id="{div_gauge}"></div>
                <div id="{div_line}"></div>
                <p>Posti attuali liberi: <strong>{lib}</strong> / Totali: {tot}</p>
            </div>
            <script>
                // Grafico Tachimetro
                Plotly.newPlot("{div_gauge}", [{{
                    type: "indicator", mode: "gauge+number", value: {percentuale},
                    number: {{ suffix: "%" }},
                    gauge: {{ axis: {{ range: [0, 100] }}, bar: {{ color: "{ "#e74c3c" if percentuale > 85 else "#2ecc71" }" }} }}
                }}], {{ width: 400, height: 200, margin: {{ t: 0, b: 0 }} }});

                // Grafico Storico
                Plotly.newPlot("{div_line}", [{{
                    x: {x_time}, y: {y_liberi}, type: 'scatter', mode: 'lines+markers',
                    name: 'Posti Liberi', line: {{ color: '#007bff' }}
                }}], {{ 
                    title: 'Andamento Posti Liberi (24h)',
                    xaxis: {{ title: 'Ora' }},
                    yaxis: {{ title: 'Liberi' }},
                    width: 400, height: 200, margin: {{ t: 30, b: 40, l: 40, r: 20 }}
                }});
            </script>"""

        html += "</div></body></html>"
        with open("index.html", "w", encoding="utf-8") as f: f.write(html)
        conn.close()
    except Exception as e: print(f"❌ Errore Web: {e}")

if __name__ == "__main__":
    esegui_aggiornamento()
    genera_pagina_web()
