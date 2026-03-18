#!/usr/bin/env python3
"""
04_plot.py — Genera i 3 grafici dell'analisi
Input:  data/matched_delta.csv
Output: output/01_histogram.png  — distribuzione completa con backfill evidenziato
        output/02_cdf.png        — CDF vista pulita (delta >= -365)
        output/03_outliers.png   — breakdown categorie + top veloci + coda lunga
"""

import csv
import os
import numpy as np

# Prova matplotlib
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import PercentFormatter
except ImportError:
    print('[!] Installa matplotlib: pip install matplotlib')
    raise SystemExit(1)

INPUT_FILE = os.path.join('data', 'matched_delta.csv')
OUTPUT_DIR = 'output'

# Soglia backfill (stessa di 03_match_and_delta.py)
BACKFILL_THRESHOLD = -365

# Stile coerente col blog (sfondo scuro, verde accento)
DARK_BG = '#0a0a0f'
DARK_FG = '#e0e0e0'
GREEN = '#00ff88'
PURPLE = '#7c4dff'
RED = '#ff6b6b'
CYAN = '#4ecdc4'
ORANGE = '#ff8800'
GRID_COLOR = '#1a1a2e'
DIM = '#3a3a5a'


def load_data():
    deltas = []
    rows = []
    with open(INPUT_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            d = int(row['delta_days'])
            deltas.append(d)
            rows.append(row)
    return np.array(deltas), rows


def style_ax(ax, title, xlabel, ylabel):
    ax.set_facecolor(DARK_BG)
    ax.set_title(title, color=GREEN, fontsize=14, fontweight='bold',
                 fontfamily='monospace', pad=15)
    ax.set_xlabel(xlabel, color=DARK_FG, fontsize=10, fontfamily='monospace')
    ax.set_ylabel(ylabel, color=DARK_FG, fontsize=10, fontfamily='monospace')
    ax.tick_params(colors=DARK_FG, labelsize=8)
    ax.spines['bottom'].set_color(GRID_COLOR)
    ax.spines['left'].set_color(GRID_COLOR)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='y', color=GRID_COLOR, linewidth=0.5)


