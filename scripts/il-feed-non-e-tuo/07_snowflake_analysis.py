#!/usr/bin/env python3
"""
07_snowflake_analysis.py — Snowflake ID analysis sugli autori dei due feed.

Decodifica gli user_id (Twitter Snowflake) per estrarre:
  - timestamp di creazione account
  - datacenter ID
  - worker ID
  - sequence ID

Poi confronta i due feed su:
  1. Timeline creazione account (quando sono stati creati gli autori)
  2. Heatmap DC:WK — su quali nodi infrastrutturali sono stati creati
  3. Distribuzione sequence ID — segnali di creazione massiva
  4. Eta' media degli account per feed
  5. Cluster temporali — account creati nello stesso minuto
  6. Scatter: eta' account vs followers

Uso:
    python 07_snowflake_analysis.py

Prerequisito:
    00_extract.py deve avere estratto anche user_id.
    Se non presente, lo script legge direttamente da MongoDB.

Output:
    output/26_account_creation_timeline.png
    output/27_dc_wk_heatmap.png
    output/28_sequence_distribution.png
    output/29_account_age.png
    output/30_creation_clusters.png
    output/31_age_vs_followers.png
    output/stats_snowflake.json
"""

import json
import os
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from collections import Counter, defaultdict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

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

TWITTER_EPOCH_MS = 1288834974657


def parse_snowflake(snowflake_id):
    """Decodifica un Twitter Snowflake ID."""
    try:
        sid = int(snowflake_id)
    except (ValueError, TypeError):
        return None
    if sid <= 0:
        return None

    is_estimate = sid < 1400000000
    sequence_id = sid & 0xFFF
    worker_id = (sid >> 12) & 0x1F
    dc_id = (sid >> 17) & 0x1F
    timestamp_ms = (sid >> 22) + TWITTER_EPOCH_MS
    created_at = datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc)

    return {
        'timestamp_ms': timestamp_ms,
        'created_at': created_at,
        'dc_id': dc_id,
        'worker_id': worker_id,
        'sequence_id': sequence_id,
        'is_estimate': is_estimate,
    }


def extract_authors_from_mongo():
    """Estrai autori unici con user_id da MongoDB."""
    from pymongo import MongoClient
    client = MongoClient('mongodb://localhost:27017')
    db = client['SnareData']

    authors = {}
    for feed_label, coll_name in [('per_te', 'twitter_per-te'), ('seguiti', 'twitter_seguiti')]:
        seen = set()
        for doc in db[coll_name].find().limit(800):
            data = doc.get('data', {}).get('data', {})
            user = data.get('core', {}).get('user_results', {}).get('result', {})
            user_id = user.get('rest_id', '')
            screen_name = user.get('core', {}).get('screen_name', '')
            followers = user.get('legacy', {}).get('followers_count', 0)
            is_verified = user.get('is_blue_verified', False)

            if not user_id or not screen_name or screen_name in seen:
                continue
            seen.add(screen_name)

            sf = parse_snowflake(user_id)
            if sf:
                key = f'{feed_label}:{screen_name}'
                authors[key] = {
                    'feed': feed_label,
                    'screen_name': screen_name,
                    'user_id': user_id,
                    'followers_count': followers,
                    'is_blue_verified': is_verified,
                    **sf,
                }
    client.close()
    return pd.DataFrame(authors.values())


