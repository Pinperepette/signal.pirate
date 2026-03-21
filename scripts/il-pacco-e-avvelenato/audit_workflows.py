#!/usr/bin/env python3
from __future__ import annotations
"""audit_workflows.py — Scansiona workflow GitHub Actions cercando ref mutabili.

Identifica Actions che usano @main, @master, @latest o tag vX.Y.Z
invece di SHA commit immutabili. Calcola il rischio per ciascuna.

Uso:
    python audit_workflows.py .github/workflows/
    python audit_workflows.py --fix .github/workflows/  # suggerisce SHA
"""
import argparse
import json
import re
import sys
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

SHA_RE = re.compile(r'uses:\s+([\w.\-/]+)@([0-9a-f]{40})')
TAG_RE = re.compile(r'uses:\s+([\w.\-/]+)@(v[\d.]+|main|master|latest|dev)')
MUTABLE_REFS = {'main', 'master', 'latest', 'dev'}


def get_sha_for_ref(action: str, ref: str) -> str | None:
    """Risolve action@ref al SHA commit corrispondente via GitHub API."""
    # action format: owner/repo
    parts = action.split('/')
    if len(parts) < 2:
        return None
    owner, repo = parts[0], parts[1]
    url = f'https://api.github.com/repos/{owner}/{repo}/git/ref/tags/{ref}'
    try:
        req = Request(url, headers={'Accept': 'application/vnd.github.v3+json'})
        with urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
            sha = data.get('object', {}).get('sha')
            # Se è un tag annotato, dereference
            if data.get('object', {}).get('type') == 'tag':
                tag_url = data['object']['url']
                with urlopen(Request(tag_url, headers={'Accept': 'application/vnd.github.v3+json'}), timeout=8) as tag_resp:
                    tag_data = json.loads(tag_resp.read())
                    sha = tag_data.get('object', {}).get('sha', sha)
            return sha
    except (HTTPError, URLError):
        return None


def audit_file(filepath: Path) -> list:
    """Analizza un singolo workflow YAML."""
    content = filepath.read_text(errors='ignore')
    findings = []

    for line_num, line in enumerate(content.splitlines(), 1):
        # Controlla se è pinned a SHA
        sha_match = SHA_RE.search(line)
        if sha_match:
            findings.append({
                'file': str(filepath),
                'line': line_num,
                'action': sha_match.group(1),
                'ref': sha_match.group(2)[:12] + '...',
                'risk': 'OK',
                'pinned': True,
            })
            continue

        # Controlla tag/branch mutabili
        tag_match = TAG_RE.search(line)
        if tag_match:
            action = tag_match.group(1)
            ref = tag_match.group(2)
            risk = 'HIGH' if ref in MUTABLE_REFS else 'MEDIUM'
            findings.append({
                'file': str(filepath),
                'line': line_num,
                'action': action,
                'ref': ref,
                'risk': risk,
                'pinned': False,
            })

    return findings


def audit_dir(base: Path, resolve_sha: bool = False) -> list:
    """Scansiona una directory di workflow."""
    all_findings = []
    yml_files = list(base.rglob('*.yml')) + list(base.rglob('*.yaml'))

    if not yml_files:
        print(f'Nessun file .yml/.yaml trovato in {base}')
        return []

    print(f'\n{"=" * 70}')
    print(f'  GitHub Actions Audit')
    print(f'  Directory: {base}')
    print(f'  Workflow files: {len(yml_files)}')
    print(f'{"=" * 70}\n')

    for f in sorted(yml_files):
        findings = audit_file(f)
        all_findings.extend(findings)

    # Report
    high = [f for f in all_findings if f['risk'] == 'HIGH']
    medium = [f for f in all_findings if f['risk'] == 'MEDIUM']
    ok = [f for f in all_findings if f['risk'] == 'OK']

    for finding in sorted(all_findings, key=lambda x: (x['risk'] != 'HIGH', x['risk'] != 'MEDIUM', x['file'])):
        risk = finding['risk']
        if risk == 'HIGH':
            color = '\033[91m'
        elif risk == 'MEDIUM':
            color = '\033[93m'
        else:
            color = '\033[92m'
        reset = '\033[0m'

        line_info = f'L{finding["line"]}' if finding.get('line') else ''
        print(f'  {color}[{risk:6s}]{reset} {finding["action"]}@{finding["ref"]}')
        print(f'          in {finding["file"]} {line_info}')

        if resolve_sha and not finding['pinned'] and finding['risk'] != 'OK':
            sha = get_sha_for_ref(finding['action'], finding['ref'])
            if sha:
                print(f'          → fix: uses: {finding["action"]}@{sha}')

    print(f'\n{"=" * 70}')
    print(f'  Risultati:')
    print(f'    \033[91mHIGH\033[0m:   {len(high)} (ref mutabili: main/master/latest)')
    print(f'    \033[93mMEDIUM\033[0m: {len(medium)} (tag versione, non SHA)')
    print(f'    \033[92mOK\033[0m:     {len(ok)} (pinned a SHA commit)')
    if high:
        print(f'\n  ⚠  Fix urgente: pinnare le {len(high)} Actions HIGH a SHA commit.')
        print(f'     Comando: pin-github-action .github/workflows/*.yml')
    print(f'{"=" * 70}')

    return all_findings


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Audit GitHub Actions per ref mutabili')
    parser.add_argument('path', type=Path, help='Directory workflow (.github/workflows/)')
    parser.add_argument('--fix', action='store_true', help='Risolvi SHA per le ref non pinnate')
    args = parser.parse_args()

    if not args.path.exists():
        print(f'Path non trovato: {args.path}')
        sys.exit(1)

    findings = audit_dir(args.path, resolve_sha=args.fix)
    high_count = sum(1 for f in findings if f['risk'] == 'HIGH')
    sys.exit(1 if high_count > 0 else 0)
