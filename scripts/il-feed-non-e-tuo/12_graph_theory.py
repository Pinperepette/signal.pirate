#!/usr/bin/env python3
"""
12_graph_theory.py — Graph Theory seria sul grafo delle menzioni.

Calcola:
  1. Betweenness centrality — chi controlla il flusso informativo
  2. Assortativity — rete community (assortativa) vs broadcast (disassortativa)
  3. Modularity (Louvain) — quante community, quanto forti
  4. Confronto componenti connesse

Output:
    output/55_betweenness_centrality.png
    output/56_assortativity.png
    output/57_modularity_communities.png
    output/58_graph_summary.png
    output/stats_graph.json
"""

import json
import os
import re
import numpy as np
import pandas as pd
from collections import Counter, defaultdict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

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
OUTPUT_DIR = 'output'
DATA_DIR = 'data'

try:
    import networkx as nx
    HAS_NX = True
except ImportError:
    HAS_NX = False


def load_feeds():
    pt = pd.read_csv(os.path.join(DATA_DIR, 'per_te.csv'))
    sg = pd.read_csv(os.path.join(DATA_DIR, 'seguiti.csv'))
    return pt, sg


def build_graph(df):
    """Costruisci grafo diretto delle menzioni."""
    G = nx.DiGraph()
    for _, row in df.iterrows():
        author = str(row['screen_name']).lower()
        text = str(row.get('full_text', ''))
        mentions = re.findall(r'@(\w+)', text)
        for m in mentions:
            m = m.lower()
            if m != author:
                if G.has_edge(author, m):
                    G[author][m]['weight'] += 1
                else:
                    G.add_edge(author, m, weight=1)
    return G


def louvain_communities(G):
    """Louvain community detection su grafo non diretto."""
    G_undirected = G.to_undirected()
    # Rimuovi self-loops
    G_undirected.remove_edges_from(nx.selfloop_edges(G_undirected))
    if len(G_undirected.nodes) == 0 or len(G_undirected.edges) == 0:
        return {}, 0
    communities = nx.community.louvain_communities(G_undirected, seed=42)
    # Calcola modularity
    modularity = nx.community.modularity(G_undirected, communities)
    # Converti in dict nodo -> community_id
    node_to_comm = {}
    for i, comm in enumerate(communities):
        for node in comm:
            node_to_comm[node] = i
    return node_to_comm, modularity, len(communities)