def plot_histogram(deltas):
    """Grafico 1: Istogramma completo con zona backfill evidenziata."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6),
                                    gridspec_kw={'width_ratios': [1, 2]})
    fig.patch.set_facecolor(DARK_BG)

    # Panel sinistro: pre-disclosure (-365..0)
    pre = deltas[(deltas >= BACKFILL_THRESHOLD) & (deltas < 0)]
    ax1.hist(pre, bins=40, color=RED, alpha=0.85, edgecolor=DARK_BG,
             linewidth=0.5)
    style_ax(ax1, 'PRE-DISCLOSURE (-365d..0)',
             'Giorni (negativi)', 'Numero CVE')

    # Annotazione
    ax1.text(0.95, 0.92, f'{len(pre):,} CVE',
             transform=ax1.transAxes, ha='right',
             color=RED, fontsize=11, fontfamily='monospace', fontweight='bold')
    ax1.text(0.95, 0.84, f'exploit prima della CVE',
             transform=ax1.transAxes, ha='right',
             color=DIM, fontsize=8, fontfamily='monospace')

    # Panel destro: post-disclosure (0..365)
    post = deltas[(deltas >= 0) & (deltas <= 365)]
    ax2.hist(post, bins=73, color=GREEN, alpha=0.85, edgecolor=DARK_BG,
             linewidth=0.5)

    # Linee verticali per riferimento
    ax2.axvline(x=7, color=RED, linestyle='--', linewidth=1.2, alpha=0.8)
    ax2.axvline(x=30, color=ORANGE, linestyle='--', linewidth=1.2, alpha=0.8)
    ax2.axvline(x=90, color=PURPLE, linestyle='--', linewidth=1.2, alpha=0.8)

    ymax = ax2.get_ylim()[1]
    ax2.text(9, ymax * 0.92, '7d', color=RED,
             fontsize=9, fontfamily='monospace', fontweight='bold')
    ax2.text(32, ymax * 0.92, '30d', color=ORANGE,
             fontsize=9, fontfamily='monospace', fontweight='bold')
    ax2.text(92, ymax * 0.92, '90d', color=PURPLE,
             fontsize=9, fontfamily='monospace', fontweight='bold')

    style_ax(ax2, 'POST-DISCLOSURE (0..365d)',
             'Giorni', 'Numero CVE')

    # Annotazione
    ax2.text(0.95, 0.92, f'{len(post):,} CVE',
             transform=ax2.transAxes, ha='right',
             color=GREEN, fontsize=11, fontfamily='monospace', fontweight='bold')

    fig.suptitle('TEMPO DI WEAPONIZATION (CVE -> EXPLOIT)',
                 color=DARK_FG, fontsize=12, fontfamily='monospace',
                 fontweight='bold', y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, '01_histogram.png'), dpi=150,
                facecolor=DARK_BG, bbox_inches='tight')
    plt.close()
    print('[+] 01_histogram.png')


def plot_cdf(deltas):
    """Grafico 2: CDF sulla vista pulita (delta >= -365)."""
    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor(DARK_BG)

    # Vista pulita: escludi backfill
    clean = np.sort(deltas[deltas >= BACKFILL_THRESHOLD])
    cdf = np.arange(1, len(clean) + 1) / len(clean)

    ax.plot(clean, cdf, color=GREEN, linewidth=2)
    ax.fill_between(clean, cdf, alpha=0.1, color=GREEN)

    # Linea verticale a x=0 (momento pubblicazione CVE)
    ax.axvline(x=0, color=DARK_FG, linestyle='-', linewidth=1, alpha=0.4)
    ax.text(5, 0.05, 'CVE pubblicata', color=DIM,
            fontsize=8, fontfamily='monospace')

    # Percentuale a delta=0 (pre-disclosure + same-day)
    pct_zero = np.sum(clean <= 0) / len(clean)
    ax.plot(0, pct_zero, 'o', color=ORANGE, markersize=8, zorder=5)
    ax.annotate(f'delta<=0: {pct_zero:.0%}', xy=(0, pct_zero),
                xytext=(-120, pct_zero + 0.08),
                color=ORANGE, fontsize=9, fontfamily='monospace',
                fontweight='bold',
                arrowprops=dict(arrowstyle='->', color=ORANGE, lw=1.2))

    # Marker a 7, 30, 90 giorni
    for days, color, label in [(7, RED, '7d'), (30, CYAN, '30d'),
                                (90, PURPLE, '90d')]:
        pct = np.sum(clean <= days) / len(clean)
        ax.plot(days, pct, 'o', color=color, markersize=8, zorder=5)
        ax.annotate(f'{label}: {pct:.0%}', xy=(days, pct),
                    xytext=(days + 20, pct - 0.04),
                    color=color, fontsize=9, fontfamily='monospace',
                    fontweight='bold',
                    arrowprops=dict(arrowstyle='->', color=color, lw=1.2))

    ax.set_xlim(-365, 365)
    ax.yaxis.set_major_formatter(PercentFormatter(1.0))

    style_ax(ax, 'CDF — VISTA PULITA (ESCLUSO BACKFILL NVD)',
             'Giorni dalla pubblicazione CVE', 'Percentuale cumulativa')

    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, '02_cdf.png'), dpi=150,
                facecolor=DARK_BG)
    plt.close()
    print('[+] 02_cdf.png')


def plot_outliers(deltas, rows):
    """Grafico 3: Breakdown categorie + top veloci + backfill."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 6))
    fig.patch.set_facecolor(DARK_BG)

    total = len(deltas)

    # Panel 1: Breakdown completo per categorie
    categories = [
        f'Backfill NVD\n(< {BACKFILL_THRESHOLD}d)',
        'Pre-disclosure\n(-365d..0)',
        'Same-day\n(= 0)',
        '1-7 giorni',
        '8-30 giorni',
        '> 30 giorni'
    ]
    counts = [
        int(np.sum(deltas < BACKFILL_THRESHOLD)),
        int(np.sum((deltas >= BACKFILL_THRESHOLD) & (deltas < 0))),
        int(np.sum(deltas == 0)),
        int(np.sum((deltas > 0) & (deltas <= 7))),
        int(np.sum((deltas > 7) & (deltas <= 30))),
        int(np.sum(deltas > 30))
    ]
    colors_bar = [DIM, RED, ORANGE, CYAN, PURPLE, DARK_FG]

    ax = axes[0]
    ax.set_facecolor(DARK_BG)
    bars = ax.barh(categories, counts, color=colors_bar, alpha=0.85,
                   edgecolor=DARK_BG)
    ax.set_title('DISTRIBUZIONE', color=GREEN, fontsize=11,
                 fontweight='bold', fontfamily='monospace')
    ax.tick_params(colors=DARK_FG, labelsize=7)
    ax.spines['bottom'].set_color(GRID_COLOR)
    ax.spines['left'].set_color(GRID_COLOR)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    for bar, count in zip(bars, counts):
        ax.text(bar.get_width() + total * 0.01, bar.get_y() + bar.get_height() / 2,
                f'{count:,} ({count/total:.0%})', va='center',
                color=DARK_FG, fontsize=8, fontfamily='monospace')

    # Panel 2: Top 20 exploit piu' veloci (delta > 0, non same-day)
    ax = axes[1]
    ax.set_facecolor(DARK_BG)
    fastest = [(r['cve_id'], int(r['delta_days'])) for r in rows
               if int(r['delta_days']) > 0]
    fastest.sort(key=lambda x: x[1])
    top20 = fastest[:20]
    labels = [f'{cve} ({d}d)' for cve, d in top20]
    vals = [d for _, d in top20]

    bars = ax.barh(labels[::-1], vals[::-1], color=GREEN, alpha=0.85,
                   edgecolor=DARK_BG)
    ax.set_title('TOP 20 PIU\' VELOCI (delta > 0)', color=GREEN, fontsize=11,
                 fontweight='bold', fontfamily='monospace')
    ax.tick_params(colors=DARK_FG, labelsize=5.5)
    ax.spines['bottom'].set_color(GRID_COLOR)
    ax.spines['left'].set_color(GRID_COLOR)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Panel 3: Distribuzione pre-disclosure reale (-365..0)
    ax = axes[2]
    ax.set_facecolor(DARK_BG)
    pre_real = deltas[(deltas >= BACKFILL_THRESHOLD) & (deltas < 0)]
    if len(pre_real) > 0:
        ax.hist(pre_real, bins=40, color=RED, alpha=0.85,
                edgecolor=DARK_BG)

        # Marker -30d
        ax.axvline(x=-30, color=ORANGE, linestyle='--', linewidth=1.2, alpha=0.8)
        within_30 = np.sum(pre_real >= -30)
        ax.text(-28, ax.get_ylim()[1] * 0.9,
                f'-30d: {within_30:,}', color=ORANGE,
                fontsize=8, fontfamily='monospace', fontweight='bold')

    ax.set_title('PRE-DISCLOSURE REALE', color=GREEN, fontsize=11,
                 fontweight='bold', fontfamily='monospace')
    ax.set_xlabel('Giorni (negativi)', color=DARK_FG, fontsize=8,
                  fontfamily='monospace')
    ax.tick_params(colors=DARK_FG, labelsize=7)
    ax.spines['bottom'].set_color(GRID_COLOR)
    ax.spines['left'].set_color(GRID_COLOR)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='y', color=GRID_COLOR, linewidth=0.5)

    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, '03_outliers.png'), dpi=150,
                facecolor=DARK_BG)
    plt.close()
    print('[+] 03_outliers.png')


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print('[*] Caricamento dati...')
    deltas, rows = load_data()
    total = len(deltas)
    print(f'[*] {total:,} CVE con exploit matchato')

    plot_histogram(deltas)
    plot_cdf(deltas)
    plot_outliers(deltas, rows)

    # Riepilogo
    clean = deltas[deltas >= BACKFILL_THRESHOLD]
    clean_pos = clean[clean >= 0]

    print(f'\n--- Riepilogo ---')
    print(f'  Totale match:            {total:,}')
    print(f'  Backfill NVD (<-365d):   {np.sum(deltas < BACKFILL_THRESHOLD):,}')
    print(f'  Vista pulita:            {len(clean):,}')
    print(f'  Pre-disclosure reale:    {np.sum((clean >= BACKFILL_THRESHOLD) & (clean < 0)):,}')
    print(f'  Same-day:                {np.sum(clean == 0):,}')
    print(f'  Entro 7d (post-CVE):     {np.sum(clean_pos <= 7):,}')
    print(f'  Entro 30d (post-CVE):    {np.sum(clean_pos <= 30):,}')
    print(f'  Mediana (pulita):        {int(np.median(clean))} giorni')

    print(f'\n[+] Grafici salvati in {OUTPUT_DIR}/')


if __name__ == '__main__':
    main()
