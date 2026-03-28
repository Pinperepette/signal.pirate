#!/usr/bin/env python3
"""
03_analisi_engagement.py — Confronto metriche di engagement tra feed.

Legge i CSV prodotti da 00_extract.py e analizza:
  1. Distribuzione engagement (favorite, retweet, reply, bookmark)
  2. Engagement mediano per feed (box plot)
  3. Rapporto reply/favorite (controversialita')
  4. Correlazione followers vs engagement

Uso:
    python 03_analisi_engagement.py

Output:
    output/10_engagement_boxplot.png
    output/11_engagement_distributions.png
    output/12_controversy_ratio.png
    output/13_followers_vs_engagement.png
    output/stats_engagement.json
"""

import json
import os
import pandas as pd
import numpy as np

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

METRICS = ['favorite_count', 'retweet_count', 'reply_count', 'bookmark_count']
METRIC_LABELS = ['Like', 'Retweet', 'Reply', 'Bookmark']


def load_feeds():
    pt = pd.read_csv(os.path.join(DATA_DIR, 'per_te.csv'))
    sg = pd.read_csv(os.path.join(DATA_DIR, 'seguiti.csv'))
    return pt, sg


def plot_engagement_boxplot(pt, sg, stats):
    """1. Box plot engagement per metrica."""
    fig, axes = plt.subplots(1, len(METRICS), figsize=(14, 4))
    fig.suptitle('Engagement: Per Te vs Seguiti (scala log)', fontsize=13, fontweight='bold')

    for ax, metric, label in zip(axes, METRICS, METRIC_LABELS):
        data_pt = pt[metric].clip(lower=1)
        data_sg = sg[metric].clip(lower=1)

        bp = ax.boxplot(
            [data_pt, data_sg],
            labels=['Per Te', 'Seguiti'],
            patch_artist=True,
            showfliers=False,
            medianprops={'color': '#ffffff', 'linewidth': 2},
        )
        bp['boxes'][0].set_facecolor(ACCENT_1)
        bp['boxes'][1].set_facecolor(ACCENT_2)
        for box in bp['boxes']:
            box.set_alpha(0.7)

        ax.set_yscale('log')
        ax.set_title(label, fontsize=10)

        stats[f'per_te_{metric}_median'] = float(pt[metric].median())
        stats[f'seguiti_{metric}_median'] = float(sg[metric].median())
        stats[f'per_te_{metric}_mean'] = round(float(pt[metric].mean()), 1)
        stats[f'seguiti_{metric}_mean'] = round(float(sg[metric].mean()), 1)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '10_engagement_boxplot.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 10_engagement_boxplot.png')


def plot_engagement_distributions(pt, sg, stats):
    """2. Istogrammi sovrapposti per like e retweet."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    for ax, metric, label in zip(axes, ['favorite_count', 'retweet_count'], ['Like', 'Retweet']):
        # Usa percentili per evitare outlier estremi
        p99 = max(pt[metric].quantile(0.95), sg[metric].quantile(0.95))
        bins = np.linspace(0, p99, 50)

        ax.hist(pt[metric].clip(upper=p99), bins=bins, alpha=0.6,
                color=ACCENT_1, label='Per Te', density=True)
        ax.hist(sg[metric].clip(upper=p99), bins=bins, alpha=0.6,
                color=ACCENT_2, label='Seguiti', density=True)
        ax.set_xlabel(label)
        ax.set_ylabel('Densita\'')
        ax.set_title(f'Distribuzione {label}', fontsize=11)
        ax.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '11_engagement_distributions.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 11_engagement_distributions.png')


def plot_controversy_ratio(pt, sg, stats):
    """3. Rapporto reply/favorite — indice di controversialita'."""
    fig, ax = plt.subplots(figsize=(8, 4))

    for df, label, color in [(pt, 'Per Te', ACCENT_1), (sg, 'Seguiti', ACCENT_2)]:
        ratio = df['reply_count'] / df['favorite_count'].clip(lower=1)
        # Distribuisci in bucket
        bins = np.linspace(0, 1, 30)
        ax.hist(ratio.clip(upper=1), bins=bins, alpha=0.6,
                color=color, label=label, density=True)

        stats[f'{label.lower().replace(" ", "_")}_controversy_median'] = round(float(ratio.median()), 4)
        stats[f'{label.lower().replace(" ", "_")}_controversy_mean'] = round(float(ratio.mean()), 4)

    ax.set_xlabel('reply / like (0 = consenso, 1 = controverso)')
    ax.set_ylabel('Densita\'')
    ax.set_title('Indice di Controversialita\'', fontsize=13, fontweight='bold')
    ax.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '12_controversy_ratio.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 12_controversy_ratio.png')


def plot_followers_vs_engagement(pt, sg, stats):
    """4. Scatter followers vs like — l'algoritmo preferisce i grandi?"""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    for ax, df, label, color in [
        (axes[0], pt, 'Per Te', ACCENT_1),
        (axes[1], sg, 'Seguiti', ACCENT_2),
    ]:
        x = df['followers_count'].clip(lower=1)
        y = df['favorite_count'].clip(lower=1)

        ax.scatter(x, y, alpha=0.15, s=8, color=color, edgecolors='none')
        ax.set_xscale('log')
        ax.set_yscale('log')
        ax.set_xlabel('Followers')
        ax.set_ylabel('Like')
        ax.set_title(label, fontsize=11)

        # Correlazione log-log
        corr = np.corrcoef(np.log10(x), np.log10(y))[0, 1]
        ax.text(0.05, 0.95, f'r = {corr:.3f}', transform=ax.transAxes,
                fontsize=10, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='#1a1a2e', alpha=0.8))
        stats[f'{label.lower().replace(" ", "_")}_followers_like_corr'] = round(corr, 4)

    fig.suptitle('Followers vs Like (log-log)', fontsize=13, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '13_followers_vs_engagement.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 13_followers_vs_engagement.png')


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    pt, sg = load_feeds()

    stats = {}
    plot_engagement_boxplot(pt, sg, stats)
    plot_engagement_distributions(pt, sg, stats)
    plot_controversy_ratio(pt, sg, stats)
    plot_followers_vs_engagement(pt, sg, stats)

    with open(os.path.join(OUTPUT_DIR, 'stats_engagement.json'), 'w') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f'[✓] Stats salvate in {OUTPUT_DIR}/stats_engagement.json')


if __name__ == '__main__':
    main()
