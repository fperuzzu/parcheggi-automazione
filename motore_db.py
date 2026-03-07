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
    # http:// → 403, solo https:// funziona da GitHub Actions
    # Namespace reale: {https://simone.5t.torino.it/ns/traffic_data.xsd}
    urls = [
        "https://opendata.5t.torino.it/get_pk",
        "http://opendata.5t.torino.it/get_pk",
    ]
    extra = {"Accept": "application/xml, text/xml, */*"}

    raw = None
    for url in urls:
        raw = get_with_retry(url, headers=extra, parse="bytes")
        if raw is not None:
            break

    if raw is None:
        log.error("✗ Torino: nessun endpoint raggiungibile")
        return 0

    if b"<html" in raw[:200].lower():
        log.error("✗ Torino: risposta HTML (blocco IP)")
        return 0

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        log.error("✗ Torino: XML non valido — %s", e)
        return 0

    # Il namespace reale è {https://simone.5t.torino.it/ns/traffic_data.xsd}
    # I tag sono: traffic_data > PK_data (contiene i parcheggi)
    # Cerchiamo con wildcard namespace {*}
    NS = "{https://simone.5t.torino.it/ns/traffic_data.xsd}"

    # I dati live sono in attributi XML oppure in tag figli — proviamo entrambi
    # Esempio struttura attesa:
    #   <PK_data name="Parcheggio X" free_slots="12" total_slots="200"/>
    #   oppure con attributi: free="12" total="200" id="..." description="..."

    salvati = 0
    pk_elements = list(root.iter(f"{NS}PK_data"))

    if not pk_elements:
        # Struttura sconosciuta: logga tutto il documento per capire
        all_tags = [(el.tag.split("}")[-1], el.attrib, el.text) for el in root.iter()]
        log.warning("  Torino: nessun PK_data. Struttura XML: %s", all_tags[:20])
        log.info("✓ Torino: 0 parcheggi salvati")
        return 0

    # Debug: mostra attributi e testo del primo PK_data
    first = pk_elements[0]
    log.info("  Torino: primo PK_data — attrib=%s text=%r figli=%s",
             first.attrib, first.text,
             [(c.tag.split("}")[-1], c.attrib, c.text) for c in first][:5])

    for pk in pk_elements:
        attrib = pk.attrib  # attributi XML: {"name": "...", "free_slots": "12", ...}

        # Prova prima attributi, poi tag figli, poi text content
        def get_val(*keys):
            for k in keys:
                v = attrib.get(k) or pk.findtext(f"{NS}{k}")
                if v is not None:
                    return v
            return None

        nome   = get_val("name", "Name", "description", "Description", "id", "Id")
        liberi = get_val("free_slots", "free", "Free", "FreeSlots", "free_slots_rt")
        totali = get_val("total_slots", "total", "Total", "TotalSlots", "capacity")

        if not nome:
            continue
        if salva(cur, "Torino", nome, liberi, totali, now):
            salvati += 1

    log.info("✓ Torino: %d parcheggi salvati", salvati)
    return salvati


# ─────────────────────────────────────────────
# FIRENZE — capacità fissa per parcheggio
# ParkFreeSpot.json fornisce solo FreeSpot, non i totali
# Fonte capacità: sito ufficiale Firenze Parcheggi S.p.A.
# ─────────────────────────────────────────────
FIRENZE_CAPACITA = {
    "Parterre":             630,
    "Palazzo di Giustizia": 480,
    "Oltrarno":             392,
    "Fortezza da Basso":    650,
    "Stazione":             600,  # Stazione SMN
    "Stazione Binario 16":  170,
    "Careggi":              340,
    "Beccaria":             800,
    "Alberti":              540,
    "San Lorenzo":          165,
    "Sant'Ambrogio":        398,
    "Porta al Prato":       490,
    "Pieraccini":           400,
}
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

    # ParkFreeSpot.json può restituire una lista diretta OPPURE un GeoJSON dict
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        records = data.get("features", [])
        if not records:
            log.error("✗ Firenze: GeoJSON vuoto. Chiavi: %s", list(data.keys()))
            return 0
    else:
        log.error("✗ Firenze: formato non gestito: %s", type(data))
        return 0

    log.info("  Firenze: %d record ricevuti", len(records))
    if records:
        # Mostra la struttura del primo record per debug
        first = records[0]
        if isinstance(first, dict):
            # Se è GeoJSON standard, le props sono nested in "properties"
            sample = first.get("properties", first)
            log.info("  Firenze: chiavi esempio: %s", list(sample.keys())[:10])

    salvati = 0
    for feat in records:
        try:
            if isinstance(feat, dict) and "properties" in feat:
                props = feat["properties"]
            elif isinstance(feat, dict):
                props = feat
            else:
                continue

            # Campi reali confermati dal log: Id, Name, FreeSpot, UpdateDate, Latitude, Longitude
            nome   = props.get("Name") or props.get("name") or props.get("NOME")
            liberi = props.get("FreeSpot") or props.get("free_spot") or props.get("FREE_SLOTS")

            if not nome:
                log.warning("  Firenze: record senza nome (chiavi: %s)", list(props.keys()))
                continue
            if liberi is None:
                log.warning("  Firenze › %s: FreeSpot non trovato. Chiavi: %s",
                            nome, list(props.keys()))
                continue

            # Cerca la capacità totale nel dizionario fisso
            # Match parziale: "Stazione" trova "Stazione SMN", ecc.
            totali = None
            for chiave, cap in FIRENZE_CAPACITA.items():
                if chiave.lower() in nome.lower() or nome.lower() in chiave.lower():
                    totali = cap
                    break

            if totali is None:
                log.warning("  Firenze › %s: capacità non in dizionario, uso FreeSpot come stima",
                            nome)
                # Fallback: salva comunque con totali=max(liberi,1) — dati parziali
                totali = max(int(liberi), 1)

        except (AttributeError, KeyError, ValueError) as e:
            log.warning("  Firenze: record malformato — %s", e)
            continue

        if salva(cur, "Firenze", nome, liberi, totali, now):
            salvati += 1

    log.info("✓ Firenze: %d parcheggi salvati su %d record", salvati, len(records))
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
