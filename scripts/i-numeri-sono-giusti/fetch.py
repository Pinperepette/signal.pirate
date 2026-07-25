#!/usr/bin/env python3
"""Scarica da ISTAT (SDMX, esploradati.istat.it) i tre dataset usati nell'articolo
"I numeri sono giusti (la conclusione no)" e li salva in data/ come CSV.

  1. delitti.csv       - delitti denunciati dalle forze di polizia, per tipo di reato,
                         Italia, 2006-2024 (flusso 73_67_DF_DCCV_DELITTIPS_1)
  2. vittime_sesso.csv - vittime di omicidio volontario per sesso, 2007-2024
                         (flusso 73_230_DF_DCCV_AUTVITTPS_1, DATA_TYPE=VICTIM)
  3. denunciati_cittadinanza.csv - autori di delitto denunciati per cittadinanza,
                         sesso ed eta', totale reati (stesso flusso, DATA_TYPE=OFFEND)

Nessuna dipendenza oltre alla libreria standard. Uso: python3 fetch.py
"""
import csv, io, time, urllib.request, os

BASE = "https://esploradati.istat.it/SDMXWS/rest"
HERE = os.path.dirname(os.path.abspath(__file__))

def get(url, timeout=180, retries=3):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.sdmx.data+csv",
        "User-Agent": "signal-pirate-repro/1.0"})
    last = None
    for i in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8-sig", errors="replace")
        except Exception as e:
            last = e; time.sleep(2 * (i + 1))
    raise RuntimeError(f"GET fallito: {url}\n{last}")

def fetch_csv(flow, key):
    text = get(f"{BASE}/data/{flow}/{key}?format=csv")
    if text.strip() in ("", "NoRecordsFound"):
        return []
    return list(csv.DictReader(io.StringIO(text)))

def save(name, rows, cols):
    path = os.path.join(HERE, "data", name)
    with open(path, "w", newline="") as f:
        w = csv.writer(f); w.writerow(cols)
        for r in rows:
            w.writerow([r.get(c, "") for c in cols])
    print(f"  {name}: {len(rows)} righe")

if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)

    print("1/3 delitti denunciati (73_67)...")
    rows = fetch_csv("IT1,73_67_DF_DCCV_DELITTIPS_1,1.0", "A.IT.CRIMEN..9.YRDUR")
    rows = [r for r in rows if r.get("OBS_VALUE")]
    save("delitti.csv", rows, ["TYPE_CRIME", "TIME_PERIOD", "OBS_VALUE"])

    print("2/3 vittime di omicidio per sesso (73_230, VICTIM)...")
    rows = fetch_csv("IT1,73_230_DF_DCCV_AUTVITTPS_1,1.0", "A.IT.VICTIM.INTENHOM...TOTAL.WORLD")
    rows = [r for r in rows if r.get("OBS_VALUE")]
    save("vittime_sesso.csv", rows, ["SEX", "AGE", "TIME_PERIOD", "OBS_VALUE"])

    print("3/3 denunciati per cittadinanza (73_230, OFFEND, totale reati)...")
    rows = fetch_csv("IT1,73_230_DF_DCCV_AUTVITTPS_1,1.0", "A.IT.OFFEND.TOT....WORLD")
    rows = [r for r in rows if r.get("OBS_VALUE")]
    save("denunciati_cittadinanza.csv", rows, ["CITIZENSHIP", "SEX", "AGE", "TIME_PERIOD", "OBS_VALUE"])
    print("fatto.")
