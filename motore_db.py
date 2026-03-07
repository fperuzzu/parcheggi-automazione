"""
motore_db.py  —  Scraper parcheggi → Turso (SQLite cloud)
──────────────────────────────────────────────────────────
Variabili d'ambiente richieste:
  TURSO_URL    → libsql://nome-db-utente.turso.io
  TURSO_TOKEN  → token dal dashboard Turso

Uso:
  python motore_db.py
  python motore_db.py --pulisci --retention 30
"""

import os
import requests
import xml.etree.ElementTree as ET
import logging
import time
import argparse
from datetime import datetime
from typing import Optional

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
TURSO_URL   = os.environ["TURSO_URL"]
TURSO_TOKEN = os.environ["TURSO_TOKEN"]

MAX_RETRIES = 3
RETRY_DELAY = 4
TIMEOUT     = 15

# ─────────────────────────────────────────────
# LOGGING
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
# DATABASE — Turso via HTTP API (zero dipendenze native)
# Docs: https://docs.turso.tech/sdk/http/reference
# ─────────────────────────────────────────────
class TursoDB:
    def __init__(self, url: str, token: str):
        self.base    = url.replace("libsql://", "https://")
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        }

    def _run(self, requests_list: list) -> dict:
        requests_list.append({"type": "close"})
        r = requests.post(
            f"{self.base}/v2/pipeline",
            json={"requests": requests_list},
            headers=self.headers,
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def _stmt(self, sql: str, params: list = None) -> dict:
        stmt = {"type": "execute", "stmt": {"sql": sql}}
        if params:
            stmt["stmt"]["args"] = [
                {"type": "integer", "value": p} if isinstance(p, int)
                else {"type": "text", "value": str(p)}
                for p in params
            ]
        return stmt

    def execute(self, sql: str, params: list = None) -> dict:
        return self._run([self._stmt(sql, params)])

    def executemany(self, sql: str, params_list: list) -> None:
        if not params_list:
            return
        self._run([self._stmt(sql, p) for p in params_list])


def init_db(db: TursoDB) -> None:
    db.execute("""
        CREATE TABLE IF NOT EXISTS storico (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            citta     TEXT    NOT NULL,
            nome      TEXT    NOT NULL,
            liberi    INTEGER,
            totali    INTEGER,
            timestamp TEXT    NOT NULL
        )
    """)
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_storico_citta_ts
        ON storico (citta, timestamp)
    """)


def valida(citta: str, nome: str, liberi, totali) -> Optional[tuple]:
    try:
        lib = int(liberi); tot = int(totali)
        if tot <= 0 or lib < 0 or lib > tot:
            log.warning("  ⚠ Anomalia — %s › %s (lib=%s tot=%s)", citta, nome, liberi, totali)
            return None
        return lib, tot
    except (ValueError, TypeError) as e:
        log.warning("  ⚠ Non convertibile — %s › %s: %s", citta, nome, e)
        return None


def salva_batch(db: TursoDB, records: list) -> int:
    if not records:
        return 0
    db.executemany(
        "INSERT INTO storico (citta, nome, liberi, totali, timestamp) VALUES (?, ?, ?, ?, ?)",
        records
    )
    return len(records)


# ─────────────────────────────────────────────
# HTTP con retry
# ─────────────────────────────────────────────
def get_with_retry(url: str, headers: dict = None, parse: str = "json"):
    base_headers = {"User-Agent": "Mozilla/5.0 (compatible; ParcheggiBot/1.0)"}
    if headers:
        base_headers.update(headers)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, headers=base_headers, timeout=TIMEOUT, allow_redirects=True)
            r.raise_for_status()
            return r.json() if parse == "json" else r.content
        except requests.exceptions.Timeout:
            log.warning("  Timeout (%d/%d): %s", attempt, MAX_RETRIES, url)
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code
            log.warning("  HTTP %s (%d/%d): %s", code, attempt, MAX_RETRIES, url)
            if code in (404, 403, 401):
                break
        except requests.exceptions.RequestException as e:
            log.warning("  Rete (%d/%d): %s", attempt, MAX_RETRIES, type(e).__name__)
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY * attempt)
    log.error("  ✗ Fallito: %s", url)
    return None


# ─────────────────────────────────────────────
# BOLOGNA
# ─────────────────────────────────────────────
def aggiorna_bologna(db: TursoDB, now: str) -> int:
    data = get_with_retry(
        "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/"
        "datasets/disponibilita-parcheggi-vigente/records?limit=50"
    )
    if not data:
        log.error("✗ Bologna: nessun dato"); return 0

    records = []
    for rec in data.get("results", []):
        nome = rec.get("parcheggio")
        v = valida("Bologna", nome, rec.get("posti_liberi"), rec.get("posti_totali"))
        if nome and v:
            records.append(("Bologna", nome, v[0], v[1], now))

    n = salva_batch(db, records)
    log.info("✓ Bologna: %d salvati", n)
    return n


# ─────────────────────────────────────────────
# TORINO
# ─────────────────────────────────────────────
def aggiorna_torino(db: TursoDB, now: str) -> int:
    NS  = "{https://simone.5t.torino.it/ns/traffic_data.xsd}"
    raw = None
    for url in ["https://opendata.5t.torino.it/get_pk", "http://opendata.5t.torino.it/get_pk"]:
        raw = get_with_retry(url, {"Accept": "application/xml, text/xml, */*"}, "bytes")
        if raw:
            break
    if not raw or b"<html" in raw[:200].lower():
        log.error("✗ Torino: nessun dato"); return 0

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        log.error("✗ Torino: XML non valido — %s", e); return 0

    records = []
    for pk in root.iter(f"{NS}PK_data"):
        a = pk.attrib
        def gv(*keys):
            for k in keys:
                v = a.get(k) or pk.findtext(f"{NS}{k}")
                if v is not None: return v
            return None
        nome   = gv("Name", "name")
        liberi = gv("Free", "free", "free_slots")
        totali = gv("Total", "total", "total_slots")
        if not nome or liberi is None or totali is None:
            continue
        v = valida("Torino", nome, liberi, totali)
        if v:
            records.append(("Torino", nome, v[0], v[1], now))

    n = salva_batch(db, records)
    log.info("✓ Torino: %d salvati", n)
    return n


# ─────────────────────────────────────────────
# FIRENZE
# ─────────────────────────────────────────────
FIRENZE_CAPACITA = {
    "Parterre": 630, "Palazzo": 480, "Oltrarno": 392, "Fortezza": 650,
    "Stazione": 600, "Careggi": 900, "Beccaria": 800, "Alberti": 540,
    "San Lorenzo": 165, "Ambrogio": 398, "Porta al Prato": 490, "Pieraccini": 800,
}

def aggiorna_firenze(db: TursoDB, now: str) -> int:
    data = None
    for url in ["https://datastore.comune.fi.it/od/ParkFreeSpot.json",
                "http://datastore.comune.fi.it/od/ParkFreeSpot.json"]:
        data = get_with_retry(url, {"Accept": "application/json, */*"})
        if data: break
    if not data:
        log.error("✗ Firenze: nessun dato"); return 0

    raw_list = data if isinstance(data, list) else data.get("features", [])
    records  = []
    for feat in raw_list:
        try:
            props  = feat.get("properties", feat) if isinstance(feat, dict) else {}
            nome   = props.get("Name") or props.get("name")
            liberi = props.get("FreeSpot") or props.get("free_spot")
            if not nome or liberi is None: continue
            totali = next((c for k, c in FIRENZE_CAPACITA.items() if k.lower() in nome.lower()), max(int(liberi), 1))
            v = valida("Firenze", nome, liberi, totali)
            if v: records.append(("Firenze", nome, v[0], v[1], now))
        except (AttributeError, KeyError, ValueError):
            continue

    n = salva_batch(db, records)
    log.info("✓ Firenze: %d salvati su %d record", n, len(raw_list))
    return n


# ─────────────────────────────────────────────
# PULIZIA
# ─────────────────────────────────────────────
def pulisci_vecchi(db: TursoDB, giorni: int = 30) -> None:
    cutoff = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.execute(
        "DELETE FROM storico WHERE timestamp < datetime(?, '-' || ? || ' days')",
        [cutoff, str(giorni)]
    )
    log.info("🗑  Pulizia: record > %d giorni rimossi", giorni)


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
def esegui(pulisci: bool = False, giorni_retention: int = 30) -> dict:
    start = time.time()
    log.info("═" * 55)
    log.info("Avvio  %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    db  = TursoDB(TURSO_URL, TURSO_TOKEN)
    init_db(db)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    stats = {
        "timestamp": now,
        "bologna":   aggiorna_bologna(db, now),
        "torino":    aggiorna_torino(db, now),
        "firenze":   aggiorna_firenze(db, now),
        "durata_s":  0.0,
    }
    if pulisci:
        pulisci_vecchi(db, giorni_retention)

    stats["durata_s"] = round(time.time() - start, 2)
    log.info("Done in %.2fs — BO:%d TO:%d FI:%d",
             stats["durata_s"], stats["bologna"], stats["torino"], stats["firenze"])
    log.info("═" * 55)
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pulisci",   action="store_true")
    parser.add_argument("--retention", type=int, default=30)
    args = parser.parse_args()
    esegui(pulisci=args.pulisci, giorni_retention=args.retention)
