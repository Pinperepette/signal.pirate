#!/usr/bin/env python3
"""
03_match_and_delta.py — Incrocia NVD + ExploitDB, calcola Dt (giorni)
Input:  data/nvd_cves.csv, data/exploitdb_cves.csv
Output: data/matched_delta.csv
"""

import csv
import os
from datetime import datetime

NVD_FILE = os.path.join('data', 'nvd_cves.csv')
EXPLOITDB_FILE = os.path.join('data', 'exploitdb_cves.csv')
OUTPUT_FILE = os.path.join('data', 'matched_delta.csv')

# Soglia per separare backfill NVD da pre-disclosure reale.
# Delta < -365 e' quasi certamente NVD che ha pubblicato la CVE
# anni dopo che il bug era noto. Delta tra -365 e 0 e' plausibile
# come exploit pubblicato prima della formalizzazione CVE.
BACKFILL_THRESHOLD = -365


def parse_date(s):
    """Parsa date in formato YYYY-MM-DD."""
    for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y'):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    return None


def match():
    # Carica NVD: CVE -> published_date
    nvd = {}
    with open(NVD_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cve_id = row['cve_id'].strip()
            d = parse_date(row['published_date'])
            if d:
                nvd[cve_id] = d

    print(f'[*] NVD: {len(nvd):,} CVE con data')

    # Carica ExploitDB: CVE -> exploit_date (primo exploit)
    exploits = {}
    with open(EXPLOITDB_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cve_id = row['cve_id'].strip()
            d = parse_date(row['exploit_date'])
            if d:
                # Tieni la data piu' vecchia (primo exploit)
                if cve_id not in exploits or d < exploits[cve_id]:
                    exploits[cve_id] = d

    print(f'[*] ExploitDB: {len(exploits):,} CVE con exploit')

    # Match
    matched = []
    for cve_id, pub_date in nvd.items():
        if cve_id in exploits:
            exp_date = exploits[cve_id]
            delta_days = (exp_date - pub_date).days
            matched.append((
                cve_id,
                pub_date.strftime('%Y-%m-%d'),
                exp_date.strftime('%Y-%m-%d'),
                delta_days
            ))

    # Ordina per delta
    matched.sort(key=lambda x: x[3])

    with open(OUTPUT_FILE, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['cve_id', 'published_date', 'exploit_date', 'delta_days'])
        w.writerows(matched)

    print(f'[+] Match: {len(matched):,} CVE con exploit pubblico')

    # Statistiche: dataset completo
    deltas = [m[3] for m in matched]
    total = len(deltas)

    backfill = sum(1 for d in deltas if d < BACKFILL_THRESHOLD)
    pre_real = sum(1 for d in deltas if BACKFILL_THRESHOLD <= d < 0)
    zero = sum(1 for d in deltas if d == 0)
    week = sum(1 for d in deltas if 0 < d <= 7)
    month = sum(1 for d in deltas if 7 < d <= 30)
    rest = sum(1 for d in deltas if d > 30)

    print(f'\n--- Dataset completo ({total:,} CVE) ---')
    print(f'  Backfill NVD (delta < {BACKFILL_THRESHOLD}d): {backfill:,} ({backfill/total*100:.1f}%)')
    print(f'  Pre-disclosure ({BACKFILL_THRESHOLD}d..0):     {pre_real:,} ({pre_real/total*100:.1f}%)')
    print(f'  Same-day (delta = 0):             {zero:,} ({zero/total*100:.1f}%)')
    print(f'  1-7 giorni:                       {week:,} ({week/total*100:.1f}%)')
    print(f'  8-30 giorni:                      {month:,} ({month/total*100:.1f}%)')
    print(f'  > 30 giorni:                      {rest:,} ({rest/total*100:.1f}%)')

    # Statistiche: vista pulita (esclude backfill NVD)
    clean = [d for d in deltas if d >= BACKFILL_THRESHOLD]
    clean_total = len(clean)
    clean_pre = sum(1 for d in clean if d < 0)
    clean_zero = sum(1 for d in clean if d == 0)
    clean_week = sum(1 for d in clean if 0 <= d <= 7)
    clean_month = sum(1 for d in clean if 0 <= d <= 30)
    clean_sorted = sorted(clean)

    print(f'\n--- Vista pulita (escluso backfill, {clean_total:,} CVE) ---')
    print(f'  Pre-disclosure (-365d..0):  {clean_pre:,} ({clean_pre/clean_total*100:.1f}%)')
    print(f'  Same-day (delta = 0):       {clean_zero:,} ({clean_zero/clean_total*100:.1f}%)')
    print(f'  Entro 7 giorni:             {clean_week:,} ({clean_week/clean_total*100:.1f}%)')
    print(f'  Entro 30 giorni:            {clean_month:,} ({clean_month/clean_total*100:.1f}%)')
    print(f'  Mediana:                    {clean_sorted[clean_total//2]} giorni')
    print(f'  Media:                      {sum(clean)/clean_total:.0f} giorni')

    print(f'\n[+] Salvato in {OUTPUT_FILE}')


if __name__ == '__main__':
    match()
