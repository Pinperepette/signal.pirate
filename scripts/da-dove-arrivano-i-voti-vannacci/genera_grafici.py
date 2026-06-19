#!/usr/bin/env python3
"""
Genera i grafici per l'articolo "Da Dove Arrivano i Voti di Vannacci".

La domanda nata su X: i voti di Vannacci vengono da destra o da sinistra?
Si risponde con i flussi elettorali. SOLO DATI VERIFICATI ALLA FONTE PRIMARIA:

 - Demopolis (Barometro Politico, demopolis.it, 9 aprile 2026): Futuro Nazionale
   3,5%, sottrae 1,3 alla Lega e 1,0 a FdI, il resto dall'astensione; il
   centrosinistra non e' citato come fonte.
 - Lab21 (per Affaritaliani, 13 giugno 2026, n=1.014): composizione FN -> Lega
   45,7%, FdI 38,9%, CasaPound 7,2%, altro centrodestra 6,1%, altre forze 2,1%.
 - Supermedia YouTrend/AGI (1 giugno 2026): CDX 44,8 / Campo largo 44,9 / FN 4,0.
 - Istituto Cattaneo (PDF 10/06/2024): flussi europee 2024, Tab.1 (stock
   Politiche 2022 vs Europee 2024, dati Min. Interno).

Le liste di Vannacci NON hanno ancora affrontato un'elezione: i flussi sono
stime di sondaggio (modello sul ricordo del voto), da leggere con incertezza.

Dipendenze: numpy, matplotlib.
Output: ../../immagini/da-dove-arrivano-i-voti-vannacci/*.png
"""
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

OUT = os.path.join(os.path.dirname(__file__), "..", "..", "immagini", "da-dove-arrivano-i-voti-vannacci")
os.makedirs(OUT, exist_ok=True)

# ---- Palette Signal Pirate (dark) -----------------------------------------
BG, FG, MUTED = "#0d1117", "#c8c8d8", "#8b949e"
GREEN  = "#00ff88"   # sinistra / altre forze / nuovo
RED    = "#ff6b6b"   # FdI
CYAN   = "#22d3ee"   # astensione
PURPLE = "#7c4dff"
ORANGE = "#ff8800"   # Lega / destra
YELLOW = "#ffd23f"

plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG,
    "text.color": FG, "axes.labelcolor": FG, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.edgecolor": "#30363d", "grid.color": "#21262d",
    "font.family": "monospace", "font.size": 11,
    "axes.grid": True, "grid.alpha": 0.5, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 120,
})

def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, name), bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print(f"  -> {name}")

print("[*] Genero i grafici (solo dati verificati)...")

# ===========================================================================
# DATI VERIFICATI
# ===========================================================================
# Demopolis (9 apr 2026): FN 3,5% = 1,3 Lega + 1,0 FdI + resto astensione
DEM_TOT  = 3.5
DEM_LEGA = 1.3
DEM_FDI  = 1.0
DEM_DX   = DEM_LEGA + DEM_FDI                  # 2.3
DEM_AST  = round(DEM_TOT - DEM_DX, 1)          # 1.2 (residuo, attribuito all'astensione)
DEM_SX   = 0.0                                 # centrosinistra: non citato

# Lab21 (13 giu 2026, n=1014): composizione % degli elettori FN
LAB_N = 1014
LAB = [("Lega", 45.7, ORANGE), ("FdI", 38.9, RED),
       ("CasaPound", 7.2, "#b3541e"), ("Altro cdx", 6.1, YELLOW),
       ("Altre forze\n(incl. sinistra)", 2.1, GREEN)]
LAB_RIGHT = 45.7 + 38.9 + 7.2 + 6.1            # 97.9
LAB_OTHER = 2.1

# Supermedia YouTrend/AGI (1 giu 2026)
CDX, CSX, FN = 44.8, 44.9, 4.0

# Istituto Cattaneo Tab.1 (ITALIA): stock Politiche 2022 -> Europee 2024
CAT = [("M5S", 15.4, 10.0), ("Az-Iv-+Eu", 10.4, 7.1), ("Altri", 8.3, 4.7),
       ("Lega", 8.8, 9.0), ("FI+Mod", 8.2, 9.6), ("AVS", 3.6, 6.7),
       ("FdI", 26.2, 28.8), ("PD", 18.9, 24.1)]

# ===========================================================================
# 1 — PROVENIENZA DEI VOTI DI FN secondo DEMOPOLIS (dato primario)
# ===========================================================================
rows = [("Lega", DEM_LEGA, ORANGE), ("Fratelli d'Italia", DEM_FDI, RED),
        ("Astensione\n(residuo, 3,5 - 2,3)", DEM_AST, CYAN),
        ("Centrosinistra", DEM_SX, GREEN)]
