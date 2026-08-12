# -*- coding: utf-8 -*-
"""7 — LA RETE DELLE PERSONE: quanto si somigliano fra loro i partecipanti.

Similarita' di Jaccard su tutte le coppie di persone. Attenzione a una trappola:
J dipende dalla lunghezza delle liste, e sulle serie il 61% delle liste ha un
titolo solo. Due persone che hanno scritto entrambe soltanto "Breaking Bad"
danno J = 1, che non vuol dire gusti identici. Quindi il conto serio si fa
tenendo solo chi si e' sbilanciato con almeno due titoli.
"""
import collections, itertools, importlib.util, os
import numpy as np
import matplotlib.pyplot as plt

import dati as serie
from stile import (BG, FG, DIM, DIMMER, GRID, MONO, BODY, TITLE_FONT,
                   testata, pieResta, sovrapposto)

C_SERIE, C_LIBRI = "#3b9dff", "#ff7a3d"


def carica(nome, percorso):
    spec = importlib.util.spec_from_file_location(nome, percorso)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


QUI = os.path.dirname(os.path.abspath(__file__))
libri = carica("dati_libri", os.path.join(QUI, "..", "libri", "dati.py"))
DATI = {"serie": serie.RECS, "libri": libri.RECS}


def liste(recs, minimo=1):
    L = collections.defaultdict(set)
    for p, k in recs:
        L[p].add(k)
    return {p: s for p, s in L.items() if len(s) >= minimo}


def jaccard(L):
    return np.array([len(L[a] & L[b]) / len(L[a] | L[b])
                     for a, b in itertools.combinations(sorted(L), 2)])


SOGLIE = list(range(1, 7))
curva = {n: [] for n in DATI}
for nome, recs in DATI.items():
    for s in SOGLIE:
        L = liste(recs, s)
        J = jaccard(L) if len(L) > 1 else np.array([0.0])
        curva[nome].append((len(L), len(J), float((J > 0).mean())))

MIN = 2                                   # la soglia onesta
JJ = {n: jaccard(liste(r, MIN)) for n, r in DATI.items()}
GREZZO = {n: jaccard(liste(r, 1)) for n, r in DATI.items()}

# l'artefatto, in numeri
identiche = {}
for nome, recs in DATI.items():
    L = liste(recs, 1)
    tot = uno = 0
    for a, b in itertools.combinations(sorted(L), 2):
        if L[a] == L[b]:
            tot += 1
            uno += len(L[a]) == 1
    identiche[nome] = (tot, uno)

FW, FH = 26.0, 15.6
fig = plt.figure(figsize=(FW, FH))
ov = sovrapposto(fig)

# ============================== pannello 1: la distribuzione, tolto l'artefatto
ax = fig.add_axes([0.045, 0.300, 0.415, 0.480])
ax.set_facecolor(BG)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
for s in ("left", "bottom"):
    ax.spines[s].set_color("#3a4048")
ax.tick_params(colors=DIM, labelsize=10)
ax.grid(True, axis="y", color=GRID, lw=0.8)
ax.set_axisbelow(True)

BIN = np.arange(0, 0.65, 0.05)
for nome, col, off in (("serie", C_SERIE, -0.010), ("libri", C_LIBRI, 0.010)):
    J = JJ[nome]
    pos = J[J > 0]
    q, _ = np.histogram(pos, bins=BIN)
    q = q / len(J) * 100                    # % su TUTTE le coppie, zeri compresi
    ax.bar(BIN[:-1] + 0.025 + off, q, width=0.019, color=col, zorder=5,
           label=nome)

ax.set_xlim(0, 0.62)
ax.set_xticks(np.arange(0, 0.65, 0.1))
ax.set_xlabel("quanto si somigliano due persone  (Jaccard)", fontsize=11,
              color=DIM, labelpad=9)
ax.set_ylabel("% di tutte le coppie", fontsize=11, color=DIM, labelpad=9)

# la barra dello zero, fuori scala, dichiarata a parte
zs = 100 * (JJ["serie"] == 0).mean()
zl = 100 * (JJ["libri"] == 0).mean()
ax.text(0.605, ax.get_ylim()[1] * 0.93,
        f"le coppie che non si toccano affatto\nnon stanno nel grafico:\n"
        f"{zs:.0f}% delle serie, {zl:.0f}% dei libri",
        fontsize=11, color="#9aa0a8", ha="right", va="top",
        fontfamily=BODY, linespacing=1.5)
