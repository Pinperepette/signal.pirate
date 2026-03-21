#!/usr/bin/env python3
"""pypi_sentinel.py — Monitor real-time di pacchetti PyPI sospetti.

Polling del feed RSS di PyPI, download sorgente, analisi euristica + AI.
Rileva: exfiltration, exec/eval offuscati, reverse shell, typosquatting,
encoded payloads, import sospetti, C2 hardcoded.

Uso:
    python pypi_sentinel.py --live                  # monitor real-time
    python pypi_sentinel.py --live --ai             # con analisi AI (Ollama)
    python pypi_sentinel.py --test test_samples/    # testa su campioni locali
    python pypi_sentinel.py --test test_samples/ --ai  # campioni + AI
    python pypi_sentinel.py --check nome-pacchetto  # analizza singolo pacchetto
"""
from __future__ import annotations

import argparse
import ast
import io
import json
import os
import re
import sys
import tarfile
import tempfile
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from xml.etree import ElementTree

# ══════════════════════════════════════════════════════════════════════════
#  CONFIGURAZIONE
# ══════════════════════════════════════════════════════════════════════════

PYPI_RSS_NEW = 'https://pypi.org/rss/packages.xml'
PYPI_RSS_UPD = 'https://pypi.org/rss/updates.xml'
PYPI_JSON = 'https://pypi.org/pypi/{}/json'
POLL_INTERVAL = 60  # secondi tra i poll

# Top pacchetti PyPI per check typosquatting (subset)
TOP_PACKAGES = [
    'requests', 'numpy', 'pandas', 'flask', 'django', 'boto3', 'urllib3',
    'setuptools', 'pip', 'wheel', 'six', 'pyyaml', 'cryptography',
    'colorama', 'pillow', 'scipy', 'matplotlib', 'sqlalchemy', 'jinja2',
    'click', 'pytest', 'sphinx', 'tqdm', 'beautifulsoup4', 'lxml',
    'paramiko', 'psutil', 'celery', 'redis', 'fastapi', 'uvicorn',
    'pydantic', 'httpx', 'aiohttp', 'scrapy', 'tensorflow', 'torch',
    'transformers', 'scikit-learn', 'keras', 'opencv-python', 'black',
    'mypy', 'ruff', 'isort', 'flake8', 'pylint', 'bandit', 'coverage',
    'docker', 'kubernetes', 'ansible', 'fabric', 'invoke', 'poetry',
    'python-dateutil', 'pytz', 'certifi', 'charset-normalizer', 'idna',
    'packaging', 'attrs', 'more-itertools', 'pluggy', 'importlib-metadata',
    'zipp', 'tomli', 'exceptiongroup', 'iniconfig', 'platformdirs',
    'filelock', 'virtualenv', 'distlib', 'pygments', 'rich', 'typer',
    'httptools', 'websockets', 'starlette', 'anyio', 'sniffio',
    'protobuf', 'grpcio', 'google-api-core', 'google-auth', 'pyarrow',
    'polars', 'dask', 'joblib', 'threadpoolctl', 'sympy', 'networkx',
    'jsonschema', 'referencing', 'rpds-py', 'cffi', 'pycparser',
    'markupsafe', 'werkzeug', 'itsdangerous', 'blinker', 'gunicorn',
    'psycopg2', 'pymysql', 'sqlparse', 'alembic', 'mako',
]

# ══════════════════════════════════════════════════════════════════════════
#  REGOLE EURISTICHE (ispirate a guarddog + ossf)
# ══════════════════════════════════════════════════════════════════════════

