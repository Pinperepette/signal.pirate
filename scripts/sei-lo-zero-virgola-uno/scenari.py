#!/usr/bin/env python3
"""
Due scenari NEUTRI per l'articolo "Sei lo 0,1%".
Scenario A: task corto ("sistemami questo bug").
Scenario B: sessione lunga (l'agente legge decine di file, gira a lungo).
In entrambi: quanto del contesto e' "TU"? Una scheggia.

HARNESS_BASELINE e' l'unico numero misurato dall'API reale (costo fisso del
tooling, uguale per tutti, non e' contenuto). Tutto il resto e' inventato e
contato con tiktoken (cl100k).
"""
import tiktoken
enc = tiktoken.get_encoding("cl100k_base")
def t(s): return len(enc.encode(s))

HARNESS_BASELINE = 19694  # system prompt + tool + CLAUDE.md + hook + skill (reale)

# ---------- SCENARIO A: task corto ----------
cart_py = '''\
"""Carrello e calcolo del totale con sconti a soglia."""

class Carrello:
    def __init__(self):
        self.righe = []

    def aggiungi(self, nome, prezzo, quantita=1):
        self.righe.append({"nome": nome, "prezzo": prezzo, "quantita": quantita})

    def subtotale(self):
        return sum(r["prezzo"] * r["quantita"] for r in self.righe)

    def sconto_percentuale(self):
        s = self.subtotale()
        if s >= 100:
            return 0.10
        if s >= 50:
            return 0.05
        return 0.0

    def totale(self):
        s = self.subtotale()
        # BUG: lo sconto viene sommato invece che sottratto
        return s + (s * self.sconto_percentuale())
'''
tu_A = "il totale del carrello e' sbagliato quando scatta lo sconto. sistemalo"
file_letto = "\n".join(f"{i+1}\t{ln}" for i, ln in enumerate(cart_py.splitlines()))
test_fail = '''\
F
=================================== FAILURES ===================================
_____________________________ test_sconto_soglia_100 ___________________________
>       assert c.totale() == 90.0
E       assert 110.0 == 90.0
test_cart.py:8: AssertionError
1 failed in 0.04s'''
agente_A = ("Probabile errore nello sconto, leggo il modulo. "
            "Vedo il bug: somma invece di sottrarre, riproduco col test. "
            "Confermato, cambio + in -. Verifico: ora passa. "
            'Read(file_path="cart.py") Bash("pytest -q") '
            'Edit("cart.py", "s + (s*sc)", "s - (s*sc)") Bash("pytest -q") '
            "Era lo sconto sommato invece che sottratto in totale(). "
            "Cambiato + in -, il test ora passa: 100 con 10% fa 90.")

A = {
    "HARNESS (system+tool+hook+skill)": HARNESS_BASELINE,
    "RISULTATI TOOL (file letti + output)": t(file_letto) + t(test_fail) + t("ok, aggiornato.") + t("1 passed"),
    "AGENTE (ragionamenti + chiamate)": t(agente_A),
    "TU (quello che hai digitato)": t(tu_A),
}

# ---------- SCENARIO B: sessione lunga ----------
# Un file sorgente "medio" rappresentativo, misurato una volta e replicato.
medio = ("import os, json\n\n" + "\n".join(
    f"def funzione_{i}(x, y):\n"
    f'    """Gestisce il caso {i} del modulo."""\n'
    f"    risultato = (x * {i}) + y - {i}\n"
    f"    if risultato < 0:\n"
    f"        return 0\n"
    f"    return risultato\n"
    for i in range(14)))
file_medio = "\n".join(f"{i+1}\t{ln}" for i, ln in enumerate(medio.splitlines()))
tok_file_medio = t(file_medio)

N_FILE = 22          # file aperti dall'agente per orientarsi nel codebase
N_COMANDI = 8        # test, grep, build... output vario
out_medio = t(test_fail) + t(file_letto)  # ~ output tipico di un comando
tu_B = (tu_A + " " +
        "no aspetta, controlla anche gli altri moduli che importano il carrello "
        "e assicurati che i test di integrazione passino tutti")

B = {
    "HARNESS (system+tool+hook+skill)": HARNESS_BASELINE,
    "RISULTATI TOOL (file letti + output)": N_FILE * tok_file_medio + N_COMANDI * out_medio,
    "AGENTE (ragionamenti + chiamate)": t(agente_A) * 6,  # molti piu' turni
    "TU (quello che hai digitato)": t(tu_B),
}

SCENARI = {
    "A — task corto ('sistemami questo bug')": A,
    "B — sessione lunga (l'agente esplora il codebase)": B,
}

def stampa(nome, d):
    TOT = sum(d.values())
    tu = d["TU (quello che hai digitato)"]
    print("="*64)
    print(f"  SCENARIO {nome}")
    print("="*64)
    for k, v in sorted(d.items(), key=lambda x: -x[1]):
        pct = 100*v/TOT
        print(f"{k:<40} {v:>7} tok  {pct:5.2f}%")
        print("  " + "█"*max(1, round(pct/2)))
    print("-"*64)
    print(f"{'TOTALE contesto':<40} {TOT:>7} tok")
    print(f"  -> TU sei lo {100*tu/TOT:.2f}%   "
          f"(per ogni tuo token, la macchina ne legge {round((TOT-tu)/tu)})")
    print()

if __name__ == "__main__":
    for nome, d in SCENARI.items():
        stampa(nome, d)
