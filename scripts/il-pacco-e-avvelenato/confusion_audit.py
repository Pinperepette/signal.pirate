#!/usr/bin/env python3
from __future__ import annotations
"""confusion_audit.py — Identifica pacchetti interni vulnerabili a dependency confusion.

Legge requirements.txt / setup.cfg / pyproject.toml, filtra per prefissi aziendali,
e controlla se quei nomi sono già registrati su PyPI pubblico.
Se non lo sono → qualcuno potrebbe registrarli e ottenere esecuzione di codice.

Uso:
    python confusion_audit.py requirements.txt --prefixes acme- mycompany- internal-
    python confusion_audit.py pyproject.toml
"""
import argparse
import json
import re
import sys
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError


def extract_from_requirements(content: str) -> list:
    """Estrae nomi pacchetti da requirements.txt."""
    pkgs = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('-'):
            continue
        name = re.split(r'[=<>!~\[]', line)[0].strip()
        if name:
            pkgs.append(name)
    return pkgs


def extract_from_pyproject(content: str) -> list:
    """Estrae dipendenze da pyproject.toml (best effort, senza toml parser)."""
    pkgs = []
    in_deps = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped in ('dependencies = [', 'install_requires = ['):
            in_deps = True
            continue
        if in_deps:
            if stripped == ']':
                in_deps = False
                continue
            match = re.match(r'["\']([a-zA-Z0-9_-]+)', stripped)
            if match:
                pkgs.append(match.group(1))
    return pkgs


def extract_packages(filepath: Path) -> list:
    """Estrae pacchetti da file di dipendenze."""
    content = filepath.read_text(errors='ignore')
    name = filepath.name.lower()

    if name == 'requirements.txt' or name.endswith('.txt'):
        return extract_from_requirements(content)
    elif name == 'pyproject.toml':
        return extract_from_pyproject(content)
    elif name == 'setup.cfg':
        return extract_from_requirements(content)
    else:
        # fallback: tratta come requirements.txt
        return extract_from_requirements(content)


def check_pypi(pkg: str) -> bool:
    """Ritorna True se il pacchetto esiste su PyPI."""
    url = f'https://pypi.org/pypi/{pkg}/json'
    try:
        req = Request(url, headers={'Accept': 'application/json'})
        with urlopen(req, timeout=8) as resp:
            return resp.status == 200
    except (HTTPError, URLError):
        return False


def audit(filepath: Path, prefixes: list, check_all: bool = False):
    """Analizza file dipendenze per dependency confusion."""
    packages = extract_packages(filepath)
    if not packages:
        print(f'Nessun pacchetto trovato in {filepath}')
        return []

    print(f'\n{"=" * 60}')
    print(f'  Dependency Confusion Audit')
    print(f'  File: {filepath}')
    print(f'  Pacchetti trovati: {len(packages)}')
    print(f'  Prefissi interni: {", ".join(prefixes) if prefixes else "(tutti)"}')
    print(f'{"=" * 60}\n')

    # Filtra per prefissi se specificati
    if prefixes and not check_all:
        candidates = [p for p in packages if any(p.startswith(pfx) for pfx in prefixes)]
    else:
        candidates = packages

    if not candidates:
        print('  Nessun pacchetto con prefisso interno trovato.')
        return []

    vulnerable = []
    for pkg in candidates:
        exists = check_pypi(pkg)
        if exists:
            print(f'  ✓  {pkg:40s} EXISTS on PyPI (safe)')
        else:
            print(f'  ✗  {pkg:40s} \033[91mNOT on PyPI ← VULNERABLE\033[0m')
            vulnerable.append(pkg)

    print(f'\n{"=" * 60}')
    if vulnerable:
        print(f'  ⚠  {len(vulnerable)} pacchetti vulnerabili a dependency confusion:')
        for v in vulnerable:
            print(f'     • {v}')
        print(f'\n  Rischio: un attaccante può registrare questi nomi su PyPI')
        print(f'  con versione alta e ottenere esecuzione di codice.')
        print(f'\n  Fix:')
        print(f'    1. Registrare i nomi su PyPI come placeholder')
        print(f'    2. Usare --index-url (solo registro privato)')
        print(f'    3. Artifactory: configurare priority-resolution')
        print(f'    4. pip: usare --extra-index-url con cautela')
    else:
        print(f'  ✓  Tutti i pacchetti interni sono registrati su PyPI')
    print(f'{"=" * 60}')

    return vulnerable


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Dependency confusion auditor')
    parser.add_argument('file', type=Path, help='File dipendenze (requirements.txt, pyproject.toml)')
    parser.add_argument('--prefixes', nargs='+', default=[], help='Prefissi pacchetti interni')
    parser.add_argument('--all', action='store_true', help='Controlla tutti i pacchetti, non solo quelli con prefisso')
    args = parser.parse_args()

    if not args.file.exists():
        print(f'File non trovato: {args.file}')
        sys.exit(1)

    vulns = audit(args.file, args.prefixes, check_all=args.all)
    sys.exit(1 if vulns else 0)
