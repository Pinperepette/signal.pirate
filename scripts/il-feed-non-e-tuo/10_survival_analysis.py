#!/usr/bin/env python3
"""
10_survival_analysis.py — Survival Analysis: il feed come filtro di sopravvivenza.

Modella il tempo tra created_at e timestamp_collected come tempo di sopravvivenza.
Un tweet "sopravvive" se riesce a comparire nel feed prima di diventare irrilevante.

Calcola:
  1. Curva Kaplan-Meier per feed
  2. Cox Proportional Hazards: quali feature accelerano/ritardano la visibilita'
  3. Hazard ratio per followers, verified, lingua, engagement
  4. Stratificazione per fasce followers

Uso:
    python 10_survival_analysis.py

Output:
    output/48_kaplan_meier.png
    output/49_cox_hazard_ratios.png
    output/50_survival_by_followers.png
    output/51_survival_by_verified.png
    output/stats_survival.json
"""

import json
import os
import numpy as np
import pandas as pd
from datetime import datetime, timezone
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


def extract_survival_data():
    """Estrai dati con latenza e covariate."""
    from pymongo import MongoClient
    client = MongoClient('mongodb://localhost:27017')
    db = client['SnareData']

    rows = []
    for feed_label, coll_name in [('per_te', 'twitter_per-te'), ('seguiti', 'twitter_seguiti')]:
        for doc in db[coll_name].find().limit(800):
            data = doc.get('data', {})
            tweet_data = data.get('data', {})
            legacy = tweet_data.get('legacy', {})
            user = tweet_data.get('core', {}).get('user_results', {}).get('result', {})

            created_at_str = legacy.get('created_at', '')
            timestamp_collected = data.get('timestamp_collected')

            tweet_dt = None
            if created_at_str:
                try:
                    tweet_dt = datetime.strptime(created_at_str, '%a %b %d %H:%M:%S %z %Y')
                except Exception:
                    pass

            collected_dt = None
            if timestamp_collected:
                try:
                    collected_dt = datetime.fromtimestamp(int(timestamp_collected) / 1000.0, tz=timezone.utc)
                except Exception:
                    pass

            if tweet_dt and collected_dt:
                latency_hours = (collected_dt - tweet_dt).total_seconds() / 3600
                if latency_hours < 0:
                    continue

                rows.append({
                    'feed': feed_label,
                    'latency_hours': latency_hours,
                    'followers_count': user.get('legacy', {}).get('followers_count', 0),
                    'is_blue_verified': 1 if user.get('is_blue_verified', False) else 0,
                    'favorite_count': legacy.get('favorite_count', 0),
                    'retweet_count': legacy.get('retweet_count', 0),
                    'reply_count': legacy.get('reply_count', 0),
                    'lang': legacy.get('lang', 'und'),
                    'is_italian': 1 if legacy.get('lang', '') == 'it' else 0,
                    'log_followers': np.log10(max(user.get('legacy', {}).get('followers_count', 0), 1)),
                    'log_likes': np.log10(max(legacy.get('favorite_count', 0), 1)),
                })

    client.close()
    return pd.DataFrame(rows)


def kaplan_meier(times, label=''):
    """Calcola Kaplan-Meier manualmente (tutti osservati, nessuna censura)."""
    times = np.sort(times)
    n = len(times)
    unique_times = np.unique(times)

    survival = []
    n_at_risk = n
    s = 1.0

    for t in unique_times:
        d = np.sum(times == t)
        s *= (1 - d / n_at_risk)
        survival.append((t, s))
        n_at_risk -= d

    return np.array(survival)


def plot_kaplan_meier(df, stats):
    """1. Curva Kaplan-Meier per feed."""
    fig, ax = plt.subplots(figsize=(10, 6))

    for feed, label, color in [('per_te', 'Per Te', ACCENT_1), ('seguiti', 'Seguiti', ACCENT_2)]:
        sub = df[df['feed'] == feed]
        times = sub['latency_hours'].values
        km = kaplan_meier(times)

        ax.step(km[:, 0], km[:, 1], color=color, label=label, linewidth=2, where='post')

        # Tempo mediano di sopravvivenza (S(t) = 0.5)
        idx_50 = np.searchsorted(-km[:, 1], -0.5)
        if idx_50 < len(km):
            median_t = km[idx_50, 0]
            ax.axvline(x=median_t, color=color, linestyle=':', alpha=0.4)
            ax.annotate(f'{median_t:.1f}h', xy=(median_t, 0.5),
                       fontsize=9, color=color,
                       xytext=(median_t + 2, 0.55 if feed == 'per_te' else 0.45),
                       arrowprops=dict(arrowstyle='->', color=color, alpha=0.5))
            stats[f'{feed}_median_survival_hours'] = round(float(median_t), 2)

    ax.set_xlabel('Latenza (ore)')
    ax.set_ylabel('S(t) — Probabilita\' di non essere ancora apparso')
    ax.set_title('Kaplan-Meier: Sopravvivenza dei Tweet\n(quanto tempo prima che il feed li mostri)',
                 fontsize=13, fontweight='bold')
    ax.set_xlim(0, 48)
    ax.axhline(y=0.5, color='#555555', linestyle='--', alpha=0.3)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '48_kaplan_meier.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 48_kaplan_meier.png')


