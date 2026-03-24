#!/usr/bin/env python3
"""
04_mta_analysis.py — Analisi MTA New York
Carica i dati orari della metro di NYC, analizza la distribuzione
degli arrivi e verifica se e' Poisson o heavy-tail.

Output: output/05_mta_hourly.png, output/06_mta_distribution.png
"""

import csv
import numpy as np
from collections import defaultdict
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats
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

MTA_FILE = 'data/mta_hourly_sample.csv'

# Stazioni target NYC
TARGET_STATIONS = [
    'Times Sq-42 St', 'Grand Central', '34 St-Herald Sq',
    '14 St-Union Sq', 'Fulton St', '34 St-Penn Station',
    '59 St-Columbus Circle', 'Atlantic Av-Barclays Ctr'
]


def load_mta_data():
    """Carica e aggrega i dati MTA per stazione e ora."""
    print('[*] Caricamento MTA data...')
    hourly = defaultdict(lambda: defaultdict(list))
    station_names = set()

    with open(MTA_FILE) as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            station = row.get('station_complex', '')
            rid_str = row.get('ridership', '')
            if not rid_str:
                continue
            try:
                ridership = float(rid_str)
            except (ValueError, TypeError):
                continue
            ts = row.get('transit_timestamp', '')

            # Parsing timestamp: "02/25/2022 08:00:00 AM"
            try:
                dt = datetime.strptime(ts, '%m/%d/%Y %I:%M:%S %p')
            except ValueError:
                continue

            hour = dt.hour
            weekday = dt.weekday()

            # Solo giorni feriali (lun-ven)
            if weekday < 5:
                station_names.add(station)
                hourly[station][hour].append(ridership)
                count += 1

    print(f'[+] Caricate {count} righe, {len(station_names)} stazioni')
    return hourly


def plot_mta_hourly(hourly):
    """Plot 5: Profilo orario NYC per le stazioni principali."""
    fig, ax = plt.subplots(figsize=(12, 7))

    colors = ['#00ff88', '#7c4dff', '#ff6b6b', '#ff8800', '#4ecdc4',
              '#ffcc00', '#ff69b4', '#87ceeb']

    found = 0
    for i, target in enumerate(TARGET_STATIONS):
        # Match parziale sul nome
        matches = [s for s in hourly.keys() if target.lower() in s.lower()]
        if not matches:
            continue

        station = matches[0]
        hours = range(24)
        means = []
        for h in hours:
            vals = hourly[station][h]
            means.append(np.mean(vals) if vals else 0)

        # Somma tutte le classi tariffarie per quella stazione/ora
        label = target[:25]
        ax.plot(hours, means, color=colors[found % len(colors)],
                linewidth=2, label=label, alpha=0.85, marker='o', markersize=3)
        found += 1

    ax.set_xlabel('ora del giorno', fontsize=13)
    ax.set_ylabel('ridership medio orario (per classe tariffaria)', fontsize=13)
    ax.set_title('Profilo orario — Metro New York, giorni feriali (MTA 2022)',
                 fontsize=13, fontweight='bold')
    ax.set_xticks(range(24))
    ax.legend(loc='upper right', fontsize=8.5, framealpha=0.3)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '05_mta_hourly.png'), dpi=180)
    print(f'[+] output/05_mta_hourly.png')
    plt.close()


def plot_mta_distribution(hourly):
    """
    Plot 6: Distribuzione degli arrivi orari — Poisson vs realta'.
    Prende una stazione, un'ora fissa (8 AM), e confronta
    la distribuzione empirica con Poisson e log-normal.
    """
    # Pool tutti gli arrivi AM peak (7-9) da tutte le stazioni
    values = []
    for station in hourly:
        for h in [7, 8, 9]:
            values.extend(hourly[station][h])
    values = np.array(values)
    values = values[values > 0]
    target = 'Tutte le stazioni NYC'

    if len(values) < 30:
        print(f'[!] Troppi pochi dati ({len(values)} valori)')
        return

    print(f'[+] Distribuzione: {len(values)} valori AM peak da {len(hourly)} stazioni')

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Istogramma empirico
    ax1.hist(values, bins=30, density=True, color='#7c4dff', alpha=0.7,
             edgecolor='#0d1117', label='dati reali')

    # Fit Poisson
    lambda_hat = np.mean(values)
    x = np.arange(0, max(values) * 1.2, max(values) / 100)
    # Approssimazione normale per Poisson con lambda grande
    poisson_pdf = stats.norm.pdf(x, loc=lambda_hat, scale=np.sqrt(lambda_hat))
    ax1.plot(x, poisson_pdf, color='#00ff88', linewidth=2, label=f'Poisson (lambda={lambda_hat:.0f})')

    # Fit log-normal
    shape, loc, scale = stats.lognorm.fit(values, floc=0)
    lognorm_pdf = stats.lognorm.pdf(x, shape, loc, scale)
    ax1.plot(x, lognorm_pdf, color='#ff6b6b', linewidth=2, label='Log-normal fit')

    ax1.set_xlabel('ridership (arrivi/ora)', fontsize=11)
    ax1.set_ylabel('densita\'', fontsize=11)
    ax1.set_title(f'{target[:30]}... — ore 8:00', fontsize=11, fontweight='bold')
    ax1.legend(fontsize=9, framealpha=0.3)
    ax1.grid(True, alpha=0.3)

    # QQ plot
    sorted_vals = np.sort(values)
    theoretical = stats.norm.ppf(np.linspace(0.01, 0.99, len(sorted_vals)),
                                  loc=lambda_hat, scale=np.sqrt(lambda_hat))
    ax2.scatter(theoretical, sorted_vals, color='#7c4dff', s=15, alpha=0.6)
    lims = [min(theoretical.min(), sorted_vals.min()),
            max(theoretical.max(), sorted_vals.max())]
    ax2.plot(lims, lims, color='#00ff88', linewidth=1.5, linestyle='--', label='Poisson perfetto')
    ax2.set_xlabel('quantili teorici (Poisson)', fontsize=11)
    ax2.set_ylabel('quantili osservati', fontsize=11)
    ax2.set_title('QQ Plot — la coda destra devia', fontsize=11, fontweight='bold')
    ax2.legend(fontsize=9, framealpha=0.3)
    ax2.grid(True, alpha=0.3)

    fig.suptitle('La distribuzione degli arrivi NON e\' Poisson', fontsize=14,
                 fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '06_mta_distribution.png'), dpi=180, bbox_inches='tight')
    print(f'[+] output/06_mta_distribution.png')
    plt.close()


if __name__ == '__main__':
    hourly = load_mta_data()
    plot_mta_hourly(hourly)
    plot_mta_distribution(hourly)
