# -*- coding: utf-8 -*-
"""4 — IL GRAFO DEI GUSTI: quali titoli finiscono nella stessa risposta."""
import collections, itertools
import numpy as np
import matplotlib.pyplot as plt

import dati
from stile import (BG, FG, DIM, DIMMER, MONO, BODY, TITLE_FONT,
                   testata, pieResta, legenda)

voti = collections.Counter(k for _, k in dati.RECS)
per_persona = collections.defaultdict(set)
for p, k in dati.RECS:
    per_persona[p].add(k)

# --- coppie: quante persone diverse hanno nominato entrambi i titoli
coppie = collections.Counter()
for ks in per_persona.values():
    for a, b in itertools.combinations(sorted(ks), 2):
        coppie[(a, b)] += 1

MIN_VOTI, MIN_ARCO = 4, 2
nodi = sorted([k for k in voti if voti[k] >= MIN_VOTI], key=lambda k: -voti[k])
archi = [(a, b, n) for (a, b), n in coppie.items()
         if n >= MIN_ARCO and a in nodi and b in nodi]
# fuori i nodi isolati: qui interessa chi si tiene per mano
collegati = {a for a, b, _ in archi} | {b for a, b, _ in archi}
nodi = [k for k in nodi if k in collegati]
idx = {k: i for i, k in enumerate(nodi)}
N = len(nodi)

# ------------------------- disposizione circolare: un settore per ogni genere
generi = sorted({dati.SERIE[k][3] for k in nodi},
                key=lambda c: -sum(voti[k] for k in nodi if dati.SERIE[k][3] == c))
ordine = []
for g in generi:
    ordine += sorted([k for k in nodi if dati.SERIE[k][3] == g],
                     key=lambda k: -voti[k])

GAP = 0.13                      # spazio vuoto fra un genere e l'altro, in radianti
utile = 2 * np.pi - GAP * len(generi)
passo_nodo = utile / N

ang = {}
a = np.pi / 2 + 0.06            # si parte in alto e si gira in senso orario
for g in generi:
    ks = [k for k in ordine if dati.SERIE[k][3] == g]
    for k in ks:
        a -= passo_nodo
        ang[k] = a
    a -= GAP

R = 0.80                        # raggio del cerchio dei nodi
pos = {k: np.array([R * np.cos(t), R * np.sin(t)]) for k, t in ang.items()}

FW, FH = 26.0, 17.0
fig = plt.figure(figsize=(FW, FH))
ax = fig.add_axes([0.010, 0.030, 0.62, 0.80])
ax.set_facecolor(BG)
ax.set_xlim(-1.30, 1.30)
ax.set_ylim(-1.22, 1.22)
ax.set_aspect("equal")
ax.set_axis_off()

# archi come corde: più i due titoli sono vicini sul cerchio, meno curva serve
MAXA = max(n for _, _, n in archi)
for a_, b_, n in sorted(archi, key=lambda e: e[2]):
    p, q = pos[a_], pos[b_]
    delta = abs(((ang[a_] - ang[b_] + np.pi) % (2 * np.pi)) - np.pi)
    tira = 0.10 + 0.72 * (delta / np.pi)          # quanto la corda cade al centro
    ctrl = (p + q) / 2 * (1 - tira)
    t = np.linspace(0, 1, 60)[:, None]
    curva = (1 - t) ** 2 * p + 2 * (1 - t) * t * ctrl + t ** 2 * q
    ax.plot(curva[:, 0], curva[:, 1], lw=0.9 + 4.6 * (n - 1) / MAXA,
            color=dati.COLORI[dati.SERIE[a_][3]],
            alpha=0.30 + 0.52 * (n - 1) / MAXA, zorder=2,
            solid_capstyle="round")

# archi dei generi, appena fuori dal cerchio
for g in generi:
    ks = [k for k in ordine if dati.SERIE[k][3] == g]
    t = np.linspace(ang[ks[0]] + passo_nodo * 0.45,
                    ang[ks[-1]] - passo_nodo * 0.45, 80)
    ax.plot(0.905 * np.cos(t), 0.905 * np.sin(t), lw=3.0,
            color=dati.COLORI[g], alpha=0.55, zorder=3, solid_capstyle="butt")

