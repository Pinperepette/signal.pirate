#!/usr/bin/env python3
"""
13_mutual_information.py — Mutual Information tra feature e visibilita'.

Piu' potente della KL: misura quanto una variabile spiega un'altra.
MI(X;Y) = sum p(x,y) * log(p(x,y) / (p(x)*p(y)))

Calcola:
  1. MI tra feature e feed type (cosa determina se un tweet finisce nel "Per Te")
  2. MI tra feature e posizione nello scroll
  3. MI tra coppie di feature per feed
  4. Heatmap MI completa

Output:
    output/59_mi_feed_selection.png
    output/60_mi_scroll_position.png
    output/61_mi_heatmap.png
    output/stats_mi.json
"""

import json
import os
import numpy as np
import pandas as pd

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
    pt['feed_id'] = 1
    sg['feed_id'] = 0
    pt['scroll_position'] = range(len(pt))
    sg['scroll_position'] = range(len(sg))
    return pt, sg


def discretize(series, n_bins=10):
    """Discretizza una serie numerica in bin equiprobabili."""
    series = series.fillna(0)
    try:
        return pd.qcut(series, n_bins, labels=False, duplicates='drop')
    except ValueError:
        return pd.cut(series, n_bins, labels=False)


def mutual_information(x, y):
    """MI(X;Y) da due serie discrete."""
    x = np.array(x)
    y = np.array(y)

    # Rimuovi NaN
    mask = ~(np.isnan(x) | np.isnan(y))
    x = x[mask].astype(int)
    y = y[mask].astype(int)

    if len(x) < 10:
        return 0.0

    # Conta joint e marginali
    joint = {}
    for xi, yi in zip(x, y):
        joint[(xi, yi)] = joint.get((xi, yi), 0) + 1

    n = len(x)
    px = np.bincount(x - x.min()) / n
    py = np.bincount(y - y.min()) / n

    mi = 0.0
    for (xi, yi), count in joint.items():
        pxy = count / n
        pxi = px[xi - x.min()]
        pyi = py[yi - y.min()]
        if pxy > 0 and pxi > 0 and pyi > 0:
            mi += pxy * np.log2(pxy / (pxi * pyi))

    return max(mi, 0.0)


def plot_mi_feed_selection(pt, sg, stats):
    """1. MI tra feature e feed type — cosa determina la selezione."""
    combined = pd.concat([pt, sg], ignore_index=True)

    features = {
        'followers_count': 'Followers',
        'favorite_count': 'Like',
        'retweet_count': 'Retweet',
        'reply_count': 'Reply',
        'bookmark_count': 'Bookmark',
        'is_blue_verified': 'Verified',
        'urls_count': 'URLs',
        'mentions_count': 'Menzioni',
    }

    mi_values = {}
    for col, label in features.items():
        if col == 'is_blue_verified':
            x_disc = combined[col].fillna(0).astype(int)
        else:
            x_disc = discretize(combined[col])
        mi = mutual_information(x_disc.values, combined['feed_id'].values)
        mi_values[label] = mi
        stats[f'mi_feed_{col}'] = round(mi, 6)

    # Sort
    sorted_mi = sorted(mi_values.items(), key=lambda x: -x[1])
    labels, values = zip(*sorted_mi)

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = [ACCENT_1 if v > np.mean(values) else '#555555' for v in values]
    ax.barh(list(labels)[::-1], list(values)[::-1], color=colors[::-1], edgecolor='none')
    ax.set_xlabel('Mutual Information (bit)')
    ax.set_title('MI(Feature, Feed): Cosa Determina Se un Tweet Finisce nel "Per Te"',
                 fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '59_mi_feed_selection.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 59_mi_feed_selection.png')


def plot_mi_scroll_position(pt, sg, stats):
    """2. MI tra feature e posizione nello scroll — cosa guida l'ordinamento."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('MI(Feature, Posizione Scroll): Cosa Guida l\'Ordinamento',
                 fontsize=13, fontweight='bold')

    features = {
        'followers_count': 'Followers',
        'favorite_count': 'Like',
        'retweet_count': 'Retweet',
        'reply_count': 'Reply',
        'is_blue_verified': 'Verified',
    }

    for ax, df, label, color in [
        (axes[0], pt, 'Per Te', ACCENT_1),
        (axes[1], sg, 'Seguiti', ACCENT_2),
    ]:
        pos_disc = discretize(df['scroll_position'], n_bins=20)
        mi_values = {}

        for col, feat_label in features.items():
            if col == 'is_blue_verified':
                x_disc = df[col].fillna(0).astype(int)
            else:
                x_disc = discretize(df[col])
            mi = mutual_information(x_disc.values, pos_disc.values)
            mi_values[feat_label] = mi
            stats[f'{label.lower().replace(" ", "_")}_mi_scroll_{col}'] = round(mi, 6)

        sorted_mi = sorted(mi_values.items(), key=lambda x: -x[1])
        feat_labels, values = zip(*sorted_mi)
        ax.barh(list(feat_labels)[::-1], list(values)[::-1], color=color, edgecolor='none')
        ax.set_xlabel('MI (bit)')
        ax.set_title(label, fontsize=11)
        ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '60_mi_scroll_position.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 60_mi_scroll_position.png')


def plot_mi_heatmap(pt, sg, stats):
    """3. Heatmap MI tra coppie di feature — per feed."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('Mutual Information tra Coppie di Feature', fontsize=13, fontweight='bold')

    features = ['followers_count', 'favorite_count', 'retweet_count',
                'reply_count', 'bookmark_count', 'urls_count', 'mentions_count']
    labels = ['Followers', 'Like', 'RT', 'Reply', 'BM', 'URL', 'Mentions']

    for ax, df, label, cmap in [
        (axes[0], pt, 'Per Te', 'Reds'),
        (axes[1], sg, 'Seguiti', 'Blues'),
    ]:
        n = len(features)
        matrix = np.zeros((n, n))

        disc_features = {}
        for col in features:
            disc_features[col] = discretize(df[col])

        for i in range(n):
            for j in range(n):
                if i == j:
                    matrix[i, j] = 0
                else:
                    matrix[i, j] = mutual_information(
                        disc_features[features[i]].values,
                        disc_features[features[j]].values
                    )

        im = ax.imshow(matrix, cmap=cmap, aspect='auto')
        ax.set_xticks(range(n))
        ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
        ax.set_yticks(range(n))
        ax.set_yticklabels(labels, fontsize=8)
        ax.set_title(label, fontsize=11)

        for i in range(n):
            for j in range(n):
                if matrix[i, j] > 0:
                    ax.text(j, i, f'{matrix[i,j]:.3f}', ha='center', va='center',
                            fontsize=6, color='white' if matrix[i,j] > matrix.max()*0.5 else '#888')

        fig.colorbar(im, ax=ax, label='MI (bit)', shrink=0.8)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '61_mi_heatmap.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 61_mi_heatmap.png')


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    pt, sg = load_feeds()

    stats = {}
    plot_mi_feed_selection(pt, sg, stats)
    plot_mi_scroll_position(pt, sg, stats)
    plot_mi_heatmap(pt, sg, stats)

    with open(os.path.join(OUTPUT_DIR, 'stats_mi.json'), 'w') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f'[✓] Stats salvate in {OUTPUT_DIR}/stats_mi.json')


if __name__ == '__main__':
    main()
