#!/usr/bin/env python3
"""
Genera i grafici per l'articolo "Numeri Veri, Storia Falsa".
Smonta il post sulle pensioni con i dati ufficiali (INPS, Itinerari Previdenziali,
RGS, ISTAT, OCSE) e con la statistica corretta.

Dipendenze: numpy, matplotlib  (NormalDist e' nella stdlib, niente scipy).
Output: ../../immagini/numeri-veri-storia-falsa/*.png
"""
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from statistics import NormalDist

OUT = os.path.join(os.path.dirname(__file__), "..", "..", "immagini", "numeri-veri-storia-falsa")
os.makedirs(OUT, exist_ok=True)

# ---- Palette Signal Pirate (dark) -----------------------------------------
BG      = "#0d1117"
FG      = "#c8c8d8"
MUTED   = "#8b949e"
GREEN   = "#00ff88"   # vero / previdenza
RED     = "#ff6b6b"   # fuorviante / non-pensioni
CYAN    = "#22d3ee"
PURPLE  = "#7c4dff"
ORANGE  = "#ff8800"
YELLOW  = "#ffd23f"

plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG,
    "text.color": FG, "axes.labelcolor": FG, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.edgecolor": "#30363d", "grid.color": "#21262d",
    "font.family": "monospace", "font.size": 11,
    "axes.grid": True, "grid.alpha": 0.5, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 120,
})
N = NormalDist()
def phi(x):  return N.cdf(x)
def ppf(p):  return N.inv_cdf(p)
def eur(x, _=None): return f"{x:,.0f}".replace(",", ".")
def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, name), bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print(f"  -> {name}")

print("[*] Genero i grafici...")

# ===========================================================================
# 1 — IL PERIMETRO DEI 180 MILIARDI
# ===========================================================================
gias = [
    ("Previdenza vera\n(pubblico impiego, quota-parte,\nanticipi, invalidita' ante-'84)", 67.36, GREEN),
    ("Decontribuzione\n(sgravi sul cuneo fiscale)",                                       44.81, RED),
    ("Assistenza pura\n(invalidi civili, assegni sociali,\nmaggiorazioni, 14esima)",       29.77, RED),
    ("Welfare famiglia\n(Assegno Unico + interventi)",                                     24.19, RED),
    ("Ammortizzatori\n(NASpI / CIG)",                                                       8.03, RED),
    ("Reddito Cittadinanza /\nAssegno di Inclusione",                                       5.63, RED),
]
labels = [g[0] for g in gias]; vals = [g[1] for g in gias]; cols = [g[2] for g in gias]
tot = sum(vals); prev = vals[0]
fig, ax = plt.subplots(figsize=(11, 6))
y = np.arange(len(labels))[::-1]
ax.barh(y, vals, color=cols, alpha=0.92, height=0.66)
ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=9)
for yy, v in zip(y, vals):
    ax.text(v + 0.8, yy, f"{v:.1f}", va="center", fontsize=10, fontweight="bold", color=FG)
ax.set_xlabel("trasferimenti GIAS 2024 (INPS, Rendiconto generale), miliardi di euro")
ax.set_title(f"Dei {tot:.0f} miliardi 'per le pensioni', solo {prev:.0f} sono previdenza",
             color=FG, fontsize=14, fontweight="bold", loc="left", pad=14)
ax.text(46, 0.15, "NON sono pensioni:  " + f"{tot-prev:.0f} mld ({(tot-prev)/tot*100:.0f}%)",
        color=RED, fontsize=11, fontweight="bold")
ax.xaxis.set_major_formatter(mtick.FuncFormatter(eur))
ax.set_xlim(0, 52)
save(fig, "01_perimetro_180mld.png")

# ===========================================================================
# 2 — DEFICIT O SURPLUS? IL PERIMETRO DEL SALDO  (waterfall)
# ===========================================================================
entrate, spesa = 260.6, 286.1
saldo_lordo = entrate - spesa            # -25.5
irpef = 71.0                             # IRPEF ri-versata dai pensionati (stima Itinerari)
saldo_netto = 60.9
assist_step = saldo_netto - saldo_lordo - irpef   # rimozione assistenza/GPT dalla spesa = +15.4
fig, ax = plt.subplots(figsize=(10, 5.4))
steps = ["Saldo\ncontabile LORDO", "+ tolgo assistenza\n/ GPT dalla spesa", "+ IRPEF\nri-versata (71)", "Saldo NETTO\n(perimetro previdenza)"]
bottoms = [0, saldo_lordo, saldo_lordo + assist_step, 0]
heights = [saldo_lordo, assist_step, irpef, saldo_netto]
colors  = [RED, MUTED, MUTED, GREEN]
for i,(b,h,c) in enumerate(zip(bottoms, heights, colors)):
    ax.bar(i, h, bottom=b, color=c, alpha=0.9, width=0.62)
