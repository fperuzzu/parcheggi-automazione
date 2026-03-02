def aggiorna_dashboard_html():
    conn = sqlite3.connect(DB_NAME)
    # Prendiamo gli ultimi 20 record di Bologna per la tabella veloce
    df = pd.read_sql_query("SELECT * FROM storico WHERE citta='Bologna' ORDER BY timestamp DESC LIMIT 20", conn)
    conn.close()

    # Creiamo un file HTML semplicissimo con i nuovi dati
    html_content = f"""
    <html>
    <head>
        <title>Monitor Parcheggi - PeruLabTech</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    </head>
    <body class="container mt-5">
        <h1 class="text-center">📊 Dashboard Parcheggi (Live)</h1>
        <p class="text-center text-muted">Ultimo aggiornamento: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
        <div class="card p-4 shadow">
            <h3>Ultimi rilevamenti Bologna</h3>
            {df.to_html(classes='table table-striped', index=False)}
        </div>
        <div class="text-center mt-4">
            <a href="https://parcheggi-automazione.streamlit.app/" class="btn btn-primary">Vai all'App Grafica Completa</a>
        </div>
    </body>
    </html>
    """
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("🖥️ Dashboard HTML rigenerata con successo!")

# E in fondo al file, sotto esegui_aggiornamento(), aggiungi la chiamata:
if __name__ == "__main__":
    esegui_aggiornamento()
    try:
        import pandas as pd # Assicurati di avere pandas
        aggiorna_dashboard_html()
    except:
        print("Puntatore HTML non aggiornato (manca Pandas?)")
