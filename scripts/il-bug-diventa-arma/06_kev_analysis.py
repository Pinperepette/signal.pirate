#!/usr/bin/env python3
"""
06_kev_analysis.py — Incrocia CISA KEV con i dati CVE/ExploitDB
Domanda: per le CVE sfruttate in attacchi reali, l'exploit pubblico
         esisteva gia' prima che CISA le aggiungesse al catalogo?

Input:  data/matched_delta.csv (CVE + exploit + delta)
        data/kev.csv (CISA KEV)
        data/nvd_cves.csv (per le CVE senza exploit pubblico)
Output: output/04_kev.png
        Statistiche a terminale
"""

import csv
import os
import numpy as np
from datetime import datetime

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import PercentFormatter
except ImportError:
    print('[!] Installa matplotlib: pip install matplotlib')
    raise SystemExit(1)

MATCHED_FILE = os.path.join('data', 'matched_delta.csv')
KEV_FILE = os.path.join('data', 'kev.csv')
NVD_FILE = os.path.join('data', 'nvd_cves.csv')
OUTPUT_DIR = 'output'

# Stile blog
DARK_BG = '#0a0a0f'
DARK_FG = '#e0e0e0'
GREEN = '#00ff88'
PURPLE = '#7c4dff'
RED = '#ff6b6b'
CYAN = '#4ecdc4'
ORANGE = '#ff8800'
GRID_COLOR = '#1a1a2e'
DIM = '#3a3a5a'


def parse_date(s):
    for fmt in ('%Y-%m-%d', '%Y/%m/%d'):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    return None


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Carica KEV
    kev = {}
    with open(KEV_FILE, 'r') as f:
        for row in csv.DictReader(f):
            cve_id = row['cve_id'].strip()
            d = parse_date(row['kev_date_added'])
            if d:
                kev[cve_id] = {
                    'date_added': d,
                    'vendor': row.get('vendor', ''),
                    'product': row.get('product', '')
                }
    print(f'[*] KEV: {len(kev):,} CVE attivamente sfruttate')

    # Carica matched (CVE con exploit pubblico)
    matched = {}
    with open(MATCHED_FILE, 'r') as f:
        for row in csv.DictReader(f):
            cve_id = row['cve_id'].strip()
            matched[cve_id] = {
                'published_date': parse_date(row['published_date']),
                'exploit_date': parse_date(row['exploit_date']),
                'delta_days': int(row['delta_days'])
            }
    print(f'[*] Matched: {len(matched):,} CVE con exploit pubblico')

    # Carica NVD (tutte le CVE)
    nvd = {}
    with open(NVD_FILE, 'r') as f:
        for row in csv.DictReader(f):
            cve_id = row['cve_id'].strip()
            d = parse_date(row['published_date'])
            if d:
                nvd[cve_id] = d

    # Incrocio KEV con matched
    kev_with_exploit = []
    kev_without_exploit = []
    kev_not_in_nvd = 0

    for cve_id, kev_data in kev.items():
        if cve_id in matched:
            m = matched[cve_id]
            # Giorni tra exploit pubblico e aggiunta a KEV
            exploit_to_kev = (kev_data['date_added'] - m['exploit_date']).days
            # Giorni tra CVE e aggiunta a KEV
            if m['published_date']:
                cve_to_kev = (kev_data['date_added'] - m['published_date']).days
            else:
                cve_to_kev = None
            kev_with_exploit.append({
                'cve_id': cve_id,
                'cve_to_exploit': m['delta_days'],
                'exploit_to_kev': exploit_to_kev,
                'cve_to_kev': cve_to_kev,
                'vendor': kev_data['vendor'],
                'product': kev_data['product']
            })
        elif cve_id in nvd:
            cve_to_kev = (kev_data['date_added'] - nvd[cve_id]).days
            kev_without_exploit.append({
                'cve_id': cve_id,
                'cve_to_kev': cve_to_kev,
                'vendor': kev_data['vendor']
            })
        else:
            kev_not_in_nvd += 1

    total_kev = len(kev)
    n_with = len(kev_with_exploit)
    n_without = len(kev_without_exploit)

    print(f'\n--- KEV vs ExploitDB ---')
    print(f'  KEV totali:                   {total_kev:,}')
    print(f'  KEV con exploit pubblico:     {n_with:,} ({n_with/total_kev*100:.1f}%)')
    print(f'  KEV senza exploit pubblico:   {n_without:,} ({n_without/total_kev*100:.1f}%)')
    print(f'  KEV non nel range NVD:        {kev_not_in_nvd:,}')

    # Statistiche exploit_to_kev (per quanti giorni l'exploit era pubblico prima di KEV)
    e2k = [e['exploit_to_kev'] for e in kev_with_exploit]
    e2k_arr = np.array(e2k)
    pre_kev = np.sum(e2k_arr > 0)  # exploit pubblico PRIMA di KEV

    print(f'\n--- Tempo exploit -> KEV ({n_with:,} CVE) ---')
    print(f'  Exploit pubblico PRIMA di KEV:  {pre_kev:,} ({pre_kev/n_with*100:.1f}%)')
    print(f'  Mediana exploit->KEV:           {int(np.median(e2k_arr))} giorni')
    print(f'  Media exploit->KEV:             {int(np.mean(e2k_arr))} giorni')

    # Quanti avevano exploit > 30d prima di KEV
    pre_30 = np.sum(e2k_arr > 30)
    pre_90 = np.sum(e2k_arr > 90)
    pre_365 = np.sum(e2k_arr > 365)
    print(f'  Exploit pubblico > 30d prima:   {pre_30:,} ({pre_30/n_with*100:.1f}%)')
    print(f'  Exploit pubblico > 90d prima:   {pre_90:,} ({pre_90/n_with*100:.1f}%)')
    print(f'  Exploit pubblico > 1 anno prima: {pre_365:,} ({pre_365/n_with*100:.1f}%)')

    # Statistiche CVE -> KEV
    c2k = [e['cve_to_kev'] for e in kev_with_exploit if e['cve_to_kev'] is not None]
    c2k_arr = np.array(c2k)
    print(f'\n--- Tempo CVE -> KEV ---')
    print(f'  Mediana CVE->KEV:   {int(np.median(c2k_arr))} giorni')
    print(f'  Media CVE->KEV:     {int(np.mean(c2k_arr))} giorni')

    # Plot
    plot_kev(kev_with_exploit, kev_without_exploit, total_kev)
    print(f'\n[+] Grafico salvato in {OUTPUT_DIR}/04_kev.png')