def plot_creation_timeline(df, stats):
    """1. Timeline creazione account per feed."""
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    fig.suptitle('Timeline Creazione Account Autori', fontsize=14, fontweight='bold')

    for ax, feed, label, color in [
        (axes[0], 'per_te', 'Per Te', ACCENT_1),
        (axes[1], 'seguiti', 'Seguiti', ACCENT_2),
    ]:
        sub = df[(df['feed'] == feed) & (~df['is_estimate'])]
        if sub.empty:
            continue

        dates = sub['created_at']
        # Bin per mese
        months = dates.dt.to_period('M').value_counts().sort_index()
        month_dates = [p.to_timestamp() for p in months.index]

        ax.bar(month_dates, months.values, width=25, color=color, edgecolor='none', alpha=0.8)
        ax.set_ylabel('Account creati')
        ax.set_title(label, fontsize=11)
        ax.grid(True, alpha=0.2)

        # Eta' mediana
        now = datetime.now(timezone.utc)
        ages_days = (now - dates).dt.total_seconds() / 86400
        stats[f'{feed}_median_age_days'] = round(float(ages_days.median()), 0)
        stats[f'{feed}_mean_age_days'] = round(float(ages_days.mean()), 0)
        stats[f'{feed}_oldest_account'] = sub.loc[dates.idxmin(), 'screen_name']
        stats[f'{feed}_newest_account'] = sub.loc[dates.idxmax(), 'screen_name']

    axes[1].xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    axes[1].xaxis.set_major_locator(mdates.YearLocator(2))
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '26_account_creation_timeline.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 26_account_creation_timeline.png')


def plot_dc_wk_heatmap(df, stats):
    """2. Heatmap DC:WK per feed — confronto."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('Heatmap Datacenter : Worker (Snowflake ID)', fontsize=14, fontweight='bold')

    for ax, feed, label, cmap in [
        (axes[0], 'per_te', 'Per Te', 'Reds'),
        (axes[1], 'seguiti', 'Seguiti', 'Blues'),
    ]:
        sub = df[(df['feed'] == feed) & (~df['is_estimate'])]
        if sub.empty:
            continue

        max_dc = sub['dc_id'].max()
        max_wk = sub['worker_id'].max()

        matrix = np.zeros((max_dc + 1, max_wk + 1))
        for _, row in sub.iterrows():
            matrix[row['dc_id'], row['worker_id']] += 1

        im = ax.imshow(matrix, cmap=cmap, aspect='auto', interpolation='nearest')
        ax.set_xlabel('Worker ID')
        ax.set_ylabel('Datacenter ID')
        ax.set_title(label, fontsize=11)
        fig.colorbar(im, ax=ax, label='Account', shrink=0.8)

        # Annota celle con valori > 0
        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                if matrix[i, j] > 0:
                    ax.text(j, i, f'{int(matrix[i,j])}', ha='center', va='center',
                            fontsize=6, color='white' if matrix[i,j] > matrix.max()*0.5 else '#888')

        # Top nodo
        top_idx = np.unravel_index(matrix.argmax(), matrix.shape)
        stats[f'{feed}_top_dc_wk'] = f'DC:{top_idx[0]}:WK:{top_idx[1]}'
        stats[f'{feed}_top_dc_wk_count'] = int(matrix[top_idx])
        stats[f'{feed}_unique_dc'] = int((matrix.sum(axis=1) > 0).sum())
        stats[f'{feed}_unique_wk'] = int((matrix.sum(axis=0) > 0).sum())

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '27_dc_wk_heatmap.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 27_dc_wk_heatmap.png')


def plot_sequence_distribution(df, stats):
    """3. Distribuzione sequence ID per feed."""
    fig, ax = plt.subplots(figsize=(10, 5))

    buckets = ['0', '1-10', '11-50', '51-100', '101-500', '501+']
    bucket_ranges = [(0, 0), (1, 10), (11, 50), (51, 100), (101, 500), (501, 4096)]

    x = np.arange(len(buckets))
    width = 0.35

    for i, (feed, label, color) in enumerate([
        ('per_te', 'Per Te', ACCENT_1),
        ('seguiti', 'Seguiti', ACCENT_2),
    ]):
        sub = df[(df['feed'] == feed) & (~df['is_estimate'])]
        vals = []
        for lo, hi in bucket_ranges:
            mask = (sub['sequence_id'] >= lo) & (sub['sequence_id'] <= hi)
            vals.append(mask.sum())

        bars = ax.bar(x + i * width, vals, width, label=label, color=color, edgecolor='none')
        for bar, val in zip(bars, vals):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                        str(val), ha='center', fontsize=8, color='#e0e0e0')

        stats[f'{feed}_high_seq_50plus'] = int(sum(vals[3:]))
        stats[f'{feed}_max_sequence'] = int(sub['sequence_id'].max()) if not sub.empty else 0

    ax.set_xticks(x + width / 2)
    ax.set_xticklabels(buckets)
    ax.set_xlabel('Sequence ID range')
    ax.set_ylabel('Account')
    ax.set_title('Distribuzione Sequence ID (Snowflake)\nValori alti = molti account creati nello stesso millisecondo',
                 fontsize=12, fontweight='bold')
    ax.legend()

    # Colore sfondo per zone sospette
    ax.axvspan(2.5, 5.5, alpha=0.05, color='red')
    ax.text(4, ax.get_ylim()[1] * 0.9, 'zona sospetta', fontsize=9, color='#ff6b6b',
            ha='center', alpha=0.7)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '28_sequence_distribution.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 28_sequence_distribution.png')


def plot_account_age(df, stats):
    """4. Distribuzione eta' account."""
    fig, ax = plt.subplots(figsize=(10, 5))

    now = datetime.now(timezone.utc)

    for feed, label, color in [('per_te', 'Per Te', ACCENT_1), ('seguiti', 'Seguiti', ACCENT_2)]:
        sub = df[(df['feed'] == feed) & (~df['is_estimate'])]
        if sub.empty:
            continue
        ages_years = (now - sub['created_at']).dt.total_seconds() / (86400 * 365.25)
        bins = np.linspace(0, ages_years.max() + 1, 30)
        ax.hist(ages_years, bins=bins, alpha=0.5, color=color, label=label, density=True)

    ax.set_xlabel('Eta\' account (anni)')
    ax.set_ylabel('Densita\'')
    ax.set_title('Distribuzione Eta\' Account Autori', fontsize=13, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '29_account_age.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 29_account_age.png')