for k in nodi:
    x, y0 = pos[k]
    col = dati.COLORI[dati.SERIE[k][3]]
    v = voti[k]
    ax.scatter([x], [y0], s=110 + 150 * v ** 0.9, color=col, zorder=6,
               edgecolors=BG, linewidths=1.8)
    ax.text(x, y0, str(v), fontfamily=MONO, fontsize=10, color=BG,
            ha="center", va="center", zorder=7, fontweight="bold")
    # etichetta radiale, girata per restare leggibile
    t = ang[k]
    gradi = np.degrees(t)
    destra = np.cos(t) >= 0
    ax.text(0.945 * np.cos(t), 0.945 * np.sin(t), "  " + dati.SERIE[k][0] + "  ",
            fontfamily=BODY, fontsize=11.5, color="#e2e5ea", zorder=7,
            rotation=gradi if destra else gradi + 180,
            rotation_mode="anchor",
            ha="left" if destra else "right", va="center")

# ------------------------------------------------ le coppie più forti, in lista
top = sorted(archi, key=lambda e: (-e[2], dati.SERIE[e[0]][0]))[:22]
XA, y = 0.660, 0.800
fig.text(XA, y + 0.038, "LE COPPIE CHE TORNANO INSIEME", fontfamily=TITLE_FONT,
         fontsize=25, color=FG, va="center", ha="left")
fig.text(XA, y + 0.017, "quante persone diverse hanno nominato tutti e due i titoli",
         fontfamily=MONO, fontsize=9, color=DIMMER, va="center", ha="left")
fig.plot = None
ax2 = fig.add_axes([0, 0, 1, 1], zorder=20)
ax2.set_axis_off(); ax2.set_xlim(0, 1); ax2.set_ylim(0, 1)
ax2.plot([XA, 0.972], [y + 0.005] * 2, lw=1.0, color="#3a4048", clip_on=False)
y -= 0.020

for a, b, n in top:
    fig.text(XA + 0.014, y, str(n), fontfamily=MONO, fontsize=13, color=FG,
             va="center", ha="right", fontweight="bold")
    ax2.scatter([XA + 0.024], [y], s=46, color=dati.COLORI[dati.SERIE[a][3]],
                zorder=21, clip_on=False, edgecolors="none")
    ax2.scatter([XA + 0.035], [y], s=46, color=dati.COLORI[dati.SERIE[b][3]],
                zorder=21, clip_on=False, edgecolors="none")
    fig.text(XA + 0.048, y, f"{dati.SERIE[a][0]}  +  {dati.SERIE[b][0]}",
             fontfamily=BODY, fontsize=12, color="#dfe3e8", va="center", ha="left")
    y -= 0.0245

# --------------------------------------------------------------- il commento
y -= 0.014
fig.text(XA, y, "COSA VUOL DIRE", fontfamily=TITLE_FONT, fontsize=25,
         color=FG, va="center", ha="left")
ax2.plot([XA, 0.972], [y - 0.016] * 2, lw=1.0, color="#3a4048", clip_on=False)
solitari = [k for k in voti if voti[k] >= MIN_VOTI and k not in collegati]
cross = [e for e in archi if dati.SERIE[e[0]][3] != dati.SERIE[e[1]][3]]


def assortativita(archi, genere):
    """Newman 2003 per attributi categorici: 0 = il genere non conta niente,
       1 = i generi sono mondi separati. Pesata sul numero di persone."""
    cats = sorted({genere[a] for a, b, _ in archi} | {genere[b] for a, b, _ in archi})
    idx = {c: i for i, c in enumerate(cats)}
    e = np.zeros((len(cats), len(cats)))
    for a, b, n in archi:
        i, j = idx[genere[a]], idx[genere[b]]
        e[i, j] += n / 2
        e[j, i] += n / 2
    e /= e.sum()
    s = float((e.sum(0) * e.sum(1)).sum())
    return (np.trace(e) - s) / (1 - s)


