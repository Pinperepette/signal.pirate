"""
AI Cloaking Lab - Detection & Cloaking Server
Dimostra come un sito puo' servire contenuti diversi
a umani e AI agent sulla stessa URL.

Ogni richiesta viene analizzata con un sistema di punteggio
su 6 layer. Sopra la soglia: sei un agent.
"""

from flask import Flask, request, render_template, jsonify
from datetime import datetime
import json
import hashlib
import os

app = Flask(__name__)

# log di tutte le visite
visit_log = []

# ──────────────────────────────────────────────
# LAYER DI DETECTION - ogni layer restituisce
# un punteggio da 0 (umano) a 1 (agent)
# ──────────────────────────────────────────────

KNOWN_BOT_UA = [
    'GPTBot', 'ChatGPT-User', 'OpenAI',
    'ClaudeBot', 'Anthropic',
    'PerplexityBot', 'Perplexity',
    'Google-Extended', 'Googlebot',
    'CCBot', 'cohere-ai',
    'Bytespider', 'PetalBot',
    'python-requests', 'Python-urllib',
    'node-fetch', 'axios',
    'Go-http-client', 'Java/',
    'Scrapy', 'curl', 'wget', 'httpx',
    'HeadlessChrome', 'PhantomJS',
]


def score_user_agent(headers):
    """Layer 1: User-Agent analysis."""
    ua = headers.get('User-Agent', '')

    if not ua:
        return 1.0, 'User-Agent assente'

    ua_lower = ua.lower()
    for bot in KNOWN_BOT_UA:
        if bot.lower() in ua_lower:
            return 1.0, f'Bot UA: {bot}'

    # headless browser signals
    if 'headless' in ua_lower:
        return 0.8, 'Headless browser detected'

    return 0.0, f'UA: {ua[:80]}'


def score_accept_headers(headers):
    """Layer 2: Accept-* headers.
    I browser reali mandano Accept-Language, Accept-Encoding
    con valori specifici. Gli agent spesso li omettono.
    """
    score = 0.0
    details = []

    if not headers.get('Accept-Language'):
        score += 0.4
        details.append('Accept-Language assente')

    accept = headers.get('Accept', '')
    if accept == '*/*' or not accept:
        score += 0.3
        details.append(f'Accept generico: {accept or "(vuoto)"}')

    if not headers.get('Accept-Encoding'):
        score += 0.3
        details.append('Accept-Encoding assente')

    return min(score, 1.0), '; '.join(details) if details else 'Headers Accept normali'


def score_sec_fetch(headers):
    """Layer 3: Sec-Fetch-* headers.
    Solo i browser reali li mandano. Script e crawler no.
    """
    sec_headers = [
        'Sec-Fetch-Mode',
        'Sec-Fetch-Site',
        'Sec-Fetch-Dest',
        'Sec-Fetch-User',
    ]
    present = sum(1 for h in sec_headers if headers.get(h))

    if present == 0:
        return 1.0, 'Nessun Sec-Fetch-* header'
    elif present <= 2:
        return 0.5, f'Solo {present}/4 Sec-Fetch-* headers'
    else:
        return 0.0, f'{present}/4 Sec-Fetch-* headers presenti'


def score_connection_hints(headers):
    """Layer 4: Connection behavior.
    Browser reali mandano header come Upgrade-Insecure-Requests,
    Cache-Control, cookie ecc. Gli agent no.
    """
    score = 0.0
    details = []

    if not headers.get('Upgrade-Insecure-Requests'):
        score += 0.3
        details.append('No Upgrade-Insecure-Requests')

    if not headers.get('Cookie'):
        score += 0.2
        details.append('No Cookie')

    if not headers.get('Referer'):
        score += 0.2
        details.append('No Referer')

    # browser hint headers
    if not headers.get('Sec-Ch-Ua'):
        score += 0.3
        details.append('No Sec-Ch-Ua (client hints)')

    return min(score, 1.0), '; '.join(details) if details else 'Connection hints normali'


def score_resource_pattern(request_path):
    """Layer 5: Resource loading pattern.
    Umani caricano HTML poi CSS, JS, immagini.
    Agent caricano solo HTML.
    Tracciamo le risorse richieste per IP.
    """
    # questo layer funziona sulla dashboard,
    # per la singola richiesta diamo un segnale base
    if request_path == '/' or request_path.endswith('.html'):
        return 0.0, 'Richiesta HTML (monitoraggio risorse attivo)'
    return 0.0, 'Richiesta risorsa secondaria'


