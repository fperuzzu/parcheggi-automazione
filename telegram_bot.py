"""
ParkPulse Telegram Bot
t.me/parkpulse_it_bot

Comandi:
  /start    — benvenuto + menu
  /bologna  — snapshot Bologna
  /torino   — snapshot Torino
  /firenze  — snapshot Firenze
  /iscrivi  — iscrizione aggiornamento mattutino
  /disiscrivi — rimozione iscrizione
  /help     — aiuto

Deploy: python telegram_bot.py (polling)
Oppure lanciato da GitHub Actions per notifiche mattutine
"""

import os
import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
BASE_URL   = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ─── Iscritti (file JSON su disco, in produzione usa Turso) ───
SUBSCRIBERS_FILE = "subscribers.json"

def load_subscribers():
    try:
        with open(SUBSCRIBERS_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

def save_subscribers(subs):
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(subs, f)

# ─── Fetch dati parcheggi ───

def fetch_bologna():
    try:
        url = "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi-vigente/records?limit=50"
        r = requests.get(url, timeout=10)
        data = r.json().get("results", [])
        parcheggi = []
        for p in data:
            nome  = p.get("parcheggio", "—")
            lib   = int(p.get("posti_liberi") or 0)
            tot   = int(p.get("posti_totali") or 1)
            occ   = int((tot - lib) / tot * 100) if tot > 0 else 0
            parcheggi.append((nome, lib, tot, occ))
        return parcheggi
    except Exception:
        return []

def fetch_torino():
    try:
        url = "https://opendata.5t.torino.it/get_pk"
        r = requests.get(url, timeout=10)
        NS = "{https://simone.5t.torino.it/ns/traffic_data.xsd}"
        root = ET.fromstring(r.content)
        parcheggi = []
        for pk in root.findall(f".//{NS}ParkingFacility"):
            nome = pk.get("Name", "—")
            lib  = int(pk.get("Free") or 0)
            tot  = int(pk.get("Total") or 1)
            occ  = int((tot - lib) / tot * 100) if tot > 0 else 0
            parcheggi.append((nome, lib, tot, occ))
        return parcheggi[:15]  # max 15 per leggibilità
    except Exception:
        return []

def fetch_firenze():
    try:
        url = "https://datastore.comune.fi.it/od/ParkFreeSpot.json"
        r = requests.get(url, timeout=10)
        data = r.json()
        TOTALI = {
            "Parterre": 630, "Oltrarno": 339, "Fortezza": 700,
            "Stazione": 480, "Beccaria": 287, "Alberti": 546,
            "Rosselli": 374, "Michelangelo": 480, "Piazzale": 480,
            "Consiglio": 750, "Novoli": 1000, "Careggi": 400, "Monna": 500,
        }
        parcheggi = []
        for p in data:
            nome = p.get("Name", "—")
            lib  = int(p.get("FreeSpot") or 0)
            tot  = next((v for k, v in TOTALI.items() if k.lower() in nome.lower()), 500)
            occ  = int((tot - lib) / tot * 100) if tot > 0 else 0
            parcheggi.append((nome, lib, tot, occ))
        return parcheggi
    except Exception:
        return []

FETCH_MAP = {
    "bologna": fetch_bologna,
    "torino":  fetch_torino,
    "firenze": fetch_firenze,
}

CITY_EMOJI = {"bologna": "🅱", "torino": "🔺", "firenze": "🌸"}

# ─── Formatta messaggio snapshot ───

def format_snapshot(city):
    parcheggi = FETCH_MAP[city]()
    if not parcheggi:
        return f"⚠️ Dati non disponibili per {city.title()} al momento."

    tot_lib = sum(p[1] for p in parcheggi)
    tot_tot = sum(p[2] for p in parcheggi)
    pct_glob = int((tot_tot - tot_lib) / tot_tot * 100) if tot_tot > 0 else 0
    ora = datetime.now().strftime("%H:%M")

    status = "🟢" if pct_glob < 60 else "🟡" if pct_glob < 85 else "🔴"

    lines = [
        f"{CITY_EMOJI[city]} *ParkPulse — {city.title()}*",
        f"🕐 Aggiornato alle {ora}",
        f"",
        f"{status} *{tot_lib} posti liberi* su {tot_tot} totali ({pct_glob}% occupato)",
        f"",
        f"📍 *Dettaglio parcheggi:*",
    ]

    # Ordina per posti liberi decrescente
    for nome, lib, tot, occ in sorted(parcheggi, key=lambda x: x[1], reverse=True):
        em = "🟢" if occ < 60 else "🟡" if occ < 85 else "🔴"
        bar = "█" * int(occ / 10) + "░" * (10 - int(occ / 10))
        lines.append(f"{em} *{nome}*: {lib} liberi ({occ}%)")

    lines += [
        f"",
        f"🗺 [Apri Dashboard](https://parkpulse.it) | [Naviga con Maps](https://maps.google.com/?q={city}+parcheggi)",
        f"",
        f"_Dati da API ufficiali — aggiornati ogni 30 min_",
    ]
    return "\n".join(lines)

# ─── Invio messaggio ───

def send_message(chat_id, text, parse_mode="Markdown"):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    requests.post(f"{BASE_URL}/sendMessage", json=payload, timeout=10)

def send_welcome(chat_id):
    text = (
        "🅿 *Benvenuto su ParkPulse\\!*\n\n"
        "Monitoro i parcheggi di Bologna, Torino e Firenze in tempo reale\\.\n\n"
        "*Comandi disponibili:*\n"
        "🅱 /bologna — Parcheggi Bologna\n"
        "🔺 /torino — Parcheggi Torino\n"
        "🌸 /firenze — Parcheggi Firenze\n"
        "🔔 /iscrivi — Aggiornamento ogni mattina alle 8:00\n"
        "🔕 /disiscrivi — Disattiva aggiornamenti\n\n"
        "🌐 [parkpulse\\.it](https://parkpulse.it)"
    )
    send_message(chat_id, text, parse_mode="MarkdownV2")

# ─── Gestione comandi ───

def handle_update(update):
    msg = update.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    text    = msg.get("text", "").strip().lower()
    if not chat_id or not text:
        return

    subs = load_subscribers()

    if text.startswith("/start") or text.startswith("/help"):
        send_welcome(chat_id)

    elif text.startswith("/bologna"):
        send_message(chat_id, "⏳ Carico dati Bologna...")
        send_message(chat_id, format_snapshot("bologna"))

    elif text.startswith("/torino"):
        send_message(chat_id, "⏳ Carico dati Torino...")
        send_message(chat_id, format_snapshot("torino"))

    elif text.startswith("/firenze"):
        send_message(chat_id, "⏳ Carico dati Firenze...")
        send_message(chat_id, format_snapshot("firenze"))

    elif text.startswith("/iscrivi"):
        city = "bologna"
        for c in ["bologna", "torino", "firenze"]:
            if c in text:
                city = c
                break
        subs[str(chat_id)] = {"city": city, "active": True}
        save_subscribers(subs)
        send_message(chat_id,
            f"✅ Iscritto! Riceverai uno snapshot di *{city.title()}* ogni mattina alle 8:00.\n\n"
            f"Per cambiare città: /iscrivi bologna | /iscrivi torino | /iscrivi firenze\n"
            f"Per disattivare: /disiscrivi",
        )

    elif text.startswith("/disiscrivi"):
        if str(chat_id) in subs:
            subs[str(chat_id)]["active"] = False
            save_subscribers(subs)
        send_message(chat_id, "🔕 Aggiornamenti disattivati. Usa /iscrivi per riattivarli.")

    else:
        send_message(chat_id,
            "Non capisco 😅 Usa /bologna, /torino o /firenze per vedere i parcheggi.\n"
            "Digita /help per tutti i comandi."
        )

# ─── Broadcast mattutino (chiamato da GitHub Actions) ───

def broadcast_morning():
    """Invia snapshot mattutino a tutti gli iscritti attivi."""
    subs = load_subscribers()
    sent = 0
    cache = {}
    for key, info in subs.items():
        if not info.get("active"):
            continue
        city = info.get("city", "bologna")
        # Supporta sia formato {"chat_id": 123} che chiave numerica
        chat_id = info.get("chat_id") or int(key)
        if city not in cache:
            cache[city] = format_snapshot(city)
        send_message(int(chat_id), "☀️ *Buongiorno da ParkPulse!*\n\n" + cache[city])
        sent += 1
    print(f"Broadcast inviato a {sent} iscritti")

# ─── Polling (per sviluppo locale) ───

def run_polling():
    print("ParkPulse Bot avviato — polling...")
    offset = 0
    while True:
        try:
            r = requests.get(f"{BASE_URL}/getUpdates",
                             params={"offset": offset, "timeout": 30}, timeout=35)
            updates = r.json().get("result", [])
            for upd in updates:
                handle_update(upd)
                offset = upd["update_id"] + 1
        except Exception as e:
            print(f"Errore polling: {e}")
            import time; time.sleep(5)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "broadcast":
        broadcast_morning()
    else:
        run_polling()
