# -*- coding: utf-8 -*-
"""5 — SERIE TV vs LIBRI: due conversazioni, due forme completamente diverse.

A differenza della prima versione, qui la coda delle serie non e' ricostruita
dai totali pubblicati: e' il dataset vero, ricontato dalle risposte.
"""
import collections, math, importlib.util, os
import matplotlib.pyplot as plt

import dati as serie
from stile import (BG, FG, DIM, DIMMER, GRID, MONO, BODY, TITLE_FONT,
                   testata, pieResta, sovrapposto)

C_SERIE, C_LIBRI = "#3b9dff", "#ff7a3d"


def carica(nome, percorso):
    spec = importlib.util.spec_from_file_location(nome, percorso)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


libri = carica("dati_libri",
               os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "libri", "dati.py"))

SERIE = sorted(collections.Counter(k for _, k in serie.RECS).values(), reverse=True)
LIBRI = sorted(collections.Counter(k for _, k in libri.RECS).values(), reverse=True)
P_SERIE = len({p for p, _ in serie.RECS})
P_LIBRI = len({p for p, _ in libri.RECS})


def rarefazione(conteggi, k):
    """Hurlbert: titoli diversi attesi dopo k menzioni estratte a caso."""
    N = sum(conteggi)
    lg = math.lgamma

    def logC(n, r):
        return -math.inf if r > n or r < 0 else lg(n + 1) - lg(r + 1) - lg(n - r + 1)

    d = logC(N, k)
    return sum(1 - math.exp(logC(N - n, k) - d) for n in conteggi)


PARI = sum(LIBRI)                       # il campione piccolo detta il confronto
q_libri = rarefazione(LIBRI, PARI)
q_serie = rarefazione(SERIE, PARI)

FW, FH = 26.0, 15.6
fig = plt.figure(figsize=(FW, FH))
ov = sovrapposto(fig)

# ================================================== pannello 1: rarefazione
ax = fig.add_axes([0.045, 0.235, 0.415, 0.545])
ax.set_facecolor(BG)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
for s in ("left", "bottom"):
    ax.spines[s].set_color("#3a4048")
ax.tick_params(colors=DIM, labelsize=10)
ax.grid(True, color=GRID, lw=0.8)
ax.set_axisbelow(True)

ax.plot(range(1, sum(SERIE) + 1, 3),
        [rarefazione(SERIE, k) for k in range(1, sum(SERIE) + 1, 3)],
        lw=3.0, color=C_SERIE, zorder=4)
ax.plot(range(1, PARI + 1, 2),
        [rarefazione(LIBRI, k) for k in range(1, PARI + 1, 2)],
        lw=3.0, color=C_LIBRI, zorder=5)
ax.axvline(PARI, color="#4d535c", lw=1.0, ls=(0, (4, 4)), zorder=2)
ax.scatter([PARI, PARI], [q_libri, q_serie], s=110, color=[C_LIBRI, C_SERIE],
           zorder=6, edgecolors=BG, linewidths=1.4)
ax.annotate(f"{len(LIBRI)} titoli diversi\nin {PARI} menzioni", (PARI, q_libri),
            (PARI + 42, q_libri + 36), fontsize=12, color=C_LIBRI,
            fontfamily=BODY, fontweight="bold",
            arrowprops=dict(arrowstyle="-", color=C_LIBRI, lw=1.0), va="center")
ax.annotate(f"alla stessa quota le serie\nne avrebbero prodotti {q_serie:.0f}",
            (PARI, q_serie), (PARI + 44, q_serie - 40), fontsize=12,
            color=C_SERIE, fontfamily=BODY,
            arrowprops=dict(arrowstyle="-", color=C_SERIE, lw=1.0), va="center")
ax.text(sum(SERIE) - 8, len(SERIE) + 4, f"serie TV\n{len(SERIE)} titoli, {sum(SERIE)} menzioni",
        fontsize=12, color=C_SERIE, ha="right", va="bottom", fontfamily=BODY,
        linespacing=1.4)
ax.text(28, len(SERIE) * 1.13, f"libri\n{len(LIBRI)} titoli, {PARI} menzioni",
        fontsize=12, color=C_LIBRI, ha="left", va="center", fontfamily=BODY,
        linespacing=1.4)

ax.set_xlim(0, sum(SERIE) * 1.06)
ax.set_ylim(0, max(len(SERIE), len(LIBRI)) * 1.22)
ax.set_xlabel("menzioni raccolte", fontsize=11, color=DIM, labelpad=9)
ax.set_ylabel("titoli diversi", fontsize=11, color=DIM, labelpad=9)
fig.text(0.045, 0.812, "QUANTI TITOLI NUOVI OGNI CENTO MENZIONI",
         fontfamily=TITLE_FONT, fontsize=23, color=FG, ha="left", va="center")
fig.text(0.045, 0.792,
         "curva di rarefazione: titoli diversi attesi dopo k menzioni, a parita' di campione",
         fontfamily=MONO, fontsize=9, color=DIMMER, ha="left", va="center")

# ================================================== pannello 2: coda lunga
ax2 = fig.add_axes([0.545, 0.235, 0.425, 0.545])
ax2.set_facecolor(BG)
for s in ("top", "right"):
    ax2.spines[s].set_visible(False)
for s in ("left", "bottom"):
    ax2.spines[s].set_color("#3a4048")
ax2.tick_params(colors=DIM, labelsize=10)
ax2.grid(True, color=GRID, lw=0.8)
ax2.set_axisbelow(True)
ax2.set_xscale("log")

