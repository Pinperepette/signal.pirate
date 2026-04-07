#!/usr/bin/env python3
"""
02_cabina.py — Il vincolo che nessuno calcola: la cabina MT/BT
===============================================================
Mostra che il vero collo di bottiglia non e' la rete nazionale
ma la cabina secondaria del quartiere, dimensionata negli anni '80.

Modello:
  Per ogni cabina j:  sum(P_base_i(t)) + sum(P_ev_k(t)) <= S_trafo_j

  con fattore di contemporaneita':
    k_c domestico = 0.3  (la gente non usa tutto insieme)
    k_c EV        = 0.85 (tutti attaccano quando arrivano)

Fonti:
  - e-distribuzione 2024: 445.144 cabine secondarie (85% rete nazionale)
    https://www.e-distribuzione.it/Azienda/I-nostri-numeri.html
  - e-distribuzione 2024: ~70 utenze per cabina
    https://www.e-distribuzione.it/archivio-news/2024/05/come-funziona-la-rete-di-distribuzione--le-cabine-secondarie.html
  - ABB: taglie standard 100/250/400/630 kVA
    https://library.e.abb.com/public/5d00023092cb45469e87fc614efc78b8/Gu_Cabine_MT-BT_it_1VCP000591_1511.pdf
  - ARERA: potenza impegnata domestica standard 3 kW
    https://web.archive.org/web/2024/https://www.arera.it/comunicati-stampa/dettaglio/elettricita-bollette-in-calo-del-198-nel-secondo-trimestre-2024

Output: output/04_cabina_saturazione.png
        output/05_cabina_nmax.png
        output/06_cabina_mappa_termica.png
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import os

OUTPUT_DIR = 'output'
os.makedirs(OUTPUT_DIR, exist_ok=True)

plt.rcParams.update({
    'figure.facecolor': '#0d1117',
    'axes.facecolor': '#0d1117',
    'axes.edgecolor': '#30363d',
    'axes.labelcolor': '#c9d1d9',
    'text.color': '#c9d1d9',
    'xtick.color': '#8b949e',
    'ytick.color': '#8b949e',
    'grid.color': '#21262d',
    'font.family': 'monospace',
    'font.size': 11,
})

# ─── PARAMETRI CABINA ────────────────────────────────────────────────

# Taglie trasformatori standard (kVA)
TAGLIE_TRAFO = [100, 250, 400, 630]

# Cabina urbana tipica
S_TRAFO        = 400            # kVA (la piu' diffusa in area urbana)
N_UTENZE       = 70             # e-distribuzione: media utenze/cabina
P_IMPEGNATA    = 3.0            # kW, contratto domestico standard (ARERA)
KC_DOMESTICO   = 0.30           # fattore di contemporaneita' domestico
KC_EV          = 0.85           # fattore di contemporaneita' EV (alto: tutti alle 19)
P_WALLBOX      = 7.4            # kW, monofase 32A
COS_PHI        = 0.95           # fattore di potenza

# Nazionale
N_CABINE_EDIST = 445_144        # e-distribuzione (85% della rete)
QUOTA_EDIST    = 0.85           # quota di e-distribuzione sulla rete nazionale
N_AUTO         = 40_300_000     # ACI 2025
N_FAMIGLIE     = 26_000_000    # ISTAT: famiglie italiane (~)


# ─── CALCOLO VINCOLO DI CABINA ──────────────────────────────────────

def vincolo_cabina(s_trafo, n_utenze, n_ev, p_imp=P_IMPEGNATA,
                   kc_dom=KC_DOMESTICO, kc_ev=KC_EV, p_wb=P_WALLBOX,
                   cos_phi=COS_PHI):
    """
    Verifica il vincolo di cabina:
      P_base + P_ev <= S_trafo * cos_phi

    Returns: (P_base_kW, P_ev_kW, P_totale_kW, S_disponibile_kW, margine_kW)
    """
    p_base = n_utenze * p_imp * kc_dom              # carico domestico coincidente
    p_ev = n_ev * p_wb * kc_ev                      # carico EV coincidente
    s_disp = s_trafo * cos_phi                      # potenza attiva disponibile
    margine = s_disp - p_base - p_ev
    return p_base, p_ev, p_base + p_ev, s_disp, margine


def n_max_auto(s_trafo=S_TRAFO, n_utenze=N_UTENZE):
    """Quante auto prima di saturare la cabina."""
    p_base = n_utenze * P_IMPEGNATA * KC_DOMESTICO
    s_disp = s_trafo * COS_PHI
    margine = s_disp - p_base
    n_max = margine / (P_WALLBOX * KC_EV)
    return int(n_max), margine


# ─── GRAFICI ─────────────────────────────────────────────────────────

def plot_saturazione():
    """Grafico 4: barre impilate — carico base + N auto su cabina 400 kVA."""
    n_ev_range = np.arange(0, 61, 1)
    fig, ax = plt.subplots(figsize=(14, 7))

    p_bases = []
    p_evs = []
    for n_ev in n_ev_range:
        pb, pe, pt, sd, mg = vincolo_cabina(S_TRAFO, N_UTENZE, n_ev)
        p_bases.append(pb)
        p_evs.append(pe)

    p_bases = np.array(p_bases)
    p_evs = np.array(p_evs)
    p_totali = p_bases + p_evs
    s_disp = S_TRAFO * COS_PHI

    ax.fill_between(n_ev_range, 0, p_bases, color='#4ecdc4', alpha=0.5,
                    label=f'Carico domestico ({N_UTENZE} utenze, k_c={KC_DOMESTICO})')
    ax.fill_between(n_ev_range, p_bases, p_totali, color='#ff6b6b', alpha=0.6,
                    label=f'Carico EV (wallbox {P_WALLBOX} kW, k_c={KC_EV})')

    # linea capacita' trasformatore
    ax.axhline(y=s_disp, color='#f5c518', linewidth=2.5, linestyle='-',
               label=f'Capacita trasformatore: {S_TRAFO} kVA = {s_disp:.0f} kW')

    # punto di saturazione
    n_max, margine = n_max_auto()
    ax.axvline(x=n_max, color='#ff6b6b', linewidth=2, linestyle='--', alpha=0.8)
    ax.annotate(f'SATURAZIONE\n{n_max} auto',
                xy=(n_max, s_disp), xytext=(n_max + 8, s_disp * 0.85),
                fontsize=13, fontweight='bold', color='#ff6b6b',
                arrowprops=dict(arrowstyle='->', color='#ff6b6b', lw=2))

    # zona rossa
    ax.fill_between(n_ev_range, s_disp, p_totali,
                    where=p_totali > s_disp,
                    color='#ff6b6b', alpha=0.2, hatch='///',
                    label='SOVRACCARICO')

    # annotazioni
    ax.text(2, p_bases[0] / 2, f'{p_bases[0]:.0f} kW\nbase',
            ha='center', va='center', fontsize=11, color='#0d1117',
            fontweight='bold')
    ax.text(2, s_disp - margine/2,
            f'{margine:.0f} kW\nmargine',
            ha='center', va='center', fontsize=10, color='#f5c518')

    ax.set_xlabel('Numero di auto elettriche sulla cabina', fontsize=13)
    ax.set_ylabel('Potenza (kW)', fontsize=13)
    ax.set_title(f'Cabina {S_TRAFO} kVA, {N_UTENZE} utenze: '
                 f'bastano {n_max} auto per saturarla',
                 fontsize=14, fontweight='bold')
    ax.legend(loc='upper left', fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 60)
    ax.set_ylim(0, max(p_totali.max(), s_disp) * 1.15)

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/04_cabina_saturazione.png', dpi=150,
                bbox_inches='tight', facecolor='#0d1117')
    plt.close()

    print(f'=== VINCOLO CABINA {S_TRAFO} kVA ===')
    print(f'Utenze:            {N_UTENZE}')
    print(f'Carico base:       {p_bases[0]:.0f} kW (k_c = {KC_DOMESTICO})')
    print(f'Capacita:          {s_disp:.0f} kW')
    print(f'Margine:           {margine:.0f} kW')
    print(f'N_max auto:        {n_max}')
    print(f'Penetrazione max:  {n_max/N_UTENZE*100:.0f}% delle utenze')
    print(f'[OK] {OUTPUT_DIR}/04_cabina_saturazione.png')
    print()


def plot_nmax_per_taglia():
    """Grafico 5: N max auto per ogni taglia di trasformatore."""
    fig, ax = plt.subplots(figsize=(12, 7))

    # Per ogni taglia, varia anche il numero di utenze proporzionalmente
    risultati = []
    for s in TAGLIE_TRAFO:
        # utenze proporzionali alla taglia (approssimazione)
        n_ut = int(N_UTENZE * s / S_TRAFO)
        p_base = n_ut * P_IMPEGNATA * KC_DOMESTICO
        s_disp = s * COS_PHI
        margine = s_disp - p_base
        n_max = max(0, int(margine / (P_WALLBOX * KC_EV)))
        pct = n_max / n_ut * 100 if n_ut > 0 else 0
        risultati.append((s, n_ut, n_max, pct, margine))

    x = np.arange(len(TAGLIE_TRAFO))
    labels = [f'{s} kVA\n({r[1]} utenze)' for s, r in zip(TAGLIE_TRAFO, risultati)]
    n_maxs = [r[2] for r in risultati]
    pcts = [r[3] for r in risultati]

    colors = ['#ff6b6b' if p < 30 else '#f5c518' if p < 50 else '#00ff88'
              for p in pcts]

    bars = ax.bar(x, n_maxs, color=colors, width=0.5, edgecolor='none')

    for i, (bar, r) in enumerate(zip(bars, risultati)):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f'{r[2]} auto\n({r[3]:.0f}%)',
                ha='center', fontsize=12, fontweight='bold', color=colors[i])

    ax.set_xlabel('Taglia trasformatore', fontsize=13)
    ax.set_ylabel('N. massimo auto elettriche', fontsize=13)
    ax.set_title('Quante auto regge ogni tipo di cabina?\n'
                 '(prima del sovraccarico)',
                 fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11)
    ax.grid(axis='y', alpha=0.3)

    # nota
    ax.text(0.98, 0.95,
            f'Wallbox: {P_WALLBOX} kW\n'
            f'k_c domestico: {KC_DOMESTICO}\n'
            f'k_c EV: {KC_EV}\n'
            f'cos(phi): {COS_PHI}',
            transform=ax.transAxes, fontsize=9, va='top', ha='right',
            bbox=dict(boxstyle='round', facecolor='#1a1a2e', alpha=0.8,
                      edgecolor='#30363d'))

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/05_cabina_nmax.png', dpi=150,
                bbox_inches='tight', facecolor='#0d1117')
    plt.close()
    print(f'[OK] {OUTPUT_DIR}/05_cabina_nmax.png')

    for s, n_ut, n_max, pct, mg in risultati:
        print(f'  {s:>4} kVA, {n_ut:>3} utenze → max {n_max:>3} auto ({pct:.0f}%)')
    print()


def plot_mappa_termica():
    """Grafico 6: heatmap — penetrazione EV vs taglia cabina vs margine."""
    penetrazioni = np.arange(0, 105, 5)   # % utenze con EV
    taglie = np.array([100, 160, 250, 400, 630, 800, 1000])

    # matrice: margine residuo in % della capacita'
    margine_pct = np.zeros((len(taglie), len(penetrazioni)))

    for i, s in enumerate(taglie):
        n_ut = int(N_UTENZE * s / S_TRAFO)
        s_disp = s * COS_PHI
        p_base = n_ut * P_IMPEGNATA * KC_DOMESTICO
        for j, pen in enumerate(penetrazioni):
            n_ev = int(n_ut * pen / 100)
            p_ev = n_ev * P_WALLBOX * KC_EV
            margine = (s_disp - p_base - p_ev) / s_disp * 100
            margine_pct[i, j] = margine

    fig, ax = plt.subplots(figsize=(14, 7))

    # heatmap con diverging colormap
    from matplotlib.colors import TwoSlopeNorm
    norm = TwoSlopeNorm(vmin=-100, vcenter=0, vmax=50)
    im = ax.imshow(margine_pct, aspect='auto', cmap='RdYlGn', norm=norm,
                   origin='lower')

    # assi
    ax.set_xticks(np.arange(0, len(penetrazioni), 2))
    ax.set_xticklabels([f'{p}%' for p in penetrazioni[::2]])
    ax.set_yticks(range(len(taglie)))
    ax.set_yticklabels([f'{s} kVA' for s in taglie])
    ax.set_xlabel('Penetrazione EV (% utenze con wallbox)', fontsize=13)
    ax.set_ylabel('Taglia trasformatore', fontsize=13)
    ax.set_title('Margine residuo cabina: verde = OK, rosso = sovraccarico',
                 fontsize=14, fontweight='bold')

    # annotazioni nei quadranti
    for i in range(len(taglie)):
        for j in range(0, len(penetrazioni), 2):
            val = margine_pct[i, j]
            color = '#0d1117' if abs(val) < 30 else '#c9d1d9'
            ax.text(j, i, f'{val:.0f}%', ha='center', va='center',
                    fontsize=8, fontweight='bold', color=color)

    # contorno zero (linea di saturazione)
    ax.contour(margine_pct, levels=[0], colors=['#f5c518'],
               linewidths=2.5, linestyles='-')

    cbar = plt.colorbar(im, ax=ax, label='Margine (%)', shrink=0.8)
    cbar.ax.yaxis.label.set_color('#c9d1d9')
    cbar.ax.tick_params(colors='#8b949e')

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/06_cabina_mappa_termica.png', dpi=150,
                bbox_inches='tight', facecolor='#0d1117')
    plt.close()
    print(f'[OK] {OUTPUT_DIR}/06_cabina_mappa_termica.png')


def calcolo_nazionale():
    """Calcolo: quante cabine servono a livello nazionale."""
    n_cabine_totali = int(N_CABINE_EDIST / QUOTA_EDIST)
    n_max, _ = n_max_auto()

    # auto per cabina se tutte elettriche
    auto_per_famiglia = N_AUTO / N_FAMIGLIE  # ~1.55
    auto_per_cabina = N_UTENZE * auto_per_famiglia

    # cabine da potenziare
    if auto_per_cabina > n_max:
        # fattore di potenziamento medio
        fattore = auto_per_cabina / n_max
        cabine_da_potenziare = n_cabine_totali  # praticamente tutte
    else:
        fattore = 1.0
        cabine_da_potenziare = 0

    # costo
    costo_potenziamento_unitario = 80_000  # EUR, media (Phase S.r.l.)
    costo_totale = cabine_da_potenziare * costo_potenziamento_unitario

    print(f'=== SCALA NAZIONALE ===')
    print(f'Cabine secondarie totali:  {n_cabine_totali:>12,}')
    print(f'N_max auto per cabina:     {n_max:>12}')
    print(f'Auto/famiglia:             {auto_per_famiglia:>12.2f}')
    print(f'Auto/cabina (100% EV):     {auto_per_cabina:>12.1f}')
    print(f'Fattore sovraccarico:      {fattore:>12.1f}x')
    print(f'Cabine da potenziare:      {cabine_da_potenziare:>12,}')
    print(f'Costo unitario:            {costo_potenziamento_unitario:>12,} EUR')
    print(f'Costo totale cabine:       {costo_totale/1e9:>12.1f} mld EUR')
    print()


# ─── MAIN ────────────────────────────────────────────────────────────

if __name__ == '__main__':
    plot_saturazione()
    plot_nmax_per_taglia()
    plot_mappa_termica()
    calcolo_nazionale()
