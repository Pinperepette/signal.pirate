#!/usr/bin/env python3
from __future__ import annotations
"""setup_analyzer.py — Analisi statica AST di setup.py per rilevare pattern malevoli.

Cerca: import socket/subprocess/os.system, chiamate a exec/eval,
network activity, file system exfiltration, encoded payloads.

Uso:
    python setup_analyzer.py pacchetto/setup.py
    python setup_analyzer.py --dir ./vendor/  # scansiona tutti i setup.py
"""
import argparse
import ast
import base64
import re
import sys
from pathlib import Path

# ── Pattern sospetti ──────────────────────────────────────────────────────
SUSPICIOUS_IMPORTS = {
    'socket', 'subprocess', 'http.client', 'urllib.request',
    'requests', 'ctypes', 'shutil', 'ftplib', 'smtplib',
    'paramiko', 'Crypto', 'cryptography',
}

SUSPICIOUS_CALLS = {
    'os.system', 'os.popen', 'os.exec', 'os.execv', 'os.execvp',
    'subprocess.run', 'subprocess.Popen', 'subprocess.call',
    'subprocess.check_output', 'subprocess.check_call',
    'exec', 'eval', 'compile', '__import__',
    'socket.socket', 'socket.create_connection',
    'urllib.request.urlopen', 'requests.get', 'requests.post',
    'base64.b64decode', 'codecs.decode',
    'shutil.copy', 'shutil.move',
}

SUSPICIOUS_PATTERNS = [
    (r'base64\.b64decode', 'Base64 decoding (possibile payload offuscato)'),
    (r'\\x[0-9a-f]{2}', 'Hex escape sequences (possibile shellcode)'),
    (r'exec\s*\(', 'Chiamata exec() (esecuzione codice dinamico)'),
    (r'eval\s*\(', 'Chiamata eval() (valutazione espressione dinamica)'),
    (r'os\.environ', 'Accesso a variabili d\'ambiente (possibile esfiltrazione)'),
    (r'getpass\.getuser|os\.getlogin|socket\.gethostname', 'Raccolta info sistema'),
    (r'curl\s|wget\s', 'Riferimento a curl/wget (network exfiltration)'),
    (r'https?://[^\s"\']+', 'URL hardcoded (possibile C2)'),
]


class SetupAnalyzer(ast.NodeVisitor):
    """Analizza AST di un file Python cercando pattern sospetti."""

    def __init__(self, filename: str):
        self.filename = filename
        self.findings = []
        self.imports = set()

    def _add(self, severity: str, line: int, msg: str):
        self.findings.append({
            'severity': severity,
            'line': line,
            'message': msg,
            'file': self.filename,
        })

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.name.split('.')[0])
            if alias.name in SUSPICIOUS_IMPORTS or alias.name.split('.')[0] in SUSPICIOUS_IMPORTS:
                self._add('HIGH', node.lineno, f'Import sospetto: {alias.name}')
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            mod = node.module.split('.')[0]
            self.imports.add(mod)
            if mod in SUSPICIOUS_IMPORTS or node.module in SUSPICIOUS_IMPORTS:
                self._add('HIGH', node.lineno, f'Import sospetto: from {node.module}')
        self.generic_visit(node)

    def visit_Call(self, node):
        call_name = self._get_call_name(node)
        if call_name in SUSPICIOUS_CALLS:
            self._add('HIGH', node.lineno, f'Chiamata sospetta: {call_name}()')

        # Controlla exec/eval con argomento stringa
        if call_name in ('exec', 'eval') and node.args:
            if isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                self._add('CRITICAL', node.lineno,
                          f'{call_name}() con stringa literal — possibile payload')

        self.generic_visit(node)

    def _get_call_name(self, node) -> str:
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            parts = []
            n = node.func
            while isinstance(n, ast.Attribute):
                parts.append(n.attr)
                n = n.value
            if isinstance(n, ast.Name):
                parts.append(n.id)
            return '.'.join(reversed(parts))
        return ''


def analyze_file(filepath: Path) -> list:
    """Analizza un singolo file Python."""
    content = filepath.read_text(errors='ignore')

    # AST analysis
    try:
        tree = ast.parse(content, filename=str(filepath))
    except SyntaxError as e:
        return [{'severity': 'ERROR', 'line': e.lineno or 0,
                 'message': f'Syntax error: {e.msg}', 'file': str(filepath)}]

    analyzer = SetupAnalyzer(str(filepath))
    analyzer.visit(tree)

    # Regex pattern matching
    for pattern, desc in SUSPICIOUS_PATTERNS:
        for i, line in enumerate(content.splitlines(), 1):
            if re.search(pattern, line):
                analyzer.findings.append({
                    'severity': 'MEDIUM',
                    'line': i,
                    'message': desc,
                    'file': str(filepath),
                })

    # Deduplica per (line, message)
    seen = set()
    unique = []
    for f in analyzer.findings:
        key = (f['line'], f['message'])
        if key not in seen:
            seen.add(key)
            unique.append(f)

    return sorted(unique, key=lambda x: x['line'])


def main():
    parser = argparse.ArgumentParser(description='Analisi statica setup.py per pattern malevoli')
    parser.add_argument('target', type=Path, help='File o directory da analizzare')
    parser.add_argument('--dir', action='store_true', help='Scansiona ricorsivamente una directory')
    args = parser.parse_args()

    if args.dir or args.target.is_dir():
        files = list(args.target.rglob('setup.py')) + list(args.target.rglob('__init__.py'))
    else:
        files = [args.target]

    if not files:
        print('Nessun file trovato da analizzare.')
        sys.exit(0)

    total_findings = 0
    for f in files:
        findings = analyze_file(f)
        if findings:
            print(f'\n{"=" * 60}')
            print(f'  {f}')
            print(f'{"=" * 60}')
            for item in findings:
                sev = item['severity']
                color = '\033[91m' if sev in ('CRITICAL', 'HIGH') else '\033[93m'
                reset = '\033[0m'
                print(f'  {color}[{sev:8s}]{reset} L{item["line"]:4d}  {item["message"]}')
            total_findings += len(findings)

    print(f'\n{"=" * 60}')
    print(f'  File analizzati: {len(files)}')
    print(f'  Finding totali:  {total_findings}')
    if total_findings == 0:
        print(f'  ✓  Nessun pattern sospetto rilevato')
    print(f'{"=" * 60}')

    sys.exit(1 if total_findings > 0 else 0)


if __name__ == '__main__':
    main()