RULES = {
    # Pattern → (nome_regola, peso, descrizione)
    r'\bexec\s*\(': ('exec-call', 25, 'Chiamata exec() — esecuzione codice dinamico'),
    r'\beval\s*\(': ('eval-call', 25, 'Chiamata eval() — valutazione dinamica'),
    r'base64\.b64decode': ('base64-decode', 30, 'Decodifica base64 — possibile payload offuscato'),
    r'codecs\.decode\s*\(.+["\']hex["\']': ('hex-decode', 30, 'Decodifica hex — payload offuscato'),
    r'\bos\.system\s*\(': ('os-system', 20, 'os.system() — esecuzione comando shell'),
    r'\bos\.popen\s*\(': ('os-popen', 20, 'os.popen() — esecuzione comando shell'),
    r'subprocess\.(run|Popen|call|check_output|check_call)\s*\(': ('subprocess', 15, 'subprocess — esecuzione processo'),
    r'socket\.(socket|create_connection)\s*\(': ('socket-create', 20, 'Creazione socket — possibile C2/reverse shell'),
    r'os\.environ': ('env-access', 15, 'Accesso variabili d\'ambiente — possibile esfiltrazione'),
    r'os\.getlogin|getpass\.getuser|socket\.gethostname|platform\.platform': ('sysinfo-collect', 15, 'Raccolta info sistema'),
    r'https?://(?!github\.com|pypi\.org|docs\.python\.org|readthedocs\.io|python\.org|apache\.org|opensource\.org|creativecommons\.org|peps\.python\.org|packaging\.python\.org|docs\.astropy\.org|codeberg\.org|sourceforge\.net|effbot\.org|algorithmic-solutions\.com|segment\.com|pint\.readthedocs\.io)[^\s"\'<>]+': ('hardcoded-url', 10, 'URL hardcoded — possibile C2'),
    r'\\x[0-9a-f]{2}': ('hex-escape', 10, 'Hex escape — possibile shellcode offuscato'),
    r'__import__\s*\(': ('dynamic-import', 20, '__import__() — import dinamico'),
    r'compile\s*\(.+exec': ('compile-exec', 25, 'compile()+exec — esecuzione codice generato'),
    r'urllib\.request\.urlopen|requests\.(get|post)\s*\(|http\.client': ('network-call', 15, 'Chiamata di rete in setup.py'),
    r'shutil\.(copy|move|rmtree)': ('file-manipulation', 10, 'Manipolazione filesystem'),
    r'cmdclass\s*[=:]': ('custom-cmdclass', 10, 'cmdclass custom — possibile install hook'),
    r'/bin/sh|/bin/bash|cmd\.exe': ('shell-reference', 20, 'Riferimento a shell — possibile RCE'),
    r'dup2\s*\(': ('fd-redirect', 25, 'File descriptor redirect — pattern reverse shell'),
    r'SOCK_STREAM.*connect': ('socket-connect', 25, 'Socket connect — pattern reverse shell'),
}

# Nomi pacchetti PyPI esplicitamente sospetti (pattern nei nomi)
SUSPICIOUS_NAME_PATTERNS = [
    r'^python[0-9]*-',       # python3-requests (impersonation)
    r'-python$',             # requests-python
    r'^py-[a-z]+-',          # py-something-extra
    r'[0-9]{5,}',           # numeri lunghi casuali
    r'(test|debug|dev|tmp|temp|hack|exploit|payload|shell|backdoor|trojan|rat|keylog|stealer)',
]

# ══════════════════════════════════════════════════════════════════════════
#  LEVENSHTEIN DISTANCE
# ══════════════════════════════════════════════════════════════════════════

def levenshtein(s1: str, s2: str) -> int:
    """Calcola distanza di Levenshtein tra due stringhe."""
    if len(s1) < len(s2):
        return levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            curr.append(min(
                prev[j + 1] + 1,
                curr[j] + 1,
                prev[j] + (0 if c1 == c2 else 1)
            ))
        prev = curr
    return prev[-1]


def check_typosquatting(name: str) -> list:
    """Controlla se il nome è simile a un pacchetto top (Levenshtein ≤ 2)."""
    name_clean = name.lower().replace('-', '').replace('_', '')
    matches = []
    for top in TOP_PACKAGES:
        top_clean = top.lower().replace('-', '').replace('_', '')
        if name_clean == top_clean:
            continue  # è lo stesso pacchetto
        dist = levenshtein(name_clean, top_clean)
        if dist <= 2 and dist > 0:
            matches.append((top, dist))
    return sorted(matches, key=lambda x: x[1])


