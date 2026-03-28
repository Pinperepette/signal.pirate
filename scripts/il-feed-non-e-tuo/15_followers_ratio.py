#!/usr/bin/env python3
"""
15_followers_ratio.py — Analisi rapporto following/followers e metriche profilo.

Estrae da MongoDB friends_count (following) e followers_count per ogni autore.
Confronta i due feed su:
  1. Distribuzione followers confrontata (gia' fatta, qui piu' dettagliata)
  2. Distribuzione following (friends_count)
  3. Rapporto following/followers — indice di "influencer" vs "utente normale"
  4. Scatter following vs followers per feed
  5. Fasce di rapporto: chi ha rapporto < 0.01 (broadcast puro)
  6. Statuses count (attivita') e favourites count

Output:
    output/66_followers_comparison_detailed.png
    output/67_following_distribution.png
    output/68_ff_ratio.png
    output/69_ff_scatter.png
    output/70_ff_tiers.png
    output/71_activity_comparison.png
    output/stats_ff_ratio.json
"""

import json
import os
import numpy as np
import pandas as pd
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


def extract_profile_data():
    """Estrai metriche profilo da MongoDB per autori unici."""
    from pymongo import MongoClient
    client = MongoClient('mongodb://localhost:27017')
    db = client['SnareData']

    rows = []
    for feed_label, coll_name in [('per_te', 'twitter_per-te'), ('seguiti', 'twitter_seguiti')]:
        seen = set()
        for doc in db[coll_name].find().limit(800):
            data = doc.get('data', {}).get('data', {})
            user = data.get('core', {}).get('user_results', {}).get('result', {})
            user_legacy = user.get('legacy', {})
            screen_name = user.get('core', {}).get('screen_name', '')

            if not screen_name or screen_name in seen:
                continue
            seen.add(screen_name)

            followers = user_legacy.get('followers_count', 0)
            following = user_legacy.get('friends_count', 0)
            statuses = user_legacy.get('statuses_count', 0)
            favourites = user_legacy.get('favourites_count', 0)
            listed = user_legacy.get('listed_count', 0)
            verified = user.get('is_blue_verified', False)

            ff_ratio = following / max(followers, 1)

            rows.append({
                'feed': feed_label,
                'screen_name': screen_name,
                'followers_count': followers,
                'friends_count': following,
                'ff_ratio': ff_ratio,
                'statuses_count': statuses,
                'favourites_count': favourites,
                'listed_count': listed,
                'is_blue_verified': verified,
            })

    client.close()
    return pd.DataFrame(rows)


def plot_followers_comparison(df, stats):
    """1. Confronto followers dettagliato con mediana e percentili."""
    fig, ax = plt.subplots(figsize=(10, 5))

    for feed, label, color in [('per_te', 'Per Te', ACCENT_1), ('seguiti', 'Seguiti', ACCENT_2)]:
        sub = df[df['feed'] == feed]
        followers = sub['followers_count'].clip(lower=1)
        log_f = np.log10(followers)
        bins = np.linspace(0, log_f.max() + 0.5, 40)
        ax.hist(log_f, bins=bins, alpha=0.5, color=color, label=label, density=True)

        # Linea mediana
        med = np.log10(sub['followers_count'].median()) if sub['followers_count'].median() > 0 else 0
        ax.axvline(x=med, color=color, linestyle='--', alpha=0.7)

        stats[f'{feed}_followers_median'] = int(sub['followers_count'].median())
        stats[f'{feed}_followers_mean'] = int(sub['followers_count'].mean())
        stats[f'{feed}_followers_p25'] = int(sub['followers_count'].quantile(0.25))
        stats[f'{feed}_followers_p75'] = int(sub['followers_count'].quantile(0.75))

    tick_vals = [1, 2, 3, 4, 5, 6, 7, 8]
    tick_labels = ['10', '100', '1K', '10K', '100K', '1M', '10M', '100M']
    ax.set_xticks(tick_vals)
    ax.set_xticklabels(tick_labels)
    ax.set_xlabel('Followers (log scale)')
    ax.set_ylabel('Densita\'')
    ax.set_title('Distribuzione Followers Autori (tratteggio = mediana)',
                 fontsize=13, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '66_followers_comparison_detailed.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 66_followers_comparison_detailed.png')