def score_request_method(headers, args):
    """Layer 6: Behavioral signals.
    Controlla pattern tipici di script automatici.
    """
    score = 0.0
    details = []

    # range header (bot che scaricano parzialmente)
    if headers.get('Range'):
        score += 0.3
        details.append('Range header presente')

    # DNT header (raro nei bot moderni, ma assente in molti script)
    # Non un segnale forte, piccolo contributo
    if not headers.get('DNT') and not headers.get('Sec-GPC'):
        score += 0.1
        details.append('No DNT/GPC')

    return min(score, 1.0), '; '.join(details) if details else 'Behavioral signals normali'


# ──────────────────────────────────────────────
# SCORING ENGINE
# ──────────────────────────────────────────────

# pesi per ogni layer (sommano a 1.0)
LAYER_WEIGHTS = {
    'user_agent':       0.30,
    'accept_headers':   0.15,
    'sec_fetch':        0.25,
    'connection_hints': 0.15,
    'resource_pattern': 0.05,
    'behavioral':       0.10,
}

AGENT_THRESHOLD = 0.45  # sopra questo punteggio = agent


def analyze_request(req):
    """Analizza la richiesta e restituisce score + dettagli."""
    headers = req.headers

    layers = {
        'user_agent':       score_user_agent(headers),
        'accept_headers':   score_accept_headers(headers),
        'sec_fetch':        score_sec_fetch(headers),
        'connection_hints': score_connection_hints(headers),
        'resource_pattern': score_resource_pattern(req.path),
        'behavioral':       score_request_method(headers, req.args),
    }

    total = sum(
        layers[name][0] * LAYER_WEIGHTS[name]
        for name in layers
    )

    is_agent = total >= AGENT_THRESHOLD

    result = {
        'timestamp': datetime.now().isoformat(),
        'ip': req.remote_addr,
        'path': req.path,
        'is_agent': is_agent,
        'total_score': round(total, 3),
        'threshold': AGENT_THRESHOLD,
        'layers': {
            name: {
                'score': round(score, 3),
                'weight': LAYER_WEIGHTS[name],
                'weighted': round(score * LAYER_WEIGHTS[name], 3),
                'detail': detail,
            }
            for name, (score, detail) in layers.items()
        },
        'user_agent': req.headers.get('User-Agent', '(none)')[:120],
    }

    visit_log.append(result)
    return result


# ──────────────────────────────────────────────
# ROUTES
# ──────────────────────────────────────────────

@app.route('/')
def index():
    """Pagina principale: serve contenuto diverso in base al punteggio."""
    analysis = analyze_request(request)

    if analysis['is_agent']:
        return render_template('page_agent.html', analysis=analysis)
    else:
        return render_template('page_human.html', analysis=analysis)


@app.route('/semantic')
def semantic():
    """Pagina con cloaking semantico: stessa pagina per tutti.
    Nessun fingerprinting, nessuna biforcazione.
    L'HTML e' identico per umani e agent."""
    analyze_request(request)
    return render_template('page_semantic.html')


@app.route('/dashboard')
def dashboard():
    """Dashboard: mostra il log di tutte le visite con i punteggi."""
    return render_template('dashboard.html', visits=visit_log)


@app.route('/api/visits')
def api_visits():
    """API JSON per il log visite."""
    return jsonify(visit_log)


@app.route('/api/analyze')
def api_analyze():
    """Analizza la richiesta corrente e restituisce il risultato."""
    return jsonify(analyze_request(request))


@app.route('/style.css')
def css():
    """CSS della pagina. Se un client lo richiede, e' un segnale umano."""
    # logghiamo la richiesta CSS (segnale di browser reale)
    analyze_request(request)
    return app.send_static_file('style.css'), 200, {'Content-Type': 'text/css'}


@app.route('/favicon.ico')
def favicon():
    """Favicon. Stessa logica: i browser la chiedono, gli agent no."""
    analyze_request(request)
    return '', 204


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────

if __name__ == '__main__':
    print()
    print('=' * 55)
    print('  AI CLOAKING LAB')
    print('  ─────────────────────────────────────')
    print('  Pagina cloaked:   http://127.0.0.1:5000/')
    print('  Dashboard:        http://127.0.0.1:5000/dashboard')
    print('  API analisi:      http://127.0.0.1:5000/api/analyze')
    print('  API log visite:   http://127.0.0.1:5000/api/visits')
    print('=' * 55)
    print()
    app.run(debug=True, host='0.0.0.0', port=5000)
