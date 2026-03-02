import requests
import sqlite3
from datetime import datetime

URL_BOLOGNA = "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=50"
DB_NAME = "storico_parcheggi.db"

def aggiorna_dati():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS storico (citta TEXT, nome TEXT, liberi INTEGER, timestamp DATETIME)")
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    righe_html = "" # Ci servirà per la dashboard

    try:
        r = requests.get(URL_BOLOGNA, timeout=20)
        r.raise_for_status()
        data = r.json()
        
        for rec in data.get('results', []):
            nome = rec.get('parcheggio', 'N/D')
            liberi = rec.get('posti_liberi', 0)
            cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?)", ("Bologna", nome, liberi, now))
            # Creiamo una riga della tabella HTML per ogni parcheggio
            righe_html += f"<tr><td>{nome}</td><td>{liberi}</td><td>{now}</td></tr>"
            
        conn.commit()
        print("✅ Database aggiornato.")
        return righe_html
    except Exception as e:
        print(f"❌ Errore: {e}")
        return "<tr><td colspan='3'>Errore durante l'aggiornamento</td></tr>"
    finally:
        conn.close()

def genera_html(tabella_body):
    html_template = f"""
    <!DOCTYPE html>
    <html lang="it">
    <head>
        <meta charset="UTF-8">
        <title>PeruLabTech - Monitor Parcheggi</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <meta http-equiv="refresh" content="600"> </head>
    <body class="bg-light">
        <div class="container py-5">
            <div class="card shadow">
                <div class="card-header bg-primary text-white">
                    <h1 class="h3 mb-0">📊 Monitor Parcheggi Bologna (Live)</h1>
                </div>
                <div class="card-body">
                    <p class="text-muted">Ultimo aggiornamento: <strong>{datetime.now().strftime('%H:%M:%S')}</strong></p>
                    <table class="table table-hover">
                        <thead class="table-dark">
                            <tr><th>Parcheggio</th><th>Posti Liberi</th><th>Rilevazione</th></tr>
                        </thead>
                        <tbody>
                            {tabella_body}
                        </tbody>
                    </table>
                    <hr>
                    <div class="text-center">
                        <a href="https://parcheggi-automazione.streamlit.app/" target="_blank" class="btn btn-outline-primary">
                            Vai all'App Grafica (Storico)
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)
    print("🖥️ index.html rigenerato.")

if __name__ == "__main__":
    dati_tabella = aggiorna_dati()
    genera_html(dati_tabella)