ax.text(0, saldo_lordo-3.5, f"{saldo_lordo:+.1f}", ha="center", color=FG, fontweight="bold", fontsize=12)
ax.text(3, saldo_netto+2.2, f"{saldo_netto:+.1f}", ha="center", color=GREEN, fontweight="bold", fontsize=13)
ax.text(1, saldo_lordo + assist_step + 2, f"+{assist_step:.0f}", ha="center", color=MUTED, fontsize=9)
ax.text(2, saldo_lordo + assist_step + irpef + 2, f"+{irpef:.0f}", ha="center", color=MUTED, fontsize=9)
ax.axhline(0, color="#484f58", lw=1)
ax.set_xticks(range(4)); ax.set_xticklabels(steps, fontsize=9.5)
ax.set_ylabel("saldo del sistema pensionistico, miliardi €")
ax.set_xlabel("Fonte: Itinerari Previdenziali, XIII Rapporto (dati 2024)")
ax.set_title("Stesso anno, stessa fonte: il segno dipende da cosa chiami 'pensione'",
             color=FG, fontsize=13, fontweight="bold", loc="left", pad=12)
ax.set_ylim(-40, 75)
save(fig, "02_saldo_perimetro.png")

# ===========================================================================
# 3 — LA MEDIA CHE MENTE: distribuzione lognormale calibrata sui dati ufficiali
#     Vincoli: mean = 21.382 €/anno (pro capite, INPS/Itinerari 2023-24)
#              P(reddito < 12.000) = 0.295  (29,5% sotto ~1.000 €/mese, ISTAT-INPS)
# ===========================================================================
target_mean = 21382.0
target_p, target_thr = 0.295, 12000.0
# Risolvo sigma:  ln(mean) = mu + sigma^2/2,  (ln thr - mu)/sigma = ppf(p)
z = ppf(target_p)                      # ~ -0.539
a, b = 1.0, z * 2                       # sigma^2 + 2z*... -> derivo da sostituzione
# mu = ln(thr) - sigma*z ; e mu = ln(mean) - sigma^2/2  => uguaglio:
# ln(thr) - sigma*z = ln(mean) - sigma^2/2
# sigma^2/2 - z*sigma + (ln thr - ln mean) = 0
A, B, C = 0.5, -z, (np.log(target_thr) - np.log(target_mean))
sigma = (-B + np.sqrt(B*B - 4*A*C)) / (2*A)
mu = np.log(target_mean) - sigma**2 / 2
median = np.exp(mu)
mean_check = np.exp(mu + sigma**2/2)
gini = 2*phi(sigma/np.sqrt(2)) - 1
frac_below_mean = phi((np.log(target_mean) - mu)/sigma)
print(f"    [fit lognormale] mu={mu:.4f} sigma={sigma:.4f}")
print(f"    media={mean_check:,.0f}  mediana={median:,.0f}  gap={mean_check-median:,.0f}")
print(f"    Gini={gini:.3f}  quota sotto la media={frac_below_mean*100:.1f}%")

x = np.linspace(0, 70000, 1000)
pdf = (1/(x[1:]*sigma*np.sqrt(2*np.pi))) * np.exp(-(np.log(x[1:])-mu)**2/(2*sigma**2))
fig, ax = plt.subplots(figsize=(11, 5.6))
ax.fill_between(x[1:], pdf, color=CYAN, alpha=0.18)
ax.plot(x[1:], pdf, color=CYAN, lw=1.6)
def vline(val, color, label, ytop=0.92):
    ax.axvline(val, color=color, ls="--", lw=1.6)
    ax.text(val, ax.get_ylim()[1]*ytop, f" {label}", color=color, fontsize=9.5,
            fontweight="bold", rotation=90, va="top")
