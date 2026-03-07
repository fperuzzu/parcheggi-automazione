"""
motore_db.py
────────────────────
Raccoglie disponibilità parcheggi da:
  • Bologna  → REST JSON   (opendata.comune.bologna.it)   3 parcheggi
  • Torino   → XML         (opendata.5t.torino.it)        ~20 parcheggi
  • Firenze  → GeoJSON     (datastore.comune.fi.it)       ~13 parcheggi

Uso:
  python motore_db.py                        # esegui una volta
  python motore_db.py --pulisci              # esegui + elimina record > 30gg
  python motore_db.py --pulisci --retention 60

Cron (ogni 5 minuti):
  */5 * * * * cd /path/al/progetto && python motore_db.py >> cron.log 2>&1
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
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_storico_citta_ts
        ON storico (citta, timestamp)
    """)
    conn.commit()
    return conn, cur


def salva(cur: sqlite3.Cursor, citta: str, nome: str,
          liberi, totali, now: str) -> bool:
    """Valida e inserisce un record. Restituisce True se salvato."""
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
# HTTP con retry + backoff esponenziale
# ─────────────────────────────────────────────
def get_with_retry(url: str, headers: Optional[dict] = None,
                   parse: str = "json") -> Optional[any]:
    """
    GET con retry automatico.
    parse = 'json'  → r.json()
    parse = 'bytes' → r.content
    Restituisce None se tutti i tentativi falliscono.
    """
    base_headers = {"User-Agent": "Mozilla/5.0 (compatible; ParcheggiBot/1.0)"}
    if headers:
        base_headers.update(headers)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, headers=base_headers, timeout=TIMEOUT,
                             allow_redirects=True)
            r.raise_for_status()
            return r.json() if parse == "json" else r.content
        except requests.exceptions.Timeout:
            log.warning("  Timeout (tentativo %d/%d): %s", attempt, MAX_RETRIES, url)
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code
            log.warning("  HTTP %s (tentativo %d/%d): %s", code, attempt, MAX_RETRIES, url)
            if code in (404, 403, 401):
                break
        except requests.exceptions.RequestException as e:
            log.warning("  Errore rete (tentativo %d/%d): %s — %s",
                        attempt, MAX_RETRIES, type(e).__name__, url)
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY * attempt)

    log.error("  ✗ Tutti i tentativi falliti: %s", url)
    return None


# ─────────────────────────────────────────────
# BOLOGNA
# Endpoint: REST JSON
# Campi: parcheggio, posti_liberi, posti_totali
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
# Endpoint: XML — URL ufficiale è http:// (doc. 5T)
# Struttura: <PK><Name/><Free/><Total/><Lat/><Lng/></PK>
# Prova prima http:// poi https:// come fallback
# ─────────────────────────────────────────────
def aggiorna_torino(cur: sqlite3.Cursor, now: str) -> int:
    # URL ufficiale nel PDF 5T è http://, non https://
    urls = [
        "http://opendata.5t.torino.it/get_pk",
        "https://opendata.5t.torino.it/get_pk",
    ]
    extra = {"Accept": "application/xml, text/xml, */*"}

    raw  = None
    used = None
    for url in urls:
        raw = get_with_retry(url, headers=extra, parse="bytes")
        if raw is not None:
            used = url
            break

    if raw is None:
        log.error("✗ Torino: nessun endpoint raggiungibile")
        return 0

    # Verifica che sia XML e non HTML (pagina di blocco)
    if raw.lstrip()[:1] in (b"<",) is False or b"<html" in raw[:200].lower():
        log.error("✗ Torino: risposta non XML da %s", used)
        return 0

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        log.error("✗ Torino: XML non valido — %s", e)
        log.debug("  Primi 200 byte: %s", raw[:200])
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

    if salvati == 0:
        # Stampa i tag trovati per debug
        tags = {child.tag for pk in root.findall(".//PK") for child in pk}
        log.warning("  Torino: 0 salvati. Tag XML trovati nei PK: %s", tags or "nessuno")
        all_tags = {el.tag for el in root.iter()}
        log.warning("  Torino: tutti i tag nel documento: %s", all_tags)

    log.info("✓ Torino: %d parcheggi salvati", salvati)
    return salvati


# ─────────────────────────────────────────────
# FIRENZE
# Endpoint unico: ParkFreeSpot.json (tutti i parcheggi)
# I ParkInfo_*.json individuali contengono solo metadati statici
# Struttura attesa: GeoJSON FeatureCollection con properties live
# ─────────────────────────────────────────────
def aggiorna_firenze(cur: sqlite3.Cursor, now: str) -> int:
    urls = [
        "https://datastore.comune.fi.it/od/ParkFreeSpot.json",
        "http://datastore.comune.fi.it/od/ParkFreeSpot.json",
    ]
    extra = {"Accept": "application/json, */*"}

    data = None
    for url in urls:
        data = get_with_retry(url, headers=extra)
        if data is not None:
            log.info("  Firenze: dati ricevuti da %s", url)
            break

    if data is None:
        log.error("✗ Firenze: impossibile ottenere ParkFreeSpot.json")
        return 0

    features = data.get("features", [])
    if not features:
        # Debug: mostra la struttura effettiva
        log.error("✗ Firenze: GeoJSON vuoto (0 features). Chiavi top-level: %s",
                  list(data.keys()))
        return 0

    log.info("  Firenze: %d features trovate", len(features))

    # Mostra le props del primo elemento per debug
    if features:
        sample_props = features[0].get("properties", {})
        log.info("  Firenze: props esempio: %s", list(sample_props.keys()))

    salvati = 0
    for feat in features:
        try:
            props = feat.get("properties", {})

            # Campo nome — prova tutti i possibili nomi
            nome = (props.get("NOME")       or props.get("nome")
                    or props.get("NAME")      or props.get("name")
                    or props.get("PARK_NAME") or props.get("park_name")
                    or props.get("Descrizione") or props.get("descrizione"))

            # Posti liberi
            liberi = (props.get("POSTI_LIBERI")  or props.get("posti_liberi")
                      or props.get("FREE_SLOTS")   or props.get("free_slots")
                      or props.get("FREE")          or props.get("free")
                      or props.get("Liberi")        or props.get("liberi"))

            # Posti totali
            totali = (props.get("POSTI_TOTALI")  or props.get("posti_totali")
                      or props.get("TOTAL_SLOTS") or props.get("total_slots")
                      or props.get("TOTAL")        or props.get("total")
                      or props.get("Totali")        or props.get("totali")
                      or props.get("CAPIENZA")      or props.get("capienza"))

            if not nome:
                log.warning("  Firenze: feature senza nome (props: %s)",
                            list(props.keys())[:8])
                continue

            if liberi is None or totali is None:
                log.warning("  Firenze › %s: posti non trovati. Props: %s",
                            nome, list(props.keys()))
                continue

        except (AttributeError, KeyError) as e:
            log.warning("  Firenze: feature malformata — %s", e)
            continue

        if salva(cur, "Firenze", nome, liberi, totali, now):
            salvati += 1

    log.info("✓ Firenze: %d parcheggi salvati su %d features", salvati, len(features))
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
    parser = argparse.ArgumentParser(
        description="Scraper parcheggi IT — Bologna · Torino · Firenze")
    parser.add_argument("--pulisci",   action="store_true",
                        help="Elimina record più vecchi di N giorni")
    parser.add_argument("--retention", type=int, default=30,
                        help="Giorni di retention (default: 30)")
    args = parser.parse_args()
    esegui(pulisci=args.pulisci, giorni_retention=args.retention)
