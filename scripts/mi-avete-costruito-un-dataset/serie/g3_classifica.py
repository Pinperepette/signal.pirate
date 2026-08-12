# -*- coding: utf-8 -*-
"""3 — LA CLASSIFICA: i titoli con almeno tre voti, i generi, le liste piu' lunghe."""
import collections
import matplotlib.pyplot as plt

import dati
from stile import (BG, FG, DIM, DIMMER, MONO, BODY, TITLE_FONT,
                   testata, pieResta, sovrapposto)

voti = collections.Counter(k for _, k in dati.RECS)
chi = collections.defaultdict(list)
for p, k in dati.RECS:
    chi[k].append(p)

def ordina(ks):
    return sorted(ks, key=lambda k: (-voti[k], dati.SERIE[k][0].lower()))


classifica = ordina([k for k in voti if voti[k] >= 5])
mezzo = ordina([k for k in voti if 3 <= voti[k] <= 4])

per_persona = collections.defaultdict(list)
for p, k in dati.RECS:
    per_persona[p].append(k)
liste = sorted(per_persona, key=lambda p: (-len(per_persona[p]), p))[:10]

# quanti voti prende ogni genere, e quanti titoli lo compongono
genere_voti = collections.Counter(dati.SERIE[k][3] for _, k in dati.RECS)
genere_titoli = collections.Counter(s[3] for s in dati.SERIE.values())
generi = sorted(genere_voti, key=lambda c: -genere_voti[c])

FW, FH = 26.0, 17.6
fig = plt.figure(figsize=(FW, FH))
ov = sovrapposto(fig)


def pip(x, y, colore, s=86):
    ov.scatter([x], [y], s=s, color=colore, zorder=6, clip_on=False,
               edgecolors="none")


# ------------------------------------------------------------- la classifica
X0, y = 0.028, 0.800
fig.text(X0, y + 0.038, "I TITOLI CON CINQUE VOTI O PIÙ", fontfamily=TITLE_FONT,
         fontsize=25, color=FG, va="center", ha="left")
fig.text(X0 + 0.286, y + 0.036, f"{len(classifica)} su {len(dati.SERIE)}",
         fontfamily=MONO, fontsize=9.5, color=DIMMER, va="center", ha="left")
ov.plot([X0, 0.505], [y + 0.021] * 2, lw=1.0, color="#3a4048", clip_on=False)

for k in classifica:
    tit, anno, paese, cat = dati.SERIE[k]
    v = voti[k]
    col = dati.COLORI[cat]
    fig.text(X0 + 0.017, y, str(v), fontfamily=MONO, fontsize=21, color=col,
             va="center", ha="right", fontweight="bold")
    fig.text(X0 + 0.026, y + 0.0055, tit, fontfamily=BODY, fontsize=15,
             color=FG, va="center", ha="left", fontweight="bold")
    fig.text(X0 + 0.026, y - 0.0115, f"{paese}, {anno}   ·   {dati.CATEGORIE[cat]}",
             fontfamily=BODY, fontsize=9.6, color="#868c95", va="center", ha="left")
    px = 0.242
    for j in range(v):
        pip(px + j * 0.0128, y + 0.0055, col)
    nomi = "  ".join("@" + p for p in sorted(chi[k], key=str.lower))
    fig.text(px, y - 0.0115, nomi if len(nomi) <= 118 else nomi[:117] + "…",
             fontfamily=MONO, fontsize=8.2, color="#9aa0a8", va="center", ha="left")
    y -= 0.0392

# ------------------------------------------------------------- i generi
XA, ya = 0.560, 0.800
fig.text(XA, ya + 0.038, "DOVE VANNO I VOTI", fontfamily=TITLE_FONT,
         fontsize=25, color=FG, va="center", ha="left")
fig.text(XA + 0.165, ya + 0.036, "consigli per genere, non titoli",
         fontfamily=MONO, fontsize=9.5, color=DIMMER, va="center", ha="left")
ov.plot([XA, 0.972], [ya + 0.021] * 2, lw=1.0, color="#3a4048", clip_on=False)

MAXV = max(genere_voti.values())
for cat in generi:
    n, t = genere_voti[cat], genere_titoli[cat]
    col = dati.COLORI[cat]
    fig.text(XA + 0.020, ya, str(n), fontfamily=MONO, fontsize=15, color=col,
             va="center", ha="right", fontweight="bold")
    fig.text(XA + 0.028, ya, dati.CATEGORIE[cat], fontfamily=BODY, fontsize=12.5,
             color=FG, va="center", ha="left")
    ov.add_patch(plt.Rectangle((XA + 0.196, ya - 0.0058),
                               0.145 * n / MAXV, 0.0116, color=col, zorder=6,
                               transform=fig.transFigure, clip_on=False))
    fig.text(XA + 0.350, ya, f"{t} titoli  ·  {n/t:.1f} voti a testa".replace(".", ","),
             fontfamily=MONO, fontsize=9, color=DIMMER, va="center", ha="left")
    ya -= 0.0265

