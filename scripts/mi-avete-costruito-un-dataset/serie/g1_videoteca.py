# -*- coding: utf-8 -*-
"""1 — LA VIDEOTECA DEI COMMENTI: tutti i titoli consigliati, in nove scaffali."""
import collections
import matplotlib.pyplot as plt

import dati
from stile import (BG, FG, DIM, DIMMER, MONO, BODY, TITLE_FONT,
                   testata, pieResta, sovrapposto)

voti = collections.Counter(k for _, k in dati.RECS)
PERSONE = len({p for p, _ in dati.RECS})
UNO = sum(1 for k in voti if voti[k] == 1)

SCAFFALI = [
    ["crime"],
    ["scifi", "horror"],
    ["spionaggio", "storico", "animazione", "__conti"],
    ["commedia", "drama", "italiana"],
]


def taglia(s, n):
    return s if len(s) <= n else s[: n - 1].rstrip(" ,.") + "…"


FW, FH = 26.0, 18.6
fig = plt.figure(figsize=(FW, FH))
ov = sovrapposto(fig)

X0 = 0.028
W = 0.2385
RIGA = 0.01162
TOP = 0.845


def intestazione(fig, ov, x, y, testo, colore, spalla):
    fig.text(x, y, testo, fontfamily=TITLE_FONT, fontsize=17, color=colore,
             va="center", ha="left")
    fig.text(x + W - 0.014, y, spalla, fontfamily=MONO, fontsize=8.5,
             color=DIMMER, va="center", ha="right")
    ov.plot([x, x + W - 0.014], [y - 0.0088] * 2, lw=0.9, color=colore,
            alpha=0.45, clip_on=False)
    return y - RIGA * 1.85


def blocco_conti(fig, ov, x, y):
    y = intestazione(fig, ov, x, y, "I CONTI", "#7d838c", "in breve")
    anni = [s[1] for s in dati.SERIE.values() if s[1]]
    usa = sum(1 for s in dati.SERIE.values() if s[2] == "USA")
    top = voti.most_common(1)[0]
    righe = [
        (str(PERSONE), "persone hanno risposto con almeno un titolo"),
        (str(len(dati.SERIE)), f"titoli diversi, per {len(dati.RECS)} consigli in tutto"),
        (str(UNO), f"titoli hanno un voto solo: il {round(100*UNO/len(voti))}%"),
        (str(top[1]), f"voti al massimo, e sono tutti per {dati.SERIE[top[0]][0]}"),
        (f"{min(anni)}–{max(anni)}", "da Ai confini della realtà a Pluribus"),
        (f"{usa}", f"titoli americani su {len(dati.SERIE)}: il resto è il {round(100*(1-usa/len(dati.SERIE)))}%"),
        (f"{len(dati.RECS)/PERSONE:.1f}".replace(".", ","),
         "titoli a testa in media, 25 il massimo"),
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
        if cat == "__conti":
            y = blocco_conti(fig, ov, x, y)
            continue
        titoli = [k for k in dati.SERIE if dati.SERIE[k][3] == cat]
        titoli.sort(key=lambda k: (-voti[k], dati.SERIE[k][0].lower()))
        col_cat = dati.COLORI[cat]
        y = intestazione(fig, ov, x, y, dati.CATEGORIE[cat].upper(), col_cat,
                         f"{len(titoli)} titoli")

        for k in titoli:
            tit, anno, paese, _ = dati.SERIE[k]
            v = voti[k]
            ov.scatter([x + 0.0125], [y], s=13 + 16 * (v - 1), color=col_cat,
                       clip_on=False, edgecolors="none", zorder=6)
            if v > 1:
                fig.text(x + 0.0035, y, str(v), fontfamily=MONO, fontsize=9,
                         color=FG, va="center", ha="center", fontweight="bold")
            fig.text(x + 0.0205, y, taglia(tit, 40), fontfamily=BODY,
                     fontsize=9.6 if v == 1 else 10.2,
                     color=FG if v > 1 else "#d3d7dd",
                     va="center", ha="left", fontweight="bold" if v > 1 else "normal")
            fig.text(x + W - 0.0295, y, paese, fontfamily=BODY,
                     fontsize=8.4, color="#868c95", va="center", ha="right")
            fig.text(x + W - 0.014, y, str(anno) if anno else "—",
                     fontfamily=MONO, fontsize=8.2,
                     color="#6f757e" if anno else "#4a5058", va="center", ha="right")
            y -= RIGA
        y -= RIGA * 0.95

testata(fig,
        "LA VIDEOTECA",
        f"{len(dati.SERIE)} titoli in 323 risposte a @pinperepette  ·  nove scaffali  ·  un voto per persona per titolo",
        "Tutto quello che mi avete consigliato, messo in ordine. Il numero a sinistra è quante persone diverse hanno nominato\n"
        f"quel titolo: compare solo da due in su, perché {UNO} serie su {len(dati.SERIE)} sono state consigliate da una persona sola.\n"
        "A destra il paese di produzione e l'anno della prima messa in onda della serie originale.",
        y=0.985, fs=58, wrap_y=0.918)

pieResta(fig,
         f"Fonte: 323 risposte alla conversazione  ·  {PERSONE} profili, {len(dati.SERIE)} titoli, {len(dati.RECS)} consigli",
         "5 titoli senza anno accertato  ·  scaffali assegnati per genere prevalente")

fig.savefig("1-videoteca.png", dpi=110, facecolor=BG)
print("1-videoteca.png ok —", len(dati.SERIE), "titoli")