ax.set_ylim(0, pdf.max()*1.15)
vline(median, GREEN,  f"MEDIANA  {median:,.0f}".replace(",","."), 0.55)
vline(target_mean, ORANGE, f"MEDIA  {target_mean:,.0f}".replace(",","."), 0.72)
vline(29019, RED, "MEDIA DEL POST  29.019", 0.95)
ax.axvspan(0, 12000, color=GREEN, alpha=0.05)
ax.text(5500, pdf.max()*1.05, "29,5% dei pensionati\nsotto 1.000 €/mese", color=GREEN, fontsize=9)
ax.set_xlabel("reddito pensionistico lordo, € / anno (modello lognormale, calibrato su dati INPS-ISTAT)")
ax.set_ylabel("densita' di pensionati")
ax.set_title("La distribuzione e' asimmetrica: meta' dei pensionati sta sotto la mediana",
             color=FG, fontsize=13, fontweight="bold", loc="left", pad=12)
ax.xaxis.set_major_formatter(mtick.FuncFormatter(eur))
save(fig, "03_distribuzione_pensioni.png")

# ===========================================================================
# 4 — LORENZ + GINI: la concentrazione che gonfia la media
# ===========================================================================
p = np.linspace(0, 1, 500)
lorenz = np.array([phi(ppf(pi) - sigma) if 0 < pi < 1 else pi for pi in p])
top20 = 1 - (phi(ppf(0.8) - sigma))
bottom50 = phi(ppf(0.5) - sigma)
print(f"    top 20% incassa {top20*100:.0f}% del reddito pensionistico; bottom 50% incassa {bottom50*100:.0f}%")
fig, ax = plt.subplots(figsize=(7.6, 6.6))
ax.plot([0,1],[0,1], color=MUTED, ls=":", lw=1.4, label="uguaglianza perfetta")
ax.plot(p, lorenz, color=PURPLE, lw=2.4, label=f"pensioni (Gini = {gini:.2f})")
ax.fill_between(p, lorenz, p, color=PURPLE, alpha=0.12)
ax.scatter([0.8],[1-top20], color=RED, zorder=5)
ax.annotate(f"il 20% piu' alto\nincassa il {top20*100:.0f}%",
            (0.8, 1-top20), (0.40, 0.30), color=RED, fontsize=10,
            arrowprops=dict(arrowstyle="->", color=RED))
ax.set_xlabel("quota cumulata di pensionati (dal piu' povero)")
ax.set_ylabel("quota cumulata di spesa pensionistica")
ax.set_title("Curva di Lorenz: la coda alta tira su la media",
             color=FG, fontsize=13, fontweight="bold", loc="left", pad=12)
ax.legend(facecolor=BG, edgecolor="#30363d", labelcolor=FG, fontsize=9.5, loc="upper left")
ax.set_xlim(0,1); ax.set_ylim(0,1)
save(fig, "04_lorenz.png")

# ===========================================================================
# 5 — LA FABBRICA DELLA MEDIA: scegli quante classi basse escludere
#     E[X | X > soglia]  al variare della frazione esclusa
# ===========================================================================
fracs = np.linspace(0, 0.55, 200)
cond_mean = []
for f in fracs:
    if f == 0:
        cond_mean.append(target_mean); continue
    zt = ppf(f)
    cm = target_mean * phi(sigma - zt) / (1 - f)
    cond_mean.append(cm)
cond_mean = np.array(cond_mean)
# trovo dove passa per 29.019
idx = int(np.argmin(np.abs(cond_mean - 29019)))
f29 = fracs[idx]
print(f"    per ottenere la 'media' 29.019 servono escludere ~{f29*100:.0f}% dei pensionati piu' bassi")
fig, ax = plt.subplots(figsize=(10.5, 5.6))
ax.plot(fracs*100, cond_mean, color=YELLOW, lw=2.4)
ax.fill_between(fracs*100, cond_mean, target_mean, color=YELLOW, alpha=0.10)
for val, lab, c in [(21382,"media reale pro capite", ORANGE), (29019,"\"media\" del post", RED)]:
    ax.axhline(val, color=c, ls="--", lw=1.3)
    ax.text(0.5, val+350, f"{lab}: {val:,.0f}".replace(",","."), color=c, fontsize=9.5, fontweight="bold")
ax.scatter([f29*100],[29019], color=RED, zorder=5, s=45)
ax.annotate(f"basta togliere il {f29*100:.0f}%\ndei pensionati piu' bassi",
            (f29*100, 29019), (f29*100+6, 24500), color=RED, fontsize=10,
            arrowprops=dict(arrowstyle="->", color=RED))