# ------------------------------------------------- il gruppone di centro
ym = ya - 0.048
fig.text(XA, ym + 0.030, "SUBITO SOTTO: QUATTRO E TRE VOTI", fontfamily=TITLE_FONT,
         fontsize=25, color=FG, va="center", ha="left")
fig.text(XA + 0.300, ym + 0.028, f"altri {len(mezzo)} titoli",
         fontfamily=MONO, fontsize=9.5, color=DIMMER, va="center", ha="left")
ov.plot([XA, 0.972], [ym + 0.013] * 2, lw=1.0, color="#3a4048", clip_on=False)
ym -= 0.016

COL_M = 3
RIGHE_M = (len(mezzo) + COL_M - 1) // COL_M
for i, k in enumerate(mezzo):
    c, r = divmod(i, RIGHE_M)
    x = XA + c * 0.140
    yy = ym - r * 0.0166
    col = dati.COLORI[dati.SERIE[k][3]]
    fig.text(x + 0.012, yy, str(voti[k]), fontfamily=MONO, fontsize=10.5,
             color=col, va="center", ha="right", fontweight="bold")
    tit = dati.SERIE[k][0]
    fig.text(x + 0.019, yy, tit if len(tit) <= 26 else tit[:25] + "…",
             fontfamily=BODY, fontsize=10.2, color="#d3d7dd", va="center", ha="left")

# ------------------------------------------------------------- le liste
yl = ym - RIGHE_M * 0.0166 - 0.032
fig.text(XA, yl + 0.030, "LE LISTE PIÙ LUNGHE", fontfamily=TITLE_FONT,
         fontsize=25, color=FG, va="center", ha="left")
fig.text(XA + 0.183, yl + 0.028, "un quadrato per titolo, colorato per genere",
         fontfamily=MONO, fontsize=9.5, color=DIMMER, va="center", ha="left")
ov.plot([XA, 0.972], [yl + 0.013] * 2, lw=1.0, color="#3a4048", clip_on=False)
yl -= 0.018

for p in liste:
    ks = sorted(per_persona[p], key=lambda k: generi.index(dati.SERIE[k][3]))
    fig.text(XA + 0.014, yl, str(len(ks)), fontfamily=MONO, fontsize=13,
             color="#9aa0a8", va="center", ha="right", fontweight="bold")
    fig.text(XA + 0.022, yl, "@" + p, fontfamily=MONO, fontsize=11.5, color=FG,
             va="center", ha="left")
    for j, k in enumerate(ks):
        ov.add_patch(plt.Rectangle((XA + 0.166 + j * 0.0122, yl - 0.0072),
                                   0.0088, 0.0144,
                                   color=dati.COLORI[dati.SERIE[k][3]], zorder=6,
                                   transform=fig.transFigure, clip_on=False))
    yl -= 0.0215

# ------------------------------------------------------------- testata
UNO = sum(1 for k in voti if voti[k] == 1)
DUE = sum(1 for k in voti if voti[k] >= 2)
testata(fig,
        "LA CLASSIFICA",
        f"{len(dati.SERIE)} titoli, {len(dati.RECS)} consigli, {len({p for p,_ in dati.RECS})} persone  ·  un voto per persona per titolo",
        "Breaking Bad vince e non è nemmeno una gara: prende il 30% di voti in più del secondo. Ma sotto la vetta la\n"
        f"classifica si sbriciola subito — solo {DUE} titoli su {len(dati.SERIE)} sono stati nominati da almeno due persone, e {UNO} sono\n"
        "stati detti da una persona sola. Qui sopra c'è la parte su cui vi siete trovati d'accordo davvero, con il nome di chi\n"
        "l'ha scelta, perché il consenso in questa conversazione è una cosa rara e vale la pena firmarla.",
        y=0.985, fs=58, wrap_y=0.912)

pieResta(fig,
         "Fonte: 323 risposte alla conversazione, raccolte il 12 agosto  ·  un voto per persona per titolo, le ripetizioni non contano",
         "colore = genere prevalente  ·  a parità di voti, ordine alfabetico")

fig.savefig("3-classifica.png", dpi=110, facecolor=BG)
print("3-classifica.png ok —", len(classifica), "titoli in classifica")
