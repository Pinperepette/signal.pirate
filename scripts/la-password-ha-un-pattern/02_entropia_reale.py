#!/usr/bin/env python3
"""
02_entropia_reale.py
Calcolo dell'entropia reale vs teorica delle password.

Dimostra che l'entropia teorica (log2(charset^len)) e' una bugia:
l'entropia reale delle password umane e' ordini di grandezza inferiore.

Output:
    output/04_entropia_teorica_vs_reale.png
    output/05_spazio_ricerca_riduzione.png
    output/06_entropia_per_posizione.png
    output/stats_entropia.json
"""

import os
import sys
import json
import math
from collections import Counter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
    'figure.facecolor': '#0a0a0f',
    'axes.facecolor': '#12121a',
    'axes.edgecolor': '#333355',
    'axes.labelcolor': '#8888aa',
    'xtick.color': '#8888aa',
    'ytick.color': '#8888aa',
    'text.color': '#e0e0e0',
    'font.family': 'monospace',
    'font.size': 10,
    'grid.color': '#1a1a2e',
    'grid.alpha': 0.5,
})


def entropia_teorica(lunghezza, charset_size=94):
    """Entropia teorica: log2(charset^len) = len * log2(charset)."""
    return lunghezza * math.log2(charset_size)


def entropia_shannon_stringa(s):
    """Entropia di Shannon per una singola stringa."""
    if len(s) == 0:
        return 0.0
    freq = Counter(s)
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in freq.values())


def entropia_primo_ordine(pwd_counts):
    """Entropia del primo ordine: quanto e' prevedibile ogni carattere indipendentemente."""
    freq = Counter()
    for pwd, count in pwd_counts:
        for c in pwd:
            freq[c] += count
    total = sum(freq.values())
    return -sum((c / total) * math.log2(c / total) for c in freq.values())


def entropia_per_posizione(pwd_counts, max_pos=12):
    """Entropia di Shannon per ogni posizione nella password."""
    result = []
    for pos in range(max_pos):
        freq = Counter()
        for pwd, count in pwd_counts:
            if len(pwd) > pos:
                freq[pwd[pos]] += count
        total = sum(freq.values())
        if total < 100:
            break
        h = -sum((c / total) * math.log2(c / total) for c in freq.values())
        result.append({
            'posizione': pos + 1,
            'entropia': round(h, 3),
            'char_unici': len(freq),
            'top_char': freq.most_common(1)[0][0],
            'top_char_pct': round(freq.most_common(1)[0][1] / total * 100, 1),
        })
    return result


def stima_spazio_effettivo(pwd_counts, total):
    """Stima lo spazio di ricerca effettivo basato sulla distribuzione reale."""
    cumulative = 0
    for i, (pwd, count) in enumerate(pwd_counts):
        cumulative += count
        if cumulative >= total * 0.5:
            return i + 1, '50%'
    return len(pwd_counts), '100%'


