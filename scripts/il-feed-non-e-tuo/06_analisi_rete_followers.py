#!/usr/bin/env python3
"""
06_analisi_rete_followers.py — Analisi rete di menzioni e distribuzione followers.

Legge i CSV prodotti da 00_extract.py e analizza:
  1. Distribuzione followers degli autori (log scale)
  2. Fasce followers: micro/piccoli/medi/grandi/mega
  3. Rete menzioni: chi menziona chi (grafo diretto)
  4. Centralita' della rete: degree, top nodi
  5. Gini coefficient sulla distribuzione followers

Uso:
    python 06_analisi_rete_followers.py

Output:
    output/21_followers_distribution.png
    output/22_followers_tiers.png
    output/23_mention_network.png
    output/24_network_stats.png
    output/25_gini_followers.png
    output/stats_rete.json
"""

import json
import os
import re
import pandas as pd
import numpy as np
from collections import Counter, defaultdict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

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

ACCENT_1 = '#ff6b6b'
ACCENT_2 = '#4ecdc4'
ACCENT_3 = '#ffd93d'
OUTPUT_DIR = 'output'
DATA_DIR = 'data'

# Fasce followers
TIERS = [
    ('nano (<1K)', 0, 1_000),
    ('micro (1K-10K)', 1_000, 10_000),
    ('piccoli (10K-100K)', 10_000, 100_000),
    ('medi (100K-1M)', 100_000, 1_000_000),
    ('grandi (1M-10M)', 1_000_000, 10_000_000),
    ('mega (>10M)', 10_000_000, float('inf')),
]


def load_feeds():
    pt = pd.read_csv(os.path.join(DATA_DIR, 'per_te.csv'))
    sg = pd.read_csv(os.path.join(DATA_DIR, 'seguiti.csv'))
    return pt, sg


def gini_coefficient(x):
    """Calcola il coefficiente di Gini."""
    x = np.array(x, dtype=float)
    x = x[x > 0]
    if len(x) == 0:
        return 0
    x = np.sort(x)
    n = len(x)
    index = np.arange(1, n + 1)
    return float((2 * np.sum(index * x) - (n + 1) * np.sum(x)) / (n * np.sum(x)))


def plot_followers_distribution(pt, sg, stats):
    """1. Distribuzione followers (log scale)."""
    fig, ax = plt.subplots(figsize=(10, 5))

    for df, label, color in [(pt, 'Per Te', ACCENT_1), (sg, 'Seguiti', ACCENT_2)]:
        followers = df['followers_count'].clip(lower=1)
        log_f = np.log10(followers)
        bins = np.linspace(0, log_f.max() + 0.5, 40)
        ax.hist(log_f, bins=bins, alpha=0.5, color=color, label=label, density=True)

        stats[f'{label.lower().replace(" ", "_")}_followers_median'] = int(df['followers_count'].median())
        stats[f'{label.lower().replace(" ", "_")}_followers_mean'] = int(df['followers_count'].mean())
        stats[f'{label.lower().replace(" ", "_")}_followers_p90'] = int(df['followers_count'].quantile(0.9))

    # Etichette asse X leggibili
    tick_vals = [1, 2, 3, 4, 5, 6, 7, 8]
    tick_labels = ['10', '100', '1K', '10K', '100K', '1M', '10M', '100M']
    ax.set_xticks(tick_vals)
    ax.set_xticklabels(tick_labels)
    ax.set_xlabel('Followers')
    ax.set_ylabel('Densita\'')
    ax.set_title('Distribuzione Followers degli autori', fontsize=13, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '21_followers_distribution.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 21_followers_distribution.png')


def plot_followers_tiers(pt, sg, stats):
    """2. % tweet per fascia followers."""
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(TIERS))
    width = 0.35

    for i, (df, label, color) in enumerate([
        (pt, 'Per Te', ACCENT_1),
        (sg, 'Seguiti', ACCENT_2),
    ]):
        vals = []
        for tier_name, lo, hi in TIERS:
            mask = (df['followers_count'] >= lo) & (df['followers_count'] < hi)
            pct = mask.sum() / len(df) * 100
            vals.append(pct)
            stats[f'{label.lower().replace(" ", "_")}_{tier_name.split("(")[0].strip()}_pct'] = round(pct, 2)

        bars = ax.bar(x + i * width, vals, width, label=label, color=color, edgecolor='none')
        for bar, val in zip(bars, vals):
            if val > 1:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                        f'{val:.0f}%', ha='center', fontsize=7, color='#e0e0e0')

    tier_labels = [t[0] for t in TIERS]
    ax.set_xticks(x + width/2)
    ax.set_xticklabels(tier_labels, fontsize=8)
    ax.set_ylabel('% tweet')
    ax.set_title('Tweet per fascia Followers', fontsize=13, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '22_followers_tiers.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 22_followers_tiers.png')


def build_mention_graph(df):
    """Costruisci grafo menzioni: autore -> menzionato."""
    edges = defaultdict(int)
    for _, row in df.iterrows():
        author = row['screen_name']
        text = str(row.get('full_text', ''))
        mentions = re.findall(r'@(\w+)', text)
        for m in mentions:
            if m.lower() != author.lower():
                edges[(author.lower(), m.lower())] += 1
    return edges


