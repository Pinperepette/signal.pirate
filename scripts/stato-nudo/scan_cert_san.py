#!/usr/bin/env python3
"""
Estrae i Subject Alternative Names (SAN) dai certificati TLS live.
I SAN rivelano sottodomini, servizi interni e infrastruttura nascosta
direttamente dal certificato presentato dal server.
Salvataggio incrementale.
"""

import csv
import os
import socket
import ssl
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Configurazione ---
METADATI = os.path.join(os.path.dirname(__file__), 'output', 'pa_metadati.csv')
OUTPUT   = os.path.join(os.path.dirname(__file__), 'output', 'cert_san_results.csv')
BATCH    = 50
SLEEP    = 0.2
TIMEOUT  = 5
WORKERS  = 30
# ----------------------

FIELDNAMES = [
    'domain', 'san_count', 'san_names',
    'has_wildcard', 'wildcard_names',
    'has_internal', 'internal_names',
    'has_test_dev', 'test_dev_names',
    'has_mail', 'has_vpn', 'has_admin',
    'other_domains', 'other_domain_count',
    'error'
]

# Pattern interessanti nei SAN
INTERNAL_PATTERNS = ['intranet', 'internal', 'private', 'local', 'lan', 'interno']
TEST_DEV_PATTERNS = ['test', 'dev', 'staging', 'stage', 'stg', 'preprod', 'uat', 'demo', 'sandbox']
MAIL_PATTERNS = ['mail', 'webmail', 'smtp', 'imap', 'pop', 'posta', 'mx', 'exchange']
VPN_PATTERNS = ['vpn', 'remote', 'access', 'gateway', 'gw', 'tunnel']
ADMIN_PATTERNS = ['admin', 'panel', 'cpanel', 'gestione', 'backoffice', 'cms', 'console']


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


def matches_any(name, patterns):
    """Controlla se un hostname contiene uno dei pattern."""
    parts = name.lower().split('.')
    prefix = parts[0] if parts else ''
    return any(p in prefix for p in patterns)


def scan_domain(domain):
    result = {f: '' for f in FIELDNAMES}
    result['domain'] = domain

    san_names = set()

    # Prova con verifica
    for verify in [True, False]:
        try:
            ctx = ssl.create_default_context()
            if not verify:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

            with socket.create_connection((domain, 443), timeout=TIMEOUT) as sock:
                with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()
                    if cert:
                        for typ, val in cert.get('subjectAltName', []):
                            if typ == 'DNS':
                                san_names.add(val.lower())
                        break  # successo, non serve fallback
                    elif verify:
                        continue  # prova senza verifica
                    else:
                        # senza verifica getpeercert() e' vuoto
                        # prendiamo almeno il cert binario per il CN
                        der = ssock.getpeercert(binary_form=True)
                        if der:
                            result['error'] = 'cert_invalid_no_san_detail'
                        return result
        except ssl.SSLCertVerificationError:
            if verify:
                continue  # riprova senza verifica
            result['error'] = 'cert_verify_failed'
            return result
        except Exception as e:
            result['error'] = str(e)[:200]
            return result

    if not san_names:
        result['san_count'] = 0
        return result

    # Analizza i SAN
    result['san_count'] = len(san_names)
    result['san_names'] = ' | '.join(sorted(san_names)[:50])

    # Wildcard
    wildcards = [n for n in san_names if n.startswith('*.')]
    result['has_wildcard'] = bool(wildcards)
    if wildcards:
        result['wildcard_names'] = ' | '.join(sorted(wildcards)[:10])

    # Nomi interni
    internal = [n for n in san_names if matches_any(n, INTERNAL_PATTERNS)]
    result['has_internal'] = bool(internal)
    if internal:
        result['internal_names'] = ' | '.join(sorted(internal)[:10])

    # Test/dev/staging
    test_dev = [n for n in san_names if matches_any(n, TEST_DEV_PATTERNS)]
    result['has_test_dev'] = bool(test_dev)
    if test_dev:
        result['test_dev_names'] = ' | '.join(sorted(test_dev)[:10])

    # Mail
    result['has_mail'] = any(matches_any(n, MAIL_PATTERNS) for n in san_names)

    # VPN
    result['has_vpn'] = any(matches_any(n, VPN_PATTERNS) for n in san_names)

    # Admin
    result['has_admin'] = any(matches_any(n, ADMIN_PATTERNS) for n in san_names)

    # Domini diversi dal principale (cert condiviso = info gratis)
    base_domain = domain.lower()
    other = set()
    for n in san_names:
        clean = n.lstrip('*.')
        # Estrai dominio di secondo livello
        parts = clean.split('.')
        if len(parts) >= 2:
            d2 = '.'.join(parts[-2:])
            if d2 != base_domain and not clean.endswith('.' + base_domain):
                other.add(clean)
    result['other_domains'] = ' | '.join(sorted(other)[:20])
    result['other_domain_count'] = len(other)

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

        wc = sum(1 for r in results if r.get('has_wildcard') == True)
        td = sum(1 for r in results if r.get('has_test_dev') == True)
        ot = sum(1 for r in results if int(r.get('other_domain_count') or 0) > 0)
        print(f'  [{scanned}/{total}] batch {i // BATCH + 1} | wildcard: {wc} | test/dev: {td} | altri domini: {ot}')

        if i + BATCH < total:
            time.sleep(SLEEP)

    print(f'\nCompleto. {scanned} domini -> {OUTPUT}')


if __name__ == '__main__':
    main()
