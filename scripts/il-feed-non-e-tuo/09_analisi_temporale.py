#!/usr/bin/env python3
"""
09_analisi_temporale.py — Analisi temporale profonda: quando i tweet arrivano nel feed.

Estrae da MongoDB sia created_at (quando il tweet e' stato scritto)
sia timestamp_collected (quando e' apparso nel feed durante lo scroll).

Calcola:
  1. Span temporale: i primi 800 tweet coprono quante ore/giorni?
  2. Latenza: delta tra created_at e timestamp_collected (quanto vecchio
     e' un tweet quando l'algoritmo te lo mostra)
  3. Distribuzione latenza per feed — CDF e istogramma
  4. Ordine cronologico: quanto e' "ordinato" il feed?
     (Kendall tau vs ordine cronologico perfetto)
  5. Scatter: posizione nello scroll vs eta' del tweet
  6. Heatmap: ora di creazione vs latenza
  7. Decadimento: come la latenza cambia man mano che scrolli
  8. Freshness score: % tweet < 1h, < 6h, < 24h, < 7gg

Uso:
    python 09_analisi_temporale.py

Output:
    output/40_time_span.png
    output/41_latency_distribution.png
    output/42_latency_cdf.png
    output/43_chronological_order.png
    output/44_scroll_vs_age.png
    output/45_hour_vs_latency.png
    output/46_latency_decay.png
    output/47_freshness_bars.png
    output/stats_temporale.json
"""

import json
import os
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from scipy import stats as scipy_stats

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


def extract_temporal_data():
    """Estrai dati temporali da MongoDB con entrambi i timestamp."""
    from pymongo import MongoClient
    client = MongoClient('mongodb://localhost:27017')
    db = client['SnareData']

    rows = []
    for feed_label, coll_name in [('per_te', 'twitter_per-te'), ('seguiti', 'twitter_seguiti')]:
        for i, doc in enumerate(db[coll_name].find().limit(800)):
            data = doc.get('data', {})
            tweet_data = data.get('data', {})
            legacy = tweet_data.get('legacy', {})
            user = tweet_data.get('core', {}).get('user_results', {}).get('result', {})
            screen_name = user.get('core', {}).get('screen_name', '')

            created_at_str = legacy.get('created_at', '')
            timestamp_collected = data.get('timestamp_collected')

            # Parse created_at del tweet
            tweet_dt = None
            if created_at_str:
                try:
                    tweet_dt = datetime.strptime(created_at_str, '%a %b %d %H:%M:%S %z %Y')
                except Exception:
                    pass

            # Parse timestamp_collected (epoch ms)
            collected_dt = None
            if timestamp_collected:
                try:
                    ts = int(timestamp_collected)
                    collected_dt = datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc)
                except Exception:
                    pass

            if tweet_dt and collected_dt:
                latency_sec = (collected_dt - tweet_dt).total_seconds()
                rows.append({
                    'feed': feed_label,
                    'scroll_position': i,
                    'screen_name': screen_name,
                    'tweet_id': legacy.get('id_str', ''),
                    'created_at': tweet_dt,
                    'collected_at': collected_dt,
                    'latency_sec': latency_sec,
                    'latency_hours': latency_sec / 3600,
                    'latency_days': latency_sec / 86400,
                    'tweet_hour': tweet_dt.hour,
                    'favorite_count': legacy.get('favorite_count', 0),
                })

    client.close()
    return pd.DataFrame(rows)


def plot_time_span(df, stats):
    """1. Span temporale coperto dai tweet in ciascun feed."""
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=False)
    fig.suptitle('Span Temporale: Quanto Indietro Va il Feed?', fontsize=14, fontweight='bold')

    for ax, feed, label, color in [
        (axes[0], 'per_te', 'Per Te', ACCENT_1),
        (axes[1], 'seguiti', 'Seguiti', ACCENT_2),
    ]:
        sub = df[df['feed'] == feed].sort_values('scroll_position')
        if sub.empty:
            continue

        dates = sub['created_at']
        span_hours = (dates.max() - dates.min()).total_seconds() / 3600
        span_days = span_hours / 24

        # Plot: tweet nel tempo (istogramma orario)
        hours_ago = (sub['collected_at'].iloc[0] - dates).dt.total_seconds() / 3600
        bins = np.linspace(0, hours_ago.max(), 50)
        ax.hist(hours_ago, bins=bins, color=color, edgecolor='none', alpha=0.8)
        ax.set_ylabel('Tweet')
        ax.set_xlabel('Ore fa (rispetto all\'inizio dello scroll)')
        ax.set_title(f'{label} — span: {span_hours:.1f} ore ({span_days:.1f} giorni)',
                     fontsize=11)
        ax.axvline(x=hours_ago.median(), color='white', linestyle='--', alpha=0.5,
                   label=f'mediana: {hours_ago.median():.1f}h')
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.2)

        stats[f'{feed}_span_hours'] = round(span_hours, 1)
        stats[f'{feed}_span_days'] = round(span_days, 2)
        stats[f'{feed}_oldest_tweet_hours_ago'] = round(float(hours_ago.max()), 1)
        stats[f'{feed}_newest_tweet_hours_ago'] = round(float(hours_ago.min()), 2)
        stats[f'{feed}_median_age_hours'] = round(float(hours_ago.median()), 2)

        # Quando e' iniziato e finito lo scroll
        scroll_start = sub['collected_at'].min()
        scroll_end = sub['collected_at'].max()
        scroll_duration = (scroll_end - scroll_start).total_seconds()
        stats[f'{feed}_scroll_duration_sec'] = round(scroll_duration, 1)
        stats[f'{feed}_scroll_start'] = scroll_start.isoformat()
        stats[f'{feed}_scroll_end'] = scroll_end.isoformat()

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '40_time_span.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 40_time_span.png')


