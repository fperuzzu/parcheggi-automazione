# manualmente
python scraper_parcheggi.py

# cron ogni 5 minuti
*/5 * * * * python3 /path/scraper_parcheggi.py

# con pulizia automatica dati vecchi
python scraper_parcheggi.py --pulisci --retention 30
