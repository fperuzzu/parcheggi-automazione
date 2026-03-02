import requests
import sqlite3
from datetime import datetime

# CONFIGURAZIONE
URL_BOLOGNA = "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=50"
DB_NAME = "storico_parcheggi.db"

def esegui_aggiornamento():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Creazione tabella per lo storico (usata dall'app Streamlit)
    cursor.execute("CREATE TABLE IF NOT EXISTS storico (citta TEXT, nome TEXT, liberi INTEGER, timestamp DATETIME)")
    
    now_dt = datetime.now()
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    display_time = now_dt.strftime("%H:%M")
    
    righe_html = "" # Qui accumuliamo le righe per la tabella della dashboard

    try:
        print(f"📡 Recupero dati Bologna ({display_time})...")
        r = requests.get(URL_BOLOGNA, timeout=20)
        r.raise_for_status()
        data = r.json()
        
        count = 0
        for rec in data.get('results', []):
            nome = rec.get('parcheggio', 'N/D')
            liberi = rec.get('posti_liberi', 0)
            
            # 1. Salva nel Database per i grafici (Streamlit)
            cursor.execute("INSERT INTO storico VALUES (?, ?, ?, ?)", ("Bologna", nome, liberi, now_str))
            
            # 2. Crea la riga per la Dashboard HTML (GitHub Pages)
            # Aggiungiamo un badge colorato per i posti
            color_class = "bg-success" if liberi > 50 else "bg-warning text-dark" if liberi > 10 else "bg-danger"
            
            righe_html += f"""
            <tr>
                <td><i class="fas fa-location-dot text-primary me-2"></i><strong>{nome}</strong></td>
                <td class="text-center"><span class="badge {color_class}" style="font-size: 0.9rem;">{liberi}</span></td>
                <td class="text-end text-muted small">{display_time}</td>
            </tr>
            """
            count += 1
            
        conn.commit()
        print(f"✅ Database aggiornato: {count} record inseriti.")
        return righe_html

    except Exception as e:
        print(f"❌ Errore durante l'aggiornamento: {e}")
        return f"<tr><td colspan='3' class='text-center text-danger'>Errore tecnico: {e}</td></tr>"
    finally:
        conn.close()

def genera_dashboard_perulabtech(tabella_body):
    aggiornamento = datetime.now().strftime("%d/%m/%Y alle %H:%M")
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="it">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PeruLabTech | Smart Parking Dashboard</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/all.min.css">
        <style>
            body {{ background-color: #f0f2f5; font-family: 'Inter', sans-serif; }}
            .navbar {{ background: #00416A; border-bottom: 4px solid #007bff; }}
            .main-card {{ border: none; border-radius: 20px; box-shadow: 0 15px 35px rgba(0,0,0,0.1); background: white; }}
            .table thead {{ background-color: #f8f9fa; border-top: 2px solid #dee2e6; }}
            .btn-streamlit {{ background-color: #ff4b4b; color: white; border-radius: 50px; padding: 12px 30px; font-weight: 600; text-decoration: none; transition: 0.3s; display: inline-block; }}
            .btn-streamlit:hover {{ background-color: #d43f3f; transform: translateY(-2px); color: white; box-shadow: 0 5px 15px rgba(255,75,75,0.4); }}
            .footer-text {{ font-size: 0.85rem; color: #adb5bd; }}
        </style>
    </head>
    <body>
        <nav class="navbar navbar-dark py-3">
            <div class="container d-flex justify-content-between">
                <span class="navbar-brand fw-bold italic"><i class="fas fa-microchip me-2"></i>PERULABTECH <span class="fw-light">SMART CITY</span></span>
                <span class="text-white-50 small">Monitor v1.2</span>
            </div>
        </nav>

        <div class="container my-5">
            <div class="row justify-content-center">
                <div class="col-lg-9">
                    <div class="main-card p-4 p-md-5">
                        <div class="d-flex justify-content-between align-items-center mb-4 border-bottom pb-3">
                            <div>
                                <h2 class="h4 m-0 text-dark">Disponibilità Parcheggi</h2>
                                <p class="text-muted small mb-0">Città di Bologna</p>
                            </div>
                            <div class="text-end">
                                <span class="badge bg-light text-dark border"><i class="fas fa-clock me-1 text-primary"></i> Aggiornato: {aggiornamento}</span>
                            </div>
                        </div>
                        
                        <div class="table-responsive">
                            <table class="table table-hover align-middle">
                                <thead>
                                    <tr>
                                        <th style="width: 50%;">Località</th>
                                        <th class="text-center">Posti Liberi</th>
                                        <th class="text-end">Stato</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {tabella_body}
                                </tbody>
                            </table>
                        </div>

                        <div class="mt-5 p-4 text-center border-top">
                            <h5 class="mb-3">Analisi Avanzata & Grafici</h5>
                            <p class="text-muted mb-4">Accedi alla piattaforma Streamlit per visualizzare gli slider temporali e l'andamento storico dei dati.</p>
                            <a href="https://parcheggi-automazione.streamlit.app/" target="_blank" class="btn-streamlit">
                                <i class="fas fa-chart-line me-2"></i>VAI ALL'APP INTERATTIVA
                            </a>
                        </div>
                    </div>
                </div>
            </div>
            <footer class="text-center mt-5 footer-text">
                Progetto di Automazione Real-Time &copy; 2026 | PeruLabTech Solutions
            </footer>
        </div>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)
    print("🖥️ Dashboard HTML (PeruLabTech Edition) generata.")

if __name__ == "__main__":
    corpo_tabella = esegui_aggiornamento()
    genera_dashboard_perulabtech(corpo_tabella)
