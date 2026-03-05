#!/usr/bin/env python3
"""
Verifica TLS e certificati per domini PA italiani.
- Versione TLS negoziata (1.2 vs 1.3)
- Info certificato: issuer, scadenza, giorni rimasti
- Salvataggio incrementale
"""

import csv
import os
import socket
import ssl
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# --- Configurazione ---
METADATI = os.path.join(os.path.dirname(__file__), 'output', 'pa_metadati.csv')
OUTPUT   = os.path.join(os.path.dirname(__file__), 'output', 'tls_results.csv')
BATCH    = 50
SLEEP    = 0.3
TIMEOUT  = 5
WORKERS  = 25
# ----------------------

FIELDNAMES = [
    'domain', 'tls_version', 'supports_tls13',
    'cert_issuer_org', 'cert_issuer_cn', 'cert_subject_cn',
    'cert_not_after', 'cert_days_left', 'cert_san_count',
    'error'
]


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


def scan_domain(domain):
    result = {f: '' for f in FIELDNAMES}
    result['domain'] = domain

    # 1. Connessione con verifica (per leggere il cert)
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=TIMEOUT) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                result['tls_version'] = ssock.version()
                result['supports_tls13'] = ssock.version() == 'TLSv1.3'

                cert = ssock.getpeercert()
                if cert:
                    issuer = dict(x[0] for x in cert.get('issuer', []))
                    result['cert_issuer_org'] = issuer.get('organizationName', '')[:80]
                    result['cert_issuer_cn'] = issuer.get('commonName', '')[:80]

                    subject = dict(x[0] for x in cert.get('subject', []))
                    result['cert_subject_cn'] = subject.get('commonName', '')[:80]

                    not_after = cert.get('notAfter', '')
                    result['cert_not_after'] = not_after
                    if not_after:
                        try:
                            expiry = datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z')
                            result['cert_days_left'] = (expiry - datetime.utcnow()).days
                        except Exception:
                            pass

                    # SAN count
                    sans = cert.get('subjectAltName', [])
                    result['cert_san_count'] = len(sans)

        return result
    except ssl.SSLCertVerificationError:
        # Cert non valido — riprova senza verifica per avere almeno la versione TLS
        pass
    except Exception as e:
        result['error'] = str(e)[:200]
        return result

    # 2. Fallback senza verifica (cert scaduto/self-signed/mismatch)
    try:
        ctx2 = ssl.create_default_context()
        ctx2.check_hostname = False
        ctx2.verify_mode = ssl.CERT_NONE
        with socket.create_connection((domain, 443), timeout=TIMEOUT) as sock:
            with ctx2.wrap_socket(sock, server_hostname=domain) as ssock:
                result['tls_version'] = ssock.version()
                result['supports_tls13'] = ssock.version() == 'TLSv1.3'
                result['error'] = 'cert_invalid'
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

        tls13 = sum(1 for r in results if r.get('supports_tls13') == True)
        invalid = sum(1 for r in results if r.get('error') == 'cert_invalid')
        print(f'  [{scanned}/{total}] batch {i // BATCH + 1} | TLS1.3: {tls13} | cert_invalid: {invalid}')

        if i + BATCH < total:
            time.sleep(SLEEP)

    print(f'\nCompleto. {scanned} domini -> {OUTPUT}')


if __name__ == '__main__':
    main()