# ══════════════════════════════════════════════════════════════════════════
#  ANALISI AST
# ══════════════════════════════════════════════════════════════════════════

def ast_analyze(source: str) -> list:
    """Analisi AST per pattern sospetti non catturabili con regex."""
    findings = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return findings

    for node in ast.walk(tree):
        # exec() con base64
        if isinstance(node, ast.Call):
            name = ''
            if isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr

            if name == 'exec' and node.args:
                # exec(base64.b64decode(...))
                arg = node.args[0]
                if isinstance(arg, ast.Call):
                    inner = ''
                    if isinstance(arg.func, ast.Attribute):
                        inner = arg.func.attr
                    if inner == 'b64decode':
                        findings.append(('exec-base64', 40,
                            f'L{node.lineno}: exec(base64.b64decode(...)) — payload offuscato'))

        # Stringhe molto lunghe (possibili payload encoded)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if len(node.value) > 200 and re.search(r'[0-9a-f]{50,}', node.value):
                findings.append(('long-hex-string', 20,
                    f'L{node.lineno}: stringa hex lunga ({len(node.value)} chars) — possibile payload'))
            if len(node.value) > 100:
                # Check if it's base64
                import string
                b64_chars = set(string.ascii_letters + string.digits + '+/=')
                if all(c in b64_chars for c in node.value.replace('\n', '')):
                    findings.append(('long-base64-string', 15,
                        f'L{node.lineno}: stringa base64 lunga ({len(node.value)} chars)'))

    return findings


# ══════════════════════════════════════════════════════════════════════════
#  ANALISI AI (Ollama)
# ══════════════════════════════════════════════════════════════════════════

