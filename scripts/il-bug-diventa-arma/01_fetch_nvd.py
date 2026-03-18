#!/usr/bin/env python3
"""
01_fetch_nvd.py — Scarica le CVE dal NIST NVD (API 2.0)
Estrae: CVE ID + data di pubblicazione
Output: data/nvd_cves.csv

NB: L'API NVD 2.0 ha un limite di 120 giorni per range date.
    Lo script itera automaticamente a blocchi di 120 giorni.
"""

import requests
import csv
import os
import time
from datetime import datetime, timedelta

API_URL = 'https://services.nvd.nist.gov/rest/json/cves/2.0'
RESULTS_PER_PAGE = 2000
OUTPUT_DIR = 'data'
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'nvd_cves.csv')

# Range: ultimi 10 anni (modificabile)
YEAR_START = 2014
YEAR_END = 2024

# NVD API 2.0: max 120 giorni per query
CHUNK_DAYS = 120


def fetch_chunk(start_date, end_date, rows):
    """Scarica tutte le CVE in un singolo range di date (max 120gg)."""
    start_str = start_date.strftime('%Y-%m-%dT00:00:00.000')
    end_str = end_date.strftime('%Y-%m-%dT23:59:59.999')
    start_index = 0

    while True:
        params = {
            'pubStartDate': start_str,
            'pubEndDate': end_str,
            'resultsPerPage': RESULTS_PER_PAGE,
            'startIndex': start_index
        }

        for attempt in range(3):
            try:
                r = requests.get(API_URL, params=params, timeout=60)
                r.raise_for_status()
                data = r.json()
                break
            except (requests.RequestException, ValueError) as e:
                print(f'\n[!] Tentativo {attempt + 1} fallito: {e}')
                if attempt < 2:
                    time.sleep(10)
                else:
                    return False

        total = data.get('totalResults', 0)
        vulnerabilities = data.get('vulnerabilities', [])

        if not vulnerabilities:
            break

        for item in vulnerabilities:
            cve = item.get('cve', {})
            cve_id = cve.get('id', '')
            published = cve.get('published', '')[:10]  # YYYY-MM-DD

            if cve_id and published:
                rows.append((cve_id, published))

        start_index += RESULTS_PER_PAGE

        if start_index >= total:
            break

        # NVD rate limit: 5 req/30s senza API key
        time.sleep(6)

    return True


def fetch_cves():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    rows = []

    start = datetime(YEAR_START, 1, 1)
    end = datetime(YEAR_END, 12, 31)

    print(f'[*] Fetch CVE da NVD API 2.0')
    print(f'[*] Range: {start.date()} -> {end.date()}')
    print(f'[*] Chunk: {CHUNK_DAYS} giorni per query')

    chunk_start = start
    chunk_num = 0
    total_days = (end - start).days

    while chunk_start <= end:
        chunk_end = min(chunk_start + timedelta(days=CHUNK_DAYS - 1), end)
        chunk_num += 1
        progress = min(100, ((chunk_start - start).days / total_days) * 100)

        print(f'    [{progress:5.1f}%] Chunk {chunk_num}: {chunk_start.date()} -> {chunk_end.date()} | {len(rows):,} CVE totali...', end='\r')

        ok = fetch_chunk(chunk_start, chunk_end, rows)
        if not ok:
            print(f'\n[!] Errore nel chunk {chunk_start.date()} -> {chunk_end.date()}. Salvo quello che ho.')
            break

        chunk_start = chunk_end + timedelta(days=1)

        # Pausa tra chunk
        time.sleep(6)

    save_csv(rows)


def save_csv(rows):
    with open(OUTPUT_FILE, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['cve_id', 'published_date'])
        w.writerows(rows)

    print(f'\n[+] Salvate {len(rows):,} CVE in {OUTPUT_FILE}')


if __name__ == '__main__':
    fetch_cves()
