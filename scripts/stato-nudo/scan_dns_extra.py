#!/usr/bin/env python3
"""
Controlli DNS aggiuntivi per domini PA italiani:
- MX record + identificazione provider email
- CAA record (chi puo' emettere certificati)
- Wildcard DNS (*.dominio risolve?)
- SPF permissiveness (analisi profonda del record SPF)
Salvataggio incrementale.
"""

import csv
import dns.resolver
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Configurazione ---
METADATI = os.path.join(os.path.dirname(__file__), 'output', 'pa_metadati.csv')
OUTPUT   = os.path.join(os.path.dirname(__file__), 'output', 'dns_extra_results.csv')
BATCH    = 50
SLEEP    = 0.2
TIMEOUT  = 5
WORKERS  = 40
# ----------------------

FIELDNAMES = [
    'domain',
    # MX
    'mx_records', 'mx_provider', 'mx_count',
    # CAA
    'has_caa', 'caa_issuers',
    # Wildcard
    'has_wildcard_dns', 'wildcard_ip',
    # SPF deep
    'spf_record', 'spf_mechanism_count', 'spf_includes',
    'spf_has_all_pass', 'spf_has_ptr', 'spf_broad_ranges',
    'spf_permissive_score',
    'error'
]

# Provider email noti (pattern -> nome)
MX_PROVIDERS = [
    ('google.com', 'Google Workspace'),
    ('googlemail.com', 'Google Workspace'),
    ('outlook.com', 'Microsoft 365'),
    ('protection.outlook.com', 'Microsoft 365'),
    ('pphosted.com', 'Proofpoint'),
    ('aruba.it', 'Aruba'),
    ('legalmail.it', 'Aruba PEC'),
    ('registerpec.it', 'Register PEC'),
    ('postecert.it', 'Poste Italiane PEC'),
    ('infocert.it', 'InfoCert PEC'),
    ('ovh.net', 'OVH'),
    ('mimecast.com', 'Mimecast'),
    ('barracudanetworks.com', 'Barracuda'),
    ('messagelabs.com', 'Broadcom/Symantec'),
    ('forcepoint.com', 'Forcepoint'),
    ('serverplan.com', 'Serverplan'),
    ('netsons.com', 'Netsons'),
    ('tophost.it', 'Tophost'),
    ('register.it', 'Register.it'),
    ('keliweb.it', 'Keliweb'),
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


def dns_query(qname, rdtype):
    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = TIMEOUT
        resolver.lifetime = TIMEOUT
        answers = resolver.resolve(qname, rdtype)
        return [str(r) for r in answers]
    except Exception:
        return []


def identify_mx_provider(mx_records):
    """Identifica il provider email dal record MX."""
    mx_lower = ' '.join(mx_records).lower()
    for pattern, provider in MX_PROVIDERS:
        if pattern in mx_lower:
            return provider
    if mx_records:
        return 'Self-hosted / altro'
    return ''


def analyze_spf(domain):
    """Analisi profonda del record SPF."""
    result = {
        'spf_record': '',
        'spf_mechanism_count': 0,
        'spf_includes': '',
        'spf_has_all_pass': False,
        'spf_has_ptr': False,
        'spf_broad_ranges': '',
        'spf_permissive_score': 0,
    }

    txt_records = dns_query(domain, 'TXT')
    spf = ''
    for t in txt_records:
        t = t.strip('"')
        if t.startswith('v=spf1'):
            spf = t
            break

    if not spf:
        return result

    result['spf_record'] = spf[:300]

    # Conta meccanismi
    parts = spf.split()
    mechanisms = [p for p in parts if p != 'v=spf1']
    result['spf_mechanism_count'] = len(mechanisms)

    # Includes
    includes = [p.replace('include:', '') for p in parts if p.startswith('include:')]
    result['spf_includes'] = ' | '.join(includes[:10])

    # +all (chiunque puo' inviare)
    if '+all' in parts or 'all' in parts:
        result['spf_has_all_pass'] = True

    # ptr (deprecato, insicuro)
    if any(p.startswith('ptr') for p in parts):
        result['spf_has_ptr'] = True

    # Range IP troppo ampi (/16 o piu' ampi)
    broad = []
    for p in parts:
        m = re.search(r'ip[46]:(\S+)', p)
        if m:
            cidr = m.group(1)
            slash = re.search(r'/(\d+)', cidr)
            if slash:
                prefix = int(slash.group(1))
                if 'ip4' in p and prefix <= 16:
                    broad.append(cidr)
                elif 'ip6' in p and prefix <= 48:
                    broad.append(cidr)
    result['spf_broad_ranges'] = ' | '.join(broad)

    # Score permissivita' (0-5)
    score = 0
    if result['spf_has_all_pass']:
        score += 3
    if result['spf_has_ptr']:
        score += 1
    if broad:
        score += 1
    if len(includes) > 5:
        score += 1
    # ~all senza DMARC e' come non avere SPF
    if '~all' in parts:
        score += 1
    result['spf_permissive_score'] = min(score, 5)

    return result


def scan_domain(domain):
    result = {f: '' for f in FIELDNAMES}
    result['domain'] = domain

    try:
        # --- MX ---
        mx_raw = dns_query(domain, 'MX')
        mx_hosts = []
        for mx in mx_raw:
            # formato: "10 mail.example.com."
            parts = mx.split()
            if len(parts) >= 2:
                mx_hosts.append(parts[-1].rstrip('.'))
        result['mx_records'] = ' | '.join(sorted(mx_hosts)[:5])
        result['mx_count'] = len(mx_hosts)
        result['mx_provider'] = identify_mx_provider(mx_hosts)

        # --- CAA ---
        caa_raw = dns_query(domain, 'CAA')
        result['has_caa'] = bool(caa_raw)
        if caa_raw:
            issuers = []
            for c in caa_raw:
                # formato: '0 issue "letsencrypt.org"'
                m = re.search(r'issue[wild]*\s+"([^"]+)"', str(c))
                if m:
                    issuers.append(m.group(1))
            result['caa_issuers'] = ' | '.join(sorted(set(issuers)))

        # --- Wildcard DNS ---
        wildcard = dns_query(f'*.{domain}', 'A')
        result['has_wildcard_dns'] = bool(wildcard)
        if wildcard:
            result['wildcard_ip'] = ' | '.join(wildcard[:3])

        # --- SPF deep ---
        spf_result = analyze_spf(domain)
        result.update(spf_result)

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

        caa = sum(1 for r in results if r.get('has_caa') == True)
        wc = sum(1 for r in results if r.get('has_wildcard_dns') == True)
        print(f'  [{scanned}/{total}] batch {i // BATCH + 1} | CAA: {caa} | wildcard: {wc}')

        if i + BATCH < total:
            time.sleep(SLEEP)

    print(f'\nCompleto. {scanned} domini -> {OUTPUT}')


if __name__ == '__main__':
    main()
