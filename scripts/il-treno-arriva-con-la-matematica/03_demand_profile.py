#!/usr/bin/env python3
"""
03_demand_profile.py — Profilo di domanda 24h
Mostra il profilo degli arrivi passeggeri a 15 min per le stazioni principali.
Due picchi: AM peak e PM peak. Il modello stazionario e' una bugia.

Output: output/03_demand_24h.png, output/04_link_load.png
"""

import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
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

# Stazioni target (le piu' trafficate + alcune interessanti)
TARGET_STATIONS = [
    'Waterloo LU', 'Victoria LU', 'Oxford Circus', 'King\'s Cross LU',
    'Bank and Monument', 'Liverpool Street LU', 'Brixton LU',
    'Clapham Junction', 'Canary Wharf LU'
]


def plot_demand_24h():
    """Plot 3: Profilo domanda 24h per le stazioni principali."""
    profiles = {}

    with open('data/station_entries_15min.csv') as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        # Colonne 15-min (dopo station, fare_zone, total)
        slot_cols = [c for c in fields if '-' in c and c[0].isdigit()]

        for row in reader:
            station = row['station']
            if station in TARGET_STATIONS:
                values = [float(row[c]) if row[c] else 0 for c in slot_cols]
                profiles[station] = values

    n_slots = len(slot_cols)
    # Genera etichette orarie
    hours = []
    for i, col in enumerate(slot_cols):
        h = col.split('-')[0]
        if len(h) == 4:
            hours.append(f'{h[:2]}:{h[2:]}')
        else:
            hours.append(col)

    fig, ax = plt.subplots(figsize=(14, 7))

    colors = ['#00ff88', '#7c4dff', '#ff6b6b', '#ff8800', '#4ecdc4',
              '#ffcc00', '#ff69b4', '#87ceeb', '#dda0dd']

    for i, station in enumerate(TARGET_STATIONS):
        if station in profiles:
            vals = profiles[station]
            name = station.replace(' LU', '').replace(' NR', '')
            ax.plot(range(n_slots), vals, color=colors[i % len(colors)],
                    linewidth=1.8, label=name, alpha=0.85)

    # Etichette x ogni ora
    tick_positions = list(range(0, n_slots, 4))
    tick_labels = [hours[i] if i < len(hours) else '' for i in tick_positions]
    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels, rotation=45, fontsize=8)

    # Fasce orarie
    # AM peak: 07:00-09:30 -> slot 8-18
    ax.axvspan(8, 18, alpha=0.08, color='#ff6b6b')
    ax.text(13, ax.get_ylim()[1] * 0.05 if ax.get_ylim()[1] > 0 else 100,
            'AM Peak', fontsize=8, color='#ff6b6b', ha='center', alpha=0.7)
    # PM peak: 16:30-19:00 -> slot 46-56
    ax.axvspan(46, 56, alpha=0.08, color='#ff8800')
    ax.text(51, ax.get_ylim()[1] * 0.05 if ax.get_ylim()[1] > 0 else 100,
            'PM Peak', fontsize=8, color='#ff8800', ha='center', alpha=0.7)

    ax.set_xlabel('ora del giorno', fontsize=13)
    ax.set_ylabel('passeggeri / 15 min', fontsize=13)
    ax.set_title('Profilo di domanda 24h — Londra, giorno feriale tipo (NUMBAT 2024)',
                 fontsize=13, fontweight='bold')
    ax.legend(loc='upper right', fontsize=8.5, framealpha=0.3, ncol=2)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, n_slots - 1)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '03_demand_24h.png'), dpi=180)
    print(f'[+] output/03_demand_24h.png')
    plt.close()


def plot_link_load():
    """Plot 4: Carico treni sul link piu' affollato della Victoria Line."""
    loads = {}
    with open('data/train_loading.csv') as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        time_cols = [c for c in fields if '-' in c and c[0].isdigit()]

        for row in reader:
            line = row['Line']
            from_st = row['From_Station']
            to_st = row['To_Station']
            direction = row['Direction']

            key = f'{line} | {from_st} -> {to_st} ({direction})'

            values = []
            for c in time_cols:
                v = row[c].strip() if row[c] else '0'
                try:
                    values.append(float(v))
                except ValueError:
                    values.append(0)

            total = sum(values)
            loads[key] = {'values': values, 'total': total, 'line': line,
                          'from': from_st, 'to': to_st}

    # Top 5 link per carico totale
    sorted_links = sorted(loads.items(), key=lambda x: x[1]['total'], reverse=True)

    fig, ax = plt.subplots(figsize=(14, 7))

    colors = ['#ff6b6b', '#00ff88', '#7c4dff', '#ff8800', '#4ecdc4']
    n_slots = len(time_cols)

    for i, (key, data) in enumerate(sorted_links[:5]):
        label = f"{data['line']}: {data['from']} -> {data['to']}"
        if len(label) > 50:
            label = label[:47] + '...'
        ax.plot(range(n_slots), data['values'], color=colors[i],
                linewidth=2, label=label, alpha=0.85)

    tick_positions = list(range(0, n_slots, 4))
    tick_labels = []
    for i in tick_positions:
        if i < len(time_cols):
            h = time_cols[i].split('-')[0]
            tick_labels.append(f'{h[:2]}:{h[2:]}')
        else:
            tick_labels.append('')
    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels, rotation=45, fontsize=8)

    ax.set_xlabel('ora del giorno', fontsize=13)
    ax.set_ylabel('passeggeri per treno (carico medio)', fontsize=13)
    ax.set_title('Carico treni — top 5 tratte piu\' affollate (TfL 2024)',
                 fontsize=13, fontweight='bold')
    ax.legend(loc='upper right', fontsize=8, framealpha=0.3)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '04_link_load.png'), dpi=180)
    print(f'[+] output/04_link_load.png')
    plt.close()


if __name__ == '__main__':
    plot_demand_24h()
    plot_link_load()