fig, ax = plt.subplots(figsize=(11, 5.6))
y = np.arange(len(rows))[::-1]
ax.barh(y, [r[1] for r in rows], color=[r[2] for r in rows], alpha=0.92, height=0.6)
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows], fontsize=10)
for yy, r in zip(y, rows):
    if r[1] > 0:
        ax.text(r[1] + 0.03, yy, f"{r[1]:.1f} pt", va="center", fontsize=11, fontweight="bold", color=FG)
    else:
        ax.text(0.03, yy, "non citato da Demopolis", va="center", fontsize=10, color=GREEN, fontweight="bold")
ax.set_xlabel("punti sottratti agli altri partiti dal 3,5% di Futuro Nazionale\n(Demopolis, Barometro Politico, 9 aprile 2026)")
ax.set_title("Da dove arrivano i 3,5 punti di Vannacci",
             color=FG, fontsize=15, fontweight="bold", loc="left", pad=14)
ax.text(1.32, 2.5, "destra: 2,3 pt (66%)", color=ORANGE, fontsize=11, fontweight="bold")
ax.set_xlim(0, 1.8)
save(fig, "01_provenienza_fn.png")

# ===========================================================================
# 2 — TORTA: DESTRA vs ASTENSIONE (Demopolis); la sinistra non compare
# ===========================================================================
parts = [("Destra\n(Lega + FdI)", DEM_DX, ORANGE), ("Astensione", DEM_AST, CYAN)]
sizes = [p[1] for p in parts]
plabels = [f"{p[0]}\n{p[1]/DEM_TOT*100:.0f}%" for p in parts]
fig, ax = plt.subplots(figsize=(8.4, 6))
wedges, _ = ax.pie(sizes, colors=[p[2] for p in parts], startangle=90,
                   wedgeprops=dict(width=0.42, edgecolor=BG, linewidth=3), counterclock=False)
ax.text(0, 0.10, "0", ha="center", fontsize=26, fontweight="bold", color=GREEN)
ax.text(0, -0.18, "dal centrosinistra", ha="center", fontsize=12, color=MUTED)
ax.legend(wedges, plabels, loc="center left", bbox_to_anchor=(1.0, 0.5),
          frameon=False, fontsize=11, labelcolor=FG)
ax.set_title("Demopolis: i voti di Vannacci sono destra e astensione.\nIl centrosinistra non e' tra le fonti.",
             color=FG, fontsize=13, fontweight="bold", pad=18)
save(fig, "02_torta_provenienza.png")

# ===========================================================================
# 3 — EUROPEE 2024: i blocchi sono stabili (Cattaneo, stock 2022 -> 2024)
# ===========================================================================
labels = [c[0] for c in CAT]
delta = [c[2] - c[1] for c in CAT]
# verde = sinistra/centro che cresce o cala, arancio = destra
cols = []
for name, d in zip(labels, delta):
    if name in ("FdI", "Lega", "FI+Mod"):
        cols.append(ORANGE)
    elif name in ("PD", "AVS", "M5S", "Az-Iv-+Eu"):
        cols.append(GREEN)
    else:
        cols.append(MUTED)
fig, ax = plt.subplots(figsize=(11, 5.2))
x = np.arange(len(labels))
ax.bar(x, delta, color=cols, alpha=0.9, width=0.62)
for xi, d in zip(x, delta):
    ax.text(xi, d + (0.15 if d >= 0 else -0.35), f"{d:+.1f}", ha="center",
            fontsize=10, fontweight="bold", color=FG)
ax.axhline(0, color=MUTED, lw=0.9)
ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9, rotation=12)
ax.set_ylabel("variazione punti %  (Europee 2024 - Politiche 2022)")
ax.set_title("Alle europee 2024 i blocchi reggono: il rimescolio e' dentro ciascun campo",
             color=FG, fontsize=13, fontweight="bold", loc="left", pad=12)
ax.text(0.5, -4.7, "a sinistra: il M5S crolla, PD e AVS crescono (travaso interno alla sinistra)",
        color=GREEN, fontsize=9)
ax.text(0.5, 3.1, "a destra: FdI e Lega tengono o salgono", color=ORANGE, fontsize=9)
save(fig, "03_europee2024_fdi.png")