def plot_entropia_confronto(pwd_counts, outdir):
    """Grafico 04: entropia teorica vs reale per lunghezza."""
    # Raggruppa per lunghezza: {len: {pwd: count}}
    by_length = {}
    for pwd, count in pwd_counts:
        l = len(pwd)
        if 4 <= l <= 14:
            by_length.setdefault(l, Counter())[pwd] += count

    lengths = sorted(by_length.keys())
    h_teorica = [entropia_teorica(l) for l in lengths]

    # Entropia reale: basata sulla distribuzione delle password a quella lunghezza
    h_reale = []
    for l in lengths:
        freq = by_length[l]
        total = sum(freq.values())
        if total < 10:
            h_reale.append(0)
            continue
        h = -sum((c / total) * math.log2(c / total) for c in freq.values())
        h_reale.append(h)

    # Entropia Shannon media delle singole password (campione)
    h_shannon = []
    for l in lengths:
        pwds_sample = list(by_length[l].keys())[:5000]
        entropie = [entropia_shannon_stringa(p) for p in pwds_sample]
        h_shannon.append(np.mean(entropie))

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.plot(lengths, h_teorica, 'o-', color='#7c4dff', linewidth=2, markersize=8,
            label='Entropia teorica (94^n)', zorder=3)
    ax.plot(lengths, h_reale, 's-', color='#ff6b6b', linewidth=2, markersize=8,
            label='Entropia reale (distribuzione)', zorder=3)
    ax.plot(lengths, h_shannon, '^-', color='#00ff88', linewidth=2, markersize=8,
            label='Shannon media (per password)', zorder=3)

    # Area tra teorica e reale
    ax.fill_between(lengths, h_reale, h_teorica, alpha=0.15, color='#ff6b6b')

    # Annota il gap massimo
    gaps = [t - r for t, r in zip(h_teorica, h_reale)]
    max_gap_idx = gaps.index(max(gaps))
    ax.annotate(
        f'Gap: {gaps[max_gap_idx]:.0f} bit\n({2**gaps[max_gap_idx]:.0e}x meno combinazioni)',
        xy=(lengths[max_gap_idx], h_reale[max_gap_idx]),
        xytext=(lengths[max_gap_idx] + 1.5, h_reale[max_gap_idx] + 15),
        fontsize=8, color='#ff6b6b', fontfamily='monospace',
        arrowprops=dict(arrowstyle='->', color='#ff6b6b', lw=1.5),
        bbox=dict(boxstyle='round,pad=0.3', facecolor='#1a1a2e', edgecolor='#ff6b6b', alpha=0.9),
    )

    ax.set_xlabel('Lunghezza password')
    ax.set_ylabel('Entropia (bit)')
    ax.set_title('Entropia teorica vs reale — il gap che uccide la sicurezza', fontsize=13, fontweight='bold')
    ax.legend(loc='upper left', framealpha=0.8, edgecolor='#333355')
    ax.set_xticks(lengths)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(outdir, '04_entropia_teorica_vs_reale.png'), dpi=150)
    plt.close()
    print(f'  [+] 04_entropia_teorica_vs_reale.png — gap max: {max(gaps):.0f} bit')
    return gaps


def plot_riduzione_spazio(outdir):
    """Grafico 05: riduzione dello spazio di ricerca."""
    categories = [
        'Bruteforce\npuro\n(94^8)',
        'Solo\nlowercase\n(26^8)',
        'Pattern\ncomuni\n(dizionario)',
        'Markov\nchain\n(ordinate)',
        'Top 10k\npassword\n(leak)',
    ]
    # Esponenti approssimati (log10 dello spazio)
    spaces_log10 = [15.76, 11.09, 8.0, 6.0, 4.0]

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ['#7c4dff', '#4ecdc4', '#ff8800', '#00ff88', '#ff6b6b']

    bars = ax.bar(range(len(categories)), spaces_log10, color=colors, alpha=0.85,
                  edgecolor=[c.replace('ff', 'cc') for c in colors], linewidth=1)

    for bar, val in zip(bars, spaces_log10):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                f'10^{val:.0f}', ha='center', va='bottom', fontsize=11,
                color='#e0e0e0', fontweight='bold', fontfamily='monospace')

    # Freccia di riduzione
    ax.annotate('', xy=(4, spaces_log10[4] + 0.8), xytext=(0, spaces_log10[0] + 0.8),
                arrowprops=dict(arrowstyle='->', color='#ff6b6b', lw=2, connectionstyle='arc3,rad=-0.2'))
    ax.text(2, 17.5, f'riduzione: 10^{spaces_log10[0] - spaces_log10[4]:.0f}x',
            ha='center', fontsize=11, color='#ff6b6b', fontweight='bold', fontfamily='monospace')

    ax.set_xticks(range(len(categories)))
    ax.set_xticklabels(categories, fontsize=8)
    ax.set_ylabel('Spazio di ricerca (log10)')
    ax.set_title('Da 10^16 a 10^4: come si riduce lo spazio di ricerca', fontsize=13, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(outdir, '05_spazio_ricerca_riduzione.png'), dpi=150)
    plt.close()
    print(f'  [+] 05_spazio_ricerca_riduzione.png — riduzione: 10^{spaces_log10[0] - spaces_log10[4]:.0f}x')


