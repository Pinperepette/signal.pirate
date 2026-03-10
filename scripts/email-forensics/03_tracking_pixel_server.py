#!/usr/bin/env python3
"""
03_tracking_pixel_server.py — Server di tracking pixel per email

Server HTTP minimale che serve un 1x1 GIF trasparente.
Ogni richiesta viene loggata con tutti i dettagli:
- Timestamp apertura
- IP del destinatario
- User-Agent (rivela il client email)
- Accept-Language
- Tutti gli header HTTP
- UUID del destinatario (dal path)

Il pixel viene inserito nell'HTML della mail come:
    <img src="http://SERVER:PORT/px/{uuid}.gif" width="1" height="1">

Dove {uuid} e' unico per ogni destinatario.

Uso:
    python3 03_tracking_pixel_server.py                    # porta 8888
    python3 03_tracking_pixel_server.py --port 9999        # porta custom
    python3 03_tracking_pixel_server.py --log tracking.db  # salva in SQLite

Test:
    curl -v http://localhost:8888/px/test-user-001.gif

NOTA: questo e' un laboratorio educativo. Non usare per tracciare
persone senza il loro consenso.
"""

import http.server
import sqlite3
import json
import sys
import os
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs


# 1x1 GIF trasparente (43 byte)
TRANSPARENT_GIF = (
    b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00'
    b'\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x00\x00\x00\x00'
    b'\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02'
    b'\x44\x01\x00\x3b'
)

# Colori terminale
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
BOLD = '\033[1m'
DIM = '\033[2m'
RESET = '\033[0m'

# Database
DB_PATH = None
db_conn = None


def init_db(path):
    """Inizializza il database SQLite."""
    global db_conn
    db_conn = sqlite3.connect(path)
    db_conn.execute('''
        CREATE TABLE IF NOT EXISTS opens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            recipient_uuid TEXT,
            ip TEXT,
            user_agent TEXT,
            accept_language TEXT,
            headers_json TEXT,
            path TEXT
        )
    ''')
    db_conn.commit()


def log_open(recipient_uuid, ip, user_agent, accept_lang, headers, path):
    """Logga un'apertura."""
    ts = datetime.now(timezone.utc).isoformat()

    # Classifica il client
    client_type = classify_client(user_agent, ip)

    # Stampa nel terminale
    print(f'\n{BOLD}{"─" * 60}{RESET}')
    print(f'  {GREEN}APERTURA RILEVATA{RESET}  {DIM}{ts}{RESET}')
    print(f'  UUID:        {CYAN}{recipient_uuid}{RESET}')
    print(f'  IP:          {YELLOW}{ip}{RESET}')
    print(f'  User-Agent:  {user_agent[:80]}')
    print(f'  Language:    {accept_lang}')
    print(f'  Client:      {BOLD}{client_type}{RESET}')

    # Header interessanti
    for h in ['Accept', 'Accept-Encoding', 'Connection', 'Cache-Control', 'X-Forwarded-For']:
        val = headers.get(h, '')
        if val:
            print(f'  {DIM}{h}: {val}{RESET}')

    print(f'{BOLD}{"─" * 60}{RESET}')

    # Salva in SQLite
    if db_conn:
        db_conn.execute(
            'INSERT INTO opens (timestamp, recipient_uuid, ip, user_agent, accept_language, headers_json, path) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (ts, recipient_uuid, ip, user_agent, accept_lang, json.dumps(dict(headers)), path)
        )
        db_conn.commit()


def classify_client(user_agent, ip):
    """Classifica il tipo di client dall'User-Agent e dall'IP."""
    ua = (user_agent or '').lower()

    if 'googleimageproxy' in ua or 'googleusercontent' in ua:
        return f'{YELLOW}Gmail Image Proxy (IP Google, non del destinatario){RESET}'
    elif 'apple' in ua or 'cfnetwork' in ua:
        return f'{YELLOW}Apple Mail Privacy Protection (prefetch, IP Apple){RESET}'
    elif 'thunderbird' in ua:
        return f'{GREEN}Thunderbird (apertura reale se le immagini sono abilitate){RESET}'
    elif 'outlook' in ua or 'microsoft' in ua:
        return f'{CYAN}Outlook (apertura reale){RESET}'
    elif 'curl' in ua:
        return f'{DIM}curl (ispezione manuale){RESET}'
    elif 'wget' in ua:
        return f'{DIM}wget (ispezione manuale){RESET}'
    elif 'python' in ua:
        return f'{DIM}Python (script automatico){RESET}'
    else:
        return f'{GREEN}Sconosciuto: {ua[:40]}{RESET}'


