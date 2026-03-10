#!/usr/bin/env python3
"""
01_header_parser.py — Parser di header email con ricostruzione percorso

Legge un file .eml (o stdin) e ricostruisce la catena Received:
- Estrae ogni hop: server mittente, server ricevente, IP, protocollo, timestamp
- Inverte l'ordine (dal basso verso l'alto = ordine cronologico)
- Calcola il delta temporale tra ogni hop
- Segnala anomalie (delta > 60s, connessioni non cifrate)

Usa solo la stdlib Python (email, re, datetime). Zero dipendenze.

Uso:
    python3 01_header_parser.py mail.eml
    cat mail.eml | python3 01_header_parser.py
"""

import sys
import re
import email
from email import policy
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


# Colori terminale
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
BOLD = '\033[1m'
DIM = '\033[2m'
RESET = '\033[0m'


def parse_received(header_value):
    """Parsa un singolo header Received e ne estrae i campi."""
    result = {}

    # from ... (hostname [IP])
    from_match = re.search(
        r'from\s+([\w.\-]+)\s*\(([^)]*?\[?([\d.]+)\]?)\)',
        header_value, re.IGNORECASE
    )
    if from_match:
        result['from_helo'] = from_match.group(1)
        result['from_rdns'] = from_match.group(2).strip()
        result['from_ip'] = from_match.group(3)
    else:
        from_simple = re.search(r'from\s+([\w.\-]+)', header_value, re.IGNORECASE)
        if from_simple:
            result['from_helo'] = from_simple.group(1)

    # by ...
    by_match = re.search(r'by\s+([\w.\-]+)', header_value, re.IGNORECASE)
    if by_match:
        result['by'] = by_match.group(1)

    # with ESMTPS / ESMTP / SMTP / LMTP
    with_match = re.search(r'with\s+(E?SMTP\w*)', header_value, re.IGNORECASE)
    if with_match:
        result['protocol'] = with_match.group(1).upper()

    # TLS info
    tls_match = re.search(r'version=(TLS[\d._]+)\s+cipher=(\S+)', header_value)
    if tls_match:
        result['tls_version'] = tls_match.group(1)
        result['tls_cipher'] = tls_match.group(2)

    # id
    id_match = re.search(r'\bid\s+(\S+)', header_value, re.IGNORECASE)
    if id_match:
        result['id'] = id_match.group(1).rstrip(';')

    # for <address>
    for_match = re.search(r'for\s+<?([^>;\s]+)>?', header_value, re.IGNORECASE)
    if for_match:
        result['for'] = for_match.group(1)

    # timestamp (alla fine, dopo il ;)
    ts_match = re.search(r';\s*(.+)$', header_value, re.DOTALL)
    if ts_match:
        ts_str = ts_match.group(1).strip()
        try:
            result['timestamp'] = parsedate_to_datetime(ts_str)
        except (ValueError, TypeError):
            result['timestamp_raw'] = ts_str

    return result


def format_delta(td):
    """Formatta un timedelta in modo leggibile."""
    total_seconds = int(td.total_seconds())
    if total_seconds < 0:
        return f'{RED}{total_seconds}s (NEGATIVO!){RESET}'
    if total_seconds == 0:
        return f'{GREEN}0s{RESET}'
    if total_seconds < 5:
        return f'{GREEN}{total_seconds}s{RESET}'
    if total_seconds < 60:
        return f'{YELLOW}{total_seconds}s{RESET}'
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f'{RED}{minutes}m {seconds}s{RESET}'


