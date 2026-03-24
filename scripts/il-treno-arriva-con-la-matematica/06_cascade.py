#!/usr/bin/env python3
"""
06_cascade.py — Effetto cascata nei sistemi accoppiati
Un singolo nodo lento avvelena l'intero sistema.
Simula una catena di 5 stazioni/servizi dove il rallentamento
si propaga a valle.

Output: output/10_cascade.png
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

OUTPUT_DIR = 'output'
os.makedirs(OUTPUT_DIR, exist_ok=True)
np.random.seed(42)

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


def simulate_cascade():
    """
    5 stazioni in serie. Stazione 3 ha un rallentamento.
    Mostra come il ritardo si propaga a monte e a valle.
    """
    N_TRAINS = 500
    N_STATIONS = 5
    STATION_NAMES = ['Brixton', 'Stockwell', 'Vauxhall\n(rallentamento)', 'Pimlico', 'Victoria']

    # Headway nominale: 2.5 min
    HEADWAY = 2.5
    # Tempo di percorrenza tra stazioni: 2 min
    TRAVEL_TIME = 2.0
    # Tempo di sosta in stazione: 0.5 min
    DWELL_TIME = 0.5

    # Scenario 1: tutto normale
    normal_delays = np.zeros((N_TRAINS, N_STATIONS))
    departures_normal = np.zeros((N_TRAINS, N_STATIONS))

    for i in range(N_TRAINS):
        for j in range(N_STATIONS):
            if i == 0 and j == 0:
                departures_normal[i][j] = 0
            elif j == 0:
                departures_normal[i][j] = i * HEADWAY + np.random.normal(0, 0.1)
            else:
                arrive = departures_normal[i][j-1] + TRAVEL_TIME + np.random.normal(0, 0.05)
                # Non puo' partire prima del treno precedente
                if i > 0:
                    min_depart = departures_normal[i-1][j] + HEADWAY * 0.8
                    arrive = max(arrive, min_depart)
                departures_normal[i][j] = arrive + DWELL_TIME

    # Scenario 2: stazione 2 (Vauxhall) ha problemi
    # Dwell time raddoppiato + varianza alta
    departures_delayed = np.zeros((N_TRAINS, N_STATIONS))

    for i in range(N_TRAINS):
        for j in range(N_STATIONS):
            if i == 0 and j == 0:
                departures_delayed[i][j] = 0
            elif j == 0:
                departures_delayed[i][j] = i * HEADWAY + np.random.normal(0, 0.1)
            else:
                arrive = departures_delayed[i][j-1] + TRAVEL_TIME + np.random.normal(0, 0.05)
                if i > 0:
                    min_depart = departures_delayed[i-1][j] + HEADWAY * 0.8
                    arrive = max(arrive, min_depart)

                if j == 2:  # Vauxhall: problemi
                    dwell = DWELL_TIME * 2.5 + abs(np.random.normal(0, 0.8))
                else:
                    dwell = DWELL_TIME

                departures_delayed[i][j] = arrive + dwell

    # Calcola ritardi rispetto a schedule
    schedule = np.zeros((N_TRAINS, N_STATIONS))
    for i in range(N_TRAINS):
        for j in range(N_STATIONS):
            schedule[i][j] = i * HEADWAY + j * (TRAVEL_TIME + DWELL_TIME)

    delays_normal = departures_normal - schedule
    delays_delayed = departures_delayed - schedule

    # Plot: ritardo medio per stazione
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Heatmap ritardi (primi 50 treni)
    show_trains = 50
    im = ax1.imshow(delays_delayed[:show_trains], aspect='auto',
                     cmap='RdYlGn_r', vmin=-1, vmax=5,
                     interpolation='nearest')
    ax1.set_xticks(range(N_STATIONS))
    ax1.set_xticklabels(STATION_NAMES, fontsize=8.5, rotation=15)
    ax1.set_ylabel('treno #', fontsize=12)
    ax1.set_title('Ritardo per treno e stazione (minuti)', fontsize=12, fontweight='bold')
    plt.colorbar(im, ax=ax1, label='ritardo (min)')

    # Ritardo medio per stazione
    mean_normal = np.mean(delays_normal[50:], axis=0)  # skip warm-up
    mean_delayed = np.mean(delays_delayed[50:], axis=0)
    std_delayed = np.std(delays_delayed[50:], axis=0)

    x = np.arange(N_STATIONS)
    ax2.bar(x - 0.15, mean_normal, 0.3, color='#00ff88', alpha=0.8, label='Normale')
    ax2.bar(x + 0.15, mean_delayed, 0.3, color='#ff6b6b', alpha=0.8, label='Con rallentamento')
    ax2.errorbar(x + 0.15, mean_delayed, yerr=std_delayed, fmt='none',
                 ecolor='#ff8800', capsize=3, alpha=0.7)

    ax2.set_xticks(x)
    ax2.set_xticklabels(STATION_NAMES, fontsize=8.5, rotation=15)
    ax2.set_ylabel('ritardo medio (min)', fontsize=12)
    ax2.set_title('Propagazione del ritardo lungo la linea', fontsize=12, fontweight='bold')
    ax2.legend(fontsize=10, framealpha=0.3)
    ax2.grid(True, alpha=0.3, axis='y')

    # Annotazione
    ax2.annotate('il ritardo\npropagato', xy=(3, mean_delayed[3]),
                 xytext=(3.5, mean_delayed[3] + 1),
                 fontsize=10, color='#ff8800',
                 arrowprops=dict(arrowstyle='->', color='#ff8800', lw=1.5))

    fig.suptitle('Effetto cascata — un nodo lento avvelena il sistema',
                 fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '10_cascade.png'), dpi=180, bbox_inches='tight')
    print(f'[+] output/10_cascade.png')
    plt.close()


if __name__ == '__main__':
    simulate_cascade()
