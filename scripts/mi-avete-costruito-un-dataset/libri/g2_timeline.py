# -*- coding: utf-8 -*-
"""2 — SETTE SECOLI SU UNO SCAFFALE: i consigli disposti sull'anno di prima edizione."""
import collections, statistics
import numpy as np
import matplotlib.pyplot as plt

import dati
from stile import (BG, FG, DIM, DIMMER, GRID, MONO, BODY, TITLE_FONT,
                   testata, pieResta, legenda)

voti = collections.Counter(k for _, k in dati.RECS)
libri = [(k, *dati.BOOKS[k]) for k in dati.BOOKS if dati.BOOKS[k][2]]

# ---------------------- gutter | 1300-1900 compresso | rottura | 1900-2030 disteso
GUT, A0, A1, B0 = 0.088, 0.100, 0.262, 0.288
TAGLIO = 1900


def X(anno):
    if anno < TAGLIO:
        return A0 + (anno - 1300) / (TAGLIO - 1300) * (A1 - A0)
    return B0 + (anno - TAGLIO) / (2030 - TAGLIO) * (0.998 - B0)


ORDINE = sorted(dati.CATEGORIE,
                key=lambda c: statistics.median([b[2] for b in dati.BOOKS.values()
                                                 if b[3] == c and b[2]]))

FW, FH = 30.0, 19.5
fig = plt.figure(figsize=(FW, FH))
ax = fig.add_axes([0.028, 0.245, 0.955, 0.60])
ax.set_facecolor(BG)
ax.set_xlim(0, 1)
ax.set_ylim(-0.62, len(ORDINE) - 0.38)
ax.invert_yaxis()
for s in ax.spines.values():
    s.set_visible(False)
ax.set_xticks([]); ax.set_yticks([])

# corsie: un rettangolo per tema
LANE = 0.43
for i, cat in enumerate(ORDINE):
    ax.add_patch(plt.Rectangle((A0 - 0.012, i - LANE), 1.01 - A0 + 0.012, LANE * 2,
                               color="#13151a", zorder=0))

# griglia verticale
for anno in [1400, 1500, 1600, 1700, 1800]:
    ax.axvline(X(anno), color=GRID, lw=0.8, zorder=1)
for anno in range(1900, 2031, 10):
    ax.axvline(X(anno), color=GRID, lw=1.2 if anno % 50 == 0 else 0.7, zorder=1)

# ------------------------------------------------- sciame
R = 0.0088          # raggio orizzontale di un punto, in coord. asse
PASSO = 0.125       # passo verticale dello sciame
pos = {}
for i, cat in enumerate(ORDINE):
    membri = sorted([l for l in libri if l[4] == cat], key=lambda l: l[3])
    piani = []      # per ogni livello, l'ultima x occupata
    for k, tit, aut, anno, _, forma in membri:
        x = X(anno)
        for lv in range(60):
            riga = lv // 2 * (1 if lv % 2 == 0 else -1) if lv else 0
            riga = (lv + 1) // 2 * (-1 if lv % 2 else 1)
            if riga not in [p[0] for p in piani] or \
               all(x - p[1] > R * 2 for p in piani if p[0] == riga):
                piani = [p for p in piani if p[0] != riga] + [(riga, x)]
                pos[k] = (x, i + riga * PASSO)
                break

# mediane + etichette di corsia nel margine di sinistra
for i, cat in enumerate(ORDINE):
    med = statistics.median([b[2] for b in dati.BOOKS.values()
                             if b[3] == cat and b[2]])
    ax.plot([X(med)] * 2, [i - LANE, i + LANE], lw=2.6,
            color=dati.COLORI[cat], alpha=0.5, zorder=2)
    ax.text(X(med) + 0.004, i - LANE + 0.045, f"mediana {med:.0f}", fontsize=8.5,
            color=dati.COLORI[cat], ha="left", va="top", fontfamily=MONO, alpha=0.95,
            zorder=6, bbox=dict(facecolor="#13151a", edgecolor="none", pad=1.6))
    n = sum(1 for b in dati.BOOKS.values() if b[3] == cat and b[2])
    ax.text(GUT - 0.012, i - 0.055, dati.CATEGORIE[cat].upper(), fontsize=15.5,
            color=dati.COLORI[cat], ha="right", va="bottom", fontfamily=TITLE_FONT)
    ax.text(GUT - 0.012, i + 0.035, f"{n} titoli", fontsize=9, color=DIMMER,
            ha="right", va="top", fontfamily=MONO)

