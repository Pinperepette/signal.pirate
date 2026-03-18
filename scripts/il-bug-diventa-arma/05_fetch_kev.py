#!/usr/bin/env python3
"""
05_fetch_kev.py — Scarica il catalogo CISA KEV (Known Exploited Vulnerabilities)
Queste sono le CVE attivamente sfruttate in attacchi reali.
Output: data/kev.csv
"""

import requests
import csv
import os

KEV_URL = 'https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json'
OUTPUT_DIR = 'data'
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'kev.csv')


def fetch_kev():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print('[*] Download catalogo CISA KEV...')
    r = requests.get(KEV_URL, timeout=30)
    r.raise_for_status()
    data = r.json()

    catalog = data.get('vulnerabilities', [])
    rows = []

    for entry in catalog:
        cve_id = entry.get('cveID', '')
        date_added = entry.get('dateAdded', '')
        vendor = entry.get('vendorProject', '')
        product = entry.get('product', '')
        name = entry.get('vulnerabilityName', '')
        due_date = entry.get('dueDate', '')

        if cve_id and date_added:
            rows.append((cve_id, date_added, vendor, product, name, due_date))

    with open(OUTPUT_FILE, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['cve_id', 'kev_date_added', 'vendor', 'product', 'name', 'due_date'])
        w.writerows(rows)

    print(f'[+] {len(rows):,} CVE nel catalogo KEV')
    print(f'[+] Salvato in {OUTPUT_FILE}')


if __name__ == '__main__':
    fetch_kev()
