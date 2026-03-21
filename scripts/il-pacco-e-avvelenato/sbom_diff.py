#!/usr/bin/env python3
from __future__ import annotations
"""sbom_diff.py — Genera e confronta SBOM (Software Bill of Materials).

Genera un inventario delle dipendenze installate e confronta due snapshot
per rilevare pacchetti aggiunti, rimossi o con versione cambiata.

Uso:
    python sbom_diff.py generate --output sbom-v1.json
    # ... dopo un aggiornamento ...
    python sbom_diff.py generate --output sbom-v2.json
    python sbom_diff.py diff sbom-v1.json sbom-v2.json
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def generate_sbom(output: Path):
    """Genera SBOM dalle dipendenze pip installate."""
    print('Raccolta dipendenze pip...')

    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'list', '--format=json'],
            capture_output=True, text=True, timeout=30
        )
        packages = json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
        print(f'Errore: {e}')
        sys.exit(1)

    sbom = {
        'bomFormat': 'CycloneDX',
        'specVersion': '1.5',
        'version': 1,
        'metadata': {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'tools': [{'name': 'sbom_diff.py', 'version': '1.0.0'}],
            'component': {
                'type': 'application',
                'name': 'python-environment',
                'version': sys.version.split()[0],
            }
        },
        'components': [],
    }

    for pkg in packages:
        component = {
            'type': 'library',
            'name': pkg['name'].lower(),
            'version': pkg['version'],
            'purl': f'pkg:pypi/{pkg["name"].lower()}@{pkg["version"]}',
        }
        sbom['components'].append(component)

    sbom['components'].sort(key=lambda x: x['name'])

    output.write_text(json.dumps(sbom, indent=2, ensure_ascii=False))
    print(f'\n{"=" * 60}')
    print(f'  SBOM generata: {output}')
    print(f'  Componenti: {len(sbom["components"])}')
    print(f'  Timestamp: {sbom["metadata"]["timestamp"]}')
    print(f'  Python: {sys.version.split()[0]}')
    print(f'{"=" * 60}')


def diff_sbom(old_path: Path, new_path: Path):
    """Confronta due SBOM e mostra le differenze."""
    old = json.loads(old_path.read_text())
    new = json.loads(new_path.read_text())

    old_pkgs = {c['name']: c['version'] for c in old.get('components', [])}
    new_pkgs = {c['name']: c['version'] for c in new.get('components', [])}

    old_names = set(old_pkgs.keys())
    new_names = set(new_pkgs.keys())

    added = new_names - old_names
    removed = old_names - new_names
    common = old_names & new_names
    changed = {n for n in common if old_pkgs[n] != new_pkgs[n]}

    old_ts = old.get('metadata', {}).get('timestamp', '?')
    new_ts = new.get('metadata', {}).get('timestamp', '?')

    print(f'\n{"=" * 60}')
    print(f'  SBOM Diff')
    print(f'  Old: {old_path} ({old_ts})')
    print(f'  New: {new_path} ({new_ts})')
    print(f'{"=" * 60}')

    if added:
        print(f'\n  \033[92m+ AGGIUNTI ({len(added)}):\033[0m')
        for name in sorted(added):
            print(f'    + {name} {new_pkgs[name]}')

    if removed:
        print(f'\n  \033[91m- RIMOSSI ({len(removed)}):\033[0m')
        for name in sorted(removed):
            print(f'    - {name} {old_pkgs[name]}')

    if changed:
        print(f'\n  \033[93m~ VERSIONE CAMBIATA ({len(changed)}):\033[0m')
        for name in sorted(changed):
            print(f'    ~ {name}: {old_pkgs[name]} → {new_pkgs[name]}')

    if not added and not removed and not changed:
        print(f'\n  ✓  Nessuna differenza trovata')

    total_changes = len(added) + len(removed) + len(changed)
    print(f'\n{"=" * 60}')
    print(f'  Old: {len(old_pkgs)} pacchetti')
    print(f'  New: {len(new_pkgs)} pacchetti')
    print(f'  Differenze: {total_changes}')

    if added:
        print(f'\n  ⚠  {len(added)} nuovi pacchetti — verificare che siano attesi.')
        print(f'     Controllare con: pip-audit --requirement requirements.txt')

    print(f'{"=" * 60}')

    return total_changes


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='SBOM generator e diff')
    sub = parser.add_subparsers(dest='command', required=True)

    gen = sub.add_parser('generate', help='Genera SBOM dalle dipendenze installate')
    gen.add_argument('--output', '-o', type=Path, default=Path('sbom.json'), help='Output file')

    diff = sub.add_parser('diff', help='Confronta due SBOM')
    diff.add_argument('old', type=Path, help='SBOM vecchia')
    diff.add_argument('new', type=Path, help='SBOM nuova')

    args = parser.parse_args()

    if args.command == 'generate':
        generate_sbom(args.output)
    elif args.command == 'diff':
        changes = diff_sbom(args.old, args.new)
        sys.exit(1 if changes > 0 else 0)
