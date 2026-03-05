#!/usr/bin/env python3
"""
Scansione email authentication (SPF, DMARC, DKIM) per domini PA italiani.
Salvataggio incrementale — se si blocca, riparte da dove era rimasto.
"""

import csv
import dns.resolver
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Configurazione ---
METADATI = os.path.join(os.path.dirname(__file__), 'output', 'pa_metadati.csv')
OUTPUT   = os.path.join(os.path.dirname(__file__), 'output', 'email_auth_results.csv')
BATCH    = 50        # domini per batch
SLEEP    = 0.5       # secondi tra batch
TIMEOUT  = 5         # secondi per query DNS
WORKERS  = 15        # thread paralleli (DNS e' leggero)
# ----------------------

FIELDNAMES = [
    'domain', 'has_mx', 'mx_records', 'spf_record', 'spf_class',
    'dmarc_record', 'dmarc_class', 'dkim_found', 'dkim_selector', 'spoofable'
]

DKIM_SELECTORS = ['default', 'selector1', 'selector2', 'google', 'k1', 'mail', 'dkim', 's1', 's2']


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


def dns_query(qname, rdtype):
    """Query DNS con timeout, ritorna lista stringhe o lista vuota."""
    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = TIMEOUT
        resolver.lifetime = TIMEOUT
        answers = resolver.resolve(qname, rdtype)
        return [str(r) for r in answers]
    except Exception:
        return []


def classify_spf(spf):
    """Classifica la policy SPF."""
    if not spf:
        return 'assente'
    if '-all' in spf:
        return '-all (hardfail)'
    if '~all' in spf:
        return '~all (softfail)'
    if '?all' in spf:
        return '?all (neutral)'
    if '+all' in spf:
        return '+all (pass-all)'
    return 'altro'


def classify_dmarc(dmarc):
    """Classifica la policy DMARC."""
    if not dmarc:
        return 'assente'
    lower = dmarc.lower()
    if 'p=reject' in lower:
        return 'p=reject'
    if 'p=quarantine' in lower:
        return 'p=quarantine'
    if 'p=none' in lower:
        return 'p=none'
    return 'altro'


def assess_spoofability(spf_class, dmarc_class, dkim_found):
    """Valuta il rischio di spoofabilita'."""
    score = 0

    # SPF
    if spf_class == 'assente' or spf_class == '+all (pass-all)':
        score += 3
    elif spf_class == '?all (neutral)':
        score += 2
    elif spf_class == '~all (softfail)':
        score += 1

    # DMARC
    if dmarc_class == 'assente':
        score += 3
    elif dmarc_class == 'p=none':
        score += 2
    elif dmarc_class == 'p=quarantine':
        score += 1

    # DKIM
    if not dkim_found:
        score += 1

    if score >= 5:
        return 'critico'
    elif score >= 3:
        return 'alto'
    elif score >= 2:
        return 'medio'
    return 'basso'


def scan_domain(domain):
    """Scansiona email auth per un singolo dominio."""
    result = {f: '' for f in FIELDNAMES}
    result['domain'] = domain

    # MX
    mx = dns_query(domain, 'MX')
    result['has_mx'] = bool(mx)
    result['mx_records'] = ' | '.join(mx) if mx else ''

    # SPF
    txts = dns_query(domain, 'TXT')
    spf = ''
    for t in txts:
        t_clean = t.strip('"')
        if t_clean.startswith('v=spf1'):
            spf = t_clean
            break
    result['spf_record'] = spf
    result['spf_class'] = classify_spf(spf)

    # DMARC
    dmarc_txts = dns_query(f'_dmarc.{domain}', 'TXT')
    dmarc = ''
    for t in dmarc_txts:
        t_clean = t.strip('"')
        if 'DMARC' in t_clean.upper():
            dmarc = t_clean
            break
    result['dmarc_record'] = dmarc
    result['dmarc_class'] = classify_dmarc(dmarc)

    # DKIM (prova selettori comuni)
    dkim_found = False
    dkim_selector = ''
    for sel in DKIM_SELECTORS:
        dkim_qname = f'{sel}._domainkey.{domain}'
        answers = dns_query(dkim_qname, 'TXT')
        if answers:
            dkim_found = True
            dkim_selector = sel
            break
        # Prova anche CNAME (Office 365 usa CNAME per DKIM)
        cnames = dns_query(dkim_qname, 'CNAME')
        if cnames:
            dkim_found = True
            dkim_selector = sel
            break

    result['dkim_found'] = dkim_found
    result['dkim_selector'] = dkim_selector

    # Spoofabilita'
    result['spoofable'] = assess_spoofability(
        result['spf_class'], result['dmarc_class'], dkim_found
    )

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
                    results.append(r)
                scanned += 1

        # Salvataggio incrementale dopo ogni batch
        with open(OUTPUT, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            for r in results:
                writer.writerow(r)

        spoofable_count = sum(1 for r in results if r.get('spoofable') in ('critico', 'alto'))
        print(f'  [{scanned}/{total}] batch {i // BATCH + 1} salvato | spoofable: {spoofable_count}/{len(results)}')

        if i + BATCH < total:
            time.sleep(SLEEP)

    print(f'\nCompleto. {scanned} domini scansionati -> {OUTPUT}')


if __name__ == '__main__':
    main()