def plot_kev(kev_with, kev_without, total_kev):
    fig, axes = plt.subplots(1, 3, figsize=(15, 6))
    fig.patch.set_facecolor(DARK_BG)
    fig.suptitle('CISA KEV: LE CVE USATE IN ATTACCHI REALI',
                 color=DARK_FG, fontsize=12, fontfamily='monospace',
                 fontweight='bold', y=1.02)

    n_with = len(kev_with)
    n_without = len(kev_without)

    # Panel 1: KEV con vs senza exploit pubblico
    ax = axes[0]
    ax.set_facecolor(DARK_BG)
    categories = ['Con exploit\npubblico', 'Senza exploit\npubblico']
    counts = [n_with, n_without]
    colors = [RED, DIM]
    bars = ax.barh(categories, counts, color=colors, alpha=0.85, edgecolor=DARK_BG)
    ax.set_title('KEV vs EXPLOITDB', color=GREEN, fontsize=11,
                 fontweight='bold', fontfamily='monospace')
    ax.tick_params(colors=DARK_FG, labelsize=8)
    ax.spines['bottom'].set_color(GRID_COLOR)
    ax.spines['left'].set_color(GRID_COLOR)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    for bar, count in zip(bars, counts):
        ax.text(bar.get_width() + total_kev * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f'{count:,} ({count/total_kev:.0%})', va='center',
                color=DARK_FG, fontsize=9, fontfamily='monospace')

    # Panel 2: Distribuzione exploit_to_kev (giorni tra exploit pubblico e KEV)
    ax = axes[1]
    ax.set_facecolor(DARK_BG)
    e2k = np.array([e['exploit_to_kev'] for e in kev_with])
    # Clip per visualizzazione
    e2k_clip = e2k[(e2k >= -365) & (e2k <= 2000)]
    if len(e2k_clip) > 0:
        ax.hist(e2k_clip, bins=50, color=ORANGE, alpha=0.85, edgecolor=DARK_BG)
    ax.axvline(x=0, color=GREEN, linestyle='-', linewidth=1.5, alpha=0.8)
    ax.text(10, ax.get_ylim()[1] * 0.9, 'KEV', color=GREEN,
            fontsize=8, fontfamily='monospace', fontweight='bold')
    ax.set_title('GIORNI EXPLOIT -> KEV', color=GREEN, fontsize=11,
                 fontweight='bold', fontfamily='monospace')
    ax.set_xlabel('Giorni (positivo = exploit prima di KEV)', color=DARK_FG,
                  fontsize=7, fontfamily='monospace')
    ax.tick_params(colors=DARK_FG, labelsize=7)
    ax.spines['bottom'].set_color(GRID_COLOR)
    ax.spines['left'].set_color(GRID_COLOR)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='y', color=GRID_COLOR, linewidth=0.5)

    # Panel 3: Timeline completa CVE -> exploit -> KEV (top 15 piu' lunghe)
    ax = axes[2]
    ax.set_facecolor(DARK_BG)

    # Ordina per exploit_to_kev decrescente (exploit pubblico piu' a lungo prima di KEV)
    sorted_kev = sorted(kev_with, key=lambda x: x['exploit_to_kev'], reverse=True)
    top15 = sorted_kev[:15]

    labels = []
    starts = []
    widths_exploit = []
    widths_kev = []

    for i, e in enumerate(top15):
        cve_short = e['cve_id'].replace('CVE-', '')
        labels.append(cve_short)
        c2e = e['cve_to_exploit']
        e2k = e['exploit_to_kev']
        # Bar 1: CVE -> exploit (verde se positivo, rosso se negativo)
        starts.append(0)
        widths_exploit.append(c2e)
        widths_kev.append(e2k)

    y = np.arange(len(labels))

    # Exploit disponibile prima di KEV
    bars1 = ax.barh(y, widths_kev, left=0, color=ORANGE, alpha=0.85,
                    edgecolor=DARK_BG, height=0.6, label='exploit -> KEV')

    for i, (w, label) in enumerate(zip(widths_kev, labels)):
        ax.text(w + 10, i, f'{w}d', va='center',
                color=DARK_FG, fontsize=6, fontfamily='monospace')

    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_title('TOP 15: EXPLOIT PUBBLICO\nPRIMA DI KEV', color=GREEN,
                 fontsize=10, fontweight='bold', fontfamily='monospace')
    ax.set_xlabel('Giorni exploit pubblico prima di KEV', color=DARK_FG,
                  fontsize=7, fontfamily='monospace')
    ax.tick_params(colors=DARK_FG, labelsize=6)
    ax.spines['bottom'].set_color(GRID_COLOR)
    ax.spines['left'].set_color(GRID_COLOR)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, '04_kev.png'), dpi=150,
                facecolor=DARK_BG, bbox_inches='tight')
    plt.close()


if __name__ == '__main__':
    main()
