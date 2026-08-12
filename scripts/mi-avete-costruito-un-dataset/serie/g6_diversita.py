# -*- coding: utf-8 -*-
"""6 — QUANTI TITOLI CONTANO DAVVERO: profilo di diversita' e struttura sociale.

Tre misure che rispondono alla stessa domanda da tre angoli:
  - numeri di Hill (q=0 ricchezza, q=1 perplexity, q=2 inverso di Herfindahl)
  - quanto due persone a caso hanno in comune
  - se il grafo dei titoli co-consigliati esiste
Tutto a parita' di campione: 223 menzioni per entrambi, sorteggiate 500 volte.
"""
import collections, itertools, math, importlib.util, os
import numpy as np
import matplotlib.pyplot as plt

import dati as serie
from stile import (BG, FG, DIM, DIMMER, GRID, MONO, BODY, TITLE_FONT,
                   testata, pieResta, sovrapposto)

C_SERIE, C_LIBRI = "#3b9dff", "#ff7a3d"
SEED = 20260812


def carica(nome, percorso):
    spec = importlib.util.spec_from_file_location(nome, percorso)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


QUI = os.path.dirname(os.path.abspath(__file__))
libri = carica("dati_libri", os.path.join(QUI, "..", "libri", "dati.py"))
DATI = {"serie": serie.RECS, "libri": libri.RECS}
GENERE = {k: v[3] for k, v in serie.SERIE.items()}


def conteggi(recs):
    return np.array(sorted(collections.Counter(k for _, k in recs).values()),
                    dtype=float)[::-1]


def hill(c, q):
    """Numero di Hill di ordine q: quanti titoli equiprobabili darebbero
       la stessa diversita'. q=0 ricchezza, q=1 exp(entropia), q=2 1/Herfindahl."""
    p = c / c.sum()
    if abs(q - 1) < 1e-9:
        return math.exp(-(p * np.log(p)).sum())
    return float((p ** q).sum() ** (1 / (1 - q)))


def gini(c):
    x = np.sort(c)
    n = len(x)
    return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))


PARI = int(conteggi(DATI["libri"]).sum())          # 223: il campione piccolo comanda
QS = np.linspace(0, 3, 61)
rng = np.random.default_rng(SEED)

profilo, banda, extra = {}, {}, {}
for nome, recs in DATI.items():
    c = conteggi(recs)
    urna = np.repeat(np.arange(len(c)), c.astype(int))
    curve, gi = [], []
    for _ in range(500):
        estratto = rng.choice(urna, size=PARI, replace=False)
        cc = np.array(sorted(collections.Counter(estratto).values()),
                      dtype=float)[::-1]
        curve.append([hill(cc, q) for q in QS])
        gi.append(gini(cc))
    curve = np.array(curve)
    profilo[nome] = curve.mean(0)
    banda[nome] = (np.percentile(curve, 2.5, axis=0),
                   np.percentile(curve, 97.5, axis=0))
    extra[nome] = {"gini": float(np.mean(gi)), "conteggi": c}


# ----------------------------------------- struttura sociale: chi somiglia a chi
def sociale(recs):
    liste = collections.defaultdict(set)
    for p, k in recs:
        liste[p].add(k)
    coppie = list(itertools.combinations(sorted(liste), 2))
    insieme = sum(1 for a, b in coppie if liste[a] & liste[b])
    co = collections.Counter()
    for s in liste.values():
        for a, b in itertools.combinations(sorted(s), 2):
            co[(a, b)] += 1
    archi = sum(1 for n in co.values() if n >= 2)
    return {"persone": len(liste),
            "lista": np.mean([len(v) for v in liste.values()]),
            "coppie": len(coppie),
            "insieme": insieme,
            "quota": insieme / len(coppie),
            "archi": archi}


SOC = {n: sociale(r) for n, r in DATI.items()}


# ------------------------------------------------- assortativita' per genere
def archi_serie(min_voti=4, min_arco=2):
    voti = collections.Counter(k for _, k in serie.RECS)
    liste = collections.defaultdict(set)
    for p, k in serie.RECS:
        liste[p].add(k)
    co = collections.Counter()
    for s in liste.values():
        for a, b in itertools.combinations(sorted(s), 2):
            co[(a, b)] += 1
    return [(a, b, n) for (a, b), n in co.items()
            if n >= min_arco and voti[a] >= min_voti and voti[b] >= min_voti]


def assortativita(archi, genere):
    """Newman 2003 per attributi categorici, pesata sul numero di persone."""
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


ARCHI = archi_serie()
R_OSS = assortativita(ARCHI, GENERE)
_nodi = sorted({a for a, b, _ in ARCHI} | {b for a, b, _ in ARCHI})
_et = [GENERE[n] for n in _nodi]
_nulli = np.array([assortativita(ARCHI, dict(zip(_nodi, rng.permutation(_et))))
                   for _ in range(3000)])
P_VAL = float((np.abs(_nulli) >= abs(R_OSS)).mean())