def plot_following_distribution(df, stats):
    """2. Distribuzione following (friends_count)."""
    fig, ax = plt.subplots(figsize=(10, 5))

    for feed, label, color in [('per_te', 'Per Te', ACCENT_1), ('seguiti', 'Seguiti', ACCENT_2)]:
        sub = df[df['feed'] == feed]
        following = sub['friends_count'].clip(lower=1)
        log_f = np.log10(following)
        bins = np.linspace(0, log_f.max() + 0.5, 40)
        ax.hist(log_f, bins=bins, alpha=0.5, color=color, label=label, density=True)

        stats[f'{feed}_following_median'] = int(sub['friends_count'].median())
        stats[f'{feed}_following_mean'] = int(sub['friends_count'].mean())

    tick_vals = [0, 1, 2, 3, 4, 5]
    tick_labels = ['1', '10', '100', '1K', '10K', '100K']
    ax.set_xticks(tick_vals)
    ax.set_xticklabels(tick_labels)
    ax.set_xlabel('Following (log scale)')
    ax.set_ylabel('Densita\'')
    ax.set_title('Distribuzione Following (friends_count) degli Autori',
                 fontsize=13, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '67_following_distribution.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 67_following_distribution.png')


def plot_ff_ratio(df, stats):
    """3. Distribuzione rapporto following/followers."""
    fig, ax = plt.subplots(figsize=(10, 5))

    for feed, label, color in [('per_te', 'Per Te', ACCENT_1), ('seguiti', 'Seguiti', ACCENT_2)]:
        sub = df[df['feed'] == feed]
        ratio = sub['ff_ratio'].clip(upper=5)
        bins = np.linspace(0, 5, 50)
        ax.hist(ratio, bins=bins, alpha=0.5, color=color, label=label, density=True)

        stats[f'{feed}_ff_ratio_median'] = round(float(sub['ff_ratio'].median()), 4)
        stats[f'{feed}_ff_ratio_mean'] = round(float(sub['ff_ratio'].mean()), 4)

        # % account con ratio < 0.01 (broadcast puro: tipo Elon, media, politici)
        broadcast = (sub['ff_ratio'] < 0.01).sum() / len(sub) * 100
        stats[f'{feed}_broadcast_pct'] = round(broadcast, 2)

        # % account con ratio > 1 (seguono piu' di quanto sono seguiti)
        consumer = (sub['ff_ratio'] > 1).sum() / len(sub) * 100
        stats[f'{feed}_consumer_pct'] = round(consumer, 2)

    ax.axvline(x=1.0, color='#ffffff', linestyle='--', alpha=0.3, label='ratio = 1 (equilibrio)')
    ax.axvline(x=0.01, color='#ff6b6b', linestyle=':', alpha=0.3, label='ratio < 0.01 (broadcast)')
    ax.set_xlabel('Following / Followers')
    ax.set_ylabel('Densita\'')
    ax.set_title('Rapporto Following/Followers\n(< 0.01 = broadcast, > 1 = consumer)',
                 fontsize=12, fontweight='bold')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '68_ff_ratio.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 68_ff_ratio.png')