def plot_latency_distribution(df, stats):
    """2. Distribuzione latenza (quanto vecchio e' un tweet quando te lo mostra)."""
    fig, ax = plt.subplots(figsize=(12, 5))

    for feed, label, color in [('per_te', 'Per Te', ACCENT_1), ('seguiti', 'Seguiti', ACCENT_2)]:
        sub = df[df['feed'] == feed]
        latency = sub['latency_hours'].clip(lower=0)

        # Usa log per visualizzare meglio
        bins = np.logspace(-2, np.log10(max(latency.max(), 1)), 50)
        ax.hist(latency, bins=bins, alpha=0.5, color=color, label=label, density=True)

        stats[f'{feed}_latency_median_hours'] = round(float(latency.median()), 2)
        stats[f'{feed}_latency_mean_hours'] = round(float(latency.mean()), 2)
        stats[f'{feed}_latency_p90_hours'] = round(float(latency.quantile(0.9)), 2)
        stats[f'{feed}_latency_p99_hours'] = round(float(latency.quantile(0.99)), 2)
        stats[f'{feed}_latency_min_min'] = round(float(latency.min() * 60), 1)

    ax.set_xscale('log')
    ax.set_xlabel('Latenza (ore, scala log)')
    ax.set_ylabel('Densita\'')
    ax.set_title('Distribuzione Latenza: Quanto Vecchio E\' un Tweet Quando Lo Vedi',
                 fontsize=13, fontweight='bold')

    # Etichette asse X leggibili
    ax.set_xticks([0.01, 0.1, 1, 6, 24, 168, 720])
    ax.set_xticklabels(['36s', '6min', '1h', '6h', '1g', '1sett', '1mese'])
    ax.legend()
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '41_latency_distribution.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 41_latency_distribution.png')


def plot_latency_cdf(df, stats):
    """3. CDF latenza — a che punto hai visto il 50%/90% dei tweet."""
    fig, ax = plt.subplots(figsize=(10, 6))

    for feed, label, color in [('per_te', 'Per Te', ACCENT_1), ('seguiti', 'Seguiti', ACCENT_2)]:
        sub = df[df['feed'] == feed]
        latency = np.sort(sub['latency_hours'].clip(lower=0).values)
        cdf = np.arange(1, len(latency) + 1) / len(latency)

        ax.plot(latency, cdf, color=color, label=label, linewidth=2)

        # Trova il punto al 50% e 90%
        idx_50 = np.searchsorted(cdf, 0.5)
        idx_90 = np.searchsorted(cdf, 0.9)
        if idx_50 < len(latency):
            ax.axvline(x=latency[idx_50], color=color, linestyle=':', alpha=0.5)
        if idx_90 < len(latency):
            ax.axvline(x=latency[idx_90], color=color, linestyle='--', alpha=0.3)

    ax.set_xscale('log')
    ax.set_xlabel('Latenza (ore)')
    ax.set_ylabel('CDF (% tweet visti)')
    ax.set_title('CDF Latenza — Quanto Tempo Prima Che il Tweet Ti Arrivi',
                 fontsize=13, fontweight='bold')
    ax.set_xticks([0.01, 0.1, 1, 6, 24, 168, 720])
    ax.set_xticklabels(['36s', '6min', '1h', '6h', '1g', '1sett', '1mese'])
    ax.axhline(y=0.5, color='#555555', linestyle='--', alpha=0.3, label='50%')
    ax.axhline(y=0.9, color='#555555', linestyle=':', alpha=0.3, label='90%')
    ax.legend()
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '42_latency_cdf.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 42_latency_cdf.png')