def plot_creation_clusters(df, stats):
    """5. Cluster spazio-temporali: stesso minuto + stesso nodo DC:WK = segnale forte."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('Cluster Spazio-Temporali: Stesso Minuto + Stesso Nodo DC:WK',
                 fontsize=13, fontweight='bold')

    for ax, feed, label, color in [
        (axes[0], 'per_te', 'Per Te', ACCENT_1),
        (axes[1], 'seguiti', 'Seguiti', ACCENT_2),
    ]:
        sub = df[(df['feed'] == feed) & (~df['is_estimate'])]
        if sub.empty:
            continue

        sub_copy = sub.copy()
        sub_copy['minute'] = sub_copy['timestamp_ms'] // 60000

        # --- Cluster solo temporali (stesso minuto, qualsiasi DC) ---
        minute_counts = sub_copy.groupby('minute').size()
        temporal_only = minute_counts[minute_counts >= 2]
        stats[f'{feed}_temporal_clusters_2plus'] = int(len(temporal_only))
        stats[f'{feed}_max_temporal_cluster'] = int(temporal_only.max()) if not temporal_only.empty else 0

        # --- Cluster spazio-temporali (stesso minuto E stesso datacenter) ---
        spatiotemporal = sub_copy.groupby(['minute', 'dc_id']).size()
        st_clusters = spatiotemporal[spatiotemporal >= 2]

        stats[f'{feed}_spatiotemporal_clusters'] = int(len(st_clusters))

        if st_clusters.empty:
            ax.text(0.5, 0.5, 'Nessun cluster\nspazio-temporale', transform=ax.transAxes,
                    ha='center', fontsize=12, color='#888888')
            ax.set_title(label)
            continue

        # Plot: confronto cluster temporali vs spazio-temporali
        temporal_sizes = temporal_only.value_counts().sort_index()
        st_sizes = st_clusters.value_counts().sort_index()

        all_sizes = sorted(set(temporal_sizes.index) | set(st_sizes.index))
        x = np.arange(len(all_sizes))
        width = 0.35

        t_vals = [temporal_sizes.get(s, 0) for s in all_sizes]
        st_vals = [st_sizes.get(s, 0) for s in all_sizes]

        ax.bar(x - width/2, t_vals, width, label='Solo temporale\n(stesso minuto)',
               color=color, alpha=0.4, edgecolor='none')
        ax.bar(x + width/2, st_vals, width, label='Spazio-temporale\n(stesso min + DC)',
               color=color, edgecolor='white', linewidth=1.5)

        ax.set_xticks(x)
        ax.set_xticklabels([str(s) for s in all_sizes])
        ax.set_xlabel('Account per cluster')
        ax.set_ylabel('Numero cluster')
        ax.set_title(label, fontsize=11)
        ax.legend(fontsize=7, loc='upper right')

        # Dettagli cluster spazio-temporali significativi
        big_st = st_clusters[st_clusters >= 2].reset_index()
        big_st.columns = ['minute', 'dc_id', 'size']
        big_st = big_st.sort_values('size', ascending=False)
        cluster_details = []
        for _, row in big_st.head(5).iterrows():
            members = sub_copy[(sub_copy['minute'] == row['minute']) &
                               (sub_copy['dc_id'] == row['dc_id'])]
            cluster_details.append({
                'size': int(row['size']),
                'dc': int(row['dc_id']),
                'users': members['screen_name'].tolist()[:5],
            })
        if cluster_details:
            stats[f'{feed}_top_st_clusters'] = cluster_details

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '30_creation_clusters.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 30_creation_clusters.png')


def plot_age_vs_followers(df, stats):
    """6. Scatter: eta' account vs followers."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Eta\' Account vs Followers', fontsize=13, fontweight='bold')

    now = datetime.now(timezone.utc)

    for ax, feed, label, color in [
        (axes[0], 'per_te', 'Per Te', ACCENT_1),
        (axes[1], 'seguiti', 'Seguiti', ACCENT_2),
    ]:
        sub = df[(df['feed'] == feed) & (~df['is_estimate'])]
        if sub.empty:
            continue

        ages_years = (now - sub['created_at']).dt.total_seconds() / (86400 * 365.25)
        followers = sub['followers_count'].clip(lower=1)

        ax.scatter(ages_years, followers, alpha=0.3, s=12, color=color, edgecolors='none')
        ax.set_yscale('log')
        ax.set_xlabel('Eta\' account (anni)')
        ax.set_ylabel('Followers (log)')
        ax.set_title(label, fontsize=11)
        ax.grid(True, alpha=0.2)

        # Correlazione
        corr = np.corrcoef(ages_years, np.log10(followers))[0, 1]
        ax.text(0.05, 0.95, f'r = {corr:.3f}', transform=ax.transAxes,
                fontsize=10, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='#1a1a2e', alpha=0.8))
        stats[f'{feed}_age_followers_corr'] = round(float(corr), 4)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '31_age_vs_followers.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 31_age_vs_followers.png')


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print('[*] Estrazione autori da MongoDB con Snowflake ID...')
    df = extract_authors_from_mongo()
    print(f'[+] {len(df)} autori unici estratti')

    # Filtra pre-snowflake per statistiche
    real = df[~df['is_estimate']]
    est = df[df['is_estimate']]
    print(f'    Snowflake reali: {len(real)}, pre-Snowflake (stima): {len(est)}')

    stats = {
        'total_authors': len(df),
        'per_te_authors': len(df[df['feed'] == 'per_te']),
        'seguiti_authors': len(df[df['feed'] == 'seguiti']),
        'snowflake_real': len(real),
        'pre_snowflake': len(est),
    }

    plot_creation_timeline(df, stats)
    plot_dc_wk_heatmap(df, stats)
    plot_sequence_distribution(df, stats)
    plot_account_age(df, stats)
    plot_creation_clusters(df, stats)
    plot_age_vs_followers(df, stats)

    # Serializza per JSON
    for k, v in stats.items():
        if isinstance(v, (np.integer, np.int64)):
            stats[k] = int(v)
        elif isinstance(v, (np.floating, np.float64)):
            stats[k] = float(v)

    with open(os.path.join(OUTPUT_DIR, 'stats_snowflake.json'), 'w') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False, default=str)
    print(f'[✓] Stats salvate in {OUTPUT_DIR}/stats_snowflake.json')


if __name__ == '__main__':
    main()
