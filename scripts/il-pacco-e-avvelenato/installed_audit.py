#!/usr/bin/env python3
"""installed_audit.py — Controlla se i pacchetti Python installati sono avvelenati.

Scansiona l'ambiente pip attivo, scarica gli sdist da PyPI, e analizza
setup.py/__init__.py con le stesse euristiche del sentinel.

Uso:
    python installed_audit.py                   # scansiona tutto
    python installed_audit.py --top 50          # solo i primi 50
    python installed_audit.py --ai              # con analisi AI (Ollama)
    python installed_audit.py --threshold 20    # mostra solo score >= 20
    python installed_audit.py --json report.json  # esporta report JSON
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Importa engine dal sentinel
sys.path.insert(0, str(Path(__file__).parent))
from pypi_sentinel import (
    analyze_package_dir,
    check_typosquatting,
    download_and_extract,
    print_report,
    severity_label,
    severity_color,
)


def get_installed_packages() -> list[dict]:
    """Lista pacchetti installati via pip."""
    result = subprocess.run(
        [sys.executable, '-m', 'pip', 'list', '--format=json'],
        capture_output=True, text=True, timeout=30
    )
    return json.loads(result.stdout)


def audit_installed(top_n: int = 0, use_ai: bool = False, ai_model: str = 'mistral',
                    threshold: int = 0, json_output: Path | None = None):
    """Scansiona pacchetti installati."""
    packages = get_installed_packages()

    if top_n > 0:
        packages = packages[:top_n]

    total = len(packages)
    print(f'\n{"=" * 60}')
    print(f'  🛡️  Installed Packages Audit')
    print(f'  Pacchetti: {total}')
    print(f'  Python: {sys.version.split()[0]}')
    print(f'  AI: {"ON (" + ai_model + ")" if use_ai else "OFF"}')
    print(f'  Soglia: {threshold}')
    print(f'{"=" * 60}\n')

    stats = {'total': 0, 'scanned': 0, 'critical': 0, 'high': 0, 'medium': 0, 'clean': 0, 'skipped': 0}
    report_entries = []

    with tempfile.TemporaryDirectory() as tmp:
        for i, pkg in enumerate(packages, 1):
            name = pkg['name']
            version = pkg['version']
            stats['total'] += 1

            progress = f'[{i:3d}/{total}]'
            sys.stdout.write(f'\r  {progress} {name:40s}')
            sys.stdout.flush()

            # Download sdist
            pkg_dir = download_and_extract(name, tmp)
            if not pkg_dir:
                stats['skipped'] += 1
                sys.stdout.write(f'\r  {progress} {name:40s} [no sdist — skip]\n')
                continue

            stats['scanned'] += 1

            # Analisi
            do_ai = use_ai and threshold <= 20
            results = analyze_package_dir(pkg_dir, use_ai=False)
            score = results['total_score']

            # AI solo se sospetto
            if use_ai and score >= 20:
                results = analyze_package_dir(pkg_dir, use_ai=True, ai_model=ai_model)
                score = results['total_score']

            typo_matches = check_typosquatting(name)

            label = severity_label(score)
            if label == 'CRITICAL':
                stats['critical'] += 1
            elif label == 'HIGH':
                stats['high'] += 1
            elif label == 'MEDIUM':
                stats['medium'] += 1
            else:
                stats['clean'] += 1

            # Report entry
            entry = {
                'name': name,
                'version': version,
                'score': score,
                'severity': label,
                'typosquatting': [(n, d) for n, d in typo_matches],
                'findings': [f['rule'] for file_r in results['files'] for f in file_r['findings']],
                'ai': results.get('ai_result'),
            }
            report_entries.append(entry)

            if score >= threshold:
                sys.stdout.write(f'\r')  # clear progress line
                print_report(f'{name}=={version}', results, typo_matches)
            else:
                color = severity_color(score)
                reset = '\033[0m'
                sys.stdout.write(f'\r  {progress} {color}●{reset} {name:40s} v{version:12s} [score: {score}]\n')

    # Summary
    print(f'\n{"=" * 60}')
    print(f'  📊 Risultati Audit')
    print(f'{"=" * 60}')
    print(f'  Pacchetti totali:    {stats["total"]}')
    print(f'  Scansionati (sdist): {stats["scanned"]}')
    print(f'  Skippati (no sdist): {stats["skipped"]}')
    print()
    print(f'  \033[91mCRITICAL: {stats["critical"]}\033[0m')
    print(f'  \033[93mHIGH:     {stats["high"]}\033[0m')
    print(f'  \033[33mMEDIUM:   {stats["medium"]}\033[0m')
    print(f'  \033[92mCLEAN:    {stats["clean"]}\033[0m')

    # Top sospetti
    suspicious = [e for e in report_entries if e['score'] > 0]
    if suspicious:
        suspicious.sort(key=lambda x: x['score'], reverse=True)
        print(f'\n  🔍 Top sospetti:')
        for e in suspicious[:10]:
            color = severity_color(e['score'])
            reset = '\033[0m'
            print(f'    {color}[{e["score"]:3d}]{reset} {e["name"]}=={e["version"]}  ({", ".join(e["findings"][:3])})')

    print(f'{"=" * 60}')

    # Export JSON
    if json_output:
        report = {
            'timestamp': datetime.now().isoformat(),
            'python': sys.version.split()[0],
            'stats': stats,
            'packages': report_entries,
        }
        json_output.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        print(f'  Report JSON: {json_output}')

    return stats


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Audit pacchetti Python installati')
    parser.add_argument('--top', type=int, default=0, help='Limita ai primi N pacchetti')
    parser.add_argument('--ai', action='store_true', help='Abilita analisi AI via Ollama')
    parser.add_argument('--model', default='mistral', help='Modello Ollama (default: mistral)')
    parser.add_argument('--threshold', type=int, default=0, help='Score minimo per report dettagliato')
    parser.add_argument('--json', type=Path, metavar='FILE', help='Esporta report JSON')
    args = parser.parse_args()

    stats = audit_installed(
        top_n=args.top,
        use_ai=args.ai,
        ai_model=args.model,
        threshold=args.threshold,
        json_output=args.json,
    )

    sys.exit(1 if stats['critical'] > 0 else 0)
