#!/usr/bin/env python3
"""
02_kingman_curve.py — La curva che esplode
Kingman's formula: E[W] ≈ (rho / (1 - rho)) * ((ca^2 + cs^2) / 2) * E[S]

Mostra come il tempo di attesa esplode PRIMA di raggiungere la capacita'.
Confronta M/M/1, M/D/1, M/G/1 con heavy tail.
Sovrappone le posizioni reali delle stazioni di Londra.

Output: output/01_kingman.png, output/02_station_rho.png
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import csv
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


def kingman_wait(rho, ca2, cs2, Es):
    """Kingman's formula per il tempo medio in coda."""
    return (rho / (1 - rho)) * ((ca2 + cs2) / 2) * Es


def plot_kingman():
    """Plot 1: Confronto M/M/1, M/D/1, M/G/1 heavy-tail."""
    rho = np.linspace(0.01, 0.98, 500)
    Es = 1.0  # tempo medio di servizio normalizzato

    # M/M/1: ca^2 = 1, cs^2 = 1
    w_mm1 = kingman_wait(rho, 1.0, 1.0, Es)

    # M/D/1: ca^2 = 1, cs^2 = 0 (deterministico)
    w_md1 = kingman_wait(rho, 1.0, 0.0, Es)

    # M/G/1 heavy tail: ca^2 = 1, cs^2 = 4 (Pareto-like)
    w_mg1_heavy = kingman_wait(rho, 1.0, 4.0, Es)

    # G/G/1 bursty arrivals + heavy service: ca^2 = 3, cs^2 = 4
    w_gg1 = kingman_wait(rho, 3.0, 4.0, Es)

    fig, ax = plt.subplots(figsize=(12, 7))

    ax.plot(rho, w_md1, color='#00ff88', linewidth=2.5, label='M/D/1  (treni puntuali)')
    ax.plot(rho, w_mm1, color='#7c4dff', linewidth=2.5, label='M/M/1  (arrivi casuali)')
    ax.plot(rho, w_mg1_heavy, color='#ff6b6b', linewidth=2.5, label='M/G/1  (servizio heavy-tail)')
    ax.plot(rho, w_gg1, color='#ff8800', linewidth=2.5, label='G/G/1  (tutto irregolare)',
            linestyle='--')

    # Zona di pericolo
    ax.axvspan(0.8, 1.0, alpha=0.15, color='#ff6b6b', label='zona di pericolo (rho > 0.8)')
    ax.axvline(x=0.8, color='#ff6b6b', linewidth=1, linestyle=':', alpha=0.5)

    # Annotazione
    ax.annotate('qui esplode', xy=(0.85, kingman_wait(0.85, 1.0, 1.0, Es)),
                xytext=(0.65, 8), fontsize=11, color='#ff6b6b',
                arrowprops=dict(arrowstyle='->', color='#ff6b6b', lw=1.5))

    ax.set_xlabel('rho (utilizzazione)', fontsize=13)
    ax.set_ylabel('tempo medio in coda (x servizio)', fontsize=13)
    ax.set_title("Kingman's formula — il tempo esplode prima della saturazione", fontsize=14,
                 fontweight='bold')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 15)
    ax.legend(loc='upper left', fontsize=10, framealpha=0.3)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '01_kingman.png'), dpi=180)
    print(f'[+] output/01_kingman.png')
    plt.close()


def plot_station_rho():
    """Plot 2: Posizione delle stazioni di Londra sulla curva."""
    stations = []
    with open('data/station_rho.csv') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rho = float(row['rho'])
            if rho > 0.01:  # filtra stazioni vuote
                stations.append({
                    'name': row['station'],
                    'rho': rho,
                    'lambda': float(row['lambda_peak_15min']),
                    'total': float(row['daily_total']),
                    'lines': row['lines']
                })

    stations.sort(key=lambda x: x['rho'], reverse=True)
    top30 = stations[:30]

    fig, ax = plt.subplots(figsize=(14, 7))

    # Sfondo: curva Kingman M/M/1
    rho_curve = np.linspace(0.01, 0.98, 500)
    w_mm1 = kingman_wait(rho_curve, 1.0, 1.0, 1.0)
    ax.plot(rho_curve, w_mm1, color='#7c4dff', linewidth=1.5, alpha=0.4, label='curva M/M/1')
    ax.fill_between(rho_curve, 0, w_mm1, alpha=0.05, color='#7c4dff')

    # Stazioni come punti
    rhos = [s['rho'] for s in top30]
    waits = [kingman_wait(s['rho'], 1.0, 0.0, 1.0) if s['rho'] < 1 else 20 for s in top30]
    sizes = [max(20, s['total'] / 200) for s in top30]

    colors = []
    for s in top30:
        if s['rho'] > 0.8:
            colors.append('#ff6b6b')
        elif s['rho'] > 0.5:
            colors.append('#ff8800')
        elif s['rho'] > 0.3:
            colors.append('#ffcc00')
        else:
            colors.append('#00ff88')

    ax.scatter(rhos, waits, s=sizes, c=colors, alpha=0.8, edgecolors='white',
               linewidth=0.5, zorder=5)

    # Etichette per top 10
    for s in top30[:10]:
        w = kingman_wait(s['rho'], 1.0, 0.0, 1.0) if s['rho'] < 1 else 15
        name = s['name'].replace(' LU', '').replace(' NR', '')
        ax.annotate(name, xy=(s['rho'], w),
                    xytext=(5, 8), textcoords='offset points',
                    fontsize=7.5, color='#c9d1d9', alpha=0.9)

    ax.axvspan(0.8, 1.2, alpha=0.12, color='#ff6b6b')
    ax.set_xlabel('rho (utilizzazione AM Peak)', fontsize=13)
    ax.set_ylabel('tempo attesa stimato M/D/1 (x headway)', fontsize=13)
    ax.set_title('Stazioni di Londra sulla curva di Kingman — AM Peak', fontsize=14,
                 fontweight='bold')
    ax.set_xlim(0, 1.2)
    ax.set_ylim(0, 18)
    ax.grid(True, alpha=0.3)

    # Legenda colori
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#00ff88', markersize=8, label='rho < 0.3'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#ffcc00', markersize=8, label='rho 0.3 - 0.5'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#ff8800', markersize=8, label='rho 0.5 - 0.8'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#ff6b6b', markersize=8, label='rho > 0.8'),
    ]
    ax.legend(handles=legend_elements, loc='upper left', fontsize=9, framealpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '02_station_rho.png'), dpi=180)
    print(f'[+] output/02_station_rho.png')
    plt.close()


if __name__ == '__main__':
    plot_kingman()
    plot_station_rho()
