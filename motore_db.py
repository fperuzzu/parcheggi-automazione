def genera_dashboard_perulabtech(dati_parcheggi):
    # dati_parcheggi ora deve essere una lista di dizionari per comodità
    # ma manteniamo la logica attuale per non stravolgere il tuo lavoro.
    
    aggiornamento = datetime.now().strftime("%H:%M")
    data_oggi = datetime.now().strftime("%d %b %Y")
    
    # Generiamo le "Cards" invece delle righe della tabella
    cards_html = ""
    for p in dati_parcheggi: # p è un dizionario {'nome': x, 'liberi': y}
        nome = p['nome']
        liberi = p['liberi']
        
        # Logica colore iOS
        color = "#34C759" if liberi > 50 else "#FF9500" if liberi > 10 else "#FF3B30"
        
        cards_html += f"""
        <div class="ios-card">
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <div class="parking-name">{nome}</div>
                    <div class="city-name"><i class="fas fa-location-arrow"></i> Bologna, IT</div>
                </div>
                <div class="status-pill" style="background-color: {color}15; color: {color};">
                    {liberi} posti
                </div>
            </div>
            <div class="progress-container">
                <div class="progress-bar" style="width: {min(liberi/5, 100)}%; background-color: {color};"></div>
            </div>
        </div>
        """

    html_template = f"""
    <!DOCTYPE html>
    <html lang="it">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Smart Parking | PeruLabTech</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/all.min.css">
        <style>
            :root {{
                --ios-bg: #F2F2F7;
                --ios-card: #FFFFFF;
                --ios-blue: #007AFF;
            }}
            body {{ 
                background-color: var(--ios-bg); 
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                color: #000;
                -webkit-font-smoothing: antialiased;
            }}
            .app-header {{
                padding: 40px 20px 20px;
                background: rgba(242, 242, 247, 0.8);
                backdrop-filter: blur(10px);
                position: sticky;
                top: 0;
                z-index: 1000;
            }}
            .header-title {{ font-size: 34px; font-weight: 800; letter-spacing: -0.5px; }}
            .header-date {{ font-size: 13px; color: #8E8E93; text-transform: uppercase; font-weight: 600; }}
            
            .ios-card {{
                background: var(--ios-card);
                border-radius: 20px;
                padding: 20px;
                margin-bottom: 16px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                transition: transform 0.2s;
            }}
            .ios-card:active {{ transform: scale(0.98); }}
            
            .parking-name {{ font-size: 18px; font-weight: 600; color: #1C1C1E; }}
            .city-name {{ font-size: 14px; color: #8E8E93; margin-top: 2px; }}
            
            .status-pill {{
                padding: 6px 12px;
                border-radius: 12px;
                font-size: 14px;
                font-weight: 700;
            }}
            
            .progress-container {{
                height: 6px;
                background: #E5E5EA;
                border-radius: 3px;
                margin-top: 15px;
                overflow: hidden;
            }}
            .progress-bar {{ height: 100%; transition: width 1s ease-in-out; }}
            
            .tab-bar {{
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                background: rgba(255,255,255,0.9);
                backdrop-filter: blur(20px);
                border-top: 0.5px solid #C6C6C8;
                padding: 10px 0 25px;
                display: flex;
                justify-content: space-around;
            }}
            .tab-item {{ text-align: center; color: var(--ios-blue); text-decoration: none; font-size: 10px; font-weight: 500; }}
            .tab-item i {{ font-size: 24px; display: block; margin-bottom: 2px; }}
            
            .btn-ios-action {{
                background: var(--ios-blue);
                color: white;
                border-radius: 12px;
                padding: 16px;
                width: 100%;
                font-weight: 600;
                border: none;
                margin-top: 20px;
                text-decoration: none;
                display: block;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="app-header">
            <div class="container">
                <div class="header-date">{data_oggi}</div>
                <div class="header-title">Parcheggi</div>
            </div>
        </div>

        <div class="container mt-2 mb-5 pb-5">
            {cards_html}
            
            <a href="https://parcheggi-automazione.streamlit.app/" class="btn-ios-action shadow">
                <i class="fas fa-chart-bar me-2"></i> Visualizza Storico Analitico
            </a>
            
            <div class="text-center mt-4 mb-5">
                <p class="text-muted small">Powered by PeruLabTech Studio<br>Aggiornato alle {aggiornamento}</p>
            </div>
        </div>

        <div class="tab-bar">
            <a href="#" class="tab-item"><i class="fas fa-square-p"></i>Mappa</a>
            <a href="#" class="tab-item" style="color: #000;"><i class="fas fa-list"></i>Elenco</a>
            <a href="#" class="tab-item"><i class="fas fa-gear"></i>Impostazioni</a>
        </div>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)