ax2.step(range(1, len(SERIE) + 1), SERIE, where="post", lw=2.6, color=C_SERIE, zorder=4)
ax2.step(range(1, len(LIBRI) + 1), LIBRI, where="post", lw=2.6, color=C_LIBRI, zorder=5)
ax2.fill_between(range(1, len(SERIE) + 1), SERIE, step="post", color=C_SERIE,
                 alpha=0.13, zorder=2)
ax2.fill_between(range(1, len(LIBRI) + 1), LIBRI, step="post", color=C_LIBRI,
                 alpha=0.16, zorder=3)

ax2.scatter([1], [SERIE[0]], s=120, color=C_SERIE, zorder=6, edgecolors=BG, linewidths=1.4)
ax2.annotate(f"Breaking Bad, {SERIE[0]} voti", (1, SERIE[0]), (1.32, SERIE[0] - 0.4),
             fontsize=12, color=C_SERIE, fontfamily=BODY, va="center", fontweight="bold")
ax2.scatter([1], [LIBRI[0]], s=120, color=C_LIBRI, zorder=6, edgecolors=BG, linewidths=1.4)
ax2.annotate(f"il libro piu' votato si ferma a {LIBRI[0]}:\ne' Godel, Escher, Bach",
             (1, LIBRI[0]), (1.5, LIBRI[0] + 3.4), fontsize=12, color=C_LIBRI,
             fontfamily=BODY, arrowprops=dict(arrowstyle="-", color=C_LIBRI, lw=1.0),
             va="center", fontweight="bold")
uno_s = sum(1 for x in SERIE if x == 1)
uno_l = sum(1 for x in LIBRI if x == 1)
ax2.annotate(f"da qui in poi un voto solo:\n{uno_s} serie e {uno_l} libri",
             (len(LIBRI) - uno_l + 4, 1), (48, 11.6), fontsize=11.5, color="#9aa0a8",
             fontfamily=BODY, va="center", linespacing=1.4,
             arrowprops=dict(arrowstyle="-", color="#6b7078", lw=1.0))

ax2.set_xlim(0.93, max(len(SERIE), len(LIBRI)) * 1.4)
ax2.set_ylim(0, SERIE[0] * 1.12)
ax2.set_xticks([1, 2, 5, 10, 20, 50, 100, 200])
ax2.set_xticklabels(["1°", "2°", "5°", "10°", "20°", "50°", "100°", "200°"])
ax2.set_xlabel("posizione in classifica (scala logaritmica)", fontsize=11,
               color=DIM, labelpad=9)
ax2.set_ylabel("persone che lo hanno consigliato", fontsize=11, color=DIM, labelpad=9)
fig.text(0.545, 0.812, "LA CODA, POSTO PER POSTO", fontfamily=TITLE_FONT,
         fontsize=23, color=FG, ha="left", va="center")
fig.text(0.545, 0.792, "voti del titolo in n-esima posizione, dalle serie TV ai libri",
         fontfamily=MONO, fontsize=9, color=DIMMER, ha="left", va="center")

# ================================================== fascia dei numeri
CARD = [
    ("titoli nominati da una persona sola",
     f"{round(100*uno_s/len(SERIE))}%", f"{round(100*uno_l/len(LIBRI))}%"),
    ("menzioni che portano un titolo nuovo",
     f"{round(100*len(SERIE)/sum(SERIE))}%", f"{round(100*len(LIBRI)/sum(LIBRI))}%"),
    ("titoli diversi per partecipante",
     f"{len(SERIE)/P_SERIE:.2f}".replace(".", ","),
     f"{len(LIBRI)/P_LIBRI:.2f}".replace(".", ",")),
    ("voti del titolo in testa", str(SERIE[0]), str(LIBRI[0])),
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

# ================================================== testata
testata(fig,
        "LE SERIE CI TROVANO D'ACCORDO, I LIBRI NO",
        f"stessa domanda, stesso pubblico, un giorno di distanza  ·  323 risposte sulle serie, 114 sui libri",
        f"Sulle serie la conversazione converge: {round(100*len(SERIE)/sum(SERIE))} menzioni su 100 portano un titolo che non aveva ancora detto nessuno,\n"
        f"le altre ripetono. Con i libri quella quota sale a {round(100*len(LIBRI)/sum(LIBRI))} su 100: quasi ogni risposta aggiunge qualcosa di inedito. E non\n"
        f"e' perche' i libri sono di piu' — sono di meno. A parita' di campione, {PARI} menzioni per entrambi, i vostri libri\n"
        f"producono il {round(100*(q_libri/q_serie-1))}% di titoli diversi in piu' delle vostre serie. Guardare e' un fatto collettivo; leggere no.",
        y=0.985, fs=58, wrap_y=0.900)

pieResta(fig,
         f"Fonte: le due conversazioni su @pinperepette, ricontate il 12 agosto  ·  serie TV: {len(SERIE)} titoli, {sum(SERIE)} menzioni, {P_SERIE} profili  ·  libri: {len(LIBRI)} titoli, {PARI} menzioni, {P_LIBRI} profili",
         "questa volta la coda delle serie non e' stimata: e' il dataset completo, titolo per titolo")

fig.savefig("5-serie-vs-libri.png", dpi=110, facecolor=BG)
print("5-serie-vs-libri.png ok — rapporto a parita' di campione:",
      round(q_libri / q_serie, 3))
