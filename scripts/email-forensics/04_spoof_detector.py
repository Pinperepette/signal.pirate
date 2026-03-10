#!/usr/bin/env python3
"""
04_spoof_detector.py — Analizza una mail e segnala indizi di spoofing

Legge un file .eml e controlla 7 indicatori di spoofing:
1. SPF fail/softfail nell'Authentication-Results
2. DKIM fail/none nell'Authentication-Results
3. DMARC fail nell'Authentication-Results
4. Return-Path diverso dal dominio From
5. HELO mismatch nei Received (hostname dichiarato != reverse DNS)
6. From: con dominio diverso da DKIM d=
7. Header sospetti (X-Mailer PHPMailer, nessun DKIM, protocollo SMTP senza TLS)

Output: semaforo verde/giallo/rosso con spiegazione.

Uso:
    python3 04_spoof_detector.py mail.eml
    cat mail.eml | python3 04_spoof_detector.py
"""

import sys
import email
import re
from email import policy
from email.utils import parseaddr


# Colori terminale
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
BOLD = '\033[1m'
DIM = '\033[2m'
RESET = '\033[0m'


def get_domain(address):
    """Estrae il dominio da un indirizzo email."""
    _, addr = parseaddr(address)
    if '@' in addr:
        return addr.split('@')[1].lower()
    return ''


def check_spoofing(msg):
    """Esegue tutti i controlli di spoofing."""
    results = []  # (level, check_name, detail)  level: 'ok', 'warn', 'danger'

    from_header = msg.get('From', '')
    from_domain = get_domain(from_header)
    return_path = msg.get('Return-Path', '')
    rp_domain = get_domain(return_path)
    auth_results = msg.get('Authentication-Results', '')
    received_headers = msg.get_all('Received', [])
    dkim_sigs = msg.get_all('DKIM-Signature', [])

    # 1. SPF
    spf_match = re.search(r'spf=(\w+)', auth_results, re.IGNORECASE)
    if spf_match:
        spf_result = spf_match.group(1).lower()
        if spf_result == 'pass':
            results.append(('ok', 'SPF', f'pass. L\'IP del server e\' autorizzato.'))
        elif spf_result in ('fail', 'hardfail'):
            results.append(('danger', 'SPF', f'FAIL. L\'IP del server NON e\' autorizzato dal dominio.'))
        elif spf_result == 'softfail':
            results.append(('warn', 'SPF', f'softfail. L\'IP probabilmente non e\' autorizzato.'))
        else:
            results.append(('warn', 'SPF', f'{spf_result}. Risultato ambiguo.'))
    else:
        results.append(('warn', 'SPF', 'Nessun risultato SPF trovato nell\'Authentication-Results.'))

    # 2. DKIM
    dkim_match = re.search(r'dkim=(\w+)', auth_results, re.IGNORECASE)
    if dkim_match:
        dkim_result = dkim_match.group(1).lower()
        if dkim_result == 'pass':
            results.append(('ok', 'DKIM', f'pass. Il messaggio e\' firmato e integro.'))
        elif dkim_result == 'fail':
            results.append(('danger', 'DKIM', f'FAIL. La firma non corrisponde. Messaggio modificato o firma falsa.'))
        elif dkim_result == 'none':
            results.append(('warn', 'DKIM', f'none. Nessuna firma DKIM. Il mittente non firma le sue mail (o non e\' chi dice di essere).'))
        else:
            results.append(('warn', 'DKIM', f'{dkim_result}. Risultato ambiguo.'))
    else:
        if dkim_sigs:
            results.append(('warn', 'DKIM', 'Firma presente ma nessun risultato nell\'Authentication-Results.'))
        else:
            results.append(('warn', 'DKIM', 'Nessuna firma DKIM nel messaggio.'))

    # 3. DMARC
    dmarc_match = re.search(r'dmarc=(\w+)', auth_results, re.IGNORECASE)
    if dmarc_match:
        dmarc_result = dmarc_match.group(1).lower()
        if dmarc_result == 'pass':
            dmarc_policy = re.search(r'dmarc=\w+\s*\(p=(\w+)', auth_results, re.IGNORECASE)
            policy_str = dmarc_policy.group(1) if dmarc_policy else '?'
            results.append(('ok', 'DMARC', f'pass (policy={policy_str}). From: allineato con SPF/DKIM.'))
        elif dmarc_result == 'fail':
            results.append(('danger', 'DMARC', f'FAIL. Il From: NON e\' allineato con SPF ne\' DKIM. Forte indizio di spoofing.'))
        else:
            results.append(('warn', 'DMARC', f'{dmarc_result}. Risultato ambiguo.'))
    else:
        results.append(('warn', 'DMARC', 'Nessun risultato DMARC. Il dominio potrebbe non avere DMARC configurato.'))

    # 4. Return-Path vs From
    if rp_domain and from_domain:
        # Confronta i domini organizzativi (netflix.com per entrambi members.netflix.com e mailer.members.netflix.com)
        from_org = '.'.join(from_domain.split('.')[-2:])
        rp_org = '.'.join(rp_domain.split('.')[-2:])
        if from_org == rp_org:
            results.append(('ok', 'Return-Path', f'Dominio coerente ({rp_domain} ~ {from_domain}).'))
        else:
            results.append(('danger', 'Return-Path', f'MISMATCH. From: {from_domain}, Return-Path: {rp_domain}. Domini diversi.'))
    elif not rp_domain:
        results.append(('warn', 'Return-Path', 'Nessun Return-Path trovato.'))

    # 5. HELO mismatch nei Received
    helo_ok = True
    for raw in received_headers:
        clean = re.sub(r'\s+', ' ', raw).strip()
        # from HELO (RDNS [IP])
        match = re.search(r'from\s+([\w.\-]+)\s+\(([\w.\-]+)', clean)
        if match:
            helo = match.group(1).lower()
            rdns = match.group(2).lower()
            if helo != rdns and rdns not in helo and helo not in rdns:
                results.append(('danger', 'HELO Mismatch', f'Il server dichiara "{helo}" ma il reverse DNS dice "{rdns}".'))
                helo_ok = False
    if helo_ok:
        results.append(('ok', 'HELO', 'Nessun mismatch HELO/rDNS rilevato.'))

    # 6. DKIM d= vs From domain
    if dkim_sigs:
        dkim_domains = []
        for sig in dkim_sigs:
            d_match = re.search(r'd=([\w.\-]+)', sig)
            if d_match:
                dkim_domains.append(d_match.group(1).lower())

        if dkim_domains:
            from_org = '.'.join(from_domain.split('.')[-2:])
            aligned = any(from_org in d or from_org == '.'.join(d.split('.')[-2:]) for d in dkim_domains)
            if aligned:
                results.append(('ok', 'DKIM Alignment', f'DKIM d= ({", ".join(dkim_domains)}) allineato con From ({from_domain}).'))
            else:
                results.append(('warn', 'DKIM Alignment', f'DKIM d= ({", ".join(dkim_domains)}) non allineato con From ({from_domain}).'))

    # 7. Header sospetti
    x_mailer = msg.get('X-Mailer', '')
    if x_mailer:
        suspicious_mailers = ['phpmailer', 'swiftmailer', 'phpmail', 'king-mailer']
        if any(s in x_mailer.lower() for s in suspicious_mailers):
            results.append(('warn', 'X-Mailer', f'Mailer sospetto: {x_mailer}. Spesso usato in phishing.'))
        else:
            results.append(('ok', 'X-Mailer', f'{x_mailer}'))

    # Protocollo non cifrato
    for raw in received_headers:
        clean = re.sub(r'\s+', ' ', raw).strip()
        with_match = re.search(r'with\s+(SMTP)\b(?!S)', clean, re.IGNORECASE)
        if with_match:
            by_match = re.search(r'by\s+([\w.\-]+)', clean)
            server = by_match.group(1) if by_match else '?'
            results.append(('warn', 'TLS', f'Hop verso {server} in chiaro (SMTP senza TLS). Il messaggio era leggibile.'))

    return results