# punti
for k, tit, aut, anno, cat, forma in libri:
    x, y = pos[k]
    v = voti[k]
    ax.scatter([x], [y], s=42 + 120 * (v - 1), color=dati.COLORI[cat],
               edgecolors=BG, linewidths=0.8, zorder=4)

# ------------------------------------------------- etichette scelte
DA_ETICHETTARE = [k for k in dati.BOOKS if voti[k] >= 2 and dati.BOOKS[k][2]] + [
    "commedia", "promessi", "montecristo", "darwin", "flat", "engels", "fronte",
    "giza", "america", "malvaldi", "floridi", "italiacarta", "autosole",
    "iorobot", "f451", "algernon", "guida", "spettacolo", "simulacri",
    "commedia", "atomi", "polya", "rothbard", "broken", "llm", "buchi",
]
box = [(0, i - 0.09, GUT, i + 0.06) for i in range(len(ORDINE))]
box.append((A1 - 0.002, -9, B0 + 0.002, 99))     # nessuna etichetta sulla rottura
ALT = 0.086


def raggio(k):
    return 0.0052 + 0.0020 * (voti[k] - 1)


for i, cat in enumerate(ORDINE):                  # le scritte "mediana" bloccano
    med = statistics.median([b[2] for b in dati.BOOKS.values()
                             if b[3] == cat and b[2]])
    box.append((X(med) - 0.005, i - LANE + 0.015, X(med) + 0.075, i - LANE + 0.165))

for k in pos:                                     # i punti bloccano le etichette
    px, py = pos[k]
    r = raggio(k)
    box.append((px - r, py - 0.052 - 0.012 * (voti[k] - 1),
                px + r, py + 0.052 + 0.012 * (voti[k] - 1)))
for k in sorted(set(DA_ETICHETTARE), key=lambda k: (-voti[k], dati.BOOKS[k][2])):
    x, y = pos[k]
    tit = dati.BOOKS[k][0]
    tit = tit if len(tit) <= 30 else tit[:29].rstrip(" ,.") + "…"
    fs = 8.6 if voti[k] < 2 else 10.0
    w = len(tit) * 0.0053 * (fs / 8.6)
    scelta = None
    off = raggio(k) + 0.0035
    for lato in (1, -1):
        for dy in (0, -.15, .15, -.25, .25, -.34, .34, -.42, .42):
            x0 = x + off if lato > 0 else x - off - w
            if x0 < GUT or x0 + w > 1:
                continue
            c = (x0, y + dy - ALT / 2, x0 + w, y + dy + ALT / 2)
            if all(not (c[0] < b[2] and b[0] < c[2] and c[1] < b[3] and b[1] < c[3])
                   for b in box):
                scelta = (lato, dy, c); break
        if scelta:
            break
    if not scelta:
        continue
    lato, dy, c = scelta
    box.append(c)
    ax.text(x + (off if lato > 0 else -off), y + dy, tit, fontsize=fs,
            color="#ffffff" if voti[k] >= 2 else "#b9bfc7",
            ha="left" if lato > 0 else "right", va="center", zorder=5,
            fontfamily=BODY, fontweight="bold" if voti[k] >= 2 else "normal")
    if abs(dy) > 0.01:
        ax.plot([x, x + (off if lato > 0 else -off)], [y, y + dy],
                lw=0.5, color="#6b7078", alpha=0.55, zorder=3)

