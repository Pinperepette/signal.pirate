#!/usr/bin/env python3
"""
07_pixel_demo.py — Demo completa tracking pixel: genera mail + avvia server

Fa tutto in un colpo:
1. Avvia il tracking pixel server (porta 8888)
2. Genera una mail HTML con il pixel embedded
3. Genera una versione plain-text della stessa mail
4. Mostra le istruzioni per il test

Test:
    # Terminale 1: avvia la demo
    python3 07_pixel_demo.py

    # Terminale 2: apri con mutt (nessun tracking)
    mutt -f pixel-demo.eml

    # Browser: apri pixel-demo.html (tracking!)
    open pixel-demo.html

NOTA: laboratorio educativo. Il server ascolta solo su localhost.
"""

import sys
import os
import http.server
import sqlite3
import json
import threading
from datetime import datetime, timezone
from urllib.parse import urlparse

# 1x1 GIF trasparente (43 byte)
TRANSPARENT_GIF = (
    b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00'
    b'\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x00\x00\x00\x00'
    b'\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02'
    b'\x44\x01\x00\x3b'
)

GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
BOLD = '\033[1m'
DIM = '\033[2m'
RESET = '\033[0m'

PORT = 8888
open_count = 0


def generate_demo_eml(port):
    """Genera la mail con tracking pixel che punta al server locale."""
    now = datetime.now(timezone.utc)
    date_str = now.strftime('%a, %d %b %Y %H:%M:%S +0000')
    pixel_url = f'http://localhost:{port}/px/pinperepette-demo-001.gif'

    eml = f"""Return-Path: <noreply@newsletter.example.com>
Delivered-To: pinperepette@gmail.com
Received: from mail.newsletter.example.com (mail.newsletter.example.com. [93.184.216.34])
        by mx.google.com with ESMTPS id demo123456
        for <pinperepette@gmail.com>;
        {date_str}
Authentication-Results: mx.google.com;
        spf=pass smtp.mailfrom=noreply@newsletter.example.com;
        dkim=pass header.i=@newsletter.example.com;
        dmarc=pass header.from=newsletter.example.com
From: Newsletter Demo <noreply@newsletter.example.com>
To: pinperepette@gmail.com
Subject: I tuoi contenuti della settimana
Date: {date_str}
Message-ID: <demo-{now.strftime('%Y%m%d%H%M%S')}@newsletter.example.com>
MIME-Version: 1.0
Content-Type: multipart/alternative;
        boundary="----=_boundary_demo_001"

------=_boundary_demo_001
Content-Type: text/plain; charset=UTF-8

Ciao pinperepette,

Ecco i contenuti che abbiamo selezionato per te questa settimana.

1. Come funzionano gli header delle email
2. SPF, DKIM e DMARC spiegati bene
3. Il tracking pixel che nessuno vede

Buona lettura!
Il team Newsletter Demo

------=_boundary_demo_001
Content-Type: text/html; charset=UTF-8

<html>
<body style="font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px;">
<div style="max-width: 600px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 8px;">
<h2 style="color: #333;">Ciao pinperepette!</h2>
<p>Ecco i contenuti che abbiamo selezionato per te questa settimana.</p>
<ol>
<li>Come funzionano gli header delle email</li>
<li>SPF, DKIM e DMARC spiegati bene</li>
<li>Il tracking pixel che nessuno vede</li>
</ol>
<p>Buona lettura!</p>
<p style="color: #999; font-size: 12px;">Il team Newsletter Demo</p>
<img src="{pixel_url}" width="1" height="1" style="display:none" alt="">
</div>
</body>
</html>
------=_boundary_demo_001--
"""

    with open('pixel-demo.eml', 'w') as f:
        f.write(eml)

    # Genera anche un file HTML standalone per aprirlo nel browser
    html_standalone = f"""<!DOCTYPE html>
<html>
<head><title>Newsletter Demo - Tracking Pixel Test</title></head>
<body style="font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px;">
<div style="max-width: 600px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 8px;">
<h2 style="color: #333;">Ciao pinperepette!</h2>
<p>Ecco i contenuti che abbiamo selezionato per te questa settimana.</p>
<ol>
<li>Come funzionano gli header delle email</li>
<li>SPF, DKIM e DMARC spiegati bene</li>
<li>Il tracking pixel che nessuno vede</li>
</ol>
<p>Buona lettura!</p>
<p style="color: #999; font-size: 12px;">Il team Newsletter Demo</p>
<img src="{pixel_url}" width="1" height="1" style="display:none" alt="">
</div>
</body>
</html>
"""

    with open('pixel-demo.html', 'w') as f:
        f.write(html_standalone)

    return pixel_url


