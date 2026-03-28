#!/usr/bin/env python3
"""
11_power_laws.py — Power Law / Heavy Tail analysis.

Fitta una distribuzione Pareto sull'engagement e sui followers.
Confronta l'esponente alpha tra i due feed.
Alpha piu' basso = coda piu' pesante = pochi dominano tutto.

Output:
    output/52_power_law_likes.png
    output/53_power_law_followers.png
    output/54_alpha_comparison.png
    output/stats_powerlaw.json
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
OUTPUT_DIR = 'output'
DATA_DIR = 'data'


def load_feeds():
    pt = pd.read_csv(os.path.join(DATA_DIR, 'per_te.csv'))
    sg = pd.read_csv(os.path.join(DATA_DIR, 'seguiti.csv'))
    return pt, sg


def fit_pareto_alpha(data, x_min=None):
    """MLE per esponente Pareto: alpha = n / sum(ln(x/x_min))."""
    data = np.array(data, dtype=float)
    data = data[data > 0]
    if x_min is None:
        x_min = np.percentile(data, 10)  # soglia al 10° percentile
    data = data[data >= x_min]
    if len(data) < 10:
        return None, None, None
    n = len(data)
    alpha = n / np.sum(np.log(data / x_min))
    return alpha, x_min, n


def ccdf(data):
    """Complementary CDF: P(X >= x)."""
    data = np.sort(data)[::-1]
    n = len(data)
    return data, np.arange(1, n + 1) / n


def plot_power_law(pt, sg, metric, metric_label, filename, stats):
    """Plot CCDF log-log con fit Pareto."""
    fig, ax = plt.subplots(figsize=(10, 6))

    for df, feed, label, color in [
        (pt, 'per_te', 'Per Te', ACCENT_1),
        (sg, 'seguiti', 'Seguiti', ACCENT_2),
    ]:
        data = df[metric].values
        data = data[data > 0]
        if len(data) < 20:
            continue

        x, y = ccdf(data)
        ax.scatter(x, y, alpha=0.3, s=5, color=color, edgecolors='none', label=f'{label} (dati)')

        # Fit Pareto
        alpha, x_min, n = fit_pareto_alpha(data)
        if alpha:
            # Plot fit
            x_fit = np.logspace(np.log10(x_min), np.log10(x.max()), 100)
            y_fit = (x_min / x_fit) ** alpha
            ax.plot(x_fit, y_fit, color=color, linewidth=2, linestyle='--',
                    label=f'{label} fit: alpha={alpha:.2f}')

            stats[f'{feed}_{metric}_alpha'] = round(float(alpha), 4)
            stats[f'{feed}_{metric}_xmin'] = round(float(x_min), 1)
            stats[f'{feed}_{metric}_n_tail'] = int(n)

    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel(metric_label)
    ax.set_ylabel('P(X >= x)')
    ax.set_title(f'CCDF {metric_label} — Fit Power Law P(x) ~ x^(-alpha)',
                 fontsize=12, fontweight='bold')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, filename), dpi=150, bbox_inches='tight')
    plt.close()
    print(f'[+] {filename}')


def plot_alpha_comparison(stats):
    """Confronto alpha tra feed e metriche."""
    fig, ax = plt.subplots(figsize=(8, 5))

    metrics = ['favorite_count', 'retweet_count', 'reply_count', 'followers_count']
    labels = ['Like', 'Retweet', 'Reply', 'Followers']

    x = np.arange(len(labels))
    width = 0.35

    pt_alphas = [stats.get(f'per_te_{m}_alpha', 0) for m in metrics]
    sg_alphas = [stats.get(f'seguiti_{m}_alpha', 0) for m in metrics]

    bars1 = ax.bar(x - width/2, pt_alphas, width, label='Per Te', color=ACCENT_1, edgecolor='none')
    bars2 = ax.bar(x + width/2, sg_alphas, width, label='Seguiti', color=ACCENT_2, edgecolor='none')

    for bars in [bars1, bars2]:
        for bar in bars:
            val = bar.get_height()
            if val > 0:
                ax.text(bar.get_x() + bar.get_width()/2, val + 0.02,
                        f'{val:.2f}', ha='center', fontsize=9, color='#e0e0e0')

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel('Esponente alpha (Pareto)')
    ax.set_title('Esponente Power Law: alpha piu\' basso = coda piu\' pesante\n(pochi dominano tutto)',
                 fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '54_alpha_comparison.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 54_alpha_comparison.png')


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    pt, sg = load_feeds()

    stats = {}
    plot_power_law(pt, sg, 'favorite_count', 'Like', '52_power_law_likes.png', stats)
    plot_power_law(pt, sg, 'followers_count', 'Followers', '53_power_law_followers.png', stats)

    # Fit anche RT e reply per il confronto alpha
    for metric in ['retweet_count', 'reply_count']:
        for df, feed in [(pt, 'per_te'), (sg, 'seguiti')]:
            data = df[metric].values
            data = data[data > 0]
            alpha, x_min, n = fit_pareto_alpha(data)
            if alpha:
                stats[f'{feed}_{metric}_alpha'] = round(float(alpha), 4)

    plot_alpha_comparison(stats)

    with open(os.path.join(OUTPUT_DIR, 'stats_powerlaw.json'), 'w') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f'[✓] Stats salvate in {OUTPUT_DIR}/stats_powerlaw.json')


if __name__ == '__main__':
    main()