def plot_entropia_posizione(pwd_counts, outdir):
    """Grafico 06: entropia per posizione nella password."""
    pos_data = entropia_per_posizione(pwd_counts, max_pos=12)
    if not pos_data:
        return

    positions = [d['posizione'] for d in pos_data]
    entropie = [d['entropia'] for d in pos_data]
    top_chars = [d['top_char'] for d in pos_data]
    top_pcts = [d['top_char_pct'] for d in pos_data]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [2, 1]})

    # Subplot 1: entropia per posizione
    bars = ax1.bar(positions, entropie, color='#00ff88', alpha=0.85, edgecolor='#00cc6a')
    ax1.axhline(y=math.log2(94), color='#7c4dff', linestyle='--', alpha=0.6,
                label=f'Max teorico (log2(94) = {math.log2(94):.1f} bit)')
    ax1.axhline(y=math.log2(26), color='#ff8800', linestyle='--', alpha=0.6,
                label=f'Solo lowercase (log2(26) = {math.log2(26):.1f} bit)')

    for bar, e in zip(bars, entropie):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                f'{e:.1f}', ha='center', va='bottom', fontsize=8, color='#e0e0e0', fontfamily='monospace')

    ax1.set_ylabel('Entropia (bit)')
    ax1.set_title('Entropia per posizione — le prime e ultime posizioni sono prevedibili',
                  fontsize=12, fontweight='bold')
    ax1.legend(loc='upper right', framealpha=0.8, edgecolor='#333355', fontsize=8)
    ax1.grid(axis='y', alpha=0.3)

    # Subplot 2: carattere piu' frequente per posizione
    bar_colors = ['#ff6b6b' if p > 20 else '#ff8800' if p > 10 else '#00ff88' for p in top_pcts]
    ax2.bar(positions, top_pcts, color=bar_colors, alpha=0.85)
    for pos, char, pct in zip(positions, top_chars, top_pcts):
        display = repr(char) if char in (' ', '\t') else char
        ax2.text(pos, pct + 0.5, f'"{display}"\n{pct:.0f}%', ha='center', va='bottom',
                fontsize=7, color='#e0e0e0', fontfamily='monospace')

    ax2.set_xlabel('Posizione nella password')
    ax2.set_ylabel('Frequenza char top (%)')
    ax2.set_title('Carattere dominante per posizione', fontsize=11, fontweight='bold')
    ax2.set_xticks(positions)
    ax2.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(outdir, '06_entropia_per_posizione.png'), dpi=150)
    plt.close()
    print(f'  [+] 06_entropia_per_posizione.png — {len(pos_data)} posizioni analizzate')
    return pos_data


def main():
    # Importa i dati dallo script 01
    script_dir = os.path.dirname(os.path.abspath(__file__))
    outdir = os.path.join(script_dir, 'output')
    os.makedirs(outdir, exist_ok=True)

    sys.path.insert(0, script_dir)
    from importlib import import_module
    mod = import_module('01_analisi_distribuzione')

    # Carica password
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        print(f'[*] Carico wordlist: {sys.argv[1]}')
        pwd_counts = mod.carica_wordlist_conteggi(sys.argv[1])
        total = sum(c for _, c in pwd_counts)
    else:
        print('[*] Genero dataset sintetico...')
        passwords = mod.genera_dataset_sintetico(500000)
        cnt = Counter(passwords)
        pwd_counts = cnt.most_common()
        total = len(passwords)

    pwd_counts.sort(key=lambda x: -x[1])
    print(f'    {total:,} password ({len(pwd_counts):,} uniche)')
    print()
    print('[*] Analisi entropia...')

    # Entropia primo ordine
    h1 = entropia_primo_ordine(pwd_counts)
    print(f'    Entropia primo ordine: {h1:.3f} bit/char')
    print(f'    vs teorica (94 char):  {math.log2(94):.3f} bit/char')
    print(f'    Rapporto:              {h1 / math.log2(94) * 100:.1f}%')

    print()
    print('[*] Generazione grafici...')
    gaps = plot_entropia_confronto(pwd_counts, outdir)
    plot_riduzione_spazio(outdir)
    pos_data = plot_entropia_posizione(pwd_counts, outdir)

    # Spazio effettivo
    n50, label = stima_spazio_effettivo(pwd_counts, total)

    stats = {
        'entropia_primo_ordine': round(h1, 3),
        'entropia_teorica_per_char': round(math.log2(94), 3),
        'rapporto_entropia_pct': round(h1 / math.log2(94) * 100, 1),
        'spazio_teorico_8char': '6.10e+15',
        'spazio_effettivo_nota': f'{n50:,} password coprono il {label} del dataset',
        'entropia_per_posizione': pos_data,
    }

    with open(os.path.join(outdir, 'stats_entropia.json'), 'w') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    print()
    print(f'[*] Risultati:')
    print(f'    Entropia reale:     {h1:.2f} bit/char (vs {math.log2(94):.2f} teorica)')
    print(f'    Spazio effettivo:   {n50:,} password coprono il {label}')
    print()
    print('[+] Done.')


if __name__ == '__main__':
    main()
