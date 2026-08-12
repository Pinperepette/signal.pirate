# -*- coding: utf-8 -*-
"""2 — LE ANNATE: i consigli disposti sull'anno di prima messa in onda."""
import collections
import numpy as np
import matplotlib.pyplot as plt

import dati
from stile import (BG, FG, DIM, DIMMER, GRID, MONO, BODY, TITLE_FONT,
                   testata, pieResta, legenda)

voti = collections.Counter(k for _, k in dati.RECS)
serie = [(k, *dati.SERIE[k]) for k in dati.SERIE if dati.SERIE[k][1]]

# ordine delle corsie: per anno mediano del genere
ORDINE = sorted(dati.CATEGORIE,
                key=lambda c: np.median([s[1] for s in dati.SERIE.values()
                                         if s[3] == c and s[1]]))
LANE = {c: i for i, c in enumerate(ORDINE)}

A_MIN, A_MAX = 1955, 2028
TAGLIO = 1995          # prima di qui l'asse e' compresso: la roba vecchia e' rada


def X(anno):
    """Asse spezzato: 1955-1995 in un quinto della larghezza, il resto disteso."""
    if anno < TAGLIO:
        return 0.02 + (anno - A_MIN) / (TAGLIO - A_MIN) * 0.20
    return 0.245 + (anno - TAGLIO) / (A_MAX - TAGLIO) * (0.995 - 0.245)


FW, FH = 30.0, 17.0
fig = plt.figure(figsize=(FW, FH))

# ------------------------------------------------------------------ corsie
ax = fig.add_axes([0.028, 0.300, 0.955, 0.545])
ax.set_facecolor(BG)
ax.set_xlim(0, 1)
ax.set_ylim(-0.7, len(ORDINE) - 0.3)
for s in ax.spines.values():
    s.set_visible(False)
ax.set_yticks([])
ax.set_xticks([])

for a in list(range(1960, 1995, 10)) + list(range(1995, 2030, 5)):
    ax.axvline(X(a), color=GRID, lw=0.9, zorder=1)
    ax.text(X(a), -0.62, str(a), fontfamily=MONO, fontsize=11, color=DIM,
            ha="center", va="top", zorder=3)

# il segno della rottura di scala
for dx in (-0.004, 0.004):
    ax.plot([0.2325 + dx] * 2, [-0.66, len(ORDINE) - 0.35], lw=1.2,
            color=BG, zorder=4)
    ax.plot([0.2325 + dx] * 2, [-0.66, len(ORDINE) - 0.35], lw=0.8,
            color="#3a4048", ls=(0, (2, 3)), zorder=5)


def raggio(v):
    return 34 + 62 * (v - 1) ** 0.85


