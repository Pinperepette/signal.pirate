#!/usr/bin/env python3
"""
Scansione HTTP security headers per domini PA italiani.
Salvataggio incrementale — se si blocca, riparte da dove era rimasto.
"""

import csv
import os
import ssl
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# --- Configurazione ---
METADATI = os.path.join(os.path.dirname(__file__), 'output', 'pa_metadati.csv')
OUTPUT   = os.path.join(os.path.dirname(__file__), 'output', 'headers_results.csv')
BATCH    = 50        # domini per batch
SLEEP    = 0.5       # secondi tra batch
TIMEOUT  = 6         # secondi per richiesta
WORKERS  = 10        # thread paralleli per batch
# ----------------------

FIELDNAMES = [
    'domain', 'https_ok', 'http_redirects_to_https', 'status_code',
    'has_hsts', 'hsts_max_age', 'has_csp', 'has_xframe', 'has_xcto',
    'has_referrer_policy', 'has_permissions_policy', 'server', 'powered_by', 'error'
]

write_lock = threading.Lock()
counter = {'done': 0}


def load_domains():
    """Carica domini unici dal CSV metadati, esclude quelli invalidi."""
    domains = []
    with open(METADATI, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        seen = set()
        for row in reader:
            d = row.get('domain', '').strip()
            if d and '.' in d and not d.startswith('.') and d not in seen:
                seen.add(d)
                domains.append(d)
    return sorted(domains)


def load_done():
    """Carica i domini gia' scansionati dal file output."""
    done = set()
    if os.path.exists(OUTPUT):
        with open(OUTPUT, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                done.add(row['domain'])
    return done


def scan_domain(domain):
    """Scansiona un singolo dominio per security headers."""
    result = {f: '' for f in FIELDNAMES}
    result['domain'] = domain

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    # 1. Prova HTTPS
    https_url = f'https://{domain}'
    try:
        req = urllib.request.Request(https_url, method='HEAD')
        req.add_header('User-Agent', 'Mozilla/5.0 (security-research)')
        resp = urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx)
        headers = resp.headers
        result['https_ok'] = True
        result['status_code'] = resp.status

        # Security headers
        hsts = headers.get('Strict-Transport-Security', '')
        result['has_hsts'] = bool(hsts)
        if 'max-age=' in hsts:
            try:
                result['hsts_max_age'] = hsts.split('max-age=')[1].split(';')[0].strip()
            except Exception:
                pass

        result['has_csp'] = bool(headers.get('Content-Security-Policy', ''))
        result['has_xframe'] = bool(headers.get('X-Frame-Options', ''))
        result['has_xcto'] = bool(headers.get('X-Content-Type-Options', ''))
        result['has_referrer_policy'] = bool(headers.get('Referrer-Policy', ''))
        result['has_permissions_policy'] = bool(headers.get('Permissions-Policy', ''))
        result['server'] = headers.get('Server', '')
        result['powered_by'] = headers.get('X-Powered-By', '')

    except Exception as e:
        result['https_ok'] = False
        result['error'] = str(e)[:200]

    # 2. Prova HTTP -> redirect a HTTPS?
    http_url = f'http://{domain}'
    try:
        req = urllib.request.Request(http_url, method='HEAD')
        req.add_header('User-Agent', 'Mozilla/5.0 (security-research)')
        resp = urllib.request.urlopen(req, timeout=TIMEOUT)
        final_url = resp.url
        result['http_redirects_to_https'] = final_url.startswith('https://')
        if not result['status_code']:
            result['status_code'] = resp.status
    except Exception:
        result['http_redirects_to_https'] = False

    return result


def main():
    domains = load_domains()
    done = load_done()
    todo = [d for d in domains if d not in done]

    total = len(todo)
    print(f'Totale domini: {len(domains)}')
    print(f'Gia\' scansionati: {len(done)}')
    print(f'Da fare: {total}')
    print(f'Batch: {BATCH} | Workers: {WORKERS} | Sleep: {SLEEP}s | Timeout: {TIMEOUT}s')
    print()

    # Crea file con header se non esiste
    if not os.path.exists(OUTPUT) or os.path.getsize(OUTPUT) == 0:
        with open(OUTPUT, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()

    scanned = 0

    for i in range(0, total, BATCH):
        batch = todo[i:i + BATCH]
        results = []

        with ThreadPoolExecutor(max_workers=WORKERS) as executor:
            futures = {executor.submit(scan_domain, d): d for d in batch}
            for future in as_completed(futures):
                domain = futures[future]
                try:
                    r = future.result()
                    results.append(r)
                except Exception as e:
                    r = {f: '' for f in FIELDNAMES}
                    r['domain'] = domain
                    r['error'] = str(e)[:200]
                    results.append(r)
                scanned += 1

        # Salvataggio incrementale dopo ogni batch
        with open(OUTPUT, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            for r in results:
                writer.writerow(r)

        ok = sum(1 for r in results if r.get('https_ok') == True)
        fail = len(results) - ok
        print(f'  [{scanned}/{total}] batch {i // BATCH + 1} salvato | OK: {ok} FAIL: {fail}')

        if i + BATCH < total:
            time.sleep(SLEEP)

    print(f'\nCompleto. {scanned} domini scansionati -> {OUTPUT}')


if __name__ == '__main__':
    main()