ax.set_xlabel("% di pensionati esclusi dal calcolo (i piu' bassi)  |  modello lognormale illustrativo, non un dato osservato")
ax.set_ylabel("'media' risultante, € / anno")
ax.set_title("La media e' una manopola: decidi tu il titolo",
             color=FG, fontsize=13, fontweight="bold", loc="left", pad=12)
ax.yaxis.set_major_formatter(mtick.FuncFormatter(eur))
ax.set_xlim(0, 55)
save(fig, "05_fabbrica_media.png")

# ===========================================================================
# 6 — OCSE: reddito relativo degli over-65 (indicatore vs lettura forte)
# ===========================================================================
cats = ["Italia\n(tutti 65+)", "Italia\nuomini", "Italia\ndonne", "Media\nOCSE"]
vv = [98.8, 105.8, 93.4, 87.0]; cc = [ORANGE, MUTED, MUTED, GREEN]
fig, ax = plt.subplots(figsize=(9.5, 5.2))
ax.bar(cats, vv, color=cc, alpha=0.92, width=0.62)
ax.axhline(100, color=RED, ls="--", lw=1.3)
ax.text(3.4, 101, "reddito 65+ = reddito popolazione totale", color=RED, fontsize=8.5, ha="right")
for i,v in enumerate(vv):
    ax.text(i, v+1, f"{v:.1f}%", ha="center", color=FG, fontweight="bold")
ax.set_ylabel("reddito disponibile equivalente,\n% della popolazione totale")
ax.set_xlabel("Fonte: OECD, Pensions at a Glance 2025 (dati 2022)")
ax.set_title("OCSE: il reddito FAMILIARE degli over-65, non la pensione del singolo",
             color=FG, fontsize=12.5, fontweight="bold", loc="left", pad=12)
ax.set_ylim(0, 120)
save(fig, "06_ocse_redditi.png")

# ===========================================================================
# 7 — TASSO DI SOSTITUZIONE: dove il post ha un punto vero
# ===========================================================================
x = np.arange(2); w = 0.36
fig, ax = plt.subplots(figsize=(8.5, 5))
ax.bar(x-w/2, [70.6, 79.0], w, label="Italia", color=ORANGE, alpha=0.92)
ax.bar(x+w/2, [47.5, 71.4], w, label="Media OCSE", color=MUTED, alpha=0.92)
ax.set_xticks(x); ax.set_xticklabels(["LORDO", "NETTO"])
ax.set_ylabel("% dell'ultimo stipendio")
ax.set_xlabel("Fonte: OECD, Pensions at a Glance 2025")
for i,(a_,b_) in enumerate([(70.6,47.5),(79.0,71.4)]):
    ax.text(i-w/2, a_+1, f"{a_}%", ha="center", color=FG, fontweight="bold", fontsize=9)
    ax.text(i+w/2, b_+1, f"{b_}%", ha="center", color=MUTED, fontsize=9)
ax.set_title("Tasso di sostituzione: le pensioni italiane SONO generose (ma eta' alta)",
             color=FG, fontsize=12.5, fontweight="bold", loc="left", pad=12)
ax.legend(facecolor=BG, edgecolor="#30363d", labelcolor=FG, fontsize=9.5)
ax.set_ylim(0, 92)
save(fig, "07_tasso_sostituzione.png")

