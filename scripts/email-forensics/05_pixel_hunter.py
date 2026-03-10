#!/usr/bin/env python3
"""
05_pixel_hunter.py — Trova tracking pixel nascosti in una mail HTML

Legge un file .eml e cerca nel body HTML:
- Immagini 1x1 pixel
- Immagini con display:none o visibility:hidden
- Immagini con width/height 0
- URL esterni con UUID/tracking ID nel path
- Link con parametri di tracking (lnktrk, trkid, utm_*)

Output: lista di URL sospetti con classificazione.

Uso:
    python3 05_pixel_hunter.py mail.eml
    cat mail.eml | python3 05_pixel_hunter.py
"""

import sys
import email
import re
from email import policy
from urllib.parse import urlparse, parse_qs


# Colori terminale
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
BOLD = '\033[1m'
DIM = '\033[2m'
RESET = '\033[0m'


def get_html_body(msg):
    """Estrae il body HTML dal messaggio."""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == 'text/html':
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or 'utf-8'
                try:
                    return payload.decode(charset, errors='replace')
                except (LookupError, UnicodeDecodeError):
                    return payload.decode('utf-8', errors='replace')
    else:
        if msg.get_content_type() == 'text/html':
            payload = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or 'utf-8'
            return payload.decode(charset, errors='replace')
    return ''


