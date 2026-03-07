"""
scraper_parcheggi.py
────────────────────
Raccoglie disponibilità parcheggi da:
  • Bologna  → REST JSON   (opendata.comune.bologna.it)   3 parcheggi
  • Torino   → XML HTTPS   (opendata.5t.torino.it)        ~20 parcheggi
  • Firenze  → GeoJSON     (datastore.comune.fi.it)       13 parcheggi

Uso:
  python scraper_parcheggi.py                        # esegui una volta
  python scraper_parcheggi.py --pulisci              # esegui + elimina record > 30gg
  python scraper_parcheggi.py --pulisci --retention 60

Cron (ogni 5 minuti):
  */5 * * * * cd /path/al/progetto && python scraper_parcheggi.py >> cron.log 2>&1
"""

import requests
import sqlite3
import xml.etree.ElementTree as ET
import logging
import time
import argparse
from datetime import datetime
from typing import Optional

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
DB_NAME     = "storico_parcheggi.db"
MAX_RETRIES = 3
RETRY_DELAY = 4    # secondi tra tentativi (backoff: 4s → 8s → stop)
TIMEOUT     = 15   # timeout per singola richiesta HTTP

# URL GeoJSON individuali per Firenze (verificati 07/03/2026 — CC-BY 4.0)
FIRENZE_PARCHEGGI = {
    "Parterre":            "https://datastore.comune.fi.it/od/ParkInfo_Parterre.json",
    "Palazzo Giustizia":   "https://datastore.comune.fi.it/od/ParkInfo_PalazzoGiustizia.json",
    "Oltrarno":            "https://datastore.comune.fi.it/od/ParkInfo_Oltrarno.json",
    "Fortezza da Basso":   "https://datastore.comune.fi.it/od/ParkInfo_FortezzaDaBasso.json",
    "Stazione SMN":        "https://datastore.comune.fi.it/od/ParkInfo_StazioneSMN.json",
    "Careggi":             "https://datastore.comune.fi.it/od/ParkInfo_Careggi.json",
    "Beccaria":            "https://datastore.comune.fi.it/od/ParkInfo_Beccaria.json",
    "Alberti":             "https://datastore.comune.fi.it/od/ParkInfo_Alberti.json",
    "Stazione Binario 16": "https://datastore.comune.fi.it/od/ParkInfo_StazioneBinario16.json",
    "San Lorenzo":         "https://datastore.comune.fi.it/od/ParkInfo_SanLorenzo.json",
    "Sant'Ambrogio":       "https://datastore.comune.fi.it/od/ParkInfo_SantAmbrogio.json",
    "Porta al Prato":      "https://datastore.comune.fi.it/od/ParkInfo_PortaAlPrato.json",
    "Pieraccini":          "https://datastore.comune.fi.it/od/ParkInfo_Pieraccini.json",
}

# ─────────────────────────────────────────────
# LOGGING  (console + file)
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("scraper.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────
def init_db() -> tuple[sqlite3.Connection, sqlite3.Cursor]:
    conn = sqlite3.connect(DB_NAME)
    cur  = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS storico (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            citta     TEXT    NOT NULL,
            nome      TEXT    NOT NULL,
            liberi    INTEGER,
            totali    INTEGER,
            timestamp TEXT    NOT NULL
        )
    """)
    # Indice per query rapide su timestamp + città (usato dall'app)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_storico_citta_ts
        ON storico (citta, timestamp)
    """)
    conn.commit()
    return conn, cur


def salva(cur: sqlite3.Cursor, citta: str, nome: str,
          liberi, totali, now: str) -> bool:
    """Valida e inserisce un record. Restituisce True se salvato, False altrimenti."""
    try:
        lib = int(liberi)
        tot = int(totali)
        if tot <= 0 or lib < 0 or lib > tot:
            log.warning("  ⚠ Dati anomali ignorati — %s › %s  (lib=%s tot=%s)",
                        citta, nome, liberi, totali)
            return False
        cur.execute(
            "INSERT INTO storico (citta, nome, liberi, totali, timestamp) "
            "VALUES (?, ?, ?, ?, ?)",
            (citta, nome, lib, tot, now),
        )
        return True
    except (ValueError, TypeError) as e:
        log.warning("  ⚠ Valore non convertibile — %s › %s: %s", citta, nome, e)
        return False


