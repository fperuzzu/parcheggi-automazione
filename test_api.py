import requests

# URL DA TESTARE (Candidati più probabili per il 2026)
TEST_SITES = {
    "Milano": "https://dati.comune.milano.it/api/explore/v2.1/catalog/datasets/disponibilita-parcheggi/records?limit=5",
    "Firenze": "https://opendata.comune.fi.it/api/explore/v2.1/catalog/datasets/parcheggi_struttura/records?limit=5",
    "Torino": "https://storing.5t.torino.it/fdt/extra/ParkingInformation.json"
}

def check_endpoints():
    headers = {"User-Agent": "Mozilla/5.0"}
    for citta, url in TEST_SITES.items():
        try:
            print(f"\n--- TEST {citta} ---")
            r = requests.get(url, headers=headers, timeout=10)
            print(f"Status Code: {r.status_code}")
            if r.status_code == 200:
                print(f"Dati ricevuti (anteprima): {str(r.json())[:200]}...")
            else:
                print(f"Errore: {r.text[:100]}")
        except Exception as e:
            print(f"Errore critico su {citta}: {e}")

if __name__ == "__main__":
    check_endpoints()