# ===========================================================================
# 8 — DEMOGRAFIA: il punto vero + l'esaurimento del retributivo
# ===========================================================================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.8), gridspec_kw={"width_ratios":[1,1.3]})
# rapporto attivi/pensionati
ratio = 1.4758
ax1.barh(0, ratio, color=ORANGE, alpha=0.92, height=0.5)
ax1.axvline(1.5, color=RED, ls="--", lw=1.6)
ax1.text(1.5, 0.34, "soglia di sicurezza 1,5", color=RED, fontsize=9, ha="center")
ax1.text(ratio/2, 0, f"{ratio:.3f}", ha="center", va="center", color=BG, fontweight="bold", fontsize=14)
ax1.set_yticks([]); ax1.set_xlim(0, 2); ax1.set_ylim(-0.5, 0.6)
ax1.set_xlabel("lavoratori attivi per pensionato, 2024\n(Itinerari Previdenziali)")
ax1.set_title("Il punto vero: troppo pochi attivi", color=FG, fontsize=11.5, fontweight="bold", loc="left")
for s in ("left","right","top"): ax1.spines[s].set_visible(False)
# esaurimento componente retributiva
anni = np.array([2024, 2030, 2035, 2040, 2044, 2050])
peso = np.array([100, 78, 55, 30, 18, 8])
ax2.plot(anni, peso, "o-", color=PURPLE, lw=2.4)
ax2.fill_between(anni, peso, color=PURPLE, alpha=0.14)
ax2.axvline(2040, color=GREEN, ls="--", lw=1.2); ax2.text(2040.2, 72, "interamente\ncontributivo (~2040)", color=GREEN, fontsize=8.5)
ax2.axvline(2044, color=YELLOW, ls="--", lw=1.2); ax2.text(2044.2, 45, "spesa/PIL\nin calo (2044)", color=YELLOW, fontsize=8.5)
ax2.set_ylabel("peso componente retributiva (indice)")
ax2.set_xlabel("anno (profilo illustrativo su trend RGS)")
ax2.set_title("Il 'problema retributivo' si esaurisce da solo", color=FG, fontsize=11.5, fontweight="bold", loc="left")
ax2.set_ylim(0, 108)
save(fig, "08_demografia.png")

# ===========================================================================
# 9 — DEBITO/PIL vs SPESA PENSIONI/PIL: le due curve non si muovono insieme
#     Debito 1995-2024: Eurostat (gov_10dd_edpt1). Pre-1995: ricostruzione storica
#     (Banca d'Italia / fonti). Spesa pensioni: Eurostat ESSPROS (spr_exp_pens, def. allargata)
# ===========================================================================
anni_deb = np.array([1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2024])
debito   = np.array([57.0, 84.0, 97.0, 119.1, 108.7, 106.2, 118.8, 134.8, 154.4, 134.7])
anni_pen = np.array([1995, 2000, 2005, 2010, 2015, 2020, 2023])
pension  = np.array([13.4, 13.8, 14.0, 15.4, 16.4, 17.5, 15.5])
fig, ax = plt.subplots(figsize=(11, 5.8))
# debito: tratteggiato la ricostruzione pre-1995, pieno il dato Eurostat
ax.plot(anni_deb[anni_deb <= 1995], debito[anni_deb <= 1995], "--", color=ORANGE, lw=2, alpha=0.85)
ax.plot(anni_deb[anni_deb >= 1995], debito[anni_deb >= 1995], "-", color=ORANGE, lw=2.6, marker="o", ms=4,
        label="Debito pubblico / PIL")
ax.plot(anni_pen, pension, "-", color=CYAN, lw=2.6, marker="o", ms=4, label="Spesa pensioni / PIL (ESSPROS)")
ax.axvspan(1980, 1994, color=ORANGE, alpha=0.06)
ax.annotate("anni '80-'90:\nil debito raddoppia\n(da 57% a ~120%)", xy=(1990, 97), xytext=(1982, 150),
            color=ORANGE, fontsize=9, arrowprops=dict(arrowstyle="->", color=ORANGE, alpha=0.7))
ax.text(1981, 49, "ricostruzione\nstorica", color=MUTED, fontsize=7.5)
ax.text(2001, 6, "la spesa pensioni/PIL sale piano e poco", color=CYAN, fontsize=8.5)
ax.set_ylabel("% del PIL")
ax.set_xlabel("Debito: Eurostat 1995-2024, Banca d'Italia pre-1995  |  Pensioni: Eurostat ESSPROS (def. allargata)")
ax.set_title("Debito e spesa pensionistica non si muovono insieme",
             color=FG, fontsize=13.5, fontweight="bold", loc="left", pad=12)
ax.legend(facecolor=BG, edgecolor="#30363d", labelcolor=FG, fontsize=9.5, loc="center right")
ax.set_ylim(0, 175); ax.set_xlim(1979, 2025)
save(fig, "09_debito_vs_pensioni.png")

