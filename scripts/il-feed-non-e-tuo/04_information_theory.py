#!/usr/bin/env python3
"""
04_information_theory.py — Analisi information-theoretic dei due feed.

Calcola:
  1. Entropia di Shannon sulle emozioni — quale feed e' piu' vario
  2. KL divergence emozioni Per Te vs Seguiti — quanto l'algoritmo deforma
  3. Entropia autori — concentrazione vs diversita'
  4. Surprisal medio per tweet (quanto e' "atteso" ogni tweet)

Uso:
    python 04_information_theory.py

Output:
    output/14_entropy_comparison.png
    output/15_kl_divergence.png
    output/16_author_entropy.png
    output/stats_information_theory.json
"""

import json
import os
import pandas as pd
import numpy as np
from collections import Counter

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
ACCENT_3 = '#ffd93d'
OUTPUT_DIR = 'output'
DATA_DIR = 'data'


def load_feeds():
    pt = pd.read_csv(os.path.join(DATA_DIR, 'per_te.csv'))
    sg = pd.read_csv(os.path.join(DATA_DIR, 'seguiti.csv'))
    return pt, sg


def shannon_entropy(counts):
    """Entropia di Shannon in bit da un array di conteggi."""
    probs = counts / counts.sum()
    probs = probs[probs > 0]
    return -np.sum(probs * np.log2(probs))


def kl_divergence(p, q):
    """KL(P || Q) in bit. P e Q sono array di probabilita' allineati."""
    # Smoothing per evitare log(0)
    eps = 1e-10
    p = np.array(p) + eps
    q = np.array(q) + eps
    p = p / p.sum()
    q = q / q.sum()
    return np.sum(p * np.log2(p / q))


def get_emotion_distribution(df):
    """Distribuzione normalizzata delle emozioni."""
    all_emotions = []
    for emos in df['emotions'].dropna():
        for e in str(emos).split('|'):
            if e:
                all_emotions.append(e)
    return Counter(all_emotions)


def plot_entropy_comparison(pt, sg, stats):
    """1. Entropia di Shannon: emozioni, sentiment, intensita', lingua, autori."""
    dimensions = {
        'Emozioni': lambda df: get_emotion_distribution(df),
        'Sentiment': lambda df: Counter(df['sentiment'].dropna()),
        'Intensita\'': lambda df: Counter(df['intensity'].dropna()),
        'Lingua': lambda df: Counter(df['lang'].dropna()),
        'Autori': lambda df: Counter(df['screen_name'].dropna()),
    }

    labels = list(dimensions.keys())
    entropy_pt = []
    entropy_sg = []

    for dim_name, counter_fn in dimensions.items():
        cnt_pt = counter_fn(pt)
        cnt_sg = counter_fn(sg)

        h_pt = shannon_entropy(np.array(list(cnt_pt.values())))
        h_sg = shannon_entropy(np.array(list(cnt_sg.values())))

        entropy_pt.append(h_pt)
        entropy_sg.append(h_sg)

        key = dim_name.lower().replace("'", "").replace(" ", "_")
        stats[f'entropy_{key}_per_te'] = round(h_pt, 4)
        stats[f'entropy_{key}_seguiti'] = round(h_sg, 4)

    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(labels))
    width = 0.35

    bars1 = ax.bar(x - width/2, entropy_pt, width, label='Per Te',
                    color=ACCENT_1, edgecolor='none')
    bars2 = ax.bar(x + width/2, entropy_sg, width, label='Seguiti',
                    color=ACCENT_2, edgecolor='none')

    for bars in [bars1, bars2]:
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                    f'{bar.get_height():.2f}', ha='center', fontsize=8, color='#e0e0e0')

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel('Entropia (bit)')
    ax.set_title('Entropia di Shannon per dimensione', fontsize=13, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '14_entropy_comparison.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 14_entropy_comparison.png')


def plot_kl_divergence(pt, sg, stats):
    """2. KL divergence tra le distribuzioni dei due feed."""
    dimensions = {
        'Emozioni': lambda df: get_emotion_distribution(df),
        'Sentiment': lambda df: Counter(df['sentiment'].dropna()),
        'Intensita\'': lambda df: Counter(df['intensity'].dropna()),
        'Lingua': lambda df: Counter(df['lang'].dropna()),
    }

    kl_values = []
    kl_labels = []

    for dim_name, counter_fn in dimensions.items():
        cnt_pt = counter_fn(pt)
        cnt_sg = counter_fn(sg)

        # Allinea le chiavi
        all_keys = sorted(set(cnt_pt.keys()) | set(cnt_sg.keys()))
        p = np.array([cnt_pt.get(k, 0) for k in all_keys], dtype=float)
        q = np.array([cnt_sg.get(k, 0) for k in all_keys], dtype=float)

        kl = kl_divergence(p / p.sum(), q / q.sum())
        kl_values.append(kl)
        kl_labels.append(dim_name)

        key = dim_name.lower().replace("'", "").replace(" ", "_")
        stats[f'kl_{key}_pt_vs_sg'] = round(kl, 6)

    fig, ax = plt.subplots(figsize=(8, 4))
    colors = [ACCENT_1, ACCENT_3, ACCENT_2, '#bb86fc']
    bars = ax.barh(kl_labels[::-1], kl_values[::-1], color=colors[::-1], edgecolor='none')

    for bar, val in zip(bars, kl_values[::-1]):
        ax.text(bar.get_width() + 0.002, bar.get_y() + bar.get_height()/2,
                f'{val:.4f} bit', va='center', fontsize=10, color='#e0e0e0')

    ax.set_xlabel('KL Divergence (bit)')
    ax.set_title('KL(Per Te || Seguiti) — quanto l\'algoritmo deforma',
                 fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '15_kl_divergence.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 15_kl_divergence.png')


def plot_author_entropy(pt, sg, stats):
    """3. Entropia autori: simulazione bootstrapped per intervallo di confidenza."""
    fig, ax = plt.subplots(figsize=(8, 5))

    for df, label, color in [(pt, 'Per Te', ACCENT_1), (sg, 'Seguiti', ACCENT_2)]:
        authors = df['screen_name'].dropna().tolist()
        entropies = []
        sample_sizes = list(range(50, min(len(authors), 801), 50))

        for n in sample_sizes:
            boot_entropies = []
            for _ in range(100):
                sample = np.random.choice(authors, size=n, replace=True)
                counts = np.array(list(Counter(sample).values()))
                boot_entropies.append(shannon_entropy(counts))
            entropies.append(boot_entropies)

        means = [np.mean(e) for e in entropies]
        ci_low = [np.percentile(e, 5) for e in entropies]
        ci_high = [np.percentile(e, 95) for e in entropies]

        ax.plot(sample_sizes, means, color=color, label=label, linewidth=2)
        ax.fill_between(sample_sizes, ci_low, ci_high, color=color, alpha=0.15)

    ax.set_xlabel('Dimensione campione')
    ax.set_ylabel('Entropia autori (bit)')
    ax.set_title('Entropia autori al crescere del campione\n(bootstrap 90% CI)',
                 fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '16_author_entropy.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 16_author_entropy.png')


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    np.random.seed(42)
    pt, sg = load_feeds()

    stats = {}
    plot_entropy_comparison(pt, sg, stats)
    plot_kl_divergence(pt, sg, stats)
    plot_author_entropy(pt, sg, stats)

    with open(os.path.join(OUTPUT_DIR, 'stats_information_theory.json'), 'w') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f'[✓] Stats salvate in {OUTPUT_DIR}/stats_information_theory.json')


if __name__ == '__main__':
    main()