def ai_analyze(source: str, filename: str, model: str = 'mistral') -> dict | None:
    """Analizza codice sorgente con LLM locale via Ollama."""
    prompt = f"""Sei un analista di sicurezza specializzato in supply chain attacks su PyPI.
Analizza questo file Python e rispondi SOLO in JSON con questa struttura:
{{"malicious": true/false, "confidence": 0-100, "reasons": ["motivo1", "motivo2"]}}

Cerca specificamente:
- Esfiltrazione di credenziali o variabili d'ambiente
- Reverse shell o connessioni a server C2
- Payload offuscati (base64, hex, exec/eval)
- Typosquatting (nome simile a pacchetto popolare)
- Download ed esecuzione di binari
- Hook su install/setup che eseguono codice

File: {filename}
```python
{source[:3000]}
```

Rispondi SOLO con il JSON, niente altro."""

    try:
        import json as _json
        req_data = _json.dumps({
            'model': model,
            'prompt': prompt,
            'stream': False,
            'options': {'temperature': 0.1, 'num_predict': 300}
        }).encode()

        req = Request(
            'http://localhost:11434/api/generate',
            data=req_data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        with urlopen(req, timeout=60) as resp:
            result = _json.loads(resp.read())
            response_text = result.get('response', '')

            # Estrai JSON dalla risposta
            json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                return _json.loads(json_match.group())
    except (HTTPError, URLError):
        return None
    except Exception:
        return None

    return None


# ══════════════════════════════════════════════════════════════════════════
#  ANALISI COMPLETA DI UN PACCHETTO
# ══════════════════════════════════════════════════════════════════════════

def analyze_source(source: str, filename: str = 'setup.py') -> dict:
    """Analizza un singolo file sorgente con tutte le euristiche."""
    findings = []
    score = 0

    # 1. Regex rules
    for pattern, (name, weight, desc) in RULES.items():
        matches = list(re.finditer(pattern, source, re.IGNORECASE))
        if matches:
            for m in matches[:3]:  # max 3 match per regola
                line_num = source[:m.start()].count('\n') + 1
                findings.append({
                    'rule': name,
                    'weight': weight,
                    'description': f'L{line_num}: {desc}',
                    'match': m.group()[:60],
                })
                score += weight

    # 2. AST analysis
    ast_findings = ast_analyze(source)
    for name, weight, desc in ast_findings:
        findings.append({
            'rule': name,
            'weight': weight,
            'description': desc,
            'match': '',
        })
        score += weight

    # Cap score a 100
    score = min(score, 100)

    return {
        'filename': filename,
        'score': score,
        'findings': findings,
    }


def analyze_package_dir(pkg_dir: Path, use_ai: bool = False, ai_model: str = 'mistral') -> dict:
    """Analizza tutti i file Python in una directory di pacchetto."""
    target_files = ['setup.py', '__init__.py', 'setup.cfg', '__main__.py']
    results = {
        'package_dir': str(pkg_dir),
        'files': [],
        'total_score': 0,
        'ai_result': None,
    }

    # Cerca file target
    for fname in target_files:
        fpath = pkg_dir / fname
        if fpath.exists():
            source = fpath.read_text(errors='ignore')
            analysis = analyze_source(source, fname)
            results['files'].append(analysis)
            results['total_score'] += analysis['score']

    # Cerca anche in sottodirectory (un livello)
    for subdir in pkg_dir.iterdir():
        if subdir.is_dir() and not subdir.name.startswith('.'):
            for fname in ['__init__.py', '__main__.py']:
                fpath = subdir / fname
                if fpath.exists():
                    source = fpath.read_text(errors='ignore')
                    analysis = analyze_source(source, f'{subdir.name}/{fname}')
                    results['files'].append(analysis)
                    results['total_score'] += analysis['score']

    results['total_score'] = min(results['total_score'], 100)

    # AI analysis (sul file più sospetto)
    if use_ai and results['files']:
        most_suspicious = max(results['files'], key=lambda x: x['score'])
        fpath = pkg_dir / most_suspicious['filename']
        if fpath.exists():
            source = fpath.read_text(errors='ignore')
            results['ai_result'] = ai_analyze(source, most_suspicious['filename'], ai_model)

    return results


# ══════════════════════════════════════════════════════════════════════════
#  DOWNLOAD PACCHETTO DA PyPI
# ══════════════════════════════════════════════════════════════════════════

def download_and_extract(pkg_name: str, tmp_dir: str) -> Path | None:
    """Scarica sdist da PyPI e lo estrae in tmp_dir."""
    try:
        url = PYPI_JSON.format(pkg_name)
        req = Request(url, headers={'Accept': 'application/json'})
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())

        # Cerca sdist (tar.gz o zip)
        urls = data.get('urls', [])
        sdist = None
        for u in urls:
            if u.get('packagetype') == 'sdist':
                sdist = u
                break

        if not sdist:
            return None

        dl_url = sdist['url']
        fname = sdist['filename']

        # Download
        with urlopen(Request(dl_url), timeout=30) as resp:
            content = resp.read()

        extract_dir = Path(tmp_dir) / pkg_name
        extract_dir.mkdir(exist_ok=True)

        if fname.endswith('.tar.gz') or fname.endswith('.tgz'):
            with tarfile.open(fileobj=io.BytesIO(content), mode='r:gz') as tar:
                # Sicurezza: filtra path traversal
                safe_members = []
                for m in tar.getmembers():
                    if m.name.startswith('/') or '..' in m.name:
                        continue
                    safe_members.append(m)
                tar.extractall(path=str(extract_dir), members=safe_members)
        elif fname.endswith('.zip'):
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                for info in zf.infolist():
                    if info.filename.startswith('/') or '..' in info.filename:
                        continue
                    zf.extract(info, str(extract_dir))

        # Trova la directory del pacchetto (spesso nome-versione/)
        subdirs = [d for d in extract_dir.iterdir() if d.is_dir()]
        if subdirs:
            return subdirs[0]
        return extract_dir

    except (HTTPError, URLError, json.JSONDecodeError, tarfile.TarError) as e:
        print(f'    Errore download {pkg_name}: {e}')
        return None