def plot_chronological_order(df, stats):
    """4. Quanto e' cronologico il feed? Kendall tau."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Ordine Cronologico: Il Feed Rispetta il Tempo?',
                 fontsize=13, fontweight='bold')

    for ax, feed, label, color in [
        (axes[0], 'per_te', 'Per Te', ACCENT_1),
        (axes[1], 'seguiti', 'Seguiti', ACCENT_2),
    ]:
        sub = df[df['feed'] == feed].sort_values('scroll_position')
        if sub.empty:
            continue

        positions = sub['scroll_position'].values
        timestamps = sub['created_at'].astype(np.int64).values

        # Kendall tau: 1 = perfettamente cronologico inverso (piu' recente prima)
        # -1 = perfettamente anti-cronologico
        tau, p_value = scipy_stats.kendalltau(positions, -timestamps)

        stats[f'{feed}_kendall_tau'] = round(float(tau), 4)
        stats[f'{feed}_kendall_pvalue'] = float(p_value)

        # Plot: posizione scroll vs timestamp
        hours_from_newest = (sub['created_at'].max() - sub['created_at']).dt.total_seconds() / 3600

        ax.scatter(positions, hours_from_newest, alpha=0.2, s=5, color=color, edgecolors='none')
        ax.set_xlabel('Posizione nello scroll (0 = primo tweet)')
        ax.set_ylabel('Ore dal tweet piu\' recente')
        ax.set_title(f'{label}\nKendall τ = {tau:.3f} (1 = cronologico perfetto)',
                     fontsize=10)
        ax.grid(True, alpha=0.2)

        # Linea di tendenza
        z = np.polyfit(positions, hours_from_newest, 1)
        p = np.poly1d(z)
        x_line = np.linspace(positions.min(), positions.max(), 100)
        ax.plot(x_line, p(x_line), color='white', linewidth=1.5, alpha=0.6, linestyle='--')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '43_chronological_order.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 43_chronological_order.png')


def plot_scroll_vs_age(df, stats):
    """5. Scroll position vs latenza — l'algoritmo ti mostra roba piu' vecchia man mano che scrolli?"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Posizione Scroll vs Latenza del Tweet',
                 fontsize=13, fontweight='bold')

    for ax, feed, label, color in [
        (axes[0], 'per_te', 'Per Te', ACCENT_1),
        (axes[1], 'seguiti', 'Seguiti', ACCENT_2),
    ]:
        sub = df[df['feed'] == feed]
        if sub.empty:
            continue

        ax.scatter(sub['scroll_position'], sub['latency_hours'].clip(lower=0.01),
                   alpha=0.2, s=5, color=color, edgecolors='none')
        ax.set_yscale('log')
        ax.set_xlabel('Posizione nello scroll')
        ax.set_ylabel('Latenza (ore, log)')
        ax.set_title(label, fontsize=11)
        ax.set_yticks([0.01, 0.1, 1, 6, 24, 168])
        ax.set_yticklabels(['36s', '6min', '1h', '6h', '1g', '1sett'])
        ax.grid(True, alpha=0.2)

        # Rolling median
        window = 50
        sub_sorted = sub.sort_values('scroll_position')
        rolling_med = sub_sorted['latency_hours'].rolling(window, center=True).median()
        ax.plot(sub_sorted['scroll_position'], rolling_med,
                color='white', linewidth=2, alpha=0.7, label=f'mediana mobile ({window})')
        ax.legend(fontsize=8)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '44_scroll_vs_age.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 44_scroll_vs_age.png')


