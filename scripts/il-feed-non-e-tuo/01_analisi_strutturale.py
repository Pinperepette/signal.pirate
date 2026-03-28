#!/usr/bin/env python3
"""
01_analisi_strutturale.py — Confronto strutturale tra i due feed.

Legge i CSV prodotti da 00_extract.py e calcola:
  1. % post da account non seguiti (following=False)
  2. Distribuzione temporale (gap tra post)
  3. % account blue verified
  4. Concentrazione autori (top N account per feed)
  5. Distribuzione lingua

Uso:
    python 01_analisi_strutturale.py

Output:
    output/01_following_ratio.png
    output/02_temporal_distribution.png
    output/03_verified_ratio.png
    output/04_author_concentration.png
    output/05_language_distribution.png
    output/stats_strutturali.json
"""

import json
import os
import pandas as pd
import numpy as np
from datetime import datetime
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

ACCENT_1 = '#ff6b6b'   # per te
ACCENT_2 = '#4ecdc4'   # seguiti
OUTPUT_DIR = 'output'
DATA_DIR = 'data'


def load_feeds():
    pt = pd.read_csv(os.path.join(DATA_DIR, 'per_te.csv'))
    sg = pd.read_csv(os.path.join(DATA_DIR, 'seguiti.csv'))
    return pt, sg


def parse_dates(df):
    """Parsa created_at di Twitter in datetime."""
    df['dt'] = pd.to_datetime(
        df['created_at'],
        format='%a %b %d %H:%M:%S %z %Y',
        errors='coerce'
    )
    return df


def plot_following_ratio(pt, sg, stats):
    """1. % post da account che segui vs non segui."""
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    fig.suptitle('Post da account seguiti vs non seguiti', fontsize=13, fontweight='bold')

    for ax, df, label, color in [
        (axes[0], pt, 'Per Te', ACCENT_1),
        (axes[1], sg, 'Seguiti', ACCENT_2),
    ]:
        following = df['following'].sum()
        not_following = len(df) - following
        pct_following = following / len(df) * 100
        pct_not = not_following / len(df) * 100

        bars = ax.bar(['Seguiti', 'Non seguiti'], [pct_following, pct_not],
                       color=[color, '#555555'], edgecolor='none')
        ax.set_title(label, fontsize=11)
        ax.set_ylabel('%')
        ax.set_ylim(0, 105)
        for bar, val in zip(bars, [pct_following, pct_not]):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5,
                    f'{val:.1f}%', ha='center', fontsize=10, color='#e0e0e0')

        stats[f'{label.lower().replace(" ", "_")}_following_pct'] = round(pct_following, 2)
        stats[f'{label.lower().replace(" ", "_")}_not_following_pct'] = round(pct_not, 2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '01_following_ratio.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 01_following_ratio.png')


def plot_temporal_distribution(pt, sg, stats):
    """2. Distribuzione temporale: ore del giorno dei tweet mostrati."""
    fig, ax = plt.subplots(figsize=(10, 4))

    for df, label, color in [(pt, 'Per Te', ACCENT_1), (sg, 'Seguiti', ACCENT_2)]:
        hours = df['dt'].dropna().dt.hour
        counts = hours.value_counts().reindex(range(24), fill_value=0)
        counts_norm = counts / counts.sum() * 100
        ax.plot(counts_norm.index, counts_norm.values, color=color, label=label,
                linewidth=2, marker='o', markersize=3)

    ax.set_xlabel('Ora del giorno (UTC)')
    ax.set_ylabel('% tweet')
    ax.set_title('Distribuzione oraria dei tweet', fontsize=13, fontweight='bold')
    ax.set_xticks(range(0, 24, 2))
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Calcola deviazione dalla cronologia: std delle differenze temporali
    for df, label in [(pt, 'per_te'), (sg, 'seguiti')]:
        dts = df['dt'].dropna().sort_values()
        if len(dts) > 1:
            gaps = dts.diff().dt.total_seconds().dropna()
            stats[f'{label}_median_gap_sec'] = round(gaps.median(), 1)
            stats[f'{label}_mean_gap_sec'] = round(gaps.mean(), 1)
            stats[f'{label}_std_gap_sec'] = round(gaps.std(), 1)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '02_temporal_distribution.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 02_temporal_distribution.png')


