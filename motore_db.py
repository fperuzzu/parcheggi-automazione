import requests
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime

DB_NAME = "storico_parcheggi.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
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
    return conn, cursor


def salva(cursor, citta, nome, liberi, totali, now):

    try:
        cursor.execute(
            "INSERT INTO storico (citta, nome, liberi, totali, timestamp) VALUES (?, ?, ?, ?, ?)",
            (citta, nome, int(liberi), int(totali), now)
        )
    except:
        pass


def aggiorna_bologna(cursor, now):

    try:

        url = "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=50"
        r = requests.get(url, timeout=15).json()

        for rec in r.get("results", []):

            nome = rec.get("parcheggio")
            liberi = rec.get("posti_liberi")
            totali = rec.get("posti_totali")

            salva(cursor, "Bologna", nome, liberi, totali, now)

        print("✅ Bologna aggiornata")

    except Exception as e:
        print("❌ Bologna:", e)


def aggiorna_torino(cursor, now):

    try:

        url = "http://opendata.5t.torino.it/get_pk"
        headers = {"User-Agent": "Mozilla/5.0"}

        r = requests.get(url, headers=headers, timeout=15)

        root = ET.fromstring(r.content)

        for pk in root.findall(".//PK"):

            nome = pk.find("Name").text
            liberi = pk.find("Free").text
            totali = pk.find("Total").text

            salva(cursor, "Torino", nome, liberi, totali, now)

        print("✅ Torino aggiornata")

    except Exception as e:
        print("❌ Torino:", e)


def esegui():

    conn, cursor = init_db()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    aggiorna_bologna(cursor, now)

    aggiorna_torino(cursor, now)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    esegui()
