#!/usr/bin/env python3
"""
La seconda dimensione: la PERSISTENZA.
Il volume (quanti token) e' solo meta' della storia. L'altra meta' e' quante
volte ogni token viene riletto. A ogni turno il modello riceve TUTTA la
conversazione accumulata: gli stessi token vengono riprocessati a ogni giro.

Qui modello lo scenario A (task corto, 5 chiamate al modello) e calcolo, per
ogni sorgente, quante volte i suoi token attraversano un'inferenza. E' la
"read amplification" del contesto.
"""
import tiktoken
enc = tiktoken.get_encoding("cl100k_base")
def t(s): return len(enc.encode(s))

HARNESS = 19694

# i pezzi e il TURNO in cui entrano nel contesto (su 5 chiamate al modello)
# un pezzo introdotto al turno k viene riletto a ogni turno successivo: (5 - k + 1) volte
pezzi = [
    # (etichetta, token, turno_introduzione)
    ("HARNESS (system+tool+hook+skill)", HARNESS,                 1),
    ("TU (la richiesta)",                t("il totale del carrello e' sbagliato quando scatta lo sconto, sistemalo"), 1),
    ("AGENTE turno 1 (ragiona+Read)",    t("Probabile errore nello sconto, leggo il modulo. Read(cart.py)"), 2),
    ("RISULTATO TOOL: file letto",       420,                     2),
    ("AGENTE turno 2 (Bash test)",       t("Vedo il bug, riproduco col test. Bash(pytest -q)"),             3),
    ("RISULTATO TOOL: test falliti",     180,                     3),
    ("AGENTE turno 3 (Edit)",            t("Confermato, cambio + in -. Edit(cart.py, ...)"),                4),
    ("RISULTATO TOOL: edit ok",          12,                      4),
    ("AGENTE turno 4 (Bash test)",       t("Verifico. Bash(pytest -q)"),                                    5),
    ("RISULTATO TOOL: test passati",     8,                       5),
]
N_TURNI = 5

print("="*74)
print("  LA VITA DI UN TOKEN  (scenario A, 5 chiamate al modello)")
print("="*74)
print(f"{'sorgente':<36}{'token':>7}{'riletto':>9}{'token-letti':>14}")
print("-"*74)
tot_picco = 0
tot_letti = 0
for etich, tok, turno in pezzi:
    riletture = N_TURNI - turno + 1
    letti = tok * riletture
    tot_picco += tok
    tot_letti += letti
    print(f"{etich:<36}{tok:>7}{riletture:>8}x{letti:>14,}")
print("-"*74)
print(f"{'TOTALE':<36}{tot_picco:>7}{'':>9}{tot_letti:>14,}")
print()
# read amplification = token complessivamente riletti / dimensione massima del contesto
print(f"  Dimensione max del contesto (turno piu' grande): {tot_picco:>10,}")
print(f"  Token effettivamente RILETTI in tutta la sessione: {tot_letti:>8,}")
print(f"  Read amplification (riletti / picco):            {tot_letti/tot_picco:>9.1f}x")
print()
print("  Nota: e' un task da 5 turni. In una sessione vera con decine di turni")
print("  l'amplificazione esplode, e cio' che viene introdotto presto (la harness)")
print("  viene riletto a OGNI giro. Misurato su una sessione reale da 99 turni:")
print("  picco del contesto 121.453 token, 6.682.856 token-letti -> 55x.")