def find_tracking_pixels(html):
    """Cerca tracking pixel nel body HTML."""
    findings = []

    # Pattern 1: <img> con dimensioni 1x1
    img_tags = re.findall(r'<img[^>]+>', html, re.IGNORECASE | re.DOTALL)

    for tag in img_tags:
        reasons = []
        src_match = re.search(r'src=["\']([^"\']+)["\']', tag, re.IGNORECASE)
        src = src_match.group(1) if src_match else ''

        # Dimensioni sospette
        w_match = re.search(r'width=["\']?(\d+)', tag, re.IGNORECASE)
        h_match = re.search(r'height=["\']?(\d+)', tag, re.IGNORECASE)
        width = int(w_match.group(1)) if w_match else None
        height = int(h_match.group(1)) if h_match else None

        if width is not None and width <= 1:
            reasons.append(f'width={width}')
        if height is not None and height <= 1:
            reasons.append(f'height={height}')

        # display:none o visibility:hidden nello style
        style_match = re.search(r'style=["\']([^"\']+)["\']', tag, re.IGNORECASE)
        if style_match:
            style = style_match.group(1).lower()
            if 'display:none' in style or 'display: none' in style:
                reasons.append('display:none')
            if 'visibility:hidden' in style or 'visibility: hidden' in style:
                reasons.append('visibility:hidden')
            if 'width:0' in style or 'width: 0' in style:
                reasons.append('width:0 in style')
            if 'height:0' in style or 'height: 0' in style:
                reasons.append('height:0 in style')

        # URL con UUID o tracking patterns
        if src:
            parsed = urlparse(src)
            path = parsed.path.lower()
            # UUID nel path
            uuid_match = re.search(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', src, re.IGNORECASE)
            if uuid_match:
                reasons.append(f'UUID nel path ({uuid_match.group()[:12]}...)')

            # Pattern comuni di tracking
            tracking_patterns = [
                (r'/px/', 'path /px/'),
                (r'/pixel', 'path /pixel'),
                (r'/track', 'path /track'),
                (r'/open', 'path /open'),
                (r'/beacon', 'path /beacon'),
                (r'/t\.gif', 'file t.gif'),
                (r'/o\.gif', 'file o.gif'),
                (r'\.gif\?', '.gif con query string'),
            ]
            for pattern, desc in tracking_patterns:
                if re.search(pattern, src, re.IGNORECASE):
                    reasons.append(desc)

        if reasons:
            findings.append({
                'type': 'pixel',
                'src': src,
                'reasons': reasons,
                'tag': tag[:120],
            })

    # Pattern 2: URL di tracking nei link
    link_tags = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>', html, re.IGNORECASE | re.DOTALL)
    for href in link_tags:
        reasons = []
        parsed = urlparse(href)
        params = parse_qs(parsed.query)

        tracking_params = ['lnktrk', 'trkid', 'lkid', 'utm_source', 'utm_medium', 'utm_campaign', 'mc_cid', 'mc_eid']
        found_params = [p for p in tracking_params if p in params]
        if found_params:
            reasons.append(f'parametri tracking: {", ".join(found_params)}')

        if reasons:
            findings.append({
                'type': 'link',
                'src': href[:120],
                'reasons': reasons,
                'tag': '',
            })

    return findings


def find_external_resources(html):
    """Trova tutte le risorse esterne (immagini, CSS, ecc.)."""
    urls = set()

    # Immagini
    for match in re.finditer(r'src=["\']https?://([^"\']+)["\']', html, re.IGNORECASE):
        urls.add(match.group(1))

    # Background images
    for match in re.finditer(r'url\(["\']?https?://([^)"\']+)["\']?\)', html, re.IGNORECASE):
        urls.add(match.group(1))

    return urls


def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'rb') as f:
            msg = email.message_from_bytes(f.read(), policy=policy.default)
    else:
        msg = email.message_from_bytes(sys.stdin.buffer.read(), policy=policy.default)

    from_header = msg.get('From', '')
    subject = msg.get('Subject', '')

    print(f'\n{BOLD}{"=" * 60}{RESET}')
    print(f'{BOLD}  PIXEL HUNTER{RESET}')
    print(f'{BOLD}{"=" * 60}{RESET}')
    print(f'  From:    {CYAN}{from_header}{RESET}')
    print(f'  Subject: {subject}')
    print(f'{BOLD}{"─" * 60}{RESET}\n')

    html = get_html_body(msg)
    if not html:
        print(f'  {YELLOW}Nessun body HTML trovato. Mail solo testo.{RESET}')
        print(f'  {GREEN}Nessun tracking pixel possibile in una mail plain text.{RESET}\n')
        return

    print(f'  {DIM}Body HTML: {len(html)} caratteri{RESET}\n')

    # Cerca pixel
    findings = find_tracking_pixels(html)

    if findings:
        pixels = [f for f in findings if f['type'] == 'pixel']
        links = [f for f in findings if f['type'] == 'link']

        if pixels:
            print(f'  {RED}{BOLD}TRACKING PIXEL TROVATI: {len(pixels)}{RESET}\n')
            for i, f in enumerate(pixels, 1):
                print(f'  {RED}#{i}{RESET} {f["src"][:80]}')
                for r in f['reasons']:
                    print(f'       {YELLOW}{r}{RESET}')
                if f['tag']:
                    print(f'       {DIM}{f["tag"][:100]}{RESET}')
                print()

        if links:
            print(f'  {YELLOW}{BOLD}LINK CON TRACKING: {len(links)}{RESET}\n')
            for i, f in enumerate(links, 1):
                print(f'  {YELLOW}#{i}{RESET} {f["src"][:80]}')
                for r in f['reasons']:
                    print(f'       {DIM}{r}{RESET}')
                print()
    else:
        print(f'  {GREEN}Nessun tracking pixel trovato.{RESET}\n')

    # Risorse esterne
    urls = find_external_resources(html)
    if urls:
        print(f'  {BOLD}RISORSE ESTERNE: {len(urls)}{RESET}')
        print(f'  {DIM}Ogni risorsa esterna e\' una potenziale fonte di tracking.{RESET}\n')
        for url in sorted(urls)[:20]:
            print(f'    {DIM}{url[:80]}{RESET}')
        if len(urls) > 20:
            print(f'    {DIM}... e altre {len(urls) - 20}{RESET}')

    print(f'\n{BOLD}{"=" * 60}{RESET}\n')


if __name__ == '__main__':
    main()