def plot_betweenness(pt, sg, stats):
    """1. Betweenness centrality — top nodi per feed."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('Betweenness Centrality: Chi Controlla il Flusso',
                 fontsize=13, fontweight='bold')

    for ax, df, feed, label, color in [
        (axes[0], pt, 'per_te', 'Per Te', ACCENT_1),
        (axes[1], sg, 'seguiti', 'Seguiti', ACCENT_2),
    ]:
        G = build_graph(df)
        if len(G.nodes) < 3:
            ax.set_title(f'{label}\n(grafo troppo piccolo)')
            continue

        bc = nx.betweenness_centrality(G, weight='weight')
        top = sorted(bc.items(), key=lambda x: -x[1])[:15]

        if not top:
            continue

        names, values = zip(*top)
        ax.barh(list(names)[::-1], list(values)[::-1], color=color, edgecolor='none')
        ax.set_xlabel('Betweenness Centrality')
        ax.set_title(label, fontsize=11)

        stats[f'{feed}_top_betweenness'] = top[0][0]
        stats[f'{feed}_top_betweenness_value'] = round(top[0][1], 4)
        stats[f'{feed}_mean_betweenness'] = round(float(np.mean(list(bc.values()))), 6)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '55_betweenness_centrality.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 55_betweenness_centrality.png')


def plot_assortativity(pt, sg, stats):
    """2. Assortativity per degree — community vs broadcast."""
    fig, ax = plt.subplots(figsize=(8, 5))

    values = []
    labels = []
    colors = []

    for df, feed, label, color in [
        (pt, 'per_te', 'Per Te', ACCENT_1),
        (sg, 'seguiti', 'Seguiti', ACCENT_2),
    ]:
        G = build_graph(df)
        if len(G.nodes) < 3:
            continue

        r = nx.degree_assortativity_coefficient(G)
        values.append(r)
        labels.append(label)
        colors.append(color)
        stats[f'{feed}_assortativity'] = round(float(r), 4)

    bars = ax.bar(labels, values, color=colors, edgecolor='none', width=0.4)

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005 * np.sign(bar.get_height()),
                f'{val:.4f}', ha='center', fontsize=11, color='#e0e0e0')

    ax.axhline(y=0, color='#ffffff', linestyle='--', alpha=0.3)
    ax.set_ylabel('Degree Assortativity r')
    ax.set_title('Assortativity: r > 0 = community, r < 0 = broadcast',
                 fontsize=12, fontweight='bold')

    # Annotazioni
    ax.text(0.02, 0.95, 'r > 0: simili parlano con simili (community)',
            transform=ax.transAxes, fontsize=8, color='#888888')
    ax.text(0.02, 0.90, 'r < 0: grandi parlano con piccoli (broadcast)',
            transform=ax.transAxes, fontsize=8, color='#888888')

    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '56_assortativity.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 56_assortativity.png')


def plot_modularity(pt, sg, stats):
    """3. Community detection con Louvain — modularita' e numero community."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('Community Detection (Louvain): L\'Algoritmo Distrugge le Community?',
                 fontsize=13, fontweight='bold')

    for ax, df, feed, label, color in [
        (axes[0], pt, 'per_te', 'Per Te', ACCENT_1),
        (axes[1], sg, 'seguiti', 'Seguiti', ACCENT_2),
    ]:
        G = build_graph(df)
        if len(G.nodes) < 3:
            ax.set_title(f'{label}\n(grafo troppo piccolo)')
            continue

        node_to_comm, modularity, n_communities = louvain_communities(G)

        stats[f'{feed}_modularity'] = round(float(modularity), 4)
        stats[f'{feed}_n_communities'] = int(n_communities)
        stats[f'{feed}_n_nodes'] = len(G.nodes)
        stats[f'{feed}_n_edges'] = len(G.edges)

        # Distribuzione dimensione community
        comm_sizes = Counter(node_to_comm.values())
        sizes = sorted(comm_sizes.values(), reverse=True)

        ax.bar(range(len(sizes)), sizes, color=color, edgecolor='none')
        ax.set_xlabel('Community (ordinata per dimensione)')
        ax.set_ylabel('Nodi')
        ax.set_title(f'{label}\nQ = {modularity:.3f}, {n_communities} community, '
                     f'{len(G.nodes)} nodi, {len(G.edges)} archi',
                     fontsize=10)
        ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '57_modularity_communities.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 57_modularity_communities.png')


def plot_graph_summary(stats):
    """4. Summary card grafico delle metriche di rete."""
    fig, ax = plt.subplots(figsize=(10, 5))

    metrics = ['n_nodes', 'n_edges', 'modularity', 'assortativity', 'n_communities']
    labels = ['Nodi', 'Archi', 'Modularita\' Q', 'Assortativity r', 'Community']

    pt_vals = [stats.get(f'per_te_{m}', 0) for m in metrics]
    sg_vals = [stats.get(f'seguiti_{m}', 0) for m in metrics]

    x = np.arange(len(labels))
    width = 0.35

    # Normalizza per visualizzazione (metriche diverse)
    max_vals = [max(abs(p), abs(s), 0.001) for p, s in zip(pt_vals, sg_vals)]
    pt_norm = [p / m for p, m in zip(pt_vals, max_vals)]
    sg_norm = [s / m for s, m in zip(sg_vals, max_vals)]

    bars1 = ax.bar(x - width/2, pt_norm, width, label='Per Te', color=ACCENT_1, edgecolor='none')
    bars2 = ax.bar(x + width/2, sg_norm, width, label='Seguiti', color=ACCENT_2, edgecolor='none')

    # Etichette con valori reali
    for bars, vals in [(bars1, pt_vals), (bars2, sg_vals)]:
        for bar, val in zip(bars, vals):
            display = f'{val:.3f}' if isinstance(val, float) and abs(val) < 10 else str(int(val))
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                    display, ha='center', fontsize=8, color='#e0e0e0')

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel('Valore normalizzato')
    ax.set_title('Riepilogo Metriche di Rete', fontsize=13, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '58_graph_summary.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 58_graph_summary.png')


def main():
    if not HAS_NX:
        print('[!] networkx non installato. pip install networkx')
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    pt, sg = load_feeds()

    stats = {}
    plot_betweenness(pt, sg, stats)
    plot_assortativity(pt, sg, stats)
    plot_modularity(pt, sg, stats)
    plot_graph_summary(stats)

    with open(os.path.join(OUTPUT_DIR, 'stats_graph.json'), 'w') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f'[✓] Stats salvate in {OUTPUT_DIR}/stats_graph.json')


if __name__ == '__main__':
    main()