# ===========================================================================
# 10 — SALARI REALI Italia vs UE27 (AMECO), base comune 1995=100, con riforme
#      Fonte: AMECO RWCDV (real compensation per employee, deflatore PIL),
#      Commissione Europea / DG ECFIN, via DBnomics. UE27 parte dal 1995.
# ===========================================================================
wyears = np.array([1995, 2000, 2005, 2010, 2015, 2020, 2024])
it_raw = np.array([109.58, 110.56, 110.30, 110.94, 106.24, 100.00, 103.48])  # AMECO idx 2020=100
eu_raw = np.array([86.25, 91.23, 93.17, 96.73, 98.70, 100.00, 102.87])
it = it_raw / it_raw[0] * 100     # reindex 1995=100
eu = eu_raw / eu_raw[0] * 100
fig, ax = plt.subplots(figsize=(11, 5.8))
ax.axhline(100, color=MUTED, ls=":", lw=1, alpha=0.6)
ax.plot(wyears, eu, "-o", color=CYAN, lw=2.6, ms=4, label="Media UE27")
ax.plot(wyears, it, "-o", color=ORANGE, lw=2.6, ms=4, label="Italia")
for ry, rn in [(1995, "Dini"), (1997, "Prodi"), (2004, "Maroni"), (2011, "Fornero")]:
    ax.axvline(ry, color=PURPLE, ls="--", lw=0.9, alpha=0.5)
    ax.text(ry + 0.35, 122, rn, color=PURPLE, fontsize=8, rotation=90, va="top", ha="left", alpha=0.9)
ax.text(2023.7, eu[-1] + 1.4, f"UE27  +{eu[-1]-100:.0f}%", color=CYAN, fontsize=10, fontweight="bold", ha="right")
ax.text(2023.7, it[-1] - 3.2, f"Italia  {it[-1]-100:.0f}%", color=ORANGE, fontsize=10, fontweight="bold", ha="right")
ax.set_ylabel("salario reale medio (1995 = 100)")
ax.set_xlabel("AMECO (Commissione Europea), real compensation per employee, deflatore PIL  |  linee viola = riforme pensioni")
ax.set_title("Trent'anni di riforme delle pensioni, salari reali italiani fermi",
             color=FG, fontsize=13.5, fontweight="bold", loc="left", pad=12)
ax.legend(facecolor=BG, edgecolor="#30363d", labelcolor=FG, fontsize=9.5, loc="lower left")
ax.set_ylim(88, 127); ax.set_xlim(1994, 2025)
save(fig, "10_salari_riforme.png")
print(f"    [salari 1995=100] Italia 2024 = {it[-1]:.1f} ({it[-1]-100:+.1f}%) | UE27 2024 = {eu[-1]:.1f} ({eu[-1]-100:+.1f}%)")

# ===========================================================================
# 11 — CURVA DI LORENZ REALE delle pensioni (ISTAT 2014, Prospetto 10)
#      Dati reali: numero pensioni e quota di spesa per classe di importo.
# ===========================================================================
n_cl = np.array([5968710, 9190137, 3166282, 2280934, 1847283, 560192, 175746, 9190], float)
inc_share = np.array([6.9, 25.9, 16.9, 16.9, 19.1, 8.9, 4.8, 0.5])  # % su spesa, ISTAT
pop_f = n_cl / n_cl.sum()
inc_f = inc_share / inc_share.sum()
cum_pop = np.concatenate([[0], np.cumsum(pop_f)])
cum_inc = np.concatenate([[0], np.cumsum(inc_f)])
gini_real = 1 - np.sum((cum_pop[1:] - cum_pop[:-1]) * (cum_inc[1:] + cum_inc[:-1]))
top20_real = 1 - np.interp(0.80, cum_pop, cum_inc)
bot50_real = np.interp(0.50, cum_pop, cum_inc)
fig, ax = plt.subplots(figsize=(7.6, 6.6))
ax.plot([0, 1], [0, 1], color=MUTED, ls=":", lw=1.4, label="uguaglianza perfetta")
ax.plot(cum_pop, cum_inc, "-o", color=PURPLE, lw=2.4, ms=4, label=f"pensioni reali (Gini = {gini_real:.2f})")
ax.fill_between(cum_pop, cum_inc, cum_pop, color=PURPLE, alpha=0.12)
ax.scatter([0.8], [1 - top20_real], color=RED, zorder=5)
ax.annotate(f"il 20% piu' alto\nincassa il {top20_real*100:.0f}%", (0.8, 1 - top20_real), (0.40, 0.28),
            color=RED, fontsize=10, arrowprops=dict(arrowstyle="->", color=RED))