def print_results(results, msg):
    """Stampa i risultati con semaforo."""
    from_header = msg.get('From', '')
    subject = msg.get('Subject', '')

    print(f'\n{BOLD}{"=" * 60}{RESET}')
    print(f'{BOLD}  SPOOF DETECTOR{RESET}')
    print(f'{BOLD}{"=" * 60}{RESET}')
    print(f'  From:    {CYAN}{from_header}{RESET}')
    print(f'  Subject: {subject}')
    print(f'{BOLD}{"─" * 60}{RESET}\n')

    dangers = 0
    warnings = 0
    oks = 0

    for level, name, detail in results:
        if level == 'ok':
            symbol = f'{GREEN}[OK]{RESET}'
            oks += 1
        elif level == 'warn':
            symbol = f'{YELLOW}[!!]{RESET}'
            warnings += 1
        else:
            symbol = f'{RED}[XX]{RESET}'
            dangers += 1

        print(f'  {symbol} {BOLD}{name}{RESET}')
        print(f'       {detail}')
        print()

    # Verdetto
    print(f'{BOLD}{"─" * 60}{RESET}')
    if dangers >= 2:
        print(f'  {RED}{BOLD}VERDETTO: PROBABILE SPOOFING{RESET}')
        print(f'  {RED}{dangers} indicatori critici. Non fidarti di questa mail.{RESET}')
    elif dangers == 1:
        print(f'  {YELLOW}{BOLD}VERDETTO: SOSPETTO{RESET}')
        print(f'  {YELLOW}1 indicatore critico, {warnings} warning. Verifica manualmente.{RESET}')
    elif warnings >= 3:
        print(f'  {YELLOW}{BOLD}VERDETTO: ATTENZIONE{RESET}')
        print(f'  {YELLOW}Nessun indicatore critico ma {warnings} warning. Controlla i dettagli.{RESET}')
    else:
        print(f'  {GREEN}{BOLD}VERDETTO: LEGITTIMA{RESET}')
        print(f'  {GREEN}{oks} controlli superati. La mail sembra autentica.{RESET}')

    print(f'\n  {DIM}Controlli: {GREEN}{oks} ok{RESET} {DIM}/ {YELLOW}{warnings} warn{RESET} {DIM}/ {RED}{dangers} danger{RESET}')
    print(f'{BOLD}{"=" * 60}{RESET}\n')


def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'rb') as f:
            msg = email.message_from_bytes(f.read(), policy=policy.default)
    else:
        msg = email.message_from_bytes(sys.stdin.buffer.read(), policy=policy.default)

    results = check_spoofing(msg)
    print_results(results, msg)


if __name__ == '__main__':
    main()
