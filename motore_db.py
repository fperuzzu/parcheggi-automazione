import requests
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime
import time
import random

DB_NAME = "storico_parcheggi.db"


# =========================
# Utility
# =========================
def safe_int(val):
    try:
        return int(val)
    except:
        return 0


def get_json(url):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    for _ in range(3):
        try:
            r = requests.get(url, headers=headers, timeout=20)
            r.raise_for_status()
            return r.json()
        except:
            time.sleep(2)
    raise Exception("Errore richiesta JSON")


def get_xml(url):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/xml,text/xml,*/*",
        "Referer": "http://www.muoversiatorino.it/"
    }

    for _ in range(3):
        try:
            r = requests.get(url, headers=headers, timeout=20)
            r.raise_for_status()
            return r.content
        except:
            time.sleep(2)
    raise Exception("Errore richiesta XML")


# =========================
# Database
# =========================
def inizializza_db(conn):
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS storico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            citta TEXT,
            nome TEXT,
            liberi INTEGER,
            totali INTEGER,
            timestamp TEXT
        )
    """)

    conn.commit()


# =========================
# Aggiornamento
# =========================
def esegui_aggiornamento():

    conn = sqlite3.connect(DB_NAME)
    inizializza_db(conn)
    cursor = conn.cursor()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # -------------------------
    # BOLOGNA
    # -------------------------
    try:
        url_bo = "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=100"
        data = get_json(url_bo)

        for rec in data.get("results", []):
            nome = rec.get("parcheggio")
            liberi = safe_int(rec.get("posti_liberi"))
            totali = safe_int(rec.get("posti_totali"))

            if nome:
                cursor.execute(
                    "INSERT INTO storico (citta, nome, liberi, totali, timestamp) VALUES (?, ?, ?, ?, ?)",
                    ("Bologna", nome, liberi, totali, now)
                )

        print("✅ Bologna aggiornata")

    except Exception as e:
        print("❌ Errore Bologna:", e)

    time.sleep(random.uniform(0.5, 1.5))

    # -------------------------
    # TORINO
    # -------------------------
    try:
        url_to = "http://opendata.5t.torino.it/get_pk"
        xml_data = get_xml(url_to)
        root = ET.fromstring(xml_data)

        for pk in root.findall("Table"):
            nome = pk.findtext("Name")
            liberi = safe_int(pk.findtext("Free"))
            totali = safe_int(pk.findtext("Total"))

            if nome:
                cursor.execute(
                    "INSERT INTO storico (citta, nome, liberi, totali, timestamp) VALUES (?, ?, ?, ?, ?)",
                    ("Torino", nome, liberi, totali, now)
                )

        print("✅ Torino aggiornata")

    except Exception as e:
        print("❌ Errore Torino:", e)

    time.sleep(random.uniform(0.5, 1.5))

    # -------------------------
    # FIRENZE
    # -------------------------
    try:
        url_fi = "https://datastore.comune.fi.it/od/ParkFreeSpot.json"
        data = get_json(url_fi)

        # IMPORTANTE: è una LISTA
        for rec in data:
            nome = rec.get("ParkName")
            liberi = safe_int(rec.get("FreeSpots"))
            totali = safe_int(rec.get("TotalSpots"))

            if nome:
                cursor.execute(
                    "INSERT INTO storico (citta, nome, liberi, totali, timestamp) VALUES (?, ?, ?, ?, ?)",
                    ("Firenze", nome, liberi, totali, now)
                )

        print("✅ Firenze aggiornata")

    except Exception as e:
        print("❌ Errore Firenze:", e)

    conn.commit()
    conn.close()


# =========================
# Main
# =========================
if __name__ == "__main__":
    esegui_aggiornamento()
