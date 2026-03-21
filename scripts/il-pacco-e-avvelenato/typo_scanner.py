#!/usr/bin/env python3
from __future__ import annotations
"""typo_scanner.py — Genera varianti typosquatting e verifica disponibilità su PyPI/npm.

Tecniche: trasposizione, sostituzione, omissione, inserzione, homoglyph.
Per ogni variante controlla se esiste già su PyPI (e opzionalmente npm).

Uso:
    python typo_scanner.py requests flask numpy
    python typo_scanner.py --npm lodash express
"""
import argparse
import itertools
import json
import sys
import time
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

# ── Homoglyph map (ASCII → visually similar Unicode) ──────────────────────
HOMOGLYPHS = {
    'a': ['а'],       # cyrillic а
    'c': ['с'],       # cyrillic с
    'e': ['е'],       # cyrillic е
    'o': ['о'],       # cyrillic о
    'p': ['р'],       # cyrillic р
    'x': ['х'],       # cyrillic х
    's': ['ѕ'],       # cyrillic ѕ
    'i': ['і'],       # cyrillic і
}

KEYBOARD_NEIGHBORS = {
    'q': 'wa', 'w': 'qeas', 'e': 'wrds', 'r': 'etdf', 't': 'ryfg',
    'y': 'tugh', 'u': 'yijh', 'i': 'uojk', 'o': 'iplk', 'p': 'ol',
    'a': 'qwsz', 's': 'awedxz', 'd': 'serfcx', 'f': 'drtgvc',
    'g': 'ftyhbv', 'h': 'gyujnb', 'j': 'huiknm', 'k': 'jiolm',
    'l': 'kop', 'z': 'asx', 'x': 'zsdc', 'c': 'xdfv', 'v': 'cfgb',
    'b': 'vghn', 'n': 'bhjm', 'm': 'njk',
}


def generate_variants(name: str) -> set:
    """Genera varianti Levenshtein-1 + homoglyph di un nome pacchetto."""
    variants = set()
    chars = list(name)
    n = len(chars)

    # 1. Trasposizione di caratteri adiacenti
    for i in range(n - 1):
        v = chars[:]
        v[i], v[i + 1] = v[i + 1], v[i]
        variants.add(''.join(v))

    # 2. Omissione di un carattere
    for i in range(n):
        variants.add(name[:i] + name[i + 1:])

    # 3. Inserzione di un carattere (solo lettere adiacenti sulla tastiera)
    for i in range(n + 1):
        if i > 0 and name[i - 1] in KEYBOARD_NEIGHBORS:
            for c in KEYBOARD_NEIGHBORS[name[i - 1]]:
                variants.add(name[:i] + c + name[i:])

    # 4. Sostituzione con tasti adiacenti
    for i in range(n):
        if chars[i] in KEYBOARD_NEIGHBORS:
            for c in KEYBOARD_NEIGHBORS[chars[i]]:
                variants.add(name[:i] + c + name[i + 1:])

    # 5. Homoglyph
    for i in range(n):
        if chars[i] in HOMOGLYPHS:
            for h in HOMOGLYPHS[chars[i]]:
                variants.add(name[:i] + h + name[i + 1:])

    # 6. Separatore: aggiunta/rimozione di trattini
    if '-' in name:
        variants.add(name.replace('-', ''))
        variants.add(name.replace('-', '_'))
    if '_' in name:
        variants.add(name.replace('_', '-'))
        variants.add(name.replace('_', ''))

    variants.discard(name)
    return variants


def check_pypi(pkg: str) -> dict | None:
    """Controlla se un pacchetto esiste su PyPI. Ritorna metadata o None."""
    # Skip nomi con caratteri non-ASCII (homoglyph) — PyPI non li accetta
    try:
        pkg.encode('ascii')
    except UnicodeEncodeError:
        return None
    url = f'https://pypi.org/pypi/{pkg}/json'
    req = Request(url, headers={'Accept': 'application/json'})
    try:
        with urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
            info = data.get('info', {})
            return {
                'name': info.get('name', pkg),
                'version': info.get('version', '?'),
                'summary': (info.get('summary') or '')[:80],
            }
    except (HTTPError, URLError, json.JSONDecodeError, UnicodeEncodeError):
        return None


def check_npm(pkg: str) -> dict | None:
    """Controlla se un pacchetto esiste su npm. Ritorna metadata o None."""
    url = f'https://registry.npmjs.org/{pkg}'
    req = Request(url, headers={'Accept': 'application/json'})
    try:
        with urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
            latest = data.get('dist-tags', {}).get('latest', '?')
            desc = (data.get('description') or '')[:80]
            return {'name': data.get('name', pkg), 'version': latest, 'summary': desc}
    except (HTTPError, URLError, json.JSONDecodeError):
        return None


def scan(packages: list, registry: str = 'pypi', delay: float = 0.3):
    """Scansiona varianti typosquatting per una lista di pacchetti."""
    check_fn = check_pypi if registry == 'pypi' else check_npm
    total_found = 0

    for pkg in packages:
        variants = generate_variants(pkg)
        print(f'\n{"=" * 60}')
        print(f'  {pkg}  →  {len(variants)} varianti generate')
        print(f'{"=" * 60}')

        found = []
        for i, v in enumerate(sorted(variants), 1):
            time.sleep(delay)
            result = check_fn(v)
            status = f'\033[91mEXISTS\033[0m' if result else '\033[92mavailable\033[0m'
            print(f'  [{i:3d}/{len(variants)}] {v:30s} {status}', end='')
            if result:
                print(f'  → {result["name"]} {result["version"]}')
                found.append({**result, 'typo_variant': v})
            else:
                print()

        if found:
            print(f'\n  ⚠  {len(found)} varianti ESISTONO su {registry}:')
            for f in found:
                print(f'     • {f["typo_variant"]} → {f["name"]} v{f["version"]}')
                if f['summary']:
                    print(f'       "{f["summary"]}"')
            total_found += len(found)
        else:
            print(f'\n  ✓  Nessuna variante trovata su {registry}')

    print(f'\n{"=" * 60}')
    print(f'  TOTALE: {total_found} varianti typosquatting trovate su {registry}')
    print(f'{"=" * 60}')
    return total_found


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Typosquatting scanner per PyPI/npm')
    parser.add_argument('packages', nargs='+', help='Nomi pacchetti da analizzare')
    parser.add_argument('--npm', action='store_true', help='Controlla npm invece di PyPI')
    parser.add_argument('--delay', type=float, default=0.3, help='Delay tra richieste (sec)')
    args = parser.parse_args()

    registry = 'npm' if args.npm else 'pypi'
    scan(args.packages, registry=registry, delay=args.delay)
