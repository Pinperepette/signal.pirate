#!/usr/bin/env python3
"""
08_grafici_extra.py — Grafici supplementari per massimizzare le visualizzazioni.

Legge i CSV prodotti da 00_extract.py e genera:
  1. Engagement totale per tweet (score composito)
  2. Matrice correlazione metriche
  3. Treemap autori (bar chart gerarchico)
  4. Rapporto bookmark/like — segnale di "qualita'"
  5. Tweet per ora del giorno (heatmap giorno x ora)
  6. CDF engagement — curva cumulativa
  7. Violin plot follower per sentiment
  8. Radar chart confronto dimensioni aggregate

Output:
    output/32_engagement_score.png
    output/33_correlation_matrix.png
    output/34_author_treemap.png
    output/35_bookmark_ratio.png
    output/36_hourly_heatmap.png
    output/37_engagement_cdf.png
    output/38_followers_sentiment_violin.png
    output/39_radar_comparison.png
    output/stats_extra.json
"""

import json
import os
import pandas as pd
import numpy as np

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

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
    pt['dt'] = pd.to_datetime(pt['created_at'], format='%a %b %d %H:%M:%S %z %Y', errors='coerce')
    sg['dt'] = pd.to_datetime(sg['created_at'], format='%a %b %d %H:%M:%S %z %Y', errors='coerce')
    return pt, sg


def engagement_score(df):
    """Score composito: like + 2*RT + 3*reply + 4*bookmark."""
    return (df['favorite_count'] +
            2 * df['retweet_count'] +
            3 * df['reply_count'] +
            4 * df['bookmark_count'])


def plot_engagement_score(pt, sg, stats):
    """1. Distribuzione engagement score."""
    fig, ax = plt.subplots(figsize=(10, 5))

    for df, label, color in [(pt, 'Per Te', ACCENT_1), (sg, 'Seguiti', ACCENT_2)]:
        score = engagement_score(df).clip(lower=1)
        log_score = np.log10(score)
        bins = np.linspace(0, log_score.max() + 0.5, 40)
        ax.hist(log_score, bins=bins, alpha=0.5, color=color, label=label, density=True)

        stats[f'{label.lower().replace(" ", "_")}_engagement_score_median'] = float(score.median())
        stats[f'{label.lower().replace(" ", "_")}_engagement_score_p90'] = float(score.quantile(0.9))

    tick_vals = [0, 1, 2, 3, 4, 5, 6]
    tick_labels = ['1', '10', '100', '1K', '10K', '100K', '1M']
    ax.set_xticks(tick_vals)
    ax.set_xticklabels(tick_labels)
    ax.set_xlabel('Engagement Score (like + 2*RT + 3*reply + 4*BM)')
    ax.set_ylabel('Densita\'')
    ax.set_title('Distribuzione Engagement Score Composito', fontsize=13, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '32_engagement_score.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 32_engagement_score.png')


def plot_correlation_matrix(pt, sg, stats):
    """2. Matrice correlazione metriche — per feed."""
    metrics = ['favorite_count', 'retweet_count', 'reply_count', 'bookmark_count',
               'followers_count', 'urls_count', 'mentions_count']
    metric_labels = ['Like', 'RT', 'Reply', 'BM', 'Followers', 'URLs', 'Mentions']

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('Matrice Correlazione Metriche', fontsize=13, fontweight='bold')

    for ax, df, label, cmap in [
        (axes[0], pt, 'Per Te', 'Reds'),
        (axes[1], sg, 'Seguiti', 'Blues'),
    ]:
        corr = df[metrics].corr()
        im = ax.imshow(corr.values, cmap=cmap, vmin=-1, vmax=1, aspect='auto')

        ax.set_xticks(range(len(metric_labels)))
        ax.set_xticklabels(metric_labels, rotation=45, ha='right', fontsize=8)
        ax.set_yticks(range(len(metric_labels)))
        ax.set_yticklabels(metric_labels, fontsize=8)
        ax.set_title(label, fontsize=11)

        for i in range(len(metrics)):
            for j in range(len(metrics)):
                val = corr.values[i, j]
                ax.text(j, i, f'{val:.2f}', ha='center', va='center',
                        fontsize=7, color='white' if abs(val) > 0.5 else '#888')

        fig.colorbar(im, ax=ax, shrink=0.8)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '33_correlation_matrix.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 33_correlation_matrix.png')