# ===========================================================================
# 4 — L'AGO DELLA BILANCIA (Supermedia YouTrend, 1 giu 2026)
# ===========================================================================
fig, ax = plt.subplots(figsize=(10, 5.6))
groups = ["Vannacci FUORI\ndalla coalizione", "Vannacci DENTRO\nla coalizione"]
x = np.arange(2); w = 0.34
cdx_vals = [CDX, CDX + FN]; csx_vals = [CSX, CSX]
b1 = ax.bar(x - w/2, cdx_vals, w, color=ORANGE, alpha=0.92, label="Centrodestra")
b2 = ax.bar(x + w/2, csx_vals, w, color=RED, alpha=0.55, label="Campo largo")
for b in list(b1) + list(b2):
    ax.text(b.get_x()+b.get_width()/2, b.get_height()+0.25, f"{b.get_height():.1f}",
            ha="center", fontsize=11, fontweight="bold", color=FG)
ax.axhline(CSX, color=RED, lw=0.8, ls=":", alpha=0.6)
ax.set_xticks(x); ax.set_xticklabels(groups, fontsize=10)
ax.set_ylabel("stima di voto (%)")
ax.set_ylim(42, 50)
ax.set_title("Lo stesso 4% sposta il vincitore - e il campo largo non si muove",
             color=FG, fontsize=13, fontweight="bold", loc="left", pad=12)
ax.legend(frameon=False, loc="upper left", labelcolor=FG)
ax.text(0, 42.25, "vince campo largo", ha="center", color=RED, fontsize=9, fontweight="bold")
ax.text(1, 42.25, "vince centrodestra", ha="center", color=ORANGE, fontsize=9, fontweight="bold")
save(fig, "04_ago_bilancia.png")

# ===========================================================================
# 5 — RICICLATO vs NUOVO (Demopolis 3,5%): cosa porta davvero a una coalizione
# ===========================================================================
fig, ax = plt.subplots(figsize=(9.6, 5.0))
segs = [("Riciclato\n(voti CDX: Lega+FdI)", DEM_DX, MUTED),
        ("Nuovo: ex astenuti", DEM_AST, CYAN),
        ("Nuovo: centrosinistra", DEM_SX, GREEN)]
left = 0
for lab, v, c in segs:
    if v <= 0:
        continue
    ax.barh(0, v, left=left, color=c, alpha=0.92, height=0.5)
    ax.text(left + v/2, 0, f"{v:.1f}", ha="center", va="center",
            fontsize=11, color=BG if c == CYAN else FG, fontweight="bold")
    left += v
ax.set_xlim(0, DEM_TOT + 0.3); ax.set_ylim(-0.6, 0.9)
ax.set_yticks([])
ax.set_xlabel("punti che Futuro Nazionale (3,5%, Demopolis) porterebbe a una coalizione di centrodestra")
ax.set_title("Dei 3,5 punti, 2,3 sono voti gia' di centrodestra; il 'nuovo' e' astensione",
             color=FG, fontsize=12.5, fontweight="bold", loc="left", pad=12)
ax.annotate("", xy=(0, 0.4), xytext=(DEM_DX, 0.4), arrowprops=dict(arrowstyle="<->", color=MUTED, lw=1.1))
ax.text(DEM_DX/2, 0.56, "gia' suoi: erano voti CDX", ha="center", color=MUTED, fontsize=9)
ax.annotate("", xy=(DEM_DX, 0.4), xytext=(DEM_TOT, 0.4), arrowprops=dict(arrowstyle="<->", color=CYAN, lw=1.1))
ax.text((DEM_DX+DEM_TOT)/2, 0.56, "nuovo: astensione", ha="center", color=CYAN, fontsize=9)
ax.grid(False)
save(fig, "05_riciclato_vs_nuovo.png")

# ===========================================================================
# 6 — DIRICHLET sui conteggi REALI Lab21 (n=1014): quota "altre forze"
# ===========================================================================
rng = np.random.default_rng(20260619)
NIT = 200_000
counts = np.array([45.7, 38.9, 7.2, 6.1, 2.1]) / 100.0 * LAB_N   # conteggi reali
alpha = counts + 0.5
draws = rng.dirichlet(alpha, NIT)
share_other = 100 * draws[:, 4]
share_right = 100 * draws[:, :4].sum(axis=1)
lo, hi = np.percentile(share_other, [2.5, 97.5])
fig, ax = plt.subplots(figsize=(10, 5.4))
ax.hist(share_other, bins=90, color=GREEN, alpha=0.85)
ax.axvline(share_other.mean(), color=FG, lw=1.4)
ax.axvspan(lo, hi, color=GREEN, alpha=0.12)
ax.set_xlabel("quota degli elettori di Vannacci da 'altre forze' (incl. sinistra), %  -  Lab21 n=1014")
ax.set_ylabel("simulazioni"); ax.set_yticks([]); ax.set_xlim(0, 6)
ax.set_title("Dirichlet sui conteggi reali Lab21: la quota 'altre forze' resta intorno al 2%",
             color=FG, fontsize=12.5, fontweight="bold", loc="left", pad=12)