ax.text(0.605, ax.get_ylim()[1] * 0.60, "serie TV", fontsize=13, color=C_SERIE,
        ha="right", va="center", fontfamily=BODY, fontweight="bold")
ax.text(0.605, ax.get_ylim()[1] * 0.52, "libri", fontsize=13, color=C_LIBRI,
        ha="right", va="center", fontfamily=BODY, fontweight="bold")

fig.text(0.045, 0.812, "QUANTO SI SOMIGLIANO DUE PERSONE A CASO",
         fontfamily=TITLE_FONT, fontsize=23, color=FG, ha="left", va="center")
fig.text(0.045, 0.792,
         f"Jaccard su ogni coppia, solo fra chi ha nominato almeno {MIN} titoli  ·  "
         f"{len(liste(DATI['serie'],MIN))} persone contro {len(liste(DATI['libri'],MIN))}",
         fontfamily=MONO, fontsize=9, color=DIMMER, ha="left", va="center")

# ===================== pannello 2: quanto regge, al variare della soglia
ax2 = fig.add_axes([0.545, 0.300, 0.425, 0.480])
ax2.set_facecolor(BG)
for s in ("top", "right"):
    ax2.spines[s].set_visible(False)
for s in ("left", "bottom"):
    ax2.spines[s].set_color("#3a4048")
ax2.tick_params(colors=DIM, labelsize=10)
ax2.grid(True, color=GRID, lw=0.8)
ax2.set_axisbelow(True)

for nome, col in (("serie", C_SERIE), ("libri", C_LIBRI)):
    y = [100 * q for _, _, q in curva[nome]]
    ax2.plot(SOGLIE, y, lw=3.0, color=col, zorder=5, marker="o", ms=9,
             markeredgecolor=BG, markeredgewidth=1.5)
    for s, v, (np_, nc, _) in zip(SOGLIE, y, curva[nome]):
        if s in (1, 2, 3, 5):
            ax2.annotate(f"{v:.1f}%".replace(".", ","), (s, v),
                         (s, v + (2.4 if nome == "serie" else -3.0)),
                         fontsize=12, color=col, fontfamily=MONO,
                         fontweight="bold", ha="center",
                         va="bottom" if nome == "serie" else "top")

ax2.axvline(MIN, color="#4d535c", lw=1.0, ls=(0, (4, 4)), zorder=2)
ax2.set_xlim(0.7, 6.3)
ax2.set_ylim(0, 42)
ax2.set_xticks(SOGLIE)
ax2.set_xlabel("tenendo solo chi ha nominato almeno N titoli", fontsize=11,
               color=DIM, labelpad=32)
# quante persone restano a ogni soglia: a destra il campione si assottiglia
# in fretta, e i punti finali vanno presi per quello che sono
for i, s in enumerate(SOGLIE):
    ax2.annotate(f"{curva['serie'][i][0]} · {curva['libri'][i][0]}", (s, 0),
                 (0, -26), textcoords="offset points", fontsize=9,
                 fontfamily=MONO, color=DIMMER, ha="center", va="top",
                 annotation_clip=False)
ax2.annotate("persone rimaste", (SOGLIE[0], 0), (-34, -26),
             textcoords="offset points", fontsize=9, fontfamily=MONO,
             color=DIMMER, ha="right", va="top", annotation_clip=False)
ax2.set_ylabel("% di coppie con almeno un titolo in comune", fontsize=11,
               color=DIM, labelpad=9)
ax2.text(6.2, 100 * curva["serie"][-1][2] + 2.5, "serie TV", fontsize=13,
         color=C_SERIE, ha="right", va="bottom", fontfamily=BODY, fontweight="bold")
ax2.text(6.2, 100 * curva["libri"][-1][2] - 2.0, "libri", fontsize=13,
         color=C_LIBRI, ha="right", va="top", fontfamily=BODY, fontweight="bold")

fig.text(0.545, 0.812, "E NON È UN EFFETTO DELLE LISTE CORTE",
         fontfamily=TITLE_FONT, fontsize=23, color=FG, ha="left", va="center")
