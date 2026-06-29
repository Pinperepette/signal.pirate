#!/usr/bin/env python3
"""
ESEMPIO NEUTRO per l'articolo "Tu sei l'1%".
Ricostruisce un task agentico tipico ("sistemami questo bug") su un toy project
inventato e conta, token per token, cosa entra nel contesto del modello e da
quale SORGENTE arriva. Niente dati reali dell'autore.

Numeri:
- HARNESS (costo fisso): valore REALE misurato dall'API (system prompt + tool +
  CLAUDE.md + hook + skill + lista tool/agent). Uguale per tutti, non e' contenuto.
- Tutto il resto: contato con tiktoken (cl100k). Stima entro ~10-15% del
  tokenizer Anthropic, sufficiente per le proporzioni.
"""
import tiktoken
enc = tiktoken.get_encoding("cl100k_base")
def t(s): return len(enc.encode(s))

# 1) COSTO FISSO DELLA HARNESS (misurato dall'API, non e' contenuto utente)
HARNESS_BASELINE = 19694

# 2) IL TOY PROJECT (inventato). Un modulo con un bug nello sconto.
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

test_py = '''\
from cart import Carrello

def test_sconto_soglia_100():
    c = Carrello()
    c.aggiungi("tastiera", 60.0)
    c.aggiungi("mouse", 40.0)        # subtotale 100 -> sconto 10%
    assert c.totale() == 90.0        # atteso 90, non 110
'''

# 3) LA SESSIONE TIPICA (la riga "tu" e' minuscola, il resto si gonfia da solo)
tu_prompt = "il totale del carrello e' sbagliato quando scatta lo sconto. sistemalo"

# turno 1 assistant: ragiona + chiede di leggere il file
a1_think = ("Probabile errore nel calcolo dello sconto. Leggo il modulo per "
            "capire come viene applicato prima di toccarlo.")
a1_toolcall = 'Read(file_path="cart.py")'
# tool_result: contenuto del file (con i numeri di riga, come fa davvero il tool)
tr1 = "\n".join(f"{i+1}\t{ln}" for i, ln in enumerate(cart_py.splitlines()))

# turno 2 assistant: lancia i test
a2_think = "Vedo il bug: somma lo sconto invece di sottrarlo. Prima riproduco col test."
a2_toolcall = 'Bash(command="python -m pytest -q")'
tr2 = '''\
F                                                                        [100%]
=================================== FAILURES ===================================
_____________________________ test_sconto_soglia_100 ___________________________

    def test_sconto_soglia_100():
        c = Carrello()
        c.aggiungi("tastiera", 60.0)
        c.aggiungi("mouse", 40.0)
>       assert c.totale() == 90.0
E       assert 110.0 == 90.0
E        +  where 110.0 = <bound method Carrello.totale of <cart.Carrello object at 0x10f3a2b50>>()

test_cart.py:8: AssertionError
1 failed in 0.04s'''

# turno 3 assistant: applica la fix
a3_think = "Confermato. Cambio il + in - nello sconto."
a3_toolcall = ('Edit(file_path="cart.py", '
               'old_string="return s + (s * self.sconto_percentuale())", '
               'new_string="return s - (s * self.sconto_percentuale())")')
tr3 = "The file cart.py has been updated successfully."

# turno 4 assistant: rilancia i test
a4_think = "Verifico che ora passi."
a4_toolcall = 'Bash(command="python -m pytest -q")'
tr4 = "1 passed in 0.03s"

# turno 5 assistant: risposta finale all'utente
a5_final = ("Era lo sconto sommato invece che sottratto in `totale()`. "
            "Cambiato `+` in `-`, il test ora passa: 100 euro con sconto 10% fa 90.")

# --- attribuzione per SORGENTE (contesto cumulato all'ultimo turno) ---
sorgenti = {
    "HARNESS (system+tool+hook+skill)": HARNESS_BASELINE,
    "TU (quello che hai digitato)":      t(tu_prompt),
    "RISULTATI TOOL (file+output)":      t(tr1)+t(tr2)+t(tr3)+t(tr4),
    "AGENTE (ragionamenti+chiamate)":    sum(t(x) for x in [
        a1_think,a1_toolcall,a2_think,a2_toolcall,a3_think,a3_toolcall,
        a4_think,a4_toolcall,a5_final]),
}
TOT = sum(sorgenti.values())

print("="*60)
print("  COSA LEGGE IL MODELLO PER 'sistemami questo bug'")
print("  (contesto cumulato, un task agentico tipico)")
print("="*60)
W=42
for k,v in sorted(sorgenti.items(), key=lambda x:-x[1]):
    pct=100*v/TOT
    bar="█"*max(1,round(pct/2))
    print(f"{k:<36} {v:>7} tok  {pct:5.1f}%")
    print(f"  {bar}")
print("-"*60)
print(f"{'TOTALE contesto':<36} {TOT:>7} tok")
tu=sorgenti['TU (quello che hai digitato)']
print()
print(f"  Tu hai scritto {tu} token su {TOT}.")
print(f"  Sei lo {100*tu/TOT:.2f}% di quello che la macchina legge per risponderti.")
print(f"  Per ogni token tuo, la harness ne mette davanti {round((TOT-tu)/tu)}.")
