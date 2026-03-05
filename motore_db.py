import requests
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime
import time
import random

DB_NAME = "storico_parcheggi.db"


# ==============================
# SESSIONE HTTP ROBUSTA
# ==============================
def crea_sessione():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json, text/plain, */*",
        "Connection": "keep-alive"
    })
    return session


def get_json(session, url):
    for tentativo in range(3):
        try:
            r = session.get(url, timeout=20)
            r.raise_for_status()
            return r.json()
        except Exception:
            if tentativo == 2:
                raise
            time.sleep(2)


def get_xml(session, url):
    for tentativo in range(3):
        try:
            r = session.get(url, timeout=20)
            r.raise_for_status()
            return r.content
        except Exception:
            if tentativo == 2:
                raise
            time.sleep(2)


# ==============================
# DATABASE
# ==============================
def migra_db(conn):
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

    # Migrazione colonne se mancanti
    try:
        cursor.execute("ALTER TABLE storico ADD COLUMN totali INTEGER")
    except:
        pass

    try:
        cursor.execute("ALTER TABLE storico ADD COLUMN citta TEXT")
    except:
        pass

    conn.commit()


def safe_int(val):
    try:
        return int(val)
    except:
        return 0


# ==============================
# AGGIORNAMENTO DATI
# ==============================
def esegui_aggiornamento():
    session = crea_sessione()

    conn = sqlite3.connect(DB_NAME)
    migra_db(conn)
    cursor = conn.cursor()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ==============================
    # BOLOGNA
    # ==============================
    try:
        url_bo = "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=100"
        data = get_json(session, url_bo)

        for rec in data.get("results", []):
            nome = rec.get("parcheggio")
            liberi = safe_int(rec.get("posti_liberi"))
            totali = safe_int(rec.get("posti_totali"))

            if nome:
                cursor.execute("""
                    INSERT INTO storico (citta, nome, liberi, totali, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, ("Bologna", nome, liberi, totali, now))

        print("✅ Bologna aggiornata")

    except Exception as e:
        print(f"❌ Errore Bologna: {e}")

    time.sleep(random.uniform(0.5, 1.5))


    # --- TORINO ---
try:
    xml_data = get_xml_torino()
    root = ET.fromstring(xml_data)

    for pk in root.findall("Table"):
        nome = pk.findtext("Name")
        liberi = safe_int(pk.findtext("Free"))
        totali = safe_int(pk.findtext("Total"))

        if nome:
            cursor.execute("""
                INSERT INTO storico (citta, nome, liberi, totali, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, ("Torino", nome, liberi, totali, now))

    print("✅ Torino aggiornata")

except Exception as e:
    print(f"❌ Errore Torino: {e}")

    # ==============================
# --- FIRENZE ---
try:
    url_fi = "https://datastore.comune.fi.it/od/ParkFreeSpot.json"
    data = get_json(session, url_fi)

    # data è una LISTA, non un dict
    for rec in data:
        nome = rec.get("ParkName")
        liberi = safe_int(rec.get("FreeSpots"))
        totali = safe_int(rec.get("TotalSpots"))

        if nome:
            cursor.execute("""
                INSERT INTO storico (citta, nome, liberi, totali, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, ("Firenze", nome, liberi, totali, now))

    print("✅ Firenze aggiornata")

except Exception as e:
    print(f"❌ Errore Firenze: {e}")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    esegui_aggiornamento()