def plot_author_treemap(pt, sg, stats):
    """3. Top 20 autori per feed — bar chart pesato."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 7))
    fig.suptitle('Top 20 Autori per Numero di Tweet', fontsize=13, fontweight='bold')

    for ax, df, label, color in [
        (axes[0], pt, 'Per Te', ACCENT_1),
        (axes[1], sg, 'Seguiti', ACCENT_2),
    ]:
        top = df['screen_name'].value_counts().head(20)
        ax.barh(top.index[::-1], top.values[::-1], color=color, edgecolor='none')
        ax.set_xlabel('Tweet')
        ax.set_title(label, fontsize=11)

        for i, (name, val) in enumerate(zip(top.index[::-1], top.values[::-1])):
            ax.text(val + 0.3, i, str(val), va='center', fontsize=8, color='#e0e0e0')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '34_author_treemap.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 34_author_treemap.png')


def plot_bookmark_ratio(pt, sg, stats):
    """4. Bookmark/Like ratio — segnale di qualita' percepita."""
    fig, ax = plt.subplots(figsize=(8, 5))

    for df, label, color in [(pt, 'Per Te', ACCENT_1), (sg, 'Seguiti', ACCENT_2)]:
        ratio = df['bookmark_count'] / df['favorite_count'].clip(lower=1)
        bins = np.linspace(0, 0.5, 40)
        ax.hist(ratio.clip(upper=0.5), bins=bins, alpha=0.5, color=color, label=label, density=True)

        stats[f'{label.lower().replace(" ", "_")}_bookmark_ratio_median'] = round(float(ratio.median()), 4)
        stats[f'{label.lower().replace(" ", "_")}_bookmark_ratio_mean'] = round(float(ratio.mean()), 4)

    ax.set_xlabel('bookmark / like (alto = contenuto da salvare)')
    ax.set_ylabel('Densita\'')
    ax.set_title('Rapporto Bookmark/Like — Qualita\' Percepita', fontsize=13, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '35_bookmark_ratio.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 35_bookmark_ratio.png')


def plot_hourly_heatmap(pt, sg, stats):
    """5. Heatmap: giorno della settimana x ora."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Heatmap: Giorno x Ora dei Tweet', fontsize=13, fontweight='bold')

    day_names = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom']

    for ax, df, label, cmap in [
        (axes[0], pt, 'Per Te', 'Reds'),
        (axes[1], sg, 'Seguiti', 'Blues'),
    ]:
        valid = df['dt'].dropna()
        if valid.empty:
            continue

        matrix = np.zeros((7, 24))
        for dt in valid:
            dow = dt.weekday()
            hour = dt.hour
            matrix[dow, hour] += 1

        # Normalizza per riga
        row_sums = matrix.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1
        matrix_norm = matrix / row_sums * 100

        im = ax.imshow(matrix_norm, cmap=cmap, aspect='auto', interpolation='nearest')
        ax.set_yticks(range(7))
        ax.set_yticklabels(day_names, fontsize=9)
        ax.set_xticks(range(0, 24, 3))
        ax.set_xlabel('Ora (UTC)')
        ax.set_title(label, fontsize=11)
        fig.colorbar(im, ax=ax, label='% tweet', shrink=0.8)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '36_hourly_heatmap.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 36_hourly_heatmap.png')


def plot_engagement_cdf(pt, sg, stats):
    """6. CDF dell'engagement — curva cumulativa."""
    fig, ax = plt.subplots(figsize=(10, 5))

    for df, label, color in [(pt, 'Per Te', ACCENT_1), (sg, 'Seguiti', ACCENT_2)]:
        likes = np.sort(df['favorite_count'].values)
        cdf = np.arange(1, len(likes) + 1) / len(likes)
        ax.plot(likes, cdf, color=color, label=label, linewidth=2)

    ax.set_xscale('log')
    ax.set_xlabel('Like (log)')
    ax.set_ylabel('CDF (proporzione cumulativa)')
    ax.set_title('CDF Like — Quanto Engagement Serve per Entrare nel Feed',
                 fontsize=12, fontweight='bold')
    ax.axhline(y=0.5, color='#555555', linestyle='--', alpha=0.5)
    ax.legend()
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '37_engagement_cdf.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 37_engagement_cdf.png')