# ══════════════════════════════════════════════════════════════════════════
#  FEED RSS
# ══════════════════════════════════════════════════════════════════════════

def fetch_rss(url: str) -> list:
    """Fetch e parse del feed RSS PyPI."""
    try:
        req = Request(url, headers={'Accept': 'application/xml'})
        with urlopen(req, timeout=15) as resp:
            tree = ElementTree.parse(resp)

        items = []
        for item in tree.findall('.//item'):
            title_el = item.find('title')
            link_el = item.find('link')
            desc_el = item.find('description')
            date_el = item.find('pubDate')

            title = title_el.text if title_el is not None else ''
            # "packagename added to PyPI" → estrai nome
            name = title.replace(' added to PyPI', '').replace(' updated on PyPI', '').strip()

            items.append({
                'name': name,
                'link': link_el.text if link_el is not None else '',
                'description': desc_el.text if desc_el is not None else '',
                'date': date_el.text if date_el is not None else '',
            })
        return items
    except (HTTPError, URLError, ElementTree.ParseError) as e:
        print(f'  Errore fetch RSS: {e}')
        return []


# ══════════════════════════════════════════════════════════════════════════
#  OUTPUT / REPORT
# ══════════════════════════════════════════════════════════════════════════

def severity_color(score: int) -> str:
    if score >= 60:
        return '\033[91m'   # rosso
    elif score >= 30:
        return '\033[93m'   # giallo
    elif score >= 10:
        return '\033[33m'   # arancione
    return '\033[92m'       # verde


def severity_label(score: int) -> str:
    if score >= 60:
        return 'CRITICAL'
    elif score >= 30:
        return 'HIGH'
    elif score >= 10:
        return 'MEDIUM'
    return 'CLEAN'


def print_report(pkg_name: str, results: dict, typo_matches: list = None):
    """Stampa report di analisi per un pacchetto."""
    score = results['total_score']
    color = severity_color(score)
    label = severity_label(score)
    reset = '\033[0m'

    print(f'\n  {color}{"━" * 58}{reset}')
    print(f'  {color}[{label:8s}]{reset}  {pkg_name}  (score: {score}/100)')
    print(f'  {color}{"━" * 58}{reset}')

    # Typosquatting matches
    if typo_matches:
        print(f'  \033[93m⚠ TYPOSQUATTING:\033[0m')
        for top_name, dist in typo_matches:
            print(f'    → simile a "{top_name}" (distanza: {dist})')

    # File findings
    for file_result in results['files']:
        if file_result['findings']:
            print(f'\n  📄 {file_result["filename"]}:')
            for f in file_result['findings']:
                w_color = '\033[91m' if f['weight'] >= 25 else '\033[93m' if f['weight'] >= 15 else '\033[33m'
                print(f'    {w_color}[{f["weight"]:2d}]{reset} {f["rule"]:20s} {f["description"]}')
                if f['match']:
                    print(f'        match: {f["match"]}')

    # AI result
    ai = results.get('ai_result')
    if ai:
        ai_color = '\033[91m' if ai.get('malicious') else '\033[92m'
        print(f'\n  🤖 AI Analysis ({ai_color}{"MALICIOUS" if ai.get("malicious") else "CLEAN"}{reset}, '
              f'confidence: {ai.get("confidence", "?")}%):')
        for reason in ai.get('reasons', []):
            print(f'     • {reason}')

    if score == 0 and not typo_matches:
        print(f'  \033[92m✓ Nessun pattern sospetto rilevato\033[0m')

    print()


# ══════════════════════════════════════════════════════════════════════════
#  MODALITÀ TEST (campioni locali)
# ══════════════════════════════════════════════════════════════════════════