class TrackingHandler(http.server.BaseHTTPRequestHandler):
    """Handler per le richieste al pixel server."""

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # Pixel tracking
        if path.startswith('/px/') and path.endswith('.gif'):
            recipient_uuid = path[4:-4]  # /px/{uuid}.gif -> uuid

            # Logga l'apertura
            log_open(
                recipient_uuid=recipient_uuid,
                ip=self.client_address[0],
                user_agent=self.headers.get('User-Agent', ''),
                accept_lang=self.headers.get('Accept-Language', ''),
                headers=self.headers,
                path=self.path,
            )

            # Rispondi con il GIF trasparente
            self.send_response(200)
            self.send_header('Content-Type', 'image/gif')
            self.send_header('Content-Length', str(len(TRANSPARENT_GIF)))
            # Anti-cache: forza il client a richiedere ogni volta
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.end_headers()
            self.wfile.write(TRANSPARENT_GIF)

        # Dashboard
        elif path == '/dashboard':
            self.serve_dashboard()

        # Genera un pixel URL per un nuovo destinatario
        elif path == '/generate':
            new_uuid = str(uuid.uuid4())
            port = self.server.server_address[1]
            pixel_url = f'http://localhost:{port}/px/{new_uuid}.gif'
            html_tag = f'<img src="{pixel_url}" width="1" height="1" style="display:none">'

            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            response = f'UUID: {new_uuid}\nPixel URL: {pixel_url}\nHTML tag: {html_tag}\n'
            self.wfile.write(response.encode())

        else:
            self.send_response(404)
            self.end_headers()

    def serve_dashboard(self):
        """Mostra una dashboard con le aperture."""
        if not db_conn:
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Dashboard disponibile solo con --log tracking.db\n')
            return

        cursor = db_conn.execute(
            'SELECT timestamp, recipient_uuid, ip, user_agent FROM opens ORDER BY id DESC LIMIT 50'
        )
        rows = cursor.fetchall()

        html = '''<!DOCTYPE html><html><head><title>Tracking Dashboard</title>
        <style>
            body { font-family: monospace; background: #0d1117; color: #c8c8d8; padding: 2rem; }
            table { border-collapse: collapse; width: 100%; }
            th { background: #1a1a2e; color: #00ff88; padding: 0.8rem; text-align: left; }
            td { padding: 0.6rem; border-bottom: 1px solid #1a1a2e; }
            tr:hover td { background: rgba(0,255,136,0.05); }
            h1 { color: #00ff88; }
        </style></head><body>
        <h1>Tracking Pixel Dashboard</h1>
        <p>Ultime 50 aperture</p>
        <table>
        <tr><th>Timestamp</th><th>UUID</th><th>IP</th><th>User-Agent</th></tr>'''

        for row in rows:
            ts, uid, ip, ua = row
            ua_short = (ua or '')[:60]
            html += f'<tr><td>{ts}</td><td>{uid[:12]}...</td><td>{ip}</td><td>{ua_short}</td></tr>'

        html += '</table></body></html>'

        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        """Silenzia i log HTTP standard."""
        pass


def main():
    port = 8888

    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '--port' and i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '--log' and i + 1 < len(sys.argv):
            global DB_PATH
            DB_PATH = sys.argv[i + 1]
            init_db(DB_PATH)
            i += 2
        else:
            i += 1

    print(f'{BOLD}{"=" * 60}{RESET}')
    print(f'{BOLD}  TRACKING PIXEL SERVER{RESET}')
    print(f'{BOLD}{"=" * 60}{RESET}')
    print(f'  Porta:     {GREEN}{port}{RESET}')
    print(f'  Database:  {GREEN}{DB_PATH or "solo terminale"}{RESET}')
    print(f'  Pixel URL: {CYAN}http://localhost:{port}/px/{{uuid}}.gif{RESET}')
    print(f'  Dashboard: {CYAN}http://localhost:{port}/dashboard{RESET}')
    print(f'  Genera:    {CYAN}http://localhost:{port}/generate{RESET}')
    print(f'  Test:      curl -v http://localhost:{port}/px/test-001.gif')
    print(f'{BOLD}{"=" * 60}{RESET}')
    print(f'  {DIM}In attesa di aperture...{RESET}\n')

    server = http.server.HTTPServer(('0.0.0.0', port), TrackingHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f'\n{DIM}Server fermato.{RESET}')
        if db_conn:
            db_conn.close()


if __name__ == '__main__':
    main()