def plot_mention_network(pt, sg, stats):
    """3. Rete menzioni — top nodi per degree."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('Rete Menzioni (top 30 nodi per degree)', fontsize=13, fontweight='bold')

    for ax, df, label, color in [
        (axes[0], pt, 'Per Te', ACCENT_1),
        (axes[1], sg, 'Seguiti', ACCENT_2),
    ]:
        edges = build_mention_graph(df)

        if not edges:
            ax.set_title(f'{label}\n(nessuna menzione)')
            continue

        # Calcola degree (in + out)
        degree = Counter()
        for (src, dst), w in edges.items():
            degree[src] += w
            degree[dst] += w

        stats[f'{label.lower().replace(" ", "_")}_n_edges'] = len(edges)
        stats[f'{label.lower().replace(" ", "_")}_n_nodes'] = len(degree)
        stats[f'{label.lower().replace(" ", "_")}_top_mentioned'] = degree.most_common(5)

        # Top 30 nodi
        top_nodes = [n for n, _ in degree.most_common(30)]
        top_degrees = [degree[n] for n in top_nodes]

        # Layout circolare semplice
        n = len(top_nodes)
        angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
        pos = {node: (np.cos(a), np.sin(a)) for node, a in zip(top_nodes, angles)}

        # Disegna archi
        top_set = set(top_nodes)
        for (src, dst), w in edges.items():
            if src in top_set and dst in top_set:
                x0, y0 = pos[src]
                x1, y1 = pos[dst]
                alpha = min(0.6, w / 5)
                ax.plot([x0, x1], [y0, y1], color='#444466', alpha=alpha, linewidth=0.5)

        # Disegna nodi
        sizes = np.array(top_degrees)
        sizes_norm = (sizes / sizes.max()) * 300 + 20

        for node, (x, y), s in zip(top_nodes, [pos[n] for n in top_nodes], sizes_norm):
            ax.scatter(x, y, s=s, color=color, alpha=0.7, edgecolors='white', linewidth=0.3)
            ax.annotate(node, (x, y), fontsize=5, ha='center', va='bottom',
                       color='#cccccc', xytext=(0, 4), textcoords='offset points')

        ax.set_title(label, fontsize=11)
        ax.set_xlim(-1.4, 1.4)
        ax.set_ylim(-1.4, 1.4)
        ax.set_aspect('equal')
        ax.axis('off')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '23_mention_network.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 23_mention_network.png')


def plot_network_stats(pt, sg, stats):
    """4. Statistiche rete: distribuzione in-degree menzioni."""
    fig, ax = plt.subplots(figsize=(10, 5))

    for df, label, color in [(pt, 'Per Te', ACCENT_1), (sg, 'Seguiti', ACCENT_2)]:
        edges = build_mention_graph(df)
        in_degree = Counter()
        for (src, dst), w in edges.items():
            in_degree[dst] += w

        if not in_degree:
            continue

        degrees = sorted(in_degree.values(), reverse=True)
        rank = np.arange(1, len(degrees) + 1)
        ax.plot(rank, degrees, color=color, label=label, linewidth=2, alpha=0.8)

    ax.set_xlabel('Rank')
    ax.set_ylabel('Menzioni ricevute')
    ax.set_title('Distribuzione In-Degree Menzioni (Zipf?)', fontsize=13, fontweight='bold')
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.legend()
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '24_network_stats.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 24_network_stats.png')


def plot_gini(pt, sg, stats):
    """5. Gini coefficient followers + curva di Lorenz."""
    fig, ax = plt.subplots(figsize=(8, 6))

    for df, label, color in [(pt, 'Per Te', ACCENT_1), (sg, 'Seguiti', ACCENT_2)]:
        followers = np.sort(df['followers_count'].values.astype(float))
        followers = followers[followers > 0]
        n = len(followers)
        cum = np.cumsum(followers) / followers.sum()
        x = np.arange(1, n + 1) / n

        ax.plot(x, cum, color=color, label=f'{label} (Gini={gini_coefficient(followers):.3f})',
                linewidth=2)

        stats[f'{label.lower().replace(" ", "_")}_gini_followers'] = round(gini_coefficient(followers), 4)

    ax.plot([0, 1], [0, 1], color='#555555', linestyle='--', alpha=0.5, label='Uguaglianza perfetta')
    ax.set_xlabel('% autori (cumulativa)')
    ax.set_ylabel('% followers (cumulativa)')
    ax.set_title('Curva di Lorenz — Disuguaglianza Followers', fontsize=13, fontweight='bold')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.2)
    ax.set_aspect('equal')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '25_gini_followers.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 25_gini_followers.png')


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    pt, sg = load_feeds()

    stats = {}
    plot_followers_distribution(pt, sg, stats)
    plot_followers_tiers(pt, sg, stats)
    plot_mention_network(pt, sg, stats)
    plot_network_stats(pt, sg, stats)
    plot_gini(pt, sg, stats)

    # Serializza top_mentioned (liste di tuple)
    for key in list(stats.keys()):
        if 'top_mentioned' in key:
            stats[key] = [[n, c] for n, c in stats[key]]

    with open(os.path.join(OUTPUT_DIR, 'stats_rete.json'), 'w') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f'[✓] Stats salvate in {OUTPUT_DIR}/stats_rete.json')


if __name__ == '__main__':
    main()
