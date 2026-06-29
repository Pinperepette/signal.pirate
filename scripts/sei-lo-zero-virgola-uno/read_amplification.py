#!/usr/bin/env python3
"""
Read amplification sulla TUA sessione, dai numeri reali dell'API.

Quante volte, in media, ogni token presente nel contesto viene riprocessato
durante la sessione. A ogni inferenza il contesto completo torna in input:
la metrica e' la somma dei token in input a ogni chiamata, divisa per la
dimensione massima del contesto (il turno piu' grande).

Privacy: legge solo i campi `usage` (conteggi), mai il contenuto. Gira in locale.

Uso:
    python read_amplification.py ~/.claude/projects/<progetto>/<id>.jsonl
Senza argomenti prende la sessione piu' recente del progetto corrente.
"""
import json, sys, os, glob

def trova_sessione_recente():
    base = os.path.expanduser("~/.claude/projects")
    cands = glob.glob(os.path.join(base, "*", "*.jsonl"))
    if not cands:
        sys.exit("Nessun transcript trovato in ~/.claude/projects")
    return max(cands, key=os.path.getmtime)

path = sys.argv[1] if len(sys.argv) > 1 else trova_sessione_recente()
rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]

per_turno = []   # token in input a ogni chiamata = input + cache_read + cache_creation
output_tot = 0
for r in rows:
    if r.get("type") == "assistant":
        u = r.get("message", {}).get("usage", {})
        ctx = (u.get("input_tokens", 0)
               + u.get("cache_read_input_tokens", 0)
               + u.get("cache_creation_input_tokens", 0))
        if ctx:
            per_turno.append(ctx)
        output_tot += u.get("output_tokens", 0)

if not per_turno:
    sys.exit("Nessun turno con dati usage in questo transcript.")

turni = len(per_turno)
picco = max(per_turno)              # dimensione massima del contesto
riletti = sum(per_turno)           # token complessivamente riprocessati in input
amp = riletti / picco

print("="*58)
print("  READ AMPLIFICATION")
print("  sessione:", os.path.basename(path))
print("="*58)
print(f"  Chiamate al modello (turni):        {turni:>12,}")
print(f"  Picco del contesto (turno piu' grande): {picco:>9,}")
print(f"  Token riletti in input (somma turni):   {riletti:>9,}")
print(f"  Token generati in output:           {output_tot:>12,}")
print("-"*58)
print(f"  Read amplification (riletti / picco):   {amp:>8.1f}x")
print()
print(f"  In media ogni token del contesto e' stato riprocessato {amp:.0f} volte.")