class DemoHandler(http.server.BaseHTTPRequestHandler):
    """Handler che logga ogni apertura del pixel."""

    def do_GET(self):
        global open_count
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith('/px/') and path.endswith('.gif'):
            open_count += 1
            recipient = path[4:-4]
            ts = datetime.now(timezone.utc).strftime('%H:%M:%S')
            ua = self.headers.get('User-Agent', '')[:80]

            # Classifica
            ua_lower = ua.lower()
            if 'mozilla' in ua_lower or 'chrome' in ua_lower or 'safari' in ua_lower:
                client = f'{RED}Browser/Webmail{RESET}'
            elif 'curl' in ua_lower:
                client = f'{DIM}curl (test manuale){RESET}'
            elif 'python' in ua_lower:
                client = f'{DIM}Python (script){RESET}'
            else:
                client = f'{YELLOW}{ua[:30]}{RESET}'

            print(f'\n  {GREEN}{BOLD}*** APERTURA #{open_count} ***{RESET}')
            print(f'  {DIM}Ora:{RESET}        {ts}')
            print(f'  {DIM}UUID:{RESET}       {CYAN}{recipient}{RESET}')
            print(f'  {DIM}IP:{RESET}         {self.client_address[0]}')
            print(f'  {DIM}Client:{RESET}     {client}')
            print(f'  {DIM}User-Agent:{RESET} {ua}')
            print(f'  {BOLD}{"─" * 50}{RESET}')

            self.send_response(200)
            self.send_header('Content-Type', 'image/gif')
            self.send_header('Content-Length', str(len(TRANSPARENT_GIF)))
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
            self.send_header('Pragma', 'no-cache')
            self.end_headers()
            self.wfile.write(TRANSPARENT_GIF)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def main():
    port = PORT
    if len(sys.argv) > 1:
        for i, arg in enumerate(sys.argv[1:]):
            if arg == '--port' and i + 2 <= len(sys.argv):
                port = int(sys.argv[i + 2])

    pixel_url = generate_demo_eml(port)

    print(f'\n{BOLD}{"=" * 60}{RESET}')
    print(f'{BOLD}  TRACKING PIXEL DEMO{RESET}')
    print(f'{BOLD}{"=" * 60}{RESET}')
    print(f'  Server:    {GREEN}http://localhost:{port}{RESET}')
    print(f'  Pixel URL: {CYAN}{pixel_url}{RESET}')
    print(f'{BOLD}{"─" * 60}{RESET}')
    print(f'  File generati:')
    print(f'    {CYAN}pixel-demo.eml{RESET}   (mail completa con pixel)')
    print(f'    {CYAN}pixel-demo.html{RESET}  (HTML per browser)')
    print(f'{BOLD}{"─" * 60}{RESET}')
    print(f'  {BOLD}TEST 1: mutt (nessun tracking){RESET}')
    print(f'    mutt -f pixel-demo.eml')
    print(f'    {DIM}mutt mostra solo il testo, ignora l\'HTML.{RESET}')
    print(f'    {DIM}Il pixel non viene mai caricato. Zero log qui sotto.{RESET}')
    print()
    print(f'  {BOLD}TEST 2: browser (tracking!){RESET}')
    print(f'    open pixel-demo.html')
    print(f'    {DIM}Il browser carica il pixel automaticamente.{RESET}')
    print(f'    {DIM}Vedrai l\'apertura loggata qui sotto.{RESET}')
    print()
    print(f'  {BOLD}TEST 3: curl (simula apertura){RESET}')
    print(f'    curl -s {pixel_url} > /dev/null')
    print(f'{BOLD}{"=" * 60}{RESET}')
    print(f'  {DIM}In attesa di aperture... (Ctrl+C per uscire){RESET}\n')

    server = http.server.HTTPServer(('127.0.0.1', port), DemoHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f'\n  {DIM}Server fermato. Aperture totali: {open_count}{RESET}\n')


if __name__ == '__main__':
    main()