def plot_hour_vs_latency(df, stats):
    """6. Heatmap: ora di creazione tweet vs latenza."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Ora di Creazione vs Latenza', fontsize=13, fontweight='bold')

    latency_buckets = [
        ('<1h', 0, 1),
        ('1-6h', 1, 6),
        ('6-24h', 6, 24),
        ('1-7g', 24, 168),
        ('>7g', 168, 99999),
    ]

    for ax, feed, label, cmap in [
        (axes[0], 'per_te', 'Per Te', 'Reds'),
        (axes[1], 'seguiti', 'Seguiti', 'Blues'),
    ]:
        sub = df[df['feed'] == feed]
        if sub.empty:
            continue

        matrix = np.zeros((len(latency_buckets), 24))
        for _, row in sub.iterrows():
            hour = int(row['tweet_hour'])
            lat = row['latency_hours']
            for bi, (bname, blo, bhi) in enumerate(latency_buckets):
                if blo <= lat < bhi:
                    matrix[bi, hour] += 1
                    break

        # Normalizza per colonna
        col_sums = matrix.sum(axis=0, keepdims=True)
        col_sums[col_sums == 0] = 1
        matrix_pct = matrix / col_sums * 100

        im = ax.imshow(matrix_pct, cmap=cmap, aspect='auto', interpolation='nearest')
        ax.set_xticks(range(0, 24, 3))
        ax.set_xlabel('Ora creazione tweet (UTC)')
        ax.set_yticks(range(len(latency_buckets)))
        ax.set_yticklabels([b[0] for b in latency_buckets])
        ax.set_title(label, fontsize=11)
        fig.colorbar(im, ax=ax, label='%', shrink=0.8)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '45_hour_vs_latency.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 45_hour_vs_latency.png')


def plot_latency_decay(df, stats):
    """7. Come la latenza mediana cambia man mano che scrolli (bucket di 100 tweet)."""
    fig, ax = plt.subplots(figsize=(10, 5))

    bucket_size = 50

    for feed, label, color in [('per_te', 'Per Te', ACCENT_1), ('seguiti', 'Seguiti', ACCENT_2)]:
        sub = df[df['feed'] == feed].sort_values('scroll_position')
        if sub.empty:
            continue

        medians = []
        positions = []
        for start in range(0, len(sub), bucket_size):
            chunk = sub.iloc[start:start + bucket_size]
            if len(chunk) < 10:
                break
            medians.append(chunk['latency_hours'].median())
            positions.append(chunk['scroll_position'].median())

        ax.plot(positions, medians, color=color, label=label, linewidth=2, marker='o', markersize=4)

    ax.set_xlabel('Posizione nello scroll')
    ax.set_ylabel('Latenza mediana (ore)')
    ax.set_title('Decadimento della Freschezza: Piu\' Scrolli, Piu\' Vecchio',
                 fontsize=13, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '46_latency_decay.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 46_latency_decay.png')


def plot_freshness(df, stats):
    """8. Freshness score: % tweet per fascia di latenza."""
    fig, ax = plt.subplots(figsize=(10, 5))

    buckets = [
        ('< 1 ora', 0, 1),
        ('1-6 ore', 1, 6),
        ('6-24 ore', 6, 24),
        ('1-3 giorni', 24, 72),
        ('3-7 giorni', 72, 168),
        ('> 7 giorni', 168, 999999),
    ]

    x = np.arange(len(buckets))
    width = 0.35

    for i, (feed, label, color) in enumerate([
        ('per_te', 'Per Te', ACCENT_1),
        ('seguiti', 'Seguiti', ACCENT_2),
    ]):
        sub = df[df['feed'] == feed]
        vals = []
        for bname, blo, bhi in buckets:
            mask = (sub['latency_hours'] >= blo) & (sub['latency_hours'] < bhi)
            pct = mask.sum() / len(sub) * 100
            vals.append(pct)
            stats[f'{feed}_{bname.replace(" ", "_").replace("<", "lt").replace(">", "gt")}_pct'] = round(pct, 2)

        bars = ax.bar(x + i * width, vals, width, label=label, color=color, edgecolor='none')
        for bar, val in zip(bars, vals):
            if val > 1:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                        f'{val:.0f}%', ha='center', fontsize=8, color='#e0e0e0')

    ax.set_xticks(x + width / 2)
    ax.set_xticklabels([b[0] for b in buckets], fontsize=9)
    ax.set_ylabel('% tweet')
    ax.set_title('Freshness: Quanto Sono Freschi i Tweet nel Feed',
                 fontsize=13, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '47_freshness_bars.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 47_freshness_bars.png')


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print('[*] Estrazione dati temporali da MongoDB...')
    df = extract_temporal_data()
    print(f'[+] {len(df)} tweet con entrambi i timestamp')
    print(f'    Per Te: {len(df[df["feed"] == "per_te"])}, Seguiti: {len(df[df["feed"] == "seguiti"])}')

    # Filtra latenze negative (tweet del futuro, errori)
    negative = (df['latency_sec'] < 0).sum()
    if negative > 0:
        print(f'[!] {negative} tweet con latenza negativa (rimossi)')
        df = df[df['latency_sec'] >= 0]

    stats = {
        'total_tweets': len(df),
        'per_te_tweets': len(df[df['feed'] == 'per_te']),
        'seguiti_tweets': len(df[df['feed'] == 'seguiti']),
    }

    plot_time_span(df, stats)
    plot_latency_distribution(df, stats)
    plot_latency_cdf(df, stats)
    plot_chronological_order(df, stats)
    plot_scroll_vs_age(df, stats)
    plot_hour_vs_latency(df, stats)
    plot_latency_decay(df, stats)
    plot_freshness(df, stats)

    # Serializza
    for k, v in list(stats.items()):
        if isinstance(v, (np.integer, np.int64)):
            stats[k] = int(v)
        elif isinstance(v, (np.floating, np.float64)):
            stats[k] = float(v)

    with open(os.path.join(OUTPUT_DIR, 'stats_temporale.json'), 'w') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f'[✓] Stats salvate in {OUTPUT_DIR}/stats_temporale.json')


if __name__ == '__main__':
    main()