GEN = {k: v[3] for k, v in dati.SERIE.items()}
R_ASS = assortativita(archi, GEN)
# quanto vale davvero: rimescolo i generi sui nodi e rifaccio il conto
_rng = np.random.default_rng(20260812)
_nodi = sorted(collegati)
_et = [GEN[n] for n in _nodi]
_null = np.array([assortativita(archi, dict(zip(_nodi, _rng.permutation(_et))))
                  for _ in range(3000)])
P = float((np.abs(_null) >= abs(R_ASS)).mean())
fig.text(XA, y - 0.032,
         f"Un arco unisce due serie quando almeno {MIN_ARCO} persone le hanno nominate\n"
         "tutte e due nella stessa risposta. Non è una classifica di qualità: è una\n"
         "mappa di quello che, nella vostra testa, sta nello stesso scaffale.\n\n"
         "Sul cerchio i settori li ho messi io, per genere. Le corde no, quelle le\n"
         f"avete tirate voi, e {round(100*len(cross)/len(archi))} su 100 saltano da un settore all'altro invece di\n"
         "restare dentro. Contarle però non basta, perché quel numero dipende da\n"
         "come ho fatto io i settori. La misura giusta è l'assortatività: 1 vuol\n"
         f"dire generi separati, 0 che il genere non conta niente. Qui vale {R_ASS:.2f},\n"
         f"contro {_null.mean():+.2f} se rimescolo le etichette a caso (p = {P:.3f}). Cioè: il\n"
         "genere conta, ma poco. Breaking Bad si lega a Black Mirror, a Mr. Robot,\n"
         "a Dark, a Chernobyl.\n\n"
         "Il nodo con più legami è Breaking Bad, con 10. Il secondo non è Better\n"
         "Call Saul, è Mr. Robot con 7: è la serie che fa da ponte fra le due metà\n"
         "del cerchio. Se dovessi indovinare da una sola risposta che altro guarda\n"
         "chi ha risposto, guarderei lì.\n\n"
         f"Restano fuori {len(solitari)} titoli con {MIN_VOTI} voti o più che non hanno mai viaggiato\n"
         "in coppia — da Dr. House a Yellowstone. Piacciono, ma a gente che non si\n"
         "somiglia fra sé.",
         fontfamily=BODY, fontsize=11.5, color="#c3c7cd", va="top", ha="left",
         linespacing=1.55)

testata(fig,
        "COME STATE INSIEME",
        f"{N} titoli con {MIN_VOTI} voti o più  ·  {len(archi)} legami  ·  un legame = almeno {MIN_ARCO} persone hanno nominato entrambi",
        "Fin qui erano classifiche. Questa invece è la forma della conversazione: chi mette due serie nella stessa risposta le\n"
        "sta associando, e se lo fanno in tanti quel legame diventa una struttura. I settori del cerchio sono i generi, cioè una\n"
        "cosa che ho deciso io. Le corde dentro il cerchio no: quelle le avete tirate voi, e quasi la metà passa da un settore\n"
        "all'altro. Misurata come si deve, l'assortatività di questa rete rispetto al genere vale 0,29 su una scala che arriva a 1.",
        y=0.985, fs=58, wrap_y=0.918)

legenda(fig, [(dati.CATEGORIE[c], dati.COLORI[c]) for c in generi],
        x=0.660, y=0.962, colonne=2, dx=0.160, dy=0.020, fs=10.5)

pieResta(fig,
         f"Fonte: 323 risposte alla conversazione  ·  {len(coppie)} coppie osservate in tutto, {len(archi)} sopra la soglia",
         "settori ordinati per peso del genere, titoli per numero di voti  ·  dimensione = numero di persone che hanno consigliato il titolo")

fig.savefig("4-grafo.png", dpi=110, facecolor=BG)
print("4-grafo.png ok —", N, "nodi,", len(archi), "archi")