etichette = []
for i, cat in enumerate(ORDINE):
    col = dati.COLORI[cat]
    ax.axhline(i, color=col, lw=0.8, alpha=0.16, zorder=1)
    ax.text(0.002, i + 0.30, dati.CATEGORIE[cat].upper(),
            fontfamily=TITLE_FONT, fontsize=15, color=col, alpha=0.85,
            va="bottom", ha="left", zorder=3)

    gruppo = sorted([s for s in serie if s[4] == cat], key=lambda s: (s[2], -voti[s[0]]))
    per_anno = collections.defaultdict(int)
    for k, tit, anno, paese, _ in gruppo:
        n = per_anno[anno]
        per_anno[anno] += 1
        dy = (-1) ** n * ((n + 1) // 2) * 0.115
        v = voti[k]
        ax.scatter([X(anno)], [i + dy], s=raggio(v), color=col, zorder=6,
                   edgecolors=BG, linewidths=0.8,
                   alpha=1.0 if v > 1 else 0.55)
        if v >= 4:
            etichette.append((X(anno), i + dy, tit, v, col))

# etichette dei titoli forti: sopra e sotto, evitando le sovrapposizioni
LARG = 0.00345         # larghezza stimata di un carattere, in coord. asse
occupato = collections.defaultdict(list)
for x, y, tit, v, col in sorted(etichette, key=lambda e: (-e[3], e[0])):
    mezza = len(tit) * LARG / 2 + 0.004
    for off in (0.215, -0.245, 0.335, -0.365, 0.455, -0.485):
        riga = round((y + off) / 0.09)
        # controlla anche le corsie confinanti: il jitter verticale dei pallini
        # sposta le etichette di meno di una riga intera
        vicini = occupato[riga - 1] + occupato[riga] + occupato[riga + 1]
        if all(x + mezza < a or x - mezza > b for a, b in vicini):
            occupato[riga].append((x - mezza, x + mezza))
            ax.annotate(tit, (x, y), (x, y + off), fontsize=10.2,
                        fontfamily=BODY, color="#e6e9ee", ha="center",
                        va="bottom" if off > 0 else "top", zorder=8,
                        arrowprops=dict(arrowstyle="-", color=col, lw=0.7,
                                        alpha=0.45, shrinkA=1, shrinkB=5))
            break

# ------------------------------------------------------- istogramma decenni
axh = fig.add_axes([0.028, 0.145, 0.955, 0.118])
axh.set_facecolor(BG)
axh.set_xlim(0, 1)
for s in axh.spines.values():
    s.set_visible(False)
axh.set_xticks([])
axh.set_yticks([])

menzioni = collections.Counter()
for p, k in dati.RECS:
    if dati.SERIE[k][1]:
        menzioni[dati.SERIE[k][1] // 10 * 10] += 1
alto = max(menzioni.values())
axh.set_ylim(0, alto * 1.30)

decenni = sorted(menzioni)
PASSO = 0.995 / len(decenni)
for i, dec in enumerate(decenni):
    n = menzioni[dec]
    x = 0.002 + i * PASSO
    quota = collections.Counter(dati.SERIE[k][3] for _, k in dati.RECS
                                if dati.SERIE[k][1] and dati.SERIE[k][1] // 10 * 10 == dec)
    base = 0
    for cat in ORDINE:
        if not quota[cat]:
            continue
        axh.add_patch(plt.Rectangle((x, base), PASSO * 0.80, quota[cat],
                                    color=dati.COLORI[cat], zorder=4))
        base += quota[cat]
    axh.text(x + PASSO * 0.40, n + alto * 0.06, str(n), fontfamily=MONO,
             fontsize=13, color=FG, ha="center", va="bottom", zorder=5,
             fontweight="bold")
    axh.text(x + PASSO * 0.40, -alto * 0.055, f"anni {str(dec)[2:]}",
             fontfamily=MONO, fontsize=10, color=DIMMER, ha="center",
             va="top", zorder=5)

axh.text(0.002, alto * 1.26, "QUANTI CONSIGLI PER DECENNIO DI USCITA",
         fontfamily=TITLE_FONT, fontsize=16, color=FG, va="top", ha="left")
axh.text(0.002 + 5 * PASSO, alto * 1.26,
         f"il decennio 2010 da solo vale il {round(100*menzioni[2010]/sum(menzioni.values()))}% dei consigli",
         fontfamily=MONO, fontsize=9.5, color=DIMMER, va="top", ha="left")

testata(fig,
        "LE ANNATE",
        f"{len(serie)} titoli con anno accertato  ·  {sum(menzioni.values())} consigli  ·  una corsia per genere, ordinate per anno mediano",
        "Ogni pallino è una serie, messa sull'anno in cui è andata in onda la prima volta. Più è grande, più persone diverse\n"
        "l'hanno consigliata. La domanda era \"anche roba vecchia va benissimo\": la risposta è che la roba vecchia esiste, ma è\n"
        "una minoranza netta. Il grosso di quello che mi avete consigliato sta in vent'anni, dal 2005 al 2025, e il picco è\n"
        "il decennio 2010. Prima del 1990 sopravvive quasi solo la fantascienza.",
        y=0.985, fs=58, wrap_y=0.916)

legenda(fig, [(dati.CATEGORIE[c], dati.COLORI[c]) for c in ORDINE],
        x=0.645, y=0.972, colonne=3, dx=0.118, dy=0.0215, fs=10.5)

pieResta(fig,
         "Fonte: 323 risposte alla conversazione  ·  5 titoli senza anno accertato esclusi da questa vista",
         "anno = prima messa in onda della serie originale, non del remake  ·  punti più grandi = più persone lo hanno consigliato")

fig.savefig("2-annate.png", dpi=110, facecolor=BG)
print("2-annate.png ok —", len(serie), "titoli,", len(etichette), "etichette")