# ─────────────────────────────────────────────
# HTTP  con retry + backoff esponenziale
# ─────────────────────────────────────────────
def get_with_retry(url: str, headers: Optional[dict] = None,
                   parse: str = "json") -> Optional[any]:
    """
    GET con retry automatico.
    parse = 'json' → r.json()
    parse = 'bytes' → r.content
    Restituisce None se tutti i tentativi falliscono.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, headers=headers, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json() if parse == "json" else r.content
        except requests.exceptions.Timeout:
            log.warning("  Timeout (tentativo %d/%d): %s", attempt, MAX_RETRIES, url)
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code
            log.warning("  HTTP %s (tentativo %d/%d): %s", code, attempt, MAX_RETRIES, url)
            if code in (404, 403, 401):  # errori permanenti, inutile riprovare
                break
        except requests.exceptions.RequestException as e:
            log.warning("  Errore rete (tentativo %d/%d): %s", attempt, MAX_RETRIES, e)
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY * attempt)
    log.error("  ✗ Tutti i tentativi falliti: %s", url)
    return None


# ─────────────────────────────────────────────
# BOLOGNA
# Endpoint: REST JSON
# Dataset:  disponibilita-parcheggi-vigente
# Campi:    parcheggio, posti_liberi, posti_totali, coordinate{lat,lon}
# ─────────────────────────────────────────────
def aggiorna_bologna(cur: sqlite3.Cursor, now: str) -> int:
    url  = ("https://opendata.comune.bologna.it/api/explore/v2.1/catalog/"
            "datasets/disponibilita-parcheggi-vigente/records?limit=50")
    data = get_with_retry(url)
    if data is None:
        log.error("✗ Bologna: impossibile ottenere dati")
        return 0

    salvati = 0
    for rec in data.get("results", []):
        nome   = rec.get("parcheggio")
        liberi = rec.get("posti_liberi")
        totali = rec.get("posti_totali")
        if nome and salva(cur, "Bologna", nome, liberi, totali, now):
            salvati += 1

    log.info("✓ Bologna: %d parcheggi salvati", salvati)
    return salvati


# ─────────────────────────────────────────────
# TORINO
# Endpoint: XML via HTTPS  (IMPORTANTE: usare https://, non http://)
# Struttura: <PK><Name/><Free/><Total/><Lat/><Lng/><Status/></PK>
# Licenza:   IODL v2.0
# ─────────────────────────────────────────────
def aggiorna_torino(cur: sqlite3.Cursor, now: str) -> int:
    url     = "https://opendata.5t.torino.it/get_pk"  # HTTPS obbligatorio
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ParcheggiBot/1.0)",
        "Accept":     "application/xml, text/xml, */*",
    }
    content = get_with_retry(url, headers=headers, parse="bytes")
    if content is None:
        log.error("✗ Torino: impossibile ottenere dati")
        return 0

    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        log.error("✗ Torino: XML non valido — %s", e)
        return 0

    salvati = 0
    for pk in root.findall(".//PK"):
        try:
            nome   = pk.find("Name").text
            liberi = pk.find("Free").text
            totali = pk.find("Total").text
        except AttributeError:
            log.warning("  Record Torino malformato, saltato")
            continue
        if nome and salva(cur, "Torino", nome, liberi, totali, now):
            salvati += 1

    log.info("✓ Torino: %d parcheggi salvati", salvati)
    return salvati


# ─────────────────────────────────────────────
# FIRENZE
# Endpoint: GeoJSON individuale per ogni parcheggio
# Struttura: FeatureCollection con properties: FREE_SLOTS, TOTAL_SLOTS
# Licenza:   CC-BY 4.0  (Firenze Parcheggi S.p.A. / Comune di Firenze)
# ─────────────────────────────────────────────
def aggiorna_firenze(cur: sqlite3.Cursor, now: str) -> int:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ParcheggiBot/1.0)",
        "Accept":     "application/json, */*",
    }
    salvati = 0
    falliti = 0

    for nome, url in FIRENZE_PARCHEGGI.items():
        data = get_with_retry(url, headers=headers)
        if data is None:
            log.warning("  Firenze › %s: skip", nome)
            falliti += 1
            continue

        try:
            features = data.get("features", [])
            if not features:
                log.warning("  Firenze › %s: GeoJSON senza features", nome)
                falliti += 1
                continue

            props = features[0].get("properties", {})

            # L'API Firenze non è uniforme tra parcheggi: proviamo più nomi
            liberi = (props.get("FREE_SLOTS")  or props.get("free_slots")
                      or props.get("POSTI_LIBERI") or props.get("posti_liberi"))
            totali = (props.get("TOTAL_SLOTS") or props.get("total_slots")
                      or props.get("POSTI_TOTALI") or props.get("posti_totali"))

            if liberi is None or totali is None:
                log.warning("  Firenze › %s: campi posti non trovati (keys: %s)",
                            nome, list(props.keys()))
                falliti += 1
                continue

        except (KeyError, IndexError, AttributeError) as e:
            log.warning("  Firenze › %s: errore parsing — %s", nome, e)
            falliti += 1
            continue

        if salva(cur, "Firenze", nome, liberi, totali, now):
            salvati += 1
        else:
            falliti += 1

        time.sleep(0.3)  # pausa per non essere bloccati come bot

    log.info("✓ Firenze: %d salvati, %d falliti su %d",
             salvati, falliti, len(FIRENZE_PARCHEGGI))
    return salvati


# ─────────────────────────────────────────────
# PULIZIA DATI VECCHI
# ─────────────────────────────────────────────
def pulisci_vecchi(cur: sqlite3.Cursor, giorni: int = 30) -> int:
    cutoff = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        "DELETE FROM storico WHERE timestamp < datetime(?, '-' || ? || ' days')",
        (cutoff, giorni),
    )
    deleted = cur.rowcount
    if deleted:
        log.info("🗑  Pulizia: %d record eliminati (> %d giorni)", deleted, giorni)
    return deleted


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
def esegui(pulisci: bool = False, giorni_retention: int = 30) -> dict:
    start = time.time()
    log.info("═" * 55)
    log.info("Avvio  %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    conn, cur = init_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    stats = {
        "timestamp": now,
        "bologna":   aggiorna_bologna(cur, now),
        "torino":    aggiorna_torino(cur, now),
        "firenze":   aggiorna_firenze(cur, now),
        "eliminati": 0,
        "durata_s":  0.0,
    }

    if pulisci:
        stats["eliminati"] = pulisci_vecchi(cur, giorni_retention)

    conn.commit()
    conn.close()

    stats["durata_s"] = round(time.time() - start, 2)
    log.info("Done in %.2fs — BO:%d TO:%d FI:%d",
             stats["durata_s"], stats["bologna"], stats["torino"], stats["firenze"])
    log.info("═" * 55)
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scraper parcheggi IT — Bologna · Torino · Firenze")
    parser.add_argument("--pulisci",   action="store_true", help="Elimina record più vecchi di N giorni")
    parser.add_argument("--retention", type=int, default=30, help="Giorni di retention (default: 30)")
    args = parser.parse_args()
    esegui(pulisci=args.pulisci, giorni_retention=args.retention)
