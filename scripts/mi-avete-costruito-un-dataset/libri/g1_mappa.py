# -*- coding: utf-8 -*-
"""1 — LA BIBLIOTECA DEI COMMENTI: tutti i 195 titoli, ordinati in nove scaffali."""
import collections
import matplotlib.pyplot as plt

import dati
from stile import (BG, FG, DIM, DIMMER, MONO, BODY, TITLE_FONT,
                   testata, pieResta, sovrapposto)

voti = collections.Counter(k for _, k in dati.RECS)

SCAFFALI = [
    ["narrativa"],
    ["scienza", "fantascienza", "__sette"],
    ["economia", "potere", "tech"],
    ["storia", "mente", "esoterico", "__conti"],
]

def taglia(s, n):
    return s if len(s) <= n else s[: n - 1].rstrip(" ,.") + "…"

FW, FH = 26.0, 18.6
fig = plt.figure(figsize=(FW, FH))
ov = sovrapposto(fig)

X0 = 0.028
W = 0.2385
RIGA = 0.01245          # altezza di una riga, in frazione di figura
TOP = 0.845


def intestazione(fig, ov, x, y, testo, colore, spalla):
    fig.text(x, y, testo, fontfamily=TITLE_FONT, fontsize=17, color=colore,
             va="center", ha="left")
    fig.text(x + W - 0.014, y, spalla, fontfamily=MONO, fontsize=8.5,
             color=DIMMER, va="center", ha="right")
    ov.plot([x, x + W - 0.014], [y - 0.0088] * 2, lw=0.9, color=colore,
            alpha=0.45, clip_on=False)
    return y - RIGA * 1.85


def blocco_partenza(fig, ov, x, y):
    """I sette libri da cui e' partito il post."""
    y = intestazione(fig, ov, x, y, "I SETTE DI PARTENZA", "#7d838c", "fuori classifica")
    for tit, aut, anno in dati.DI_PARTENZA:
        ov.scatter([x + 0.0125], [y], s=13, color="#4e545c", clip_on=False,
                   edgecolors="none", zorder=6)
        fig.text(x + 0.0205, y, taglia(tit, 40), fontfamily=BODY, fontsize=9.6,
                 color="#9aa0a8", va="center", ha="left")
        fig.text(x + W - 0.0295, y, taglia(aut, 24), fontfamily=BODY,
                 fontsize=8.4, color="#6f757e", va="center", ha="right")
        fig.text(x + W - 0.014, y, str(anno), fontfamily=MONO, fontsize=8.2,
                 color="#5b6169", va="center", ha="right")
        y -= RIGA
    return y - RIGA * 0.95


def blocco_conti(fig, ov, x, y):
    y = intestazione(fig, ov, x, y, "I CONTI", "#7d838c", "in breve")
    anni = [b[2] for b in dati.BOOKS.values() if b[2]]
    narr = sum(1 for b in dati.BOOKS.values() if b[4] == "N")
    righe = [
        ("74", "persone hanno risposto con almeno un titolo"),
        ("195", "titoli diversi, per 223 consigli in tutto"),
        ("177", "titoli hanno un voto solo: il 91%"),
        ("5", "voti al massimo, e li prende Gödel, Escher, Bach"),
        (f"{min(anni)}–{max(anni)}", "dalla Divina Commedia a Malanga e Dell'Arti"),
        (f"{narr}", f"titoli di narrativa, {len(dati.BOOKS)-narr} di saggistica"),
        ("3,0", "titoli a testa in media, 10 il massimo"),
    ]
    for n, t in righe:
        fig.text(x + 0.030, y, n, fontfamily=MONO, fontsize=11, color=FG,
                 va="center", ha="right", fontweight="bold")
        fig.text(x + 0.038, y, t, fontfamily=BODY, fontsize=9.2, color="#9aa0a8",
                 va="center", ha="left")
        y -= RIGA * 1.15
    return y

for col, cats in enumerate(SCAFFALI):
    x = X0 + col * W
    y = TOP
    for cat in cats:
        if cat == "__sette":
            y = blocco_partenza(fig, ov, x, y)
            continue
        if cat == "__conti":
            y = blocco_conti(fig, ov, x, y)
            continue
        titoli = [k for k in dati.BOOKS if dati.BOOKS[k][3] == cat]
        titoli.sort(key=lambda k: (-voti[k], dati.BOOKS[k][0].lower()))
        col_cat = dati.COLORI[cat]
        y = intestazione(fig, ov, x, y, dati.CATEGORIE[cat].upper(), col_cat,
                         f"{len(titoli)} titoli")

        for k in titoli:
            tit, aut, anno, _, forma = dati.BOOKS[k]
            v = voti[k]
            ov.scatter([x + 0.0125], [y], s=13 + 26 * (v - 1), color=col_cat,
                       clip_on=False, edgecolors="none", zorder=6)
            if v > 1:
                fig.text(x + 0.0035, y, str(v), fontfamily=MONO, fontsize=9,
                         color=FG, va="center", ha="center", fontweight="bold")
            fig.text(x + 0.0205, y, taglia(tit, 40), fontfamily=BODY,
                     fontsize=9.6 if v == 1 else 10.2, color=FG if v > 1 else "#d3d7dd",
                     va="center", ha="left", fontweight="bold" if v > 1 else "normal")
            fig.text(x + W - 0.0295, y, taglia(aut, 24), fontfamily=BODY,
                     fontsize=8.4, color="#868c95", va="center", ha="right")
            fig.text(x + W - 0.014, y, str(anno) if anno else "—",
                     fontfamily=MONO, fontsize=8.2,
                     color="#6f757e" if anno else "#4a5058", va="center", ha="right")
            if forma == "N":     # segno discreto per la narrativa
                ov.plot([x + W - 0.0088], [y], marker="s", ms=2.4,
                        color=col_cat, alpha=0.75, clip_on=False)
            y -= RIGA
        y -= RIGA * 0.95

# ---------------------------------------------------------------- testata
testata(fig,
        "LA BIBLIOTECA DEI COMMENTI",
        "195 titoli in 114 risposte a @pinperepette  ·  nove scaffali  ·  un voto per persona per titolo",
        "Tutto quello che mi avete consigliato, messo in ordine. Il numero a sinistra e' quante persone diverse hanno nominato\n"
        "quel titolo: compare solo da due in su, perche' 177 libri su 195 sono stati consigliati da una persona sola.\n"
        "A destra l'autore e l'anno della prima edizione originale. Il quadratino segna la narrativa: il resto e' saggistica.",
        y=0.985, fs=58, wrap_y=0.918)

pieResta(fig,
         "Fonte: 114 risposte alla conversazione  ·  74 profili, 195 titoli, 223 consigli",
         "esclusi 15 autori citati senza un titolo preciso  ·  6 titoli senza anno accertato  ·  scaffali assegnati per tema")

fig.savefig("1-biblioteca.png", dpi=110, facecolor=BG)
print("1-biblioteca.png ok — riga finale a y =", round(y, 4))