ax.set_xlabel("quota cumulata di pensioni (dalla piu' bassa)")
ax.set_ylabel("quota cumulata di spesa pensionistica")
ax.set_title("Curva di Lorenz delle pensioni: dati reali ISTAT",
             color=FG, fontsize=13, fontweight="bold", loc="left", pad=12)
ax.legend(facecolor=BG, edgecolor="#30363d", labelcolor=FG, fontsize=9.5, loc="upper left")
ax.text(0.02, -0.13, "Fonte: ISTAT, Trattamenti pensionistici 2014, Prospetto 10 (per trattamento, importo incl. rateo 13a)",
        transform=ax.transAxes, color=MUTED, fontsize=7.5)
ax.set_xlim(0, 1); ax.set_ylim(0, 1)
save(fig, "11_lorenz_reale.png")
print(f"    [Lorenz reale ISTAT 2014] Gini = {gini_real:.3f} | top20% = {top20_real*100:.0f}% | bottom50% = {bot50_real*100:.0f}%")

# ===========================================================================
# 12 — SALARI REALI vs PRODUTTIVITA', Italia vs UE27, 1995=100
#      Salari: AMECO. Produttivita': Eurostat nama_10_lp_ulc (RLPR_HW), reindex 1995=100.
# ===========================================================================
pyears = np.array([1995, 2000, 2005, 2010, 2015, 2020, 2024])
it_prod = np.array([100.0, 105.8, 106.7, 105.8, 106.9, 110.7, 106.2])
eu_prod = np.array([100.0, 110.9, 119.8, 124.7, 131.6, 138.3, 138.8])
it_wage = it_raw / it_raw[0] * 100   # gia' calcolati per il grafico 10
eu_wage = eu_raw / eu_raw[0] * 100
fig, ax = plt.subplots(figsize=(11, 5.8))
ax.axhline(100, color=MUTED, ls=":", lw=1, alpha=0.5)
ax.plot(pyears, eu_prod, "--", color=CYAN, lw=2, ms=4, marker="o", alpha=0.95, label="UE27 produttivita'")
ax.plot(wyears, eu_wage, "-", color=CYAN, lw=2.6, ms=4, marker="o", label="UE27 salari")
ax.plot(pyears, it_prod, "--", color=ORANGE, lw=2, ms=4, marker="o", alpha=0.95, label="Italia produttivita'")
ax.plot(wyears, it_wage, "-", color=ORANGE, lw=2.6, ms=4, marker="o", label="Italia salari")
ax.set_ylabel("indice, 1995 = 100")
ax.set_xlabel("Salari: AMECO (Commissione UE).  Produttivita': Eurostat, produttivita' oraria reale (nama_10_lp_ulc)")
ax.set_title("I salari seguono la produttivita', non le pensioni",
             color=FG, fontsize=13.5, fontweight="bold", loc="left", pad=12)
ax.legend(facecolor=BG, edgecolor="#30363d", labelcolor=FG, fontsize=9, loc="upper left", ncol=2)
ax.set_ylim(85, 145); ax.set_xlim(1994, 2025)
ax.text(2024.2, eu_prod[-1], "+39%", color=CYAN, fontsize=9, va="center")
ax.text(2024.2, it_prod[-1]+1.5, "+6%", color=ORANGE, fontsize=9, va="center")
save(fig, "12_salari_produttivita.png")
print(f"    [produttivita' 1995=100] Italia 2024 = {it_prod[-1]:.0f} | UE27 = {eu_prod[-1]:.0f}")

print("[*] Fatto. Tutti i grafici in:", os.path.relpath(OUT))
print()
print("=== NUMERI CHIAVE (da citare nell'articolo) ===")
print(f"GIAS totale: {tot:.1f} mld | previdenza: {prev:.1f} ({prev/tot*100:.0f}%) | non-pensioni: {tot-prev:.1f} ({(tot-prev)/tot*100:.0f}%)")
print(f"Cuneo+famiglia gia' dentro i 180: {44.81+24.19:.0f} mld")
print(f"Saldo lordo {saldo_lordo:+.1f} | netto {saldo_netto:+.1f}")
print(f"Media {target_mean:,.0f} | Mediana {median:,.0f} | gap {target_mean-median:,.0f} | sotto la media {frac_below_mean*100:.0f}%")
print(f"Gini {gini:.2f} | top20% {top20*100:.0f}% | bottom50% {bottom50*100:.0f}%")
print(f"'Media 29.019' = escludere ~{f29*100:.0f}% piu' basso")
