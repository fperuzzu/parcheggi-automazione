def genera_pagina_web():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Prendiamo l'ultimo inserimento per ogni parcheggio di ogni città
    cursor.execute("""
        SELECT citta, nome, liberi, totali, MAX(timestamp) 
        FROM storico 
        GROUP BY citta, nome
    """)
    rows = cursor.fetchall()
    conn.close()

    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Stato Parcheggi - Bicchiere Mezzo Pieno</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            body { font-family: sans-serif; display: flex; flex-wrap: wrap; justify-content: center; background: #f4f4f4; }
            .card { background: white; margin: 10px; padding: 10px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); width: 300px; text-align: center; }
            h2 { color: #333; font-size: 1.2em; }
        </style>
    </head>
    <body>
    """

    for row in rows:
        citta, nome, liberi, totali, ts = row
        # Logica bicchiere pieno: se totali è 0 o None, mettiamo 0%
        occupati = (totali - liberi) if (totali and liberi is not None) else 0
        percentuale = (occupati / totali * 100) if (totali and totali > 0) else 0
        
        div_id = f"graph_{nome.replace(' ', '_')}"
        html_content += f"""
        <div class="card">
            <h2>{citta} - {nome}</h2>
            <div id="{div_id}"></div>
            <p><small>Ultimo aggiornamento: {ts}</small></p>
            <script>
                var data = [{{
                    domain: {{ x: [0, 1], y: [0, 1] }},
                    value: {percentuale},
                    title: {{ text: "Occupazione %" }},
                    type: "indicator",
                    mode: "gauge+number",
                    gauge: {{
                        axis: {{ range: [0, 100] }},
                        bar: {{ color: "{'red' if percentuale > 80 else 'orange' if percentuale > 50 else 'green'}" }},
                        steps: [
                            {{ range: [0, 50], color: "#e8f5e9" }},
                            {{ range: [50, 80], color: "#fff3e0" }},
                            {{ range: [80, 100], color: "#ffebee" }}
                        ]
                    }}
                }}];
                Plotly.newPlot('{div_id}', data, {{ width: 250, height: 200, margin: {{ t: 0, b: 0 }} }});
            </script>
        </div>
        """

    html_content += "</body></html>"
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("🖥️ Pagina web generata (index.html)")

# Ricordati di chiamarla nel main:
if __name__ == "__main__":
    esegui_aggiornamento()
    genera_pagina_web()