def run_test(test_dir: Path, use_ai: bool = False, ai_model: str = 'mistral'):
    """Analizza campioni locali in una directory di test."""
    print(f'\n{"=" * 60}')
    print(f'  🔬 PyPI Sentinel — Modalità TEST')
    print(f'  Directory: {test_dir}')
    print(f'  AI: {"ON (" + ai_model + ")" if use_ai else "OFF"}')
    print(f'{"=" * 60}')

    sample_dirs = sorted([d for d in test_dir.iterdir() if d.is_dir() and not d.name.startswith('.')])

    if not sample_dirs:
        print('  Nessun campione trovato.')
        return

    stats = {'total': 0, 'critical': 0, 'high': 0, 'medium': 0, 'clean': 0}

    for sample_dir in sample_dirs:
        pkg_name = sample_dir.name
        results = analyze_package_dir(sample_dir, use_ai=use_ai, ai_model=ai_model)
        typo_matches = check_typosquatting(pkg_name)
        print_report(pkg_name, results, typo_matches)

        stats['total'] += 1
        label = severity_label(results['total_score'])
        if label == 'CRITICAL':
            stats['critical'] += 1
        elif label == 'HIGH':
            stats['high'] += 1
        elif label == 'MEDIUM':
            stats['medium'] += 1
        else:
            stats['clean'] += 1

    print(f'{"=" * 60}')
    print(f'  Campioni analizzati: {stats["total"]}')
    print(f'  \033[91mCRITICAL: {stats["critical"]}\033[0m  '
          f'\033[93mHIGH: {stats["high"]}\033[0m  '
          f'\033[33mMEDIUM: {stats["medium"]}\033[0m  '
          f'\033[92mCLEAN: {stats["clean"]}\033[0m')
    print(f'{"=" * 60}')


# ══════════════════════════════════════════════════════════════════════════
#  MODALITÀ CHECK (singolo pacchetto)
# ══════════════════════════════════════════════════════════════════════════

def run_check(pkg_name: str, use_ai: bool = False, ai_model: str = 'mistral'):
    """Analizza un singolo pacchetto PyPI."""
    print(f'\n{"=" * 60}')
    print(f'  🔍 PyPI Sentinel — Check: {pkg_name}')
    print(f'{"=" * 60}')

    typo_matches = check_typosquatting(pkg_name)

    with tempfile.TemporaryDirectory() as tmp:
        print(f'  Downloading {pkg_name}...')
        pkg_dir = download_and_extract(pkg_name, tmp)
        if not pkg_dir:
            print(f'  ✗ Impossibile scaricare {pkg_name}')
            return

        results = analyze_package_dir(pkg_dir, use_ai=use_ai, ai_model=ai_model)
        print_report(pkg_name, results, typo_matches)


# ══════════════════════════════════════════════════════════════════════════
#  MODALITÀ LIVE (monitor real-time)
# ══════════════════════════════════════════════════════════════════════════