def plot_ff_scatter(df, stats):
    """4. Scatter following vs followers per feed."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('Following vs Followers (log-log)', fontsize=13, fontweight='bold')

    for ax, feed, label, color in [
        (axes[0], 'per_te', 'Per Te', ACCENT_1),
        (axes[1], 'seguiti', 'Seguiti', ACCENT_2),
    ]:
        sub = df[df['feed'] == feed]
        x = sub['followers_count'].clip(lower=1)
        y = sub['friends_count'].clip(lower=1)

        ax.scatter(x, y, alpha=0.3, s=10, color=color, edgecolors='none')
        ax.set_xscale('log')
        ax.set_yscale('log')

        # Linea ratio = 1
        lim = [1, max(x.max(), y.max()) * 2]
        ax.plot(lim, lim, color='#555555', linestyle='--', alpha=0.3, label='ratio = 1')

        ax.set_xlabel('Followers')
        ax.set_ylabel('Following')
        ax.set_title(label, fontsize=11)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.2)

        # Correlazione
        corr = np.corrcoef(np.log10(x), np.log10(y))[0, 1]
        ax.text(0.05, 0.95, f'r = {corr:.3f}', transform=ax.transAxes,
                fontsize=10, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='#1a1a2e', alpha=0.8))
        stats[f'{feed}_ff_corr'] = round(float(corr), 4)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '69_ff_scatter.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 69_ff_scatter.png')


def plot_ff_tiers(df, stats):
    """5. Fasce di rapporto following/followers."""
    fig, ax = plt.subplots(figsize=(10, 5))

    tiers = [
        ('Broadcast\n(< 0.01)', 0, 0.01),
        ('Influencer\n(0.01-0.1)', 0.01, 0.1),
        ('Creator\n(0.1-0.5)', 0.1, 0.5),
        ('Equilibrio\n(0.5-2)', 0.5, 2),
        ('Consumer\n(> 2)', 2, 1e6),
    ]

    x = np.arange(len(tiers))
    width = 0.35

    for i, (feed, label, color) in enumerate([
        ('per_te', 'Per Te', ACCENT_1),
        ('seguiti', 'Seguiti', ACCENT_2),
    ]):
        sub = df[df['feed'] == feed]
        vals = []
        for tier_name, lo, hi in tiers:
            mask = (sub['ff_ratio'] >= lo) & (sub['ff_ratio'] < hi)
            pct = mask.sum() / len(sub) * 100
            vals.append(pct)

        bars = ax.bar(x + i * width, vals, width, label=label, color=color, edgecolor='none')
        for bar, val in zip(bars, vals):
            if val > 1:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                        f'{val:.0f}%', ha='center', fontsize=8, color='#e0e0e0')

    ax.set_xticks(x + width/2)
    ax.set_xticklabels([t[0] for t in tiers], fontsize=8)
    ax.set_ylabel('% autori')
    ax.set_title('Tipologia Account per Rapporto Following/Followers',
                 fontsize=13, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '70_ff_tiers.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 70_ff_tiers.png')


def plot_activity(df, stats):
    """6. Confronto attivita': statuses e favourites."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Attivita\' degli Autori', fontsize=13, fontweight='bold')

    for ax, metric, label in [
        (axes[0], 'statuses_count', 'Tweet pubblicati'),
        (axes[1], 'favourites_count', 'Like messi'),
    ]:
        for feed, flabel, color in [('per_te', 'Per Te', ACCENT_1), ('seguiti', 'Seguiti', ACCENT_2)]:
            sub = df[df['feed'] == feed]
            data = sub[metric].clip(lower=1)
            log_d = np.log10(data)
            bins = np.linspace(0, log_d.max() + 0.5, 35)
            ax.hist(log_d, bins=bins, alpha=0.5, color=color, label=flabel, density=True)

            stats[f'{feed}_{metric}_median'] = int(sub[metric].median())

        tick_vals = [1, 2, 3, 4, 5, 6]
        tick_labels = ['10', '100', '1K', '10K', '100K', '1M']
        ax.set_xticks(tick_vals)
        ax.set_xticklabels(tick_labels)
        ax.set_xlabel(label)
        ax.set_ylabel('Densita\'')
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '71_activity_comparison.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 71_activity_comparison.png')


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print('[*] Estrazione dati profilo...')
    df = extract_profile_data()
    print(f'[+] {len(df)} autori unici ({len(df[df["feed"]=="per_te"])} Per Te, {len(df[df["feed"]=="seguiti"])} Seguiti)')

    stats = {}
    plot_followers_comparison(df, stats)
    plot_following_distribution(df, stats)
    plot_ff_ratio(df, stats)
    plot_ff_scatter(df, stats)
    plot_ff_tiers(df, stats)
    plot_activity(df, stats)

    with open(os.path.join(OUTPUT_DIR, 'stats_ff_ratio.json'), 'w') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f'[✓] Stats salvate in {OUTPUT_DIR}/stats_ff_ratio.json')


if __name__ == '__main__':
    main()
