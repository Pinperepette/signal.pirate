# -*- coding: utf-8 -*-
"""3 — LA CLASSIFICA: i titoli con almeno due voti, gli autori, le librerie piu' lunghe."""
import collections
import matplotlib.pyplot as plt

import dati
from stile import (BG, FG, DIM, DIMMER, MONO, BODY, TITLE_FONT,
                   testata, pieResta, sovrapposto)

voti = collections.Counter(k for _, k in dati.RECS)
chi = collections.defaultdict(list)
for p, k in dati.RECS:
    chi[k].append(p)

classifica = sorted([k for k in voti if voti[k] >= 2],
                    key=lambda k: (-voti[k], dati.BOOKS[k][0].lower()))

autori_persone, autori_titoli = collections.defaultdict(set), collections.defaultdict(set)
for p, k in dati.RECS:
    autori_persone[dati.BOOKS[k][1]].add(p)
    autori_titoli[dati.BOOKS[k][1]].add(k)
for p, a in dati.AUTORI_SOLI:
    autori_persone[a].add(p)
autori = sorted(autori_persone, key=lambda a: (-len(autori_persone[a]),
                                               -len(autori_titoli[a]), a))[:13]

per_persona = collections.defaultdict(list)
for p, k in dati.RECS:
    per_persona[p].append(k)
librerie = sorted(per_persona, key=lambda p: (-len(per_persona[p]), p))[:16]

FW, FH = 26.0, 16.4
fig = plt.figure(figsize=(FW, FH))
ov = sovrapposto(fig)


def pip(x, y, colore, s=86):
    ov.scatter([x], [y], s=s, color=colore, zorder=6, clip_on=False,
               edgecolors="none")


# ------------------------------------------------------------- la classifica
X0, y = 0.028, 0.800
fig.text(X0, y + 0.038, "I TITOLI CON PIÙ DI UN VOTO", fontfamily=TITLE_FONT,
         fontsize=25, color=FG, va="center", ha="left")
fig.text(X0 + 0.245, y + 0.036, "diciotto su centonovantacinque", fontfamily=MONO,
         fontsize=9.5, color=DIMMER, va="center", ha="left")
ov.plot([X0, 0.505], [y + 0.021] * 2, lw=1.0, color="#3a4048", clip_on=False)

for i, k in enumerate(classifica):
    tit, aut, anno, cat, forma = dati.BOOKS[k]
    v = voti[k]
    col = dati.COLORI[cat]
    fig.text(X0 + 0.017, y, str(v), fontfamily=MONO, fontsize=21, color=col,
             va="center", ha="right", fontweight="bold")
    fig.text(X0 + 0.026, y + 0.006, tit, fontfamily=BODY, fontsize=15,
             color=FG, va="center", ha="left", fontweight="bold")
    fig.text(X0 + 0.026, y - 0.0135, f"{aut}, {anno}   ·   {dati.CATEGORIE[cat]}",
             fontfamily=BODY, fontsize=9.6, color="#868c95", va="center", ha="left")
    # i quadratini dei voti e i nomi di chi lo ha consigliato
    px = 0.302
    for j in range(v):
        pip(px + j * 0.0132, y + 0.006, col)
    fig.text(0.302, y - 0.0135, "  ".join("@" + p for p in sorted(chi[k], key=str.lower)),
             fontfamily=MONO, fontsize=8.6, color="#9aa0a8", va="center", ha="left")
    y -= 0.0424

# ------------------------------------------------------------- gli autori
XA, ya = 0.560, 0.800
fig.text(XA, ya + 0.038, "GLI AUTORI PIÙ NOMINATI", fontfamily=TITLE_FONT,
         fontsize=25, color=FG, va="center", ha="left")
fig.text(XA + 0.212, ya + 0.036, "per numero di persone diverse", fontfamily=MONO,
         fontsize=9.5, color=DIMMER, va="center", ha="left")