fig.text(0.545, 0.792,
         "piu' alzo l'asticella, piu' le due curve si allontanano invece di avvicinarsi",
         fontfamily=MONO, fontsize=9, color=DIMMER, ha="left", va="center")

# ================================================== fascia dei numeri
r2 = curva["serie"][1][2] / curva["libri"][1][2]
r3 = curva["serie"][2][2] / curva["libri"][2][2]
CARD = [
    ("coppie che si incontrano  ·  tutti",
     f"{100*curva['serie'][0][2]:.1f}%".replace(".", ","),
     f"{100*curva['libri'][0][2]:.1f}%".replace(".", ",")),
    ("coppie che si incontrano  ·  da 2 titoli in su",
     f"{100*curva['serie'][1][2]:.1f}%".replace(".", ","),
     f"{100*curva['libri'][1][2]:.1f}%".replace(".", ",")),
    ("coppie che si incontrano  ·  da 3 titoli in su",
     f"{100*curva['serie'][2][2]:.1f}%".replace(".", ","),
     f"{100*curva['libri'][2][2]:.1f}%".replace(".", ",")),
    ("somiglianza media, fra chi si tocca",
     f"{JJ['serie'][JJ['serie']>0].mean():.2f}".replace(".", ","),
     f"{JJ['libri'][JJ['libri']>0].mean():.2f}".replace(".", ",")),
]
y0 = 0.150
for i, (etichetta, a, b) in enumerate(CARD):
    x = 0.045 + i * 0.2345
    ov.plot([x, x + 0.205], [y0 + 0.055] * 2, lw=1.0, color="#3a4048", clip_on=False)
    fig.text(x, y0 + 0.036, etichetta.upper(), fontfamily=MONO, fontsize=9,
             color=DIM, ha="left", va="center")
    fig.text(x + 0.058, y0 - 0.012, a, fontfamily=TITLE_FONT, fontsize=46,
             color=C_SERIE, ha="right", va="center")
    fig.text(x + 0.063, y0 - 0.012, "serie TV", fontfamily=BODY, fontsize=11,
             color=C_SERIE, ha="left", va="center")
    fig.text(x + 0.163, y0 - 0.012, b, fontfamily=TITLE_FONT, fontsize=46,
             color=C_LIBRI, ha="right", va="center")
    fig.text(x + 0.168, y0 - 0.012, "libri", fontfamily=BODY, fontsize=11,
             color=C_LIBRI, ha="left", va="center")

testata(fig,
        "E ADESSO LE PERSONE",
        f"ogni coppia di partecipanti, misurata con l'indice di Jaccard  ·  "
        f"soglia dichiarata: almeno {MIN} titoli a testa",
        "Ultimo giro, e stavolta non conto titoli ma persone: prendo due di voi a caso e guardo quanto le loro liste si\n"
        f"sovrappongono. Sul grezzo le serie darebbero {identiche['serie'][0]} coppie con gusti identici, ma {identiche['serie'][1]} di quelle {identiche['serie'][0]} sono\n"
        "gente che ha nominato un titolo solo, lo stesso: non e' affinita', e' una lista corta. Tolte quelle, restano due\n"
        f"mondi che si allontanano: fra chi si e' sbilanciato con almeno tre titoli, si incontra una coppia di spettatori su\n"
        f"cinque e una coppia di lettori su venti.",
        y=0.985, fs=58, wrap_y=0.900)

pieResta(fig,
         f"Fonte: le due conversazioni su @pinperepette  ·  a soglia {MIN}: "
         f"{len(liste(DATI['serie'],MIN))} profili e {len(JJ['serie']):,} coppie per le serie, "
         f"{len(liste(DATI['libri'],MIN))} profili e {len(JJ['libri']):,} coppie per i libri".replace(",", "."),
         "J = titoli in comune diviso titoli totali dei due  ·  le coppie a somiglianza zero sono la stragrande maggioranza e stanno fuori dal primo grafico")

fig.savefig("7-persone.png", dpi=110, facecolor=BG)
print("7-persone.png ok")
for nome in DATI:
    print(f"  {nome}: " + "  ".join(
        f"N>={s}: {100*q:.2f}% ({p} persone)" for s, (p, _, q) in zip(SOGLIE, curva[nome])))
print(f"  liste identiche: serie {identiche['serie']}, libri {identiche['libri']}"
      "   (totale, di cui da 1 titolo)")
