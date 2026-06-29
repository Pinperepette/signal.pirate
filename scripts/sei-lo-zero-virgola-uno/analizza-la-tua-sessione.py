#!/usr/bin/env python3
"""
Smonta una TUA sessione di Claude Code e dice quanto del contesto sei davvero tu.

Privacy: legge solo i CONTEGGI di token, non stampa mai il contenuto dei tuoi
messaggi ne' dei file letti. Gira tutto in locale.

Uso:
    pip install tiktoken
    python analizza-la-tua-sessione.py ~/.claude/projects/<progetto>/<id>.jsonl

Se ometti il path, prende la sessione piu' recente del progetto corrente.

Come funziona il conto:
- TOTALE = il numero REALE di token del contesto all'ultimo turno, preso dai
  campi usage dell'API (input + cache_read + cache_creation). Niente stime.
- TU / RISULTATI TOOL / AGENTE = contati con tiktoken sui messaggi visibili.
- HARNESS = il resto (TOTALE meno i visibili): system prompt, definizioni dei
  tool, CLAUDE.md, hook, skill. Tutto cio' che la macchina mette nel contesto
  senza che tu lo veda.
"""
import json, sys, os, glob

try:
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    def t(s): return len(enc.encode(s if isinstance(s, str) else json.dumps(s)))
except ImportError:
    sys.exit("Manca tiktoken:  pip install tiktoken")

def trova_sessione_recente():
    base = os.path.expanduser("~/.claude/projects")
    cands = glob.glob(os.path.join(base, "*", "*.jsonl"))
    if not cands:
        sys.exit("Nessun transcript trovato in ~/.claude/projects")
    return max(cands, key=os.path.getmtime)

path = sys.argv[1] if len(sys.argv) > 1 else trova_sessione_recente()
rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]

tu = tool = agente = 0
totale_reale = 0  # contesto reale all'ultimo turno (dai campi usage)

for r in rows:
    typ = r.get("type")
    msg = r.get("message", {})
    content = msg.get("content")

    if typ == "user":
        if isinstance(content, str):
            tu += t(content)                       # quello che hai digitato
        elif isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    tool += t(b.get("content", ""))  # output dei tool
                elif isinstance(b, dict) and b.get("type") == "text":
                    tu += t(b.get("text", ""))

    elif typ == "assistant":
        for b in content or []:
            if isinstance(b, dict):
                if b.get("type") == "text":
                    agente += t(b.get("text", ""))
                elif b.get("type") == "tool_use":
                    agente += t(b.get("input", {})) + t(b.get("name", ""))
        u = msg.get("usage", {})
        ctx = (u.get("input_tokens", 0)
               + u.get("cache_read_input_tokens", 0)
               + u.get("cache_creation_input_tokens", 0))
        totale_reale = max(totale_reale, ctx)  # il piu' grande = contesto pieno

visibili = tu + tool + agente
harness = max(0, totale_reale - visibili)  # il resto: system+tool+hook+skill

sorgenti = {
    "HARNESS (system+tool+hook+skill)": harness,
    "RISULTATI TOOL (file letti + output)": tool,
    "AGENTE (ragionamenti + chiamate)": agente,
    "TU (quello che hai digitato)": tu,
}
TOT = totale_reale if totale_reale else max(1, visibili)

print("="*60)
print("  Quanto del contesto sei davvero TU?")
print("  sessione:", os.path.basename(path))
print("="*60)
for k, v in sorted(sorgenti.items(), key=lambda x: -x[1]):
    pct = 100*v/TOT
    print(f"{k:<38} {v:>8} tok  {pct:5.2f}%")
    print("  " + "█"*max(1, round(pct/2)))
print("-"*60)
print(f"{'TOTALE contesto (reale, dai campi usage)':<38} {TOT:>8} tok")
if tu:
    print(f"\n  Sei lo {100*tu/TOT:.2f}% del contesto.")
    print(f"  Per ogni tuo token, la macchina ne legge {round((TOT-tu)/tu)} "
          f"che non hai scritto.")