def analyze_email(msg):
    """Analizza gli header di un messaggio email."""

    # Header principali
    print(f'\n{BOLD}{"=" * 70}{RESET}')
    print(f'{BOLD}  EMAIL HEADER FORENSICS{RESET}')
    print(f'{BOLD}{"=" * 70}{RESET}\n')

    headers_of_interest = [
        ('From', CYAN),
        ('To', CYAN),
        ('Subject', CYAN),
        ('Date', DIM),
        ('Return-Path', YELLOW),
        ('Message-ID', DIM),
    ]

    for name, color in headers_of_interest:
        val = msg.get(name, '')
        if val:
            print(f'  {DIM}{name}:{RESET} {color}{val}{RESET}')

    # Authentication-Results
    auth_results = msg.get('Authentication-Results', '')
    if auth_results:
        print(f'\n{BOLD}  AUTHENTICATION RESULTS{RESET}')
        print(f'  {DIM}{"─" * 50}{RESET}')

        for check in ['spf', 'dkim', 'dmarc']:
            match = re.search(rf'{check}=(\w+)', auth_results, re.IGNORECASE)
            if match:
                result = match.group(1).lower()
                if result == 'pass':
                    color = GREEN
                    symbol = 'PASS'
                elif result in ('fail', 'hardfail'):
                    color = RED
                    symbol = 'FAIL'
                elif result == 'softfail':
                    color = YELLOW
                    symbol = 'SOFTFAIL'
                else:
                    color = DIM
                    symbol = result.upper()
                print(f'  {check.upper():>8}: {color}{BOLD}{symbol}{RESET}')

        # DMARC policy
        dmarc_policy = re.search(r'dmarc=\w+\s*\(p=(\w+)', auth_results, re.IGNORECASE)
        if dmarc_policy:
            print(f'  {"Policy":>8}: {YELLOW}{dmarc_policy.group(1)}{RESET}')

    # DKIM signatures
    dkim_sigs = msg.get_all('DKIM-Signature', [])
    if dkim_sigs:
        print(f'\n{BOLD}  DKIM SIGNATURES ({len(dkim_sigs)}){RESET}')
        print(f'  {DIM}{"─" * 50}{RESET}')
        for i, sig in enumerate(dkim_sigs, 1):
            d_match = re.search(r'd=([\w.\-]+)', sig)
            s_match = re.search(r's=([\w.\-]+)', sig)
            a_match = re.search(r'a=([\w.\-]+)', sig)
            domain = d_match.group(1) if d_match else '?'
            selector = s_match.group(1) if s_match else '?'
            algo = a_match.group(1) if a_match else '?'
            print(f'  #{i}: {GREEN}{domain}{RESET} (selector: {CYAN}{selector}{RESET}, algo: {algo})')
            print(f'      DNS: dig TXT {selector}._domainkey.{domain} +short')

    # X- headers interessanti
    x_headers = [
        'X-SES-Outgoing', 'X-Mailer', 'User-Agent', 'X-Originating-IP',
        'X-Google-DKIM-Signature', 'X-Microsoft-Antispam',
        'X-SourceAppName', 'X-LocaleCountry', 'X-TrackingGuid',
        'X-MessageGuid', 'Feedback-ID', 'X-Mailgun-Sid',
    ]
    found_x = []
    for xh in x_headers:
        val = msg.get(xh, '')
        if val:
            found_x.append((xh, val.strip()))

    if found_x:
        print(f'\n{BOLD}  HEADER NON STANDARD{RESET}')
        print(f'  {DIM}{"─" * 50}{RESET}')
        for name, val in found_x:
            print(f'  {YELLOW}{name}:{RESET} {val[:80]}{"..." if len(val) > 80 else ""}')

    # Catena Received (ordine cronologico = invertito)
    received_headers = msg.get_all('Received', [])
    if not received_headers:
        print(f'\n{RED}  Nessun header Received trovato.{RESET}')
        return

    hops = []
    for raw in received_headers:
        # Normalizza multiline
        clean = re.sub(r'\s+', ' ', raw).strip()
        parsed = parse_received(clean)
        parsed['raw'] = clean
        hops.append(parsed)

    # Inverti: il primo Received e' l'ultimo hop
    hops.reverse()

    print(f'\n{BOLD}  CATENA RECEIVED ({len(hops)} hop){RESET}')
    print(f'  {DIM}{"─" * 50}{RESET}')

    prev_ts = None
    for i, hop in enumerate(hops, 1):
        from_server = hop.get('from_helo', '?')
        from_ip = hop.get('from_ip', '')
        by_server = hop.get('by', '?')
        proto = hop.get('protocol', '?')
        ts = hop.get('timestamp')
        tls = hop.get('tls_version', '')

        # Delta
        delta_str = ''
        if ts and prev_ts:
            delta = ts - prev_ts
            delta_str = f' ({format_delta(delta)})'

        # Protocollo: colorato
        if 'S' in proto:
            proto_colored = f'{GREEN}{proto}{RESET}'
            if tls:
                proto_colored += f' {DIM}({tls}){RESET}'
        elif proto == 'SMTP':
            proto_colored = f'{RED}{proto} (NO TLS!){RESET}'
        else:
            proto_colored = proto

        print(f'\n  {BOLD}Hop {i}{RESET}{delta_str}')
        if from_ip:
            print(f'    from: {CYAN}{from_server}{RESET} [{from_ip}]')
        else:
            print(f'    from: {CYAN}{from_server}{RESET}')
        print(f'    by:   {CYAN}{by_server}{RESET}')
        print(f'    with: {proto_colored}')
        if ts:
            print(f'    time: {DIM}{ts.strftime("%Y-%m-%d %H:%M:%S %Z")}{RESET}')

        # Warnings
        if proto == 'SMTP':
            print(f'    {RED}[!] Connessione in chiaro. Il messaggio era leggibile in transito.{RESET}')
        if from_ip and hop.get('from_helo', '') != '':
            rdns = hop.get('from_rdns', '')
            if rdns and hop['from_helo'].lower() not in rdns.lower():
                print(f'    {YELLOW}[?] HELO ({from_server}) non corrisponde a reverse DNS ({rdns}){RESET}')

        if ts:
            prev_ts = ts

    # Tempo totale
    first_ts = None
    last_ts = None
    for hop in hops:
        ts = hop.get('timestamp')
        if ts:
            if first_ts is None:
                first_ts = ts
            last_ts = ts

    if first_ts and last_ts:
        total = last_ts - first_ts
        print(f'\n  {BOLD}Tempo totale:{RESET} {format_delta(total)} (dal primo all\'ultimo hop)')

    print(f'\n{BOLD}{"=" * 70}{RESET}\n')


def main():
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        with open(filename, 'rb') as f:
            msg = email.message_from_bytes(f.read(), policy=policy.default)
    else:
        msg = email.message_from_bytes(sys.stdin.buffer.read(), policy=policy.default)

    analyze_email(msg)


if __name__ == '__main__':
    main()
