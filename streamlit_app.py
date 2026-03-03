    # 2. MAPPA CON NUMERO POSTI VISIBILE
    st.markdown("<br><div style='color:#8b949e; font-size:0.75rem; font-weight:600; letter-spacing:1px; margin-bottom:10px;'>LIVE MAP - POSTI DISPONIBILI</div>", unsafe_allow_html=True)
    
    # Centro su Bologna
    m = folium.Map(location=[44.494, 11.342], zoom_start=13, tiles="cartodbpositron")
    
    for row in ultimi.itertuples():
        coords = COORDINATE.get(row.nome, [44.49, 11.34])
        nav_url = f"https://www.google.com/maps/dir/?api=1&destination={coords[0]},{coords[1]}"
        
        # Colore in base alla disponibilità
        lib = row.liberi
        tot = row.totali if row.totali > 0 else (lib + 20)
        perc = lib / tot if tot > 0 else 0
        bg_color = "#3fb950" if perc > 0.4 else "#d29922" if perc > 0.15 else "#f85149"
        
        # CREAZIONE ICONA CON NUMERO
        icon_html = f"""
            <div style="
                background-color: {bg_color};
                border: 2px solid white;
                border-radius: 50%;
                color: white;
                font-weight: bold;
                font-size: 14px;
                display: flex;
                align-items: center;
                justify-content: center;
                width: 35px;
                height: 35px;
                box-shadow: 0px 2px 5px rgba(0,0,0,0.3);
            ">
                {lib}
            </div>
        """
        
        popup_content = f"""
        <div style='font-family:sans-serif; width:160px; color:black;'>
            <b style='font-size:14px;'>{row.nome}</b><br>
            <span style='color:#666;'>Liberi: {lib} / {tot}</span><br>
            <a href='{nav_url}' target='_blank' style='display:block; background:#238636; color:white; text-align:center; padding:8px; border-radius:5px; text-decoration:none; margin-top:8px; font-weight:bold;'>PORTAMI QUI</a>
        </div>
        """
        
        folium.Marker(
            location=coords,
            popup=folium.Popup(popup_content, max_width=200),
            icon=folium.DivIcon(html=icon_html)
        ).add_to(m)
    
    folium_static(m, width=1000, height=350)