# =============================================================================
FW, FH = 26.0, 15.6
fig = plt.figure(figsize=(FW, FH))
ov = sovrapposto(fig)

# ------------------------------------------- pannello 1: profilo di diversita'
ax = fig.add_axes([0.045, 0.300, 0.415, 0.480])
ax.set_facecolor(BG)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
for s in ("left", "bottom"):
    ax.spines[s].set_color("#3a4048")
ax.tick_params(colors=DIM, labelsize=10)
ax.grid(True, color=GRID, lw=0.8)
ax.set_axisbelow(True)

for nome, col in (("libri", C_LIBRI), ("serie", C_SERIE)):
    lo, hi = banda[nome]
    ax.fill_between(QS, lo, hi, color=col, alpha=0.16, zorder=3)
    ax.plot(QS, profilo[nome], lw=3.0, color=col, zorder=5)

for q, stile in ((0, ":"), (1, ":"), (2, ":")):
    ax.axvline(q, color="#4d535c", lw=0.9, ls=(0, (3, 4)), zorder=2)

for nome, col, dy in (("serie", C_SERIE, -13), ("libri", C_LIBRI, 9)):
    for q in (0, 1, 2):
        v = profilo[nome][np.argmin(np.abs(QS - q))]
        ax.scatter([q], [v], s=90, color=col, zorder=7, edgecolors=BG, linewidths=1.4)
        ax.annotate(f"{v:.0f}", (q, v), (q + 0.07, v + dy), fontsize=12.5,
                    color=col, fontfamily=MONO, fontweight="bold", va="center")

ax.text(2.95, profilo["libri"][-1] + 12, "libri", fontsize=13, color=C_LIBRI,
        ha="right", va="bottom", fontfamily=BODY, fontweight="bold")
ax.text(2.95, profilo["serie"][-1] - 12, "serie TV", fontsize=13, color=C_SERIE,
        ha="right", va="top", fontfamily=BODY, fontweight="bold")

ax.set_xlim(-0.08, 3.05)
ax.set_ylim(0, 215)
ax.set_xticks([0, 1, 2, 3])
ax.set_xticklabels(["q=0", "q=1", "q=2", "q=3"])
ax.set_ylabel("titoli equivalenti", fontsize=11, color=DIM, labelpad=9)
for q, testo in ((0, "quanti titoli esistono"), (1, "quanti ne sopravvivono"),
                 (2, "quanti contano davvero")):
    ax.text(q + 0.045, 6, testo, fontfamily=MONO, fontsize=9.5, color=DIMMER,
            rotation=90, va="bottom", ha="left")

fig.text(0.045, 0.812, "QUANTI TITOLI CONTANO DAVVERO", fontfamily=TITLE_FONT,
         fontsize=23, color=FG, ha="left", va="center")
fig.text(0.045, 0.792,
         "numeri di Hill: quanti titoli equiprobabili darebbero la stessa diversita'  ·  banda al 95% del sorteggio",
         fontfamily=MONO, fontsize=9, color=DIMMER, ha="left", va="center")

# --------------------------------- pannello 2: quanto si somigliano le persone
ax2 = fig.add_axes([0.545, 0.300, 0.425, 0.480])
ax2.set_facecolor(BG)
ax2.set_axis_off()
ax2.set_xlim(0, 1)
ax2.set_ylim(0, 1)

fig.text(0.545, 0.812, "E LE PERSONE, SI SOMIGLIANO?", fontfamily=TITLE_FONT,
         fontsize=23, color=FG, ha="left", va="center")
fig.text(0.545, 0.792,
         "ogni coppia di partecipanti, e se hanno almeno un titolo in comune",
         fontfamily=MONO, fontsize=9, color=DIMMER, ha="left", va="center")

RIGHE = [
    ("quante persone hanno risposto", "persone", "{:.0f}"),
    ("quanti titoli a testa, in media", "lista", "{:.2f}"),
    ("coppie di persone possibili", "coppie", "{:,.0f}"),
    ("coppie con almeno un titolo in comune", "insieme", "{:,.0f}"),
]
y = 0.93
for etichetta, chiave, fmt in RIGHE:
    ax2.text(0.0, y, etichetta.upper(), fontfamily=MONO, fontsize=9.5,
             color=DIM, va="center", ha="left")
    for nome, col, x in (("serie", C_SERIE, 0.63), ("libri", C_LIBRI, 0.90)):
        ax2.text(x, y, fmt.format(SOC[nome][chiave]).replace(",", "."),
                 fontfamily=MONO, fontsize=15, color=col, va="center", ha="right",
                 fontweight="bold")
    ax2.plot([0, 1], [y - 0.043] * 2, lw=0.9, color="#262a32")
    y -= 0.086

ax2.text(0.63, 0.985, "SERIE TV", fontfamily=MONO, fontsize=9.5, color=C_SERIE,
         va="center", ha="right")
ax2.text(0.90, 0.985, "LIBRI", fontfamily=MONO, fontsize=9.5, color=C_LIBRI,
         va="center", ha="right")