def run_live(use_ai: bool = False, ai_model: str = 'mistral', interval: int = POLL_INTERVAL,
             threshold: int = 0):
    """Monitor real-time del feed RSS PyPI."""
    print(f'\n{"=" * 60}')
    print(f'  📡 PyPI Sentinel — Monitor LIVE')
    print(f'  Intervallo: {interval}s')
    print(f'  Soglia alert: {threshold}')
    print(f'  AI: {"ON (" + ai_model + ")" if use_ai else "OFF"}')
    print(f'  Ctrl+C per uscire')
    print(f'{"=" * 60}')

    seen = set()
    total_scanned = 0
    total_alerts = 0
    log_path = Path('sentinel_log.jsonl')

    while True:
        try:
            now = datetime.now().strftime('%H:%M:%S')
            print(f'\n  [{now}] Fetching PyPI RSS...')

            items = fetch_rss(PYPI_RSS_NEW)
            new_items = [i for i in items if i['name'] not in seen]

            if not new_items:
                print(f'  Nessun pacchetto nuovo. (visti: {len(seen)})')
            else:
                print(f'  {len(new_items)} nuovi pacchetti da analizzare')

                for item in new_items:
                    seen.add(item['name'])
                    total_scanned += 1
                    pkg_name = item['name']

                    # Quick checks prima del download
                    typo_matches = check_typosquatting(pkg_name)
                    name_suspicious = any(
                        re.search(p, pkg_name.lower())
                        for p in SUSPICIOUS_NAME_PATTERNS
                    )

                    # Se il nome è pulito e nessun typosquatting, skip download
                    if not typo_matches and not name_suspicious and threshold > 10:
                        print(f'  ○ {pkg_name:40s} [skip — nome pulito]')
                        continue

                    # Download e analisi
                    with tempfile.TemporaryDirectory() as tmp:
                        pkg_dir = download_and_extract(pkg_name, tmp)
                        if not pkg_dir:
                            print(f'  ○ {pkg_name:40s} [no sdist]')
                            continue

                        # Analisi AI solo se score euristico > 20
                        results = analyze_package_dir(pkg_dir, use_ai=False)
                        if use_ai and results['total_score'] >= 20:
                            results = analyze_package_dir(pkg_dir, use_ai=True, ai_model=ai_model)

                        score = results['total_score']

                        if score >= threshold:
                            print_report(pkg_name, results, typo_matches)
                            total_alerts += 1

                            # Log su file
                            log_entry = {
                                'timestamp': datetime.now().isoformat(),
                                'package': pkg_name,
                                'score': score,
                                'severity': severity_label(score),
                                'typosquatting': [(n, d) for n, d in typo_matches],
                                'findings': [f['rule'] for file_r in results['files'] for f in file_r['findings']],
                                'ai': results.get('ai_result'),
                            }
                            with open(log_path, 'a') as lf:
                                lf.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
                        else:
                            color = severity_color(score)
                            reset = '\033[0m'
                            print(f'  {color}●{reset} {pkg_name:40s} [score: {score}]')

            # Stats periodiche
            print(f'  ─── scansionati: {total_scanned} | alert: {total_alerts} | visti: {len(seen)} ───')

            time.sleep(interval)

        except KeyboardInterrupt:
            print(f'\n\n{"=" * 60}')
            print(f'  Sentinel fermato.')
            print(f'  Pacchetti scansionati: {total_scanned}')
            print(f'  Alert generati: {total_alerts}')
            if log_path.exists():
                print(f'  Log: {log_path}')
            print(f'{"=" * 60}')
            break


# ══════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='PyPI Sentinel — monitor real-time pacchetti sospetti',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  %(prog)s --test test_samples/              # testa su campioni locali
  %(prog)s --test test_samples/ --ai         # campioni + analisi AI
  %(prog)s --check requests                  # analizza singolo pacchetto
  %(prog)s --live                            # monitor real-time
  %(prog)s --live --ai --interval 30         # live + AI ogni 30s
  %(prog)s --live --threshold 20             # alert solo se score >= 20
        """)

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--test', type=Path, metavar='DIR', help='Analizza campioni locali')
    mode.add_argument('--check', type=str, metavar='PKG', help='Analizza singolo pacchetto PyPI')
    mode.add_argument('--live', action='store_true', help='Monitor real-time feed RSS')

    parser.add_argument('--ai', action='store_true', help='Abilita analisi AI via Ollama')
    parser.add_argument('--model', default='mistral', help='Modello Ollama (default: mistral)')
    parser.add_argument('--interval', type=int, default=POLL_INTERVAL, help='Intervallo polling in secondi')
    parser.add_argument('--threshold', type=int, default=0, help='Score minimo per alert (0-100)')

    args = parser.parse_args()

    if args.test:
        if not args.test.exists():
            print(f'Directory non trovata: {args.test}')
            sys.exit(1)
        run_test(args.test, use_ai=args.ai, ai_model=args.model)
    elif args.check:
        run_check(args.check, use_ai=args.ai, ai_model=args.model)
    elif args.live:
        run_live(use_ai=args.ai, ai_model=args.model,
                 interval=args.interval, threshold=args.threshold)
