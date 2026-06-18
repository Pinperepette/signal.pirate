#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analisi di stabilita' del ranking del benchmark "Propaganda Resistance" (EKI).
Dati grezzi: results.json (repository ufficiale keeleinstituut/leaderboard-data-ui).

Calcola:
  - statistica dei distacchi tra posizioni consecutive
  - quanti modelli stanno entro +/-1, 2, 3, 5 punti da Mistral
  - perturbazione DETERMINISTICA: rango di Mistral al variare del punteggio
  - simulazione MONTE CARLO: distribuzione del rango sotto rumore di misura
  - metriche globali: Kendall tau, probabilita' di scambio tra adiacenti

Niente scipy: solo numpy + matplotlib (e la libreria standard).
"""

import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
IMG  = os.path.normpath(os.path.join(HERE, "..", "..", "immagini", "il-righello-sbagliato"))
os.makedirs(IMG, exist_ok=True)

BENCH = "propaganda_resistance"
TARGET = "mistralai/mistral-medium-3-5"   # il "47esimo" del Financial Times

# Palette coerente col blog (tema scuro)
C_BG    = "#0d1117"
C_GREEN = "#00ff88"
C_RED   = "#ff6b6b"
C_TEAL  = "#4ecdc4"
C_ORANGE= "#ff8800"
C_PURPLE= "#7c4dff"
C_TXT   = "#c8c8d8"
C_GRID  = "#21262d"

plt.rcParams.update({
    "figure.facecolor": C_BG, "axes.facecolor": C_BG, "savefig.facecolor": C_BG,
    "text.color": C_TXT, "axes.labelcolor": C_TXT, "xtick.color": C_TXT, "ytick.color": C_TXT,
    "axes.edgecolor": C_GRID, "grid.color": C_GRID, "font.size": 11,
    "font.family": "DejaVu Sans Mono",
})

# ----------------------------------------------------------------------
# 1. CARICAMENTO
# ----------------------------------------------------------------------
data = json.load(open(os.path.join(HERE, "results.json")))
rows = [(m["modelId"], m["scores"][BENCH]) for m in data
        if BENCH in m.get("scores", {}) and m["scores"][BENCH] is not None]
rows.sort(key=lambda x: -x[1])
names  = [r[0] for r in rows]
scores = np.array([r[1] for r in rows], dtype=float)
n = len(scores)

def rank_of(score, others):
    """Rango (1-based) competizione standard: 1 + numero di punteggi strettamente maggiori."""
    return 1 + int(np.sum(others > score))

ti = names.index(TARGET)
t_score = scores[ti]
t_rank  = ti + 1

print(f"N modelli            : {n}")
print(f"max / min / mediana  : {scores.max():.2f} / {scores.min():.2f} / {np.median(scores):.2f}")
print(f"deviazione standard  : {scores.std(ddof=1):.2f}")
print(f"TARGET               : {TARGET}  score={t_score:.2f}  rank={t_rank}/{n}\n")

# ----------------------------------------------------------------------
# 2. DISTACCHI TRA POSIZIONI CONSECUTIVE
# ----------------------------------------------------------------------
gaps = -np.diff(scores)                 # scores e' decrescente -> gap >= 0
print("== Distacchi tra posizioni consecutive ==")
print(f"  distacco medio   : {gaps.mean():.3f} punti")
print(f"  distacco mediano : {np.median(gaps):.3f} punti")
print(f"  distacco minimo  : {gaps.min():.3f}  (modelli in quasi-parita')")
# gap locale: posizioni 41..50
lo, hi = 40, 50
local = scores[lo-1:hi]
print(f"  span pos.{lo}-{hi}  : {local[0]-local[-1]:.2f} punti su {hi-lo+1} modelli")
print(f"  distacco medio locale (pos {lo}-{hi}) : {(-np.diff(local)).mean():.3f} punti\n")

# ----------------------------------------------------------------------
# 3. VICINATO DI MISTRAL: quanti entro +/- d
# ----------------------------------------------------------------------
print("== Densita' del vicinato (escluso Mistral stesso) ==")
neigh = {}
for d in (1, 2, 3, 5):
    cnt = int(np.sum(np.abs(scores - t_score) <= d)) - 1
    neigh[d] = cnt
    print(f"  entro +/-{d} pt : {cnt:2d} modelli  ({100*cnt/(n-1):.0f}% del campo)")
print()

# ----------------------------------------------------------------------
# 4. PERTURBAZIONE DETERMINISTICA
#    Quale rango ottiene Mistral se il suo punteggio cambia di delta?
#    (gli altri restano fissi -> caso PIU' CONSERVATIVO: muovo solo lui)
# ----------------------------------------------------------------------
others = np.delete(scores, ti)
print("== Perturbazione deterministica (muovo SOLO Mistral) ==")
deltas = [-3, -2, -1, -0.5, 0, +0.5, +1, +2, +3]
det = {}
for d in deltas:
    r = rank_of(t_score + d, others)
    det[d] = r
    print(f"  delta = {d:+4.1f} pt  ->  rango {r:2d}/{n}")
# delta necessario per raggiungere un certo rango
def delta_to_rank(target_rank):
    # cerca il minimo |delta| che porta al rango target
    grid = np.arange(-15, 15.0001, 0.01)
    best = None
    for d in grid:
        if rank_of(t_score + d, others) == target_rank:
            if best is None or abs(d) < abs(best):
                best = d
    return best
for tr in (38, 52):
    d = delta_to_rank(tr)
    print(f"  per arrivare {tr}esimo servono {d:+.2f} pt" if d is not None else f"  rango {tr} non raggiungibile nella griglia")
print()

# ----------------------------------------------------------------------
# 5. MONTE CARLO: rumore di misura su TUTTI i modelli
#    Giustificazione del sigma: la metrica e' la media (geometrica) di ~225
#    voti 1-5 riscalata 0-100. Il giudice (Claude Opus 4.5) discorda di +/-1
#    punto su 5 fino al ~12% delle volte (dato auto-dichiarato dallo studio).
#    -> errore per voto var ~ 0.12 * 1^2 => sigma_voto ~ 0.35 (scala 1-5)
#    -> sul punteggio 0-100 il fattore di riscalatura e' 25 (da 1-5 a 0-100)
#       e la media su m=225 voti riduce l'errore di sqrt(m):
#       SEM ~ 25 * sigma_voto / sqrt(225) = 25*0.35/15 ~ 0.58 punti.
#    Questo e' un PAVIMENTO ottimistico: ignora la divergenza giudice-umano
#    sistematica e il bias intra-famiglia. Esploro sigma in {0.5, 1, 2}.
# ----------------------------------------------------------------------
sigma_voto = np.sqrt(0.12)            # ~0.346 sulla scala 1-5
SEM = 25 * sigma_voto / np.sqrt(225)  # ~0.577 sulla scala 0-100
print("== Stima analitica dell'errore standard del punteggio ==")
print(f"  sigma per voto (scala 1-5)   : {sigma_voto:.3f}")
print(f"  SEM del punteggio (0-100)    : {SEM:.3f} punti  (pavimento ottimistico)\n")

rng = np.random.default_rng(20260618)
N = 100_000

def kendall_tau(a, b):
    """Kendall tau-a su due vettori (n piccolo, O(n^2))."""
    nn = len(a); c = d = 0
    for i in range(nn):
        for j in range(i+1, nn):
            s = np.sign(a[i]-a[j]) * np.sign(b[i]-b[j])
            if s > 0: c += 1
            elif s < 0: d += 1
    return (c-d)/(c+d)

print("== Monte Carlo: distribuzione del rango di Mistral sotto rumore ==")
mc = {}
base_order = np.argsort(-scores)   # riferimento per Kendall tau
for sigma in (0.5, 1.0, 2.0):
    noisy = scores[None, :] + rng.normal(0, sigma, size=(N, n))
    nt = noisy[:, ti]
    ranks = 1 + np.sum(noisy > nt[:, None], axis=1)
    p_not47 = np.mean(ranks != t_rank)
    lo_r, hi_r = np.percentile(ranks, [2.5, 97.5])
    mc[sigma] = ranks
    # Kendall tau su un sotto-campione (costo O(n^2) per trial)
    taus = []
    for k in range(300):
        order_k = np.argsort(-noisy[k])
        # rango perturbato di ciascun modello vs rango originale
        r_pert = np.empty(n); r_pert[order_k] = np.arange(n)
        r_orig = np.empty(n); r_orig[base_order] = np.arange(n)
        taus.append(kendall_tau(r_orig, r_pert))
    print(f"  sigma={sigma:>3} pt | rango medio {ranks.mean():5.1f} | sd {ranks.std():4.1f} "
          f"| IC95% [{lo_r:.0f}, {hi_r:.0f}] | P(rango!=47)={p_not47:.2f} "
          f"| Kendall tau medio {np.mean(taus):.3f}")
print()

# probabilita' di scambio coi due vicini immediati (sigma=1)
up_name, up_score = names[ti-1], scores[ti-1]      # 46esimo
dn_name, dn_score = names[ti+1], scores[ti+1]      # 48esimo
s = 1.0
# differenza di due gaussiane indipendenti ~ N(mu, 2 sigma^2)
from math import erf, sqrt
def p_swap(diff):
    sd = sqrt(2)*s
    z = diff/sd
    return 0.5*(1-erf(abs(z)/sqrt(2)))
print("== Probabilita' di scambio coi vicini immediati (sigma=1) ==")
print(f"  vs 46esimo ({up_score:.2f}, gap {up_score-t_score:.2f}) : P(scambio) = {p_swap(up_score-t_score):.2f}")
print(f"  vs 48esimo ({dn_score:.2f}, gap {t_score-dn_score:.2f}) : P(scambio) = {p_swap(t_score-dn_score):.2f}")
print()

# ======================================================================
# FIGURA 1 - Curva di stabilita' del rango (perturbazione deterministica)
# ======================================================================
fig, ax = plt.subplots(figsize=(8, 4.6))
xx = np.arange(-3, 3.0001, 0.02)
yy = [rank_of(t_score + d, others) for d in xx]
ax.step(xx, yy, where="mid", color=C_TEAL, lw=2.2)
ax.axvline(0, color=C_GRID, lw=1)
ax.scatter([0], [t_rank], color=C_ORANGE, zorder=5, s=70)
ax.annotate(f"  47esimo (score {t_score:.2f})", (0, t_rank),
            color=C_ORANGE, va="center", fontsize=10)
for d in (-1, +1):
    r = rank_of(t_score + d, others)
    ax.scatter([d], [r], color=C_RED, zorder=5, s=45)
    ax.annotate(f"{d:+d} pt -> {r}o", (d, r), color=C_RED,
                va="bottom" if d > 0 else "top", ha="center", fontsize=9)
ax.set_xlabel("Perturbazione del punteggio di Mistral (punti su 100)")
ax.set_ylabel("Rango risultante (1 = migliore)")
ax.set_title("Quanto e' stabile il '47esimo'? Rango vs perturbazione di 1 modello",
             color=C_GREEN, fontsize=12, pad=12)
ax.invert_yaxis()
ax.grid(True, alpha=0.4)
fig.tight_layout()
f1 = os.path.join(IMG, "01_stabilita_rango.png")
fig.savefig(f1, dpi=150); plt.close(fig); print("salvato", f1)

# ======================================================================
# FIGURA 2 - Strip dei 60 punteggi con le bande +/-1,2,3 attorno a Mistral
# ======================================================================
fig, ax = plt.subplots(figsize=(8, 3.4))
for d, col in ((3, C_PURPLE), (2, C_TEAL), (1, C_ORANGE)):
    ax.axvspan(t_score-d, t_score+d, color=col, alpha=0.10)
ax.scatter(scores, np.zeros_like(scores), color=C_TXT, alpha=0.55, s=28, zorder=3)
ax.scatter([t_score], [0], color=C_ORANGE, s=90, zorder=5, label="Mistral Medium 3.5")
for d, col in ((1, C_ORANGE), (2, C_TEAL), (3, C_PURPLE)):
    cnt = int(np.sum(np.abs(scores - t_score) <= d)) - 1
    ax.annotate(f"+/-{d} pt: {cnt} modelli", (t_score, 0.018*d),
                color=col, ha="center", fontsize=9)
ax.set_yticks([])
ax.set_xlabel("Punteggio Propaganda Resistance (0-100)")
ax.set_title("Il campo e' affollato: quanti modelli stanno a un soffio da Mistral",
             color=C_GREEN, fontsize=12, pad=10)
ax.set_ylim(-0.02, 0.075)
ax.grid(True, axis="x", alpha=0.4)
fig.tight_layout()
f2 = os.path.join(IMG, "02_vicinato.png")
fig.savefig(f2, dpi=150); plt.close(fig); print("salvato", f2)

# ======================================================================
# FIGURA 3 - Monte Carlo: distribuzione del rango (sigma = 1 punto)
# ======================================================================
fig, ax = plt.subplots(figsize=(8, 4.0))
ranks1 = mc[1.0]
bins = np.arange(ranks1.min()-0.5, ranks1.max()+1.5, 1)
ax.hist(ranks1, bins=bins, color=C_TEAL, alpha=0.85, edgecolor=C_BG)
ax.axvline(t_rank, color=C_ORANGE, lw=2, label=f"rango nominale = {t_rank}")
lo_r, hi_r = np.percentile(ranks1, [2.5, 97.5])
ax.axvspan(lo_r, hi_r, color=C_ORANGE, alpha=0.12, label=f"IC 95%: [{lo_r:.0f}, {hi_r:.0f}]")
ax.set_xlabel("Rango di Mistral su 100.000 simulazioni (rumore sigma = 1 punto)")
ax.set_ylabel("Frequenza")
ax.set_title("Con 1 punto di rumore il '47esimo' diventa una distribuzione",
             color=C_GREEN, fontsize=12, pad=10)
ax.legend(facecolor=C_BG, edgecolor=C_GRID, labelcolor=C_TXT, fontsize=9)
ax.grid(True, axis="y", alpha=0.4)
fig.tight_layout()
f3 = os.path.join(IMG, "03_montecarlo.png")
fig.savefig(f3, dpi=150); plt.close(fig); print("salvato", f3)

# ======================================================================
# FIGURA 4 - Curva posizione vs punteggio, con la zona piatta evidenziata
#            (il colpo d'occhio: dal 40esimo al 50esimo la curva e' piatta)
# ======================================================================
fig, ax = plt.subplots(figsize=(8.4, 4.8))
positions = np.arange(1, n + 1)
ax.plot(positions, scores, color=C_TXT, lw=1.4, alpha=0.7, zorder=2)
ax.scatter(positions, scores, color=C_TXT, s=18, alpha=0.6, zorder=3)

# banda evidenziata 40-50
b0, b1 = 40, 50
ax.axvspan(b0, b1, color=C_ORANGE, alpha=0.12, zorder=1)
y_lo, y_hi = scores[b1 - 1], scores[b0 - 1]
ax.annotate("", xy=(b1 + 0.3, y_lo), xytext=(b1 + 0.3, y_hi),
            arrowprops=dict(arrowstyle="<->", color=C_ORANGE, lw=1.6))
ax.text(b1 + 1.2, (y_lo + y_hi) / 2,
        f"dal 40esimo al 50esimo:\nsolo {y_hi - y_lo:.2f} punti\n(curva quasi piatta)",
        color=C_ORANGE, va="center", fontsize=9.5)

# Mistral
ax.scatter([t_rank], [t_score], color=C_RED, s=90, zorder=5)
ax.annotate(f"Mistral Medium 3.5\n47esimo, {t_score:.2f}", (t_rank, t_score),
            xytext=(t_rank - 14, t_score - 9), color=C_RED, fontsize=9.5,
            arrowprops=dict(arrowstyle="->", color=C_RED, lw=1.4))

# riferimenti: pendenza media globale vs locale
ax.text(2, 52,
        f"distacco medio per posizione:\n  globale  {gaps.mean():.2f} pt\n  zona 40-50  {(-np.diff(scores[b0-1:b1])).mean():.2f} pt",
        color=C_TEAL, fontsize=9, va="top",
        bbox=dict(boxstyle="round", fc=C_BG, ec=C_GRID))

ax.set_xlabel("Posizione in classifica (1 = migliore)")
ax.set_ylabel("Punteggio Propaganda Resistance (0-100)")
ax.set_title("Posizione vs punteggio: nel centro la classifica e' un pianoro",
             color=C_GREEN, fontsize=12, pad=12)
ax.grid(True, alpha=0.4)
fig.tight_layout()
f4 = os.path.join(IMG, "04_curva_posizione.png")
fig.savefig(f4, dpi=150); plt.close(fig); print("salvato", f4)

print("\nFatto.")