def plot_verified_ratio(pt, sg, stats):
    """3. % blue verified per feed."""
    fig, ax = plt.subplots(figsize=(6, 4))

    pct_pt = pt['is_blue_verified'].sum() / len(pt) * 100
    pct_sg = sg['is_blue_verified'].sum() / len(sg) * 100

    bars = ax.bar(['Per Te', 'Seguiti'], [pct_pt, pct_sg],
                   color=[ACCENT_1, ACCENT_2], edgecolor='none', width=0.5)
    for bar, val in zip(bars, [pct_pt, pct_sg]):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f'{val:.1f}%', ha='center', fontsize=11, color='#e0e0e0')

    ax.set_ylabel('% tweet da account verificati')
    ax.set_title('Blue Verified nei due feed', fontsize=13, fontweight='bold')
    ax.set_ylim(0, max(pct_pt, pct_sg) * 1.3)

    stats['per_te_verified_pct'] = round(pct_pt, 2)
    stats['seguiti_verified_pct'] = round(pct_sg, 2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '03_verified_ratio.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 03_verified_ratio.png')


def plot_author_concentration(pt, sg, stats):
    """4. Concentrazione autori: curva cumulativa dei top autori."""
    fig, ax = plt.subplots(figsize=(10, 4))

    for df, label, color in [(pt, 'Per Te', ACCENT_1), (sg, 'Seguiti', ACCENT_2)]:
        author_counts = df['screen_name'].value_counts()
        cumulative = author_counts.values.cumsum() / author_counts.values.sum() * 100
        x = np.arange(1, len(cumulative) + 1)
        ax.plot(x, cumulative, color=color, label=label, linewidth=2)

        # Quanti autori servono per il 50% dei tweet
        idx_50 = np.searchsorted(cumulative, 50) + 1
        stats[f'{label.lower().replace(" ", "_")}_authors_for_50pct'] = int(idx_50)
        stats[f'{label.lower().replace(" ", "_")}_unique_authors'] = len(author_counts)
        stats[f'{label.lower().replace(" ", "_")}_top1_author'] = author_counts.index[0]
        stats[f'{label.lower().replace(" ", "_")}_top1_count'] = int(author_counts.iloc[0])

    ax.set_xlabel('Numero autori (ordinati per frequenza)')
    ax.set_ylabel('% cumulativa tweet')
    ax.set_title('Concentrazione autori', fontsize=13, fontweight='bold')
    ax.axhline(y=50, color='#555555', linestyle='--', alpha=0.5)
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '04_author_concentration.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 04_author_concentration.png')


def plot_language_distribution(pt, sg, stats):
    """5. Distribuzione lingue."""
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    fig.suptitle('Distribuzione lingue', fontsize=13, fontweight='bold')

    for ax, df, label, color in [
        (axes[0], pt, 'Per Te', ACCENT_1),
        (axes[1], sg, 'Seguiti', ACCENT_2),
    ]:
        lang_counts = df['lang'].value_counts().head(8)
        lang_pct = lang_counts / len(df) * 100

        ax.barh(lang_counts.index[::-1], lang_pct.values[::-1],
                color=color, edgecolor='none')
        ax.set_xlabel('%')
        ax.set_title(label, fontsize=11)

        stats[f'{label.lower().replace(" ", "_")}_top_lang'] = lang_counts.index[0]
        stats[f'{label.lower().replace(" ", "_")}_top_lang_pct'] = round(lang_pct.iloc[0], 2)
        stats[f'{label.lower().replace(" ", "_")}_n_langs'] = int(df['lang'].nunique())

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '05_language_distribution.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 05_language_distribution.png')


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    pt, sg = load_feeds()
    pt = parse_dates(pt)
    sg = parse_dates(sg)

    stats = {
        'per_te_count': len(pt),
        'seguiti_count': len(sg),
    }

    plot_following_ratio(pt, sg, stats)
    plot_temporal_distribution(pt, sg, stats)
    plot_verified_ratio(pt, sg, stats)
    plot_author_concentration(pt, sg, stats)
    plot_language_distribution(pt, sg, stats)

    with open(os.path.join(OUTPUT_DIR, 'stats_strutturali.json'), 'w') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f'[✓] Stats salvate in {OUTPUT_DIR}/stats_strutturali.json')


if __name__ == '__main__':
    main()
