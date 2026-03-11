"""
AI Agent Simulator - Dimostra come un agent legge contenuti cloaked.

Tre modalita':
1. fetch grezzo (come python-requests)
2. fetch con UA browser (spoofing base)
3. confronto: mostra le differenze tra le due risposte

Uso:
    python agent.py              # tutti e 3 i test
    python agent.py --raw        # solo fetch grezzo
    python agent.py --spoof      # solo fetch con UA spoofato
    python agent.py --compare    # confronto side by side
    python agent.py --llm        # manda il contenuto a un LLM e mostra la risposta
"""

import argparse
import requests
import re
import sys
import json
import os

SERVER = os.environ.get('SERVER', 'http://127.0.0.1:5000')

# ──────────────────────────────────────────────
# UTILS
# ──────────────────────────────────────────────

def strip_html(html):
    """Estrae il testo visibile da HTML, inclusi commenti e hidden elements.
    Questo e' quello che un LLM 'vede' quando riceve HTML grezzo."""
    return html


def extract_visible_text(html):
    """Estrae solo il testo che un browser renderebbe visibile.
    Rimuove commenti, display:none, font-size:0, noscript, aria-label."""
    # rimuovi commenti HTML
    text = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
    # rimuovi tag style e script
    text = re.sub(r'<style.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<script.*?</script>', '', text, flags=re.DOTALL)
    # rimuovi noscript (JS attivo = ignorato)
    text = re.sub(r'<noscript>.*?</noscript>', '', text, flags=re.DOTALL)
    # rimuovi div con classi di hiding note (lab 1: cloaking classico)
    text = re.sub(r'<div[^>]*class="[^"]*seo-metadata[^"]*"[^>]*>.*?</div>', '', text, flags=re.DOTALL)
    text = re.sub(r'<span[^>]*class="[^"]*tracking-pixel[^"]*"[^>]*>.*?</span>', '', text, flags=re.DOTALL)
    # rimuovi elementi nascosti (lab 2: cloaking semantico)
    text = re.sub(r'<div[^>]*class="[^"]*visually-hidden[^"]*"[^>]*>.*?</div>', '', text, flags=re.DOTALL)
    text = re.sub(r'<div[^>]*class="[^"]*sr-only[^"]*"[^>]*>.*?</div>', '', text, flags=re.DOTALL)
    text = re.sub(r'<span[^>]*class="[^"]*page-metadata[^"]*"[^>]*>.*?</span>', '', text, flags=re.DOTALL)
    # rimuovi aria-label (non visibili)
    text = re.sub(r'<div[^>]*aria-label="[^"]*"[^>]*>\s*</div>', '', text, flags=re.DOTALL)
    # rimuovi tag HTML rimanenti
    text = re.sub(r'<[^>]+>', '', text)
    # pulisci whitespace
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    return '\n'.join(lines)


def fetch_as_agent():
    """Fetch come un tipico agent Python (nessun header browser)."""
    resp = requests.get(SERVER + '/')
    return resp.text, resp.status_code