# la barra della quota
y -= 0.02
ax2.text(0.0, y, "IN PERCENTUALE", fontfamily=MONO, fontsize=9.5, color=DIM,
         va="center", ha="left")
y -= 0.075
for nome, col in (("serie", C_SERIE), ("libri", C_LIBRI)):
    q = SOC[nome]["quota"]
    ax2.add_patch(plt.Rectangle((0.0, y - 0.028), 0.86 * q / 0.04, 0.056,
                                color=col, zorder=4))
    ax2.text(0.88, y, f"{100*q:.2f}%".replace(".", ","), fontfamily=MONO,
             fontsize=17, color=col, va="center", ha="left", fontweight="bold")
    y -= 0.085

y -= 0.055
ax2.text(0.0, y, "COPPIE DI TITOLI CONSIGLIATE INSIEME DA 2 PERSONE O PIÙ, A QUALSIASI SOGLIA DI VOTI",
         fontfamily=MONO, fontsize=9.5, color=DIM, va="center", ha="left")
y -= 0.10
for nome, col in (("serie", C_SERIE), ("libri", C_LIBRI)):
    n = str(SOC[nome]["archi"])
    x0 = 0.0 if nome == "serie" else 0.30
    ax2.text(x0, y, n, fontfamily=TITLE_FONT, fontsize=62, color=col,
             va="center", ha="left")
    # l'etichetta segue la larghezza del numero, che puo' essere di una cifra
    ax2.text(x0 + 0.042 * len(n) + 0.021, y, nome,
             fontfamily=BODY, fontsize=12, color=col, va="center", ha="left")
ax2.text(0.60, y, "nel grafo circolare ne vedete 36:\n"
                  "le altre 10 toccano titoli\n"
                  "sotto i 4 voti, tenuti fuori di la'.",
         fontfamily=BODY, fontsize=12.5, color="#c3c7cd", va="center", ha="left",
         linespacing=1.5)

# ================================================== fascia dei numeri
CARD = [
    ("titoli osservati  ·  q=0",
     f"{profilo['serie'][0]:.0f}", f"{profilo['libri'][0]:.0f}"),
    ("titoli che contano  ·  q=2",
     f"{profilo['serie'][np.argmin(abs(QS-2))]:.0f}",
     f"{profilo['libri'][np.argmin(abs(QS-2))]:.0f}"),
    ("gini della classifica",
     f"{extra['serie']['gini']:.2f}".replace(".", ","),
     f"{extra['libri']['gini']:.2f}".replace(".", ",")),
    ("coppie di persone che si incontrano",
     f"{100*SOC['serie']['quota']:.1f}%".replace(".", ","),
     f"{100*SOC['libri']['quota']:.1f}%".replace(".", ",")),
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
q2s = profilo["serie"][np.argmin(abs(QS - 2))]
q2l = profilo["libri"][np.argmin(abs(QS - 2))]
testata(fig,
        "DUECENTODIECI TITOLI, MA QUANTI CONTANO?",
        f"stessa taglia di campione: {PARI} menzioni per entrambi, sorteggiate 500 volte  ·  seed fisso",
        "Contare i titoli diversi e' la misura piu' fragile che esista: dipende dal campione. Se dalle serie ne sorteggio\n"
        f"tanti quanti ne ho per i libri, i 210 titoli diventano {profilo['serie'][0]:.0f}. Il modo serio di rispondere e' chiedersi quanti titoli\n"
        f"equiprobabili darebbero la stessa diversita': per le serie sono {q2s:.0f}, per i libri {q2l:.0f}. Sono due mondi diversi, e la\n"
        "differenza non e' nel numero di titoli, e' in quanto la massa dei consigli si concentra su pochi.",
        y=0.985, fs=58, wrap_y=0.900)

pieResta(fig,
         f"Fonte: le due conversazioni su @pinperepette  ·  serie TV: {int(conteggi(serie.RECS).sum())} menzioni da {SOC['serie']['persone']} profili  ·  libri: {PARI} menzioni da {SOC['libri']['persone']} profili",
         f"assortativita' del grafo delle serie rispetto al genere: r = {R_OSS:+.2f} (p = {P_VAL:.3f} su 3000 permutazioni)")

fig.savefig("6-diversita.png", dpi=110, facecolor=BG)
print("6-diversita.png ok")
print(f"  Hill serie q0/q1/q2 = {profilo['serie'][0]:.1f} / "
      f"{profilo['serie'][np.argmin(abs(QS-1))]:.1f} / {q2s:.1f}")
print(f"  Hill libri q0/q1/q2 = {profilo['libri'][0]:.1f} / "
      f"{profilo['libri'][np.argmin(abs(QS-1))]:.1f} / {q2l:.1f}")
print(f"  assortativita' r = {R_OSS:+.3f}  p = {P_VAL:.4f}")
print(f"  archi: serie {SOC['serie']['archi']}, libri {SOC['libri']['archi']}")