# ------------------------------------------------- istogramma per decennio
axh = fig.add_axes([0.028, 0.115, 0.955, 0.105])
axh.set_facecolor(BG)
axh.set_xlim(0, 1); axh.set_ylim(0, 34)
for s in axh.spines.values():
    s.set_visible(False)
axh.set_xticks([]); axh.set_yticks([])
dec = collections.Counter((b[2] // 10) * 10 for b in dati.BOOKS.values() if b[2])
for d, n in sorted(dec.items()):
    x0, x1 = X(d), X(d + 10)
    axh.add_patch(plt.Rectangle((x0 + 0.0012, 0), max(x1 - x0 - 0.0024, 0.0035), n,
                                color="#454b55" if d >= TAGLIO else "#2e333b", zorder=2))
    if n >= 5:
        axh.text((x0 + x1) / 2, n + 1.2, str(n), fontsize=9.5, color=DIM,
                 ha="center", va="bottom", fontfamily=MONO)
axh.text(GUT - 0.012, 30, "TITOLI PER DECENNIO", fontsize=13.5, color="#9aa0a8",
         ha="right", va="top", fontfamily=TITLE_FONT)

# ticks anno
for anno in [1400, 1600, 1800]:
    axh.text(X(anno), -2.6, str(anno), fontsize=9.5, color=DIM, ha="center",
             va="top", fontfamily=MONO, clip_on=False)
for anno in range(1900, 2031, 20):
    axh.text(X(anno), -2.6, str(anno), fontsize=9.5, color=DIM, ha="center",
             va="top", fontfamily=MONO, clip_on=False)

# rottura dell'asse: una fascia vuota tra la scala compressa e quella distesa
xb = (A1 + B0) / 2
for ax_, (y0, y1) in ((ax, ax.get_ylim()), (axh, axh.get_ylim())):
    ax_.add_patch(plt.Rectangle((A1 + 0.003, min(y0, y1)), B0 - A1 - 0.006,
                                abs(y1 - y0), color=BG, zorder=8))
    for off in (-0.0055, 0.0055):
        ax_.plot([xb + off - 0.004, xb + off + 0.004], [min(y0, y1), max(y0, y1)],
                 lw=1.0, color="#4d535c", zorder=9)
fig.text(A0, 0.076, "1300–1900: scala compressa, sei titoli in sei secoli",
         fontfamily=MONO, fontsize=8.5, color=DIMMER, ha="left")
fig.text(B0 + 0.008, 0.076, "1900–2026: scala distesa, 163 titoli in 126 anni",
         fontfamily=MONO, fontsize=8.5, color=DIMMER, ha="left")

# ------------------------------------------------- testata
testata(fig,
        "SETTE SECOLI SU UNO SCAFFALE",
        "169 titoli con anno accertato  ·  posizione = prima edizione originale  ·  corsie ordinate per anno mediano",
        "Con le serie TV non si poteva fare: i libri hanno una data, e le date raccontano una cosa che i titoli da soli non dicono.\n"
        "La fantascienza che mi consigliate ha in media quarantasette anni, l'economia e la tecnologia poco piu' di dieci. Il tema piu'\n"
        "antico e' quello che immagina il futuro; i temi piu' recenti sono quelli che provano a spiegare il presente. In mezzo,\n"
        "cinque secoli quasi vuoti e un solo libro prima del 1800: la Divina Commedia, che uno di voi mette al primo posto.",
        y=0.985, fs=58, wrap_y=0.916)

legenda(fig, [(dati.CATEGORIE[c], dati.COLORI[c]) for c in ORDINE],
        x=0.615, y=0.972, colonne=3, dx=0.130, dy=0.0215, fs=10.5)

pieResta(fig,
         "Fonte: 114 risposte alla conversazione  ·  6 titoli senza anno accertato esclusi da questa vista",
         "anno = prima edizione nella lingua originale, non la traduzione italiana  ·  punti piu' grandi = piu' persone lo hanno consigliato")

fig.savefig("2-secoli.png", dpi=110, facecolor=BG)
print("2-secoli.png ok —", len(libri), "titoli,", len(box), "etichette")
