#!/usr/bin/env python3
"""
02_spf_dkim_dmarc_check.py — Verifica SPF, DKIM e DMARC di un dominio

Dato un dominio (es. members.netflix.com), interroga il DNS e mostra:
- Record SPF: chi e' autorizzato a spedire
- Selettori DKIM: scarica la chiave pubblica
- Policy DMARC: none/quarantine/reject

Usa solo la stdlib Python (subprocess per dig). Zero dipendenze.

Uso:
    python3 02_spf_dkim_dmarc_check.py members.netflix.com
    python3 02_spf_dkim_dmarc_check.py members.netflix.com --selector 22seek5htn6zhuvy5jwo2o764amigf2d
"""

import subprocess
import sys
import re


# Colori terminale
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
BOLD = '\033[1m'
DIM = '\033[2m'
RESET = '\033[0m'


def dig_txt(domain):
    """Esegue dig TXT e restituisce i record."""
    try:
        result = subprocess.run(
            ['dig', 'TXT', domain, '+short'],
            capture_output=True, text=True, timeout=10
        )
        lines = result.stdout.strip().split('\n')
        # Rimuovi le virgolette e unisci i frammenti
        records = []
        for line in lines:
            if line.strip():
                clean = line.strip().strip('"')
                records.append(clean)
        return records
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def dig_reverse(ip):
    """Esegue dig -x per reverse DNS."""
    try:
        result = subprocess.run(
            ['dig', '-x', ip, '+short'],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ''


def check_spf(domain):
    """Controlla il record SPF di un dominio."""
    print(f'\n{BOLD}{"=" * 60}{RESET}')
    print(f'{BOLD}  SPF CHECK: {CYAN}{domain}{RESET}')
    print(f'{BOLD}{"=" * 60}{RESET}\n')

    records = dig_txt(domain)
    spf_records = [r for r in records if r.startswith('v=spf1')]

    if not spf_records:
        print(f'  {RED}[!] Nessun record SPF trovato per {domain}{RESET}')
        print(f'  {RED}    Chiunque puo\' spedire email da @{domain}{RESET}')
        return

    for spf in spf_records:
        print(f'  {GREEN}Record:{RESET} {spf}\n')

        # Parsa i meccanismi
        parts = spf.split()
        for part in parts[1:]:  # Salta v=spf1
            if part.startswith('include:'):
                included = part.split(':')[1]
                print(f'  {CYAN}include:{RESET} {included}')
                # Segui la catena
                sub_records = dig_txt(included)
                for sr in sub_records:
                    if sr.startswith('v=spf1'):
                        ips = re.findall(r'ip4:([\d./]+)', sr)
                        for ip in ips[:5]:
                            print(f'    {DIM}ip4:{ip}{RESET}')
                        if len(ips) > 5:
                            print(f'    {DIM}... e altri {len(ips) - 5} range{RESET}')
            elif part.startswith('ip4:'):
                print(f'  {GREEN}ip4:{RESET} {part[4:]}')
            elif part.startswith('ip6:'):
                print(f'  {GREEN}ip6:{RESET} {part[4:]}')
            elif part.startswith('redirect='):
                redirect = part.split('=')[1]
                print(f'  {YELLOW}redirect:{RESET} {redirect}')
            elif part in ('-all', '~all', '?all', '+all'):
                if part == '-all':
                    print(f'\n  {GREEN}Policy: -all (HARD FAIL){RESET}')
                    print(f'  {DIM}Tutto cio\' che non e\' elencato viene rifiutato.{RESET}')
                elif part == '~all':
                    print(f'\n  {YELLOW}Policy: ~all (SOFT FAIL){RESET}')
                    print(f'  {DIM}Tutto cio\' che non e\' elencato e\' sospetto ma non rifiutato.{RESET}')
                elif part == '?all':
                    print(f'\n  {YELLOW}Policy: ?all (NEUTRAL){RESET}')
                    print(f'  {DIM}Il dominio non si pronuncia. Nessuna garanzia.{RESET}')
                elif part == '+all':
                    print(f'\n  {RED}Policy: +all (PASS ALL){RESET}')
                    print(f'  {RED}PERICOLOSO: chiunque puo\' spedire per questo dominio!{RESET}')


def check_dkim(domain, selector=None):
    """Controlla la chiave DKIM di un dominio."""
    print(f'\n{BOLD}{"=" * 60}{RESET}')
    print(f'{BOLD}  DKIM CHECK: {CYAN}{domain}{RESET}')
    print(f'{BOLD}{"=" * 60}{RESET}\n')

    if selector:
        selectors = [selector]
    else:
        # Prova selettori comuni
        selectors = [
            'default', 'google', 'selector1', 'selector2',
            'k1', 'k2', 'dkim', 'mail', 's1', 's2',
            '20230601', '20221208',
        ]
        print(f'  {DIM}Nessun selettore specificato, provo quelli comuni...{RESET}')
        print(f'  {DIM}Usa --selector NOME per specificarne uno.{RESET}\n')

    found = False
    for sel in selectors:
        query = f'{sel}._domainkey.{domain}'
        records = dig_txt(query)

        if records and any('DKIM1' in r or 'p=' in r for r in records):
            found = True
            full_record = ' '.join(records)
            print(f'  {GREEN}Trovato!{RESET} Selettore: {CYAN}{sel}{RESET}')
            print(f'  {DIM}DNS: dig TXT {query} +short{RESET}')

            # Parsa i campi
            k_match = re.search(r'k=(\w+)', full_record)
            p_match = re.search(r'p=(\S+)', full_record)

            if k_match:
                print(f'  Algoritmo: {k_match.group(1)}')
            if p_match:
                pubkey = p_match.group(1)
                if len(pubkey) > 60:
                    print(f'  Chiave pubblica: {pubkey[:60]}...')
                else:
                    print(f'  Chiave pubblica: {pubkey}')
                if not pubkey or pubkey == '':
                    print(f'  {RED}[!] Chiave vuota. DKIM revocato per questo selettore.{RESET}')

            print()

    if not found:
        if selector:
            print(f'  {RED}[!] Nessuna chiave DKIM trovata per selettore {selector}{RESET}')
            print(f'  {DIM}Query: dig TXT {selector}._domainkey.{domain} +short{RESET}')
        else:
            print(f'  {YELLOW}[?] Nessun selettore comune trovato.{RESET}')
            print(f'  {DIM}Specifica il selettore dall\'header DKIM-Signature (campo s=){RESET}')


def check_dmarc(domain):
    """Controlla il record DMARC di un dominio."""
    # DMARC si cerca sul dominio organizzativo (netflix.com, non members.netflix.com)
    parts = domain.split('.')
    org_domains = []
    if len(parts) > 2:
        org_domains.append('.'.join(parts[-2:]))  # netflix.com
    org_domains.insert(0, domain)  # members.netflix.com (prova prima)

    print(f'\n{BOLD}{"=" * 60}{RESET}')
    print(f'{BOLD}  DMARC CHECK: {CYAN}{domain}{RESET}')
    print(f'{BOLD}{"=" * 60}{RESET}\n')

    for d in org_domains:
        query = f'_dmarc.{d}'
        records = dig_txt(query)
        dmarc_records = [r for r in records if 'DMARC1' in r]

        if dmarc_records:
            rec = dmarc_records[0]
            print(f'  {GREEN}Trovato:{RESET} _dmarc.{d}')
            print(f'  {DIM}Record:{RESET} {rec}\n')

            # Policy
            p_match = re.search(r'p=(\w+)', rec)
            if p_match:
                policy = p_match.group(1).lower()
                if policy == 'reject':
                    print(f'  Policy:        {GREEN}{BOLD}REJECT{RESET} (mail non autenticate rifiutate)')
                elif policy == 'quarantine':
                    print(f'  Policy:        {YELLOW}{BOLD}QUARANTINE{RESET} (mail non autenticate in spam)')
                elif policy == 'none':
                    print(f'  Policy:        {RED}{BOLD}NONE{RESET} (solo monitoraggio, non blocca nulla)')

            # Subdomain policy
            sp_match = re.search(r'sp=(\w+)', rec)
            if sp_match:
                sp = sp_match.group(1).lower()
                color = GREEN if sp == 'reject' else YELLOW if sp == 'quarantine' else RED
                print(f'  Sottodomini:   {color}{BOLD}{sp.upper()}{RESET}')

            # Reporting
            rua_match = re.search(r'rua=([^;]+)', rec)
            if rua_match:
                print(f'  Report (agg):  {DIM}{rua_match.group(1)}{RESET}')
            ruf_match = re.search(r'ruf=([^;]+)', rec)
            if ruf_match:
                print(f'  Report (for):  {DIM}{ruf_match.group(1)}{RESET}')

            # Percentage
            pct_match = re.search(r'pct=(\d+)', rec)
            if pct_match:
                print(f'  Percentuale:   {pct_match.group(1)}%')

            return

    print(f'  {RED}[!] Nessun record DMARC trovato per {domain}{RESET}')
    print(f'  {RED}    Chiunque puo\' spoofare il From: di questo dominio.{RESET}')


def check_ip(ip):
    """Reverse DNS e blacklist check su un IP."""
    print(f'\n{BOLD}{"=" * 60}{RESET}')
    print(f'{BOLD}  IP CHECK: {CYAN}{ip}{RESET}')
    print(f'{BOLD}{"=" * 60}{RESET}\n')

    # Reverse DNS
    rdns = dig_reverse(ip)
    if rdns:
        print(f'  Reverse DNS: {GREEN}{rdns}{RESET}')
    else:
        print(f'  Reverse DNS: {RED}nessuno{RESET}')

    # Spamhaus check
    octets = ip.split('.')
    if len(octets) == 4:
        reversed_ip = '.'.join(reversed(octets))
        for bl_name, bl_domain in [
            ('Spamhaus ZEN', 'zen.spamhaus.org'),
            ('Barracuda', 'b.barracudacentral.org'),
        ]:
            query = f'{reversed_ip}.{bl_domain}'
            try:
                result = subprocess.run(
                    ['dig', query, '+short'],
                    capture_output=True, text=True, timeout=5
                )
                response = result.stdout.strip()
                if response and response.startswith('127.'):
                    print(f'  {bl_name}: {RED}{BOLD}LISTED{RESET} ({response})')
                elif response == '' or 'NXDOMAIN' in response:
                    print(f'  {bl_name}: {GREEN}CLEAN{RESET}')
                else:
                    print(f'  {bl_name}: {DIM}{response}{RESET}')
            except (subprocess.TimeoutExpired, FileNotFoundError):
                print(f'  {bl_name}: {DIM}timeout{RESET}')


def main():
    if len(sys.argv) < 2:
        print(f'Uso: python3 {sys.argv[0]} DOMINIO [--selector NOME] [--ip INDIRIZZO]')
        print(f'')
        print(f'Esempi:')
        print(f'  python3 {sys.argv[0]} members.netflix.com')
        print(f'  python3 {sys.argv[0]} members.netflix.com --selector 22seek5htn6zhuvy5jwo2o764amigf2d')
        print(f'  python3 {sys.argv[0]} members.netflix.com --ip 54.240.114.85')
        sys.exit(1)

    domain = sys.argv[1]
    selector = None
    ip = None

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--selector' and i + 1 < len(sys.argv):
            selector = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--ip' and i + 1 < len(sys.argv):
            ip = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    check_spf(domain)
    check_dkim(domain, selector)
    check_dmarc(domain)

    if ip:
        check_ip(ip)

    print()


if __name__ == '__main__':
    main()