def plot_cox_hazard_ratios(df, stats):
    """2. Cox-like hazard ratios via logistic regression sui quantili di latenza."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    fig, ax = plt.subplots(figsize=(10, 5))

    features = ['log_followers', 'is_blue_verified', 'log_likes', 'is_italian']
    feature_labels = ['log(Followers)', 'Blue Verified', 'log(Like)', 'Italiano']

    all_hrs = {}

    for feed, label, color in [('per_te', 'Per Te', ACCENT_1), ('seguiti', 'Seguiti', ACCENT_2)]:
        sub = df[df['feed'] == feed].copy()

        # Binarizza: tweet "veloci" (sotto mediana) vs "lenti"
        median_lat = sub['latency_hours'].median()
        sub['fast'] = (sub['latency_hours'] <= median_lat).astype(int)

        X = sub[features].values
        y = sub['fast'].values

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        lr = LogisticRegression(max_iter=1000)
        lr.fit(X_scaled, y)

        # Coefficienti come log-hazard ratios (approssimazione)
        hrs = np.exp(lr.coef_[0])
        all_hrs[label] = hrs

        for feat, hr in zip(feature_labels, hrs):
            stats[f'{feed}_hr_{feat.lower().replace("(","").replace(")","").replace(" ","_")}'] = round(float(hr), 4)

    # Plot confronto
    x = np.arange(len(feature_labels))
    width = 0.35

    bars1 = ax.barh(x - width/2, all_hrs['Per Te'], width, label='Per Te',
                     color=ACCENT_1, edgecolor='none')
    bars2 = ax.barh(x + width/2, all_hrs['Seguiti'], width, label='Seguiti',
                     color=ACCENT_2, edgecolor='none')

    ax.axvline(x=1, color='#ffffff', linestyle='--', alpha=0.3, label='HR = 1 (nessun effetto)')

    for bars in [bars1, bars2]:
        for bar in bars:
            val = bar.get_width()
            ax.text(val + 0.02, bar.get_y() + bar.get_height()/2,
                    f'{val:.2f}', va='center', fontsize=8, color='#e0e0e0')

    ax.set_yticks(x)
    ax.set_yticklabels(feature_labels)
    ax.set_xlabel('Hazard Ratio (>1 = appare piu\' velocemente)')
    ax.set_title('Hazard Ratio: Cosa Accelera la Visibilita\'',
                 fontsize=13, fontweight='bold')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '49_cox_hazard_ratios.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 49_cox_hazard_ratios.png')


def plot_survival_by_followers(df, stats):
    """3. Kaplan-Meier stratificata per fascia followers."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Sopravvivenza per Fascia Followers', fontsize=13, fontweight='bold')

    tiers = [
        ('< 1K', 0, 1000, '#ff6b6b'),
        ('1K-10K', 1000, 10000, '#ffd93d'),
        ('10K-100K', 10000, 100000, '#4ecdc4'),
        ('> 100K', 100000, 1e12, '#bb86fc'),
    ]

    for ax, feed, label in [
        (axes[0], 'per_te', 'Per Te'),
        (axes[1], 'seguiti', 'Seguiti'),
    ]:
        sub = df[df['feed'] == feed]

        for tier_name, lo, hi, color in tiers:
            mask = (sub['followers_count'] >= lo) & (sub['followers_count'] < hi)
            times = sub[mask]['latency_hours'].values
            if len(times) < 10:
                continue
            km = kaplan_meier(times)
            ax.step(km[:, 0], km[:, 1], color=color, label=tier_name, linewidth=1.5, where='post')

        ax.set_xlabel('Latenza (ore)')
        ax.set_ylabel('S(t)')
        ax.set_title(label, fontsize=11)
        ax.set_xlim(0, 48)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '50_survival_by_followers.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 50_survival_by_followers.png')


def plot_survival_by_verified(df, stats):
    """4. Kaplan-Meier: verified vs non-verified."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Sopravvivenza: Verified vs Non-Verified', fontsize=13, fontweight='bold')

    for ax, feed, label in [
        (axes[0], 'per_te', 'Per Te'),
        (axes[1], 'seguiti', 'Seguiti'),
    ]:
        sub = df[df['feed'] == feed]

        for verified, vl, color in [(1, 'Blue Verified', '#4ecdc4'), (0, 'Non Verified', '#ff6b6b')]:
            times = sub[sub['is_blue_verified'] == verified]['latency_hours'].values
            if len(times) < 10:
                continue
            km = kaplan_meier(times)
            ax.step(km[:, 0], km[:, 1], color=color, label=vl, linewidth=2, where='post')

        ax.set_xlabel('Latenza (ore)')
        ax.set_ylabel('S(t)')
        ax.set_title(label, fontsize=11)
        ax.set_xlim(0, 48)
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '51_survival_by_verified.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 51_survival_by_verified.png')


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print('[*] Estrazione dati survival...')
    df = extract_survival_data()
    print(f'[+] {len(df)} tweet con latenza valida')

    stats = {}
    plot_kaplan_meier(df, stats)
    plot_cox_hazard_ratios(df, stats)
    plot_survival_by_followers(df, stats)
    plot_survival_by_verified(df, stats)

    with open(os.path.join(OUTPUT_DIR, 'stats_survival.json'), 'w') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f'[✓] Stats salvate in {OUTPUT_DIR}/stats_survival.json')


if __name__ == '__main__':
    main()