def fetch_as_browser():
    """Fetch simulando un browser reale con tutti gli header."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Ch-Ua': '"Chromium";v="131", "Not_A Brand";v="24"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"macOS"',
        'DNT': '1',
    }
    resp = requests.get(SERVER + '/', headers=headers)
    return resp.text, resp.status_code


def get_analysis(headers=None):
    """Chiedi al server come ha classificato la richiesta."""
    if headers:
        resp = requests.get(SERVER + '/api/analyze', headers=headers)
    else:
        resp = requests.get(SERVER + '/api/analyze')
    return resp.json()


# ──────────────────────────────────────────────
# DISPLAY
# ──────────────────────────────────────────────

RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
DIM = '\033[2m'
BOLD = '\033[1m'
RESET = '\033[0m'


def print_header(title):
    print()
    print(f'{CYAN}{"=" * 60}')
    print(f'  {title}')
    print(f'{"=" * 60}{RESET}')
    print()


def print_analysis(analysis):
    score = analysis['total_score']
    is_agent = analysis['is_agent']
    color = RED if is_agent else GREEN
    label = 'AI AGENT' if is_agent else 'HUMAN'

    print(f'  Classificazione: {color}{BOLD}[{label}]{RESET}')
    print(f'  Score totale:    {color}{score}{RESET} (soglia: {analysis["threshold"]})')
    print()

    for name, data in analysis['layers'].items():
        bar_len = int(data['score'] * 20)
        bar = '#' * bar_len + '.' * (20 - bar_len)
        s_color = RED if data['score'] > 0.5 else (YELLOW if data['score'] > 0 else GREEN)
        print(f'  {name:<20} [{s_color}{bar}{RESET}] {data["score"]:.2f} x{data["weight"]} = {data["weighted"]:.3f}')
        if data['detail']:
            print(f'  {DIM}                     {data["detail"]}{RESET}')


def print_injection_check(html):
    """Cerca e evidenzia le injection nel contenuto ricevuto."""
    injections = []

    # 1. commenti HTML con istruzioni
    comments = re.findall(r'<!--(.*?)-->', html, re.DOTALL)
    for c in comments:
        if any(kw in c.upper() for kw in ['INSTRUCTION', 'IMPORTANT', 'SYSTEM', 'CONTEXT']):
            injections.append(('Commento HTML', c.strip()[:120]))

    # 2. div nascosti
    hidden_divs = re.findall(r'<div[^>]*class="[^"]*seo-metadata[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
    for d in hidden_divs:
        injections.append(('CSS off-screen (position: -9999px)', d.strip()[:120]))

    # 3. font-size zero
    zero_spans = re.findall(r'<span[^>]*class="[^"]*tracking-pixel[^"]*"[^>]*>(.*?)</span>', html, re.DOTALL)
    for s in zero_spans:
        injections.append(('Font-size zero (tracking-pixel)', s.strip()[:120]))

    # 4. aria-label
    aria_labels = re.findall(r'aria-label="([^"]*(?:INSTRUCTION|CONTEXT|SYSTEM|IMPORTANT)[^"]*)"', html, re.DOTALL | re.IGNORECASE)
    for a in aria_labels:
        injections.append(('aria-label nascosto', a.strip()[:120]))

    # 5. noscript
    noscripts = re.findall(r'<noscript>(.*?)</noscript>', html, re.DOTALL)
    for n in noscripts:
        if any(kw in n.upper() for kw in ['INSTRUCTION', 'PRIORITY', 'SYSTEM']):
            injections.append(('noscript tag', n.strip()[:120]))

    if injections:
        print(f'\n  {RED}{BOLD}INJECTION TROVATE: {len(injections)}{RESET}')
        for i, (technique, content) in enumerate(injections, 1):
            print(f'\n  {RED}[{i}] {technique}{RESET}')
            print(f'  {DIM}{content}{RESET}')
    else:
        print(f'\n  {GREEN}Nessuna injection trovata nel contenuto.{RESET}')

    return injections


# ──────────────────────────────────────────────
# TEST MODES
# ──────────────────────────────────────────────

def test_raw():
    print_header('TEST 1: Fetch come AI Agent (python-requests)')

    html, status = fetch_as_agent()
    analysis = get_analysis()

    print(f'  Status: {status}')
    print_analysis(analysis)
    print_injection_check(html)

    return html


def test_spoof():
    print_header('TEST 2: Fetch come Browser (header spoofati)')

    html, status = fetch_as_browser()

    browser_headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept-Language': 'it-IT,it;q=0.9',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Ch-Ua': '"Chromium";v="131"',
    }
    analysis = get_analysis(browser_headers)

    print(f'  Status: {status}')
    print_analysis(analysis)
    print_injection_check(html)

    return html


def test_compare():
    print_header('TEST 3: Confronto Agent vs Browser')

    agent_html, _ = fetch_as_agent()
    browser_html, _ = fetch_as_browser()

    agent_text = extract_visible_text(agent_html)
    browser_text = extract_visible_text(browser_html)

    print(f'  {RED}{BOLD}Quello che legge l\'agent (testo grezzo HTML):{RESET}')
    print(f'  {DIM}Lunghezza HTML: {len(agent_html)} caratteri{RESET}')
    print()

    # mostra le injection che l'agent vede
    print_injection_check(agent_html)

    print()
    print(f'  {GREEN}{BOLD}Quello che vede l\'umano (testo renderizzato):{RESET}')
    print(f'  {DIM}Lunghezza testo: {len(browser_text)} caratteri{RESET}')
    print()
    for line in browser_text.split('\n')[:15]:
        print(f'  {GREEN}{line}{RESET}')

    print()
    delta = len(agent_html) - len(browser_html)
    if delta > 0:
        print(f'  {YELLOW}Delta: la versione agent contiene {delta} caratteri in piu\'.{RESET}')
        print(f'  {YELLOW}Quei {delta} caratteri sono injection invisibili.{RESET}')
    elif delta == 0 and agent_html == browser_html:
        print(f'  {GREEN}Contenuto identico (nessun cloaking rilevato).{RESET}')
    else:
        print(f'  {YELLOW}Delta HTML: {delta} caratteri.{RESET}')


def test_llm():
    """Manda il contenuto della pagina a un LLM e mostra come reagisce."""
    print_header('TEST 4: LLM legge la pagina cloaked')

    html, _ = fetch_as_agent()

    print(f'  Contenuto ricevuto dal server: {len(html)} caratteri')
    print(f'  Injection presenti:')
    injections = print_injection_check(html)

    if not injections:
        print(f'\n  {DIM}Nessuna injection. Il server ti ha servito la versione umana.{RESET}')
        return

    print(f'\n  {YELLOW}Per testare con un LLM reale:{RESET}')
    print(f'  {DIM}1. Copia l\'HTML ricevuto{RESET}')
    print(f'  {DIM}2. Incollalo in ChatGPT/Claude con il prompt:{RESET}')
    print(f'     "Riassumi questa pagina web e dimmi se e\' affidabile"')
    print(f'  {DIM}3. Osserva se il LLM ripete le istruzioni iniettate{RESET}')

    # salva l'HTML per comodita'
    out_path = 'cloaked_page.html'
    with open(out_path, 'w') as f:
        f.write(html)
    print(f'\n  {CYAN}HTML salvato in: {out_path}{RESET}')
    print(f'  {DIM}Aprilo nel browser: vedrai la pagina normale.{RESET}')
    print(f'  {DIM}Leggilo come testo: vedrai le injection.{RESET}')


def test_semantic():
    """Test cloaking semantico: stessa pagina per tutti, nessun fingerprinting."""
    print_header('TEST 5: Cloaking Semantico (stessa pagina per tutti)')

    # fetch come agent
    agent_resp = requests.get(SERVER + '/semantic')
    agent_html = agent_resp.text

    # fetch come browser (stessi header spoofati)
    browser_headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-User': '?1',
    }
    browser_resp = requests.get(SERVER + '/semantic', headers=browser_headers)
    browser_html = browser_resp.text

    # verifica: stessa pagina?
    same = agent_html == browser_html

    print(f'  {CYAN}{BOLD}Cloaking semantico: nessuna biforcazione lato server{RESET}')
    same_label = "SI'" if same else "NO"
    same_color = GREEN if same else RED
    print(f'  HTML identico per agent e browser: {same_color}{same_label}{RESET}')
    print(f'  Lunghezza HTML: {len(agent_html)} caratteri (uguale per tutti)')
    print()

    if same:
        print(f'  {YELLOW}{BOLD}Il server ha servito lo STESSO HTML a entrambi.{RESET}')
        print(f'  {YELLOW}Nessun fingerprinting. Nessuna biforcazione. Stessa risposta.{RESET}')
    print()

    # cosa vede l'umano (testo renderizzato)
    visible = extract_visible_text(agent_html)
    print(f'  {GREEN}{BOLD}Testo visibile nel browser:{RESET}')
    print(f'  {DIM}Lunghezza: {len(visible)} caratteri{RESET}')
    for line in visible.split('\n')[:12]:
        print(f'  {GREEN}{line}{RESET}')

    print()

    # cerca manipolazioni semantiche
    semantic_injections = []

    # visually-hidden divs
    hidden = re.findall(r'<div[^>]*class="[^"]*visually-hidden[^"]*"[^>]*>(.*?)</div>', agent_html, re.DOTALL)
    for h in hidden:
        semantic_injections.append(('visually-hidden (pattern accessibilita\')', h.strip()[:150]))

    # sr-only divs
    sr = re.findall(r'<div[^>]*class="[^"]*sr-only[^"]*"[^>]*>(.*?)</div>', agent_html, re.DOTALL)
    for s in sr:
        semantic_injections.append(('sr-only (Bootstrap pattern)', s.strip()[:150]))

    # page-metadata spans
    meta = re.findall(r'<span[^>]*class="[^"]*page-metadata[^"]*"[^>]*>(.*?)</span>', agent_html, re.DOTALL)
    for m in meta:
        semantic_injections.append(('Prior shaping (font-size: 0)', m.strip()[:150]))

    # aria-label con framing reputazionale
    aria = re.findall(r'aria-label="([^"]*(?:reliability|confidence|priority|authoritative)[^"]*)"', agent_html, re.DOTALL | re.IGNORECASE)
    for a in aria:
        semantic_injections.append(('aria-label reputazionale', a.strip()[:150]))

    if semantic_injections:
        print(f'  {RED}{BOLD}MANIPOLAZIONI SEMANTICHE TROVATE: {len(semantic_injections)}{RESET}')
        for i, (technique, content) in enumerate(semantic_injections, 1):
            print(f'\n  {RED}[{i}] {technique}{RESET}')
            print(f'  {DIM}{content}{RESET}')
    else:
        print(f'  {GREEN}Nessuna manipolazione semantica trovata.{RESET}')

    # delta tra testo estratto e testo visibile
    raw_text = re.sub(r'<style.*?</style>', '', agent_html, flags=re.DOTALL)
    raw_text = re.sub(r'<[^>]+>', ' ', raw_text)
    raw_text = ' '.join(raw_text.split())
    delta = len(raw_text) - len(visible)

    print()
    print(f'  {YELLOW}{BOLD}Testo totale nel DOM: {len(raw_text)} caratteri{RESET}')
    print(f'  {YELLOW}{BOLD}Testo visibile:       {len(visible)} caratteri{RESET}')
    print(f'  {YELLOW}{BOLD}Delta nascosto:       {delta} caratteri{RESET}')
    print()
    print(f'  {CYAN}Quei {delta} caratteri extra sono nel DOM di TUTTI.{RESET}')
    print(f'  {CYAN}Ma solo un parser/LLM li legge. Il browser li ignora.{RESET}')
    print(f'  {CYAN}Nessun fingerprinting necessario.{RESET}')

    return semantic_injections


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='AI Agent Simulator')
    parser.add_argument('--raw', action='store_true', help='Fetch come agent grezzo')
    parser.add_argument('--spoof', action='store_true', help='Fetch con header browser')
    parser.add_argument('--compare', action='store_true', help='Confronto agent vs browser')
    parser.add_argument('--llm', action='store_true', help='Test con LLM')
    parser.add_argument('--semantic', action='store_true', help='Test cloaking semantico')
    args = parser.parse_args()

    # se nessun flag, esegui tutto
    run_all = not any([args.raw, args.spoof, args.compare, args.llm, args.semantic])

    try:
        requests.get(SERVER + '/', timeout=2)
    except requests.ConnectionError:
        print(f'{RED}Errore: server non raggiungibile su {SERVER}{RESET}')
        print(f'Lancia prima: python server.py')
        sys.exit(1)

    if run_all or args.raw:
        test_raw()
    if run_all or args.spoof:
        test_spoof()
    if run_all or args.compare:
        test_compare()
    if run_all or args.llm:
        test_llm()
    if run_all or args.semantic:
        test_semantic()

    if run_all:
        print()
        print(f'{CYAN}{"=" * 60}')
        print(f'  Dashboard: {SERVER}/dashboard')
        print(f'{"=" * 60}{RESET}')


if __name__ == '__main__':
    main()