ov.plot([XA, 0.972], [ya + 0.021] * 2, lw=1.0, color="#3a4048", clip_on=False)

for a in autori:
    n = len(autori_persone[a])
    t = len(autori_titoli[a])
    cats = [dati.BOOKS[k][3] for k in autori_titoli[a]]
    col = dati.COLORI[collections.Counter(cats).most_common(1)[0][0]] if cats else "#6b7078"
    fig.text(XA + 0.014, ya, str(n), fontfamily=MONO, fontsize=14, color=col,
             va="center", ha="right", fontweight="bold")
    fig.text(XA + 0.022, ya, a, fontfamily=BODY, fontsize=12.5, color=FG,
             va="center", ha="left")
    for j in range(n):
        pip(XA + 0.176 + j * 0.0132, ya, col, s=72)
    fig.text(XA + 0.238, ya, f"{t} titol{'o' if t == 1 else 'i'}", fontfamily=MONO,
             fontsize=9, color=DIMMER, va="center", ha="left")
    esempi = sorted(autori_titoli[a], key=lambda k: -voti[k])[:2]
    testo = ", ".join(dati.BOOKS[k][0] for k in esempi)
    fig.text(XA + 0.292, ya, testo if len(testo) <= 46 else testo[:45] + "…",
             fontfamily=BODY, fontsize=9.4, color="#7d838c", va="center", ha="left")
    ya -= 0.0245

# ------------------------------------------------------------- le librerie
yl = ya - 0.048
fig.text(XA, yl + 0.030, "LE LIBRERIE PIÙ LUNGHE", fontfamily=TITLE_FONT,
         fontsize=25, color=FG, va="center", ha="left")
fig.text(XA + 0.206, yl + 0.028, "un quadrato per titolo, colorato per tema",
         fontfamily=MONO, fontsize=9.5, color=DIMMER, va="center", ha="left")
ov.plot([XA, 0.972], [yl + 0.013] * 2, lw=1.0, color="#3a4048", clip_on=False)
yl -= 0.018

for p in librerie:
    ks = sorted(per_persona[p], key=lambda k: dati.BOOKS[k][3])
    fig.text(XA + 0.014, yl, str(len(ks)), fontfamily=MONO, fontsize=13,
             color="#9aa0a8", va="center", ha="right", fontweight="bold")
    fig.text(XA + 0.022, yl, "@" + p, fontfamily=MONO, fontsize=11.5, color=FG,
             va="center", ha="left")
    for j, k in enumerate(ks):
        ov.add_patch(plt.Rectangle((XA + 0.176 + j * 0.0148, yl - 0.0083),
                                   0.0105, 0.0166,
                                   color=dati.COLORI[dati.BOOKS[k][3]], zorder=6,
                                   transform=fig.transFigure, clip_on=False))
    yl -= 0.0245

# ------------------------------------------------------------- testata
testata(fig,
        "LA CLASSIFICA",
        "195 titoli, 223 consigli, 74 persone  ·  un voto per persona per titolo",
        "Un solo libro in testa con cinque voti, e sotto un pianerottolo di tre a quota quattro. Sotto ai due voti non esiste\n"
        "classifica: 177 titoli su 195 sono stati nominati da una persona sola. Qui sopra c'e' tutto quello che due o piu'\n"
        "persone hanno scelto indipendentemente — con il nome di chi lo ha scelto, perche' e' l'unico posto in cui\n"
        "questa conversazione si e' trovata d'accordo.",
        y=0.985, fs=58, wrap_y=0.912)

pieResta(fig,
         "Fonte: 114 risposte alla conversazione  ·  gli autori contano anche le 15 citazioni senza titolo preciso",
         "colore = tema del titolo  ·  a parita' di voti, ordine alfabetico")

fig.savefig("3-classifica.png", dpi=110, facecolor=BG)
print("3-classifica.png ok —", len(classifica), "titoli in classifica")
