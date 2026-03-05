#!/usr/bin/env python3
"""
Verifica DNSSEC per domini PA italiani.
Salvataggio incrementale.
"""

import csv
import dns.resolver
import dns.rdatatype
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Configurazione ---
METADATI = os.path.join(os.path.dirname(__file__), 'output', 'pa_metadati.csv')
OUTPUT   = os.path.join(os.path.dirname(__file__), 'output', 'dnssec_results.csv')
BATCH    = 50
SLEEP    = 0.5
TIMEOUT  = 5
WORKERS  = 15
# ----------------------

FIELDNAMES = ['domain', 'has_dnssec', 'has_dnskey', 'has_ds', 'ns_records', 'error']


def load_domains():
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
    done = set()
    if os.path.exists(OUTPUT):
        with open(OUTPUT, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                done.add(row['domain'])
    return done


def dns_query(qname, rdtype):
    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = TIMEOUT
        resolver.lifetime = TIMEOUT
        answers = resolver.resolve(qname, rdtype)
        return [str(r) for r in answers]
    except Exception:
        return []


def scan_domain(domain):
    result = {f: '' for f in FIELDNAMES}
    result['domain'] = domain

    try:
        # DNSKEY
        dnskey = dns_query(domain, 'DNSKEY')
        result['has_dnskey'] = bool(dnskey)

        # DS (delegation signer) — va cercato nel parent
        ds = dns_query(domain, 'DS')
        result['has_ds'] = bool(ds)

        # DNSSEC = ha almeno DNSKEY o DS
        result['has_dnssec'] = bool(dnskey or ds)

        # NS
        ns = dns_query(domain, 'NS')
        result['ns_records'] = ' | '.join(sorted(ns)[:5]) if ns else ''

    except Exception as e:
        result['error'] = str(e)[:200]

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

        with open(OUTPUT, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            for r in results:
                writer.writerow(r)

        dnssec_count = sum(1 for r in results if r.get('has_dnssec') == True)
        print(f'  [{scanned}/{total}] batch {i // BATCH + 1} | DNSSEC: {dnssec_count}/{len(results)}')

        if i + BATCH < total:
            time.sleep(SLEEP)

    print(f'\nCompleto. {scanned} domini -> {OUTPUT}')


if __name__ == '__main__':
    main()