def plot_followers_sentiment_violin(pt, sg, stats):
    """7. Violin: followers per sentiment."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle('Followers per Sentiment', fontsize=13, fontweight='bold')

    sentiments = sorted(set(
        pt['sentiment'].dropna().unique().tolist() +
        sg['sentiment'].dropna().unique().tolist()
    ))

    for ax, df, label, color in [
        (axes[0], pt, 'Per Te', ACCENT_1),
        (axes[1], sg, 'Seguiti', ACCENT_2),
    ]:
        data_by_sent = []
        labels_used = []
        for s in sentiments:
            vals = df[df['sentiment'] == s]['followers_count'].clip(lower=1)
            if len(vals) > 5:
                data_by_sent.append(np.log10(vals.values))
                labels_used.append(s)

        if data_by_sent:
            parts = ax.violinplot(data_by_sent, showmedians=True, showextrema=False)
            for pc in parts['bodies']:
                pc.set_facecolor(color)
                pc.set_alpha(0.6)
            parts['cmedians'].set_color('#ffffff')

            ax.set_xticks(range(1, len(labels_used) + 1))
            ax.set_xticklabels(labels_used, fontsize=9)
            ax.set_ylabel('log10(Followers)')
            ax.set_title(label, fontsize=11)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '38_followers_sentiment_violin.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 38_followers_sentiment_violin.png')


def plot_radar_comparison(pt, sg, stats):
    """8. Radar chart — confronto dimensioni aggregate."""
    dimensions = {
        'Engagement\nmediano': (pt['favorite_count'].median(), sg['favorite_count'].median()),
        'Followers\nmediano': (pt['followers_count'].median(), sg['followers_count'].median()),
        '% Verificati': (pt['is_blue_verified'].mean() * 100, sg['is_blue_verified'].mean() * 100),
        'Autori\nunici': (pt['screen_name'].nunique(), sg['screen_name'].nunique()),
        '% con\nHashtag': ((pt['hashtags'].fillna('') != '').mean() * 100,
                           (sg['hashtags'].fillna('') != '').mean() * 100),
        '% Alta\nIntensita\'': ((pt['intensity'] == 'Alta').mean() * 100,
                                (sg['intensity'] == 'Alta').mean() * 100),
        'URL per\ntweet': (pt['urls_count'].mean(), sg['urls_count'].mean()),
        'Menzioni\nper tweet': (pt['mentions_count'].mean(), sg['mentions_count'].mean()),
    }

    labels = list(dimensions.keys())
    pt_vals = [v[0] for v in dimensions.values()]
    sg_vals = [v[1] for v in dimensions.values()]

    # Normalizza 0-1 per radar
    max_vals = [max(p, s, 0.001) for p, s in zip(pt_vals, sg_vals)]
    pt_norm = [p / m for p, m in zip(pt_vals, max_vals)]
    sg_norm = [s / m for s, m in zip(sg_vals, max_vals)]

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    pt_norm += pt_norm[:1]
    sg_norm += sg_norm[:1]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

    ax.plot(angles, pt_norm, color=ACCENT_1, linewidth=2, label='Per Te')
    ax.fill(angles, pt_norm, color=ACCENT_1, alpha=0.15)
    ax.plot(angles, sg_norm, color=ACCENT_2, linewidth=2, label='Seguiti')
    ax.fill(angles, sg_norm, color=ACCENT_2, alpha=0.15)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_title('Confronto Multidimensionale\n(normalizzato al max per dimensione)',
                 fontsize=13, fontweight='bold', pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.2, 1.1))

    # Stile
    ax.set_facecolor('#12121a')
    ax.spines['polar'].set_color('#333355')
    ax.grid(color='#1a1a2e', alpha=0.5)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '39_radar_comparison.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 39_radar_comparison.png')


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    pt, sg = load_feeds()

    stats = {}
    plot_engagement_score(pt, sg, stats)
    plot_correlation_matrix(pt, sg, stats)
    plot_author_treemap(pt, sg, stats)
    plot_bookmark_ratio(pt, sg, stats)
    plot_hourly_heatmap(pt, sg, stats)
    plot_engagement_cdf(pt, sg, stats)
    plot_followers_sentiment_violin(pt, sg, stats)
    plot_radar_comparison(pt, sg, stats)

    with open(os.path.join(OUTPUT_DIR, 'stats_extra.json'), 'w') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f'[✓] Stats salvate in {OUTPUT_DIR}/stats_extra.json')


if __name__ == '__main__':
    main()