ax.text(share_other.mean()+0.12, ax.get_ylim()[1]*0.84,
        f"media {share_other.mean():.1f}%\nintervallo 95%: {lo:.1f}-{hi:.1f}%",
        color=FG, fontsize=10, fontweight="bold")
save(fig, "06_montecarlo_sinistra.png")

# ===========================================================================
# 7 — STRESS TEST: quanto e' improbabile la tesi di X (su Lab21)
# ===========================================================================
flip_factor = 50.0 / LAB_OTHER                    # 23.8 -> per superare il 50% e diventare maggioranza
p_x = np.mean(share_other > share_right)          # equivale a share_other > 50 (sommano a 100)
n_x = int(np.sum(share_other > share_right))
print(f"[*] Stress test (Lab21): per la maggioranza sottostima ~{flip_factor:.0f}x; "
      f"P(altre>destra)={p_x:.2e} ({n_x}/{NIT})")
fig, ax = plt.subplots(figsize=(10, 5.2))
bars = [("Da destra\n(Lega+FdI+CasaPound+altro cdx)", LAB_RIGHT, ORANGE),
        ("Da altre forze\n(incl. sinistra)", LAB_OTHER, GREEN)]
for i, (lab, v, c) in enumerate(bars):
    ax.bar(i, v, 0.5, color=c, alpha=0.92)
    ax.text(i, v + 1.5, f"{v:.1f}%", ha="center", fontsize=12, fontweight="bold", color=FG)
ax.set_xticks([0, 1]); ax.set_xticklabels([b[0] for b in bars], fontsize=10)
ax.set_ylabel("composizione elettori di Futuro Nazionale (Lab21, %)")
ax.set_ylim(0, 110)
ax.axhline(50, color=YELLOW, lw=1.3, ls="--", alpha=0.8)
ax.text(0.5, 53, "maggioranza = 50%", ha="center", color=YELLOW, fontsize=9)
ax.set_title("Perche' la tesi di X regga, la quota verde deve diventare maggioranza (>50%)",
             color=FG, fontsize=12.5, fontweight="bold", loc="left", pad=12)
ax.annotate("", xy=(1, 50), xytext=(1, LAB_OTHER), arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.6))
ax.text(1.06, (50 + LAB_OTHER)/2, f"per passare il 50%\nservirebbe una\nsottostima di ~{flip_factor:.0f} volte",
        color=GREEN, fontsize=10.5, fontweight="bold", va="center")
ax.text(0.5, 104, f"P(piu' voti da sinistra che da destra) < 1 su {NIT//1000} mila",
        ha="center", color=ORANGE, fontsize=10.5, fontweight="bold")
save(fig, "07_stress_test.png")

# ===========================================================================
# 8 — TRIANGOLAZIONE: la quota da fuori la destra secondo i due dati verificati
# ===========================================================================
polls = [("Demopolis\n(9 apr 2026)", 0.0), ("Lab21\n(13 giu 2026)", LAB_OTHER)]
fig, ax = plt.subplots(figsize=(10, 4.4))
y = np.arange(len(polls))[::-1]
ax.barh(y, [p[1] for p in polls], color=GREEN, alpha=0.9, height=0.46)
for yy, (lab, v) in zip(y, polls):
    if v > 0:
        ax.text(v + 1.2, yy, f"{v:.1f}%", va="center", fontsize=12, fontweight="bold", color=FG)
    else:
        ax.text(1.2, yy, "0  (centrosinistra non citato)", va="center", fontsize=11, color=GREEN, fontweight="bold")
ax.set_yticks(y); ax.set_yticklabels([p[0] for p in polls], fontsize=11)
ax.axvline(50, color=ORANGE, lw=1.6, ls="--")
ax.text(48, np.mean(y), "soglia perche' la tesi di X sia vera (>50%)",
        rotation=90, ha="right", va="center", color=ORANGE, fontsize=9.5, fontweight="bold")
ax.set_xlim(0, 100)
ax.set_xlabel("quota dei voti di Vannacci dal centrosinistra / 'altre forze' (%)")
ax.set_title("Due fonti primarie, metodi diversi: la quota da fuori la destra e' ~2% o meno",
             color=FG, fontsize=12.5, fontweight="bold", loc="left", pad=12)
save(fig, "08_triangolazione.png")

print("[OK] Fatto.")
