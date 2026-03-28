#!/usr/bin/env python3
"""
02_analisi_sentiment.py — Confronto sentiment ed emozioni tra feed.

Legge i CSV prodotti da 00_extract.py e analizza:
  1. Distribuzione sentiment (Positivo/Negativo/Neutro/Misto)
  2. Distribuzione emozioni (top emozioni per feed)
  3. Distribuzione intensita' (Bassa/Media/Alta)
  4. Heatmap emozioni x intensita'

Uso:
    python 02_analisi_sentiment.py

Output:
    output/06_sentiment_comparison.png
    output/07_emotions_comparison.png
    output/08_intensity_comparison.png
    output/09_emotion_intensity_heatmap.png
    output/stats_sentiment.json
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
OUTPUT_DIR = 'output'
DATA_DIR = 'data'


def load_feeds():
    pt = pd.read_csv(os.path.join(DATA_DIR, 'per_te.csv'))
    sg = pd.read_csv(os.path.join(DATA_DIR, 'seguiti.csv'))
    return pt, sg


def explode_emotions(df):
    """Espandi il campo emotions (pipe-separated) in righe singole."""
    emotions = df['emotions'].dropna().str.split('|').explode()
    emotions = emotions[emotions != '']
    return emotions


def plot_sentiment(pt, sg, stats):
    """1. Distribuzione sentiment."""
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    fig.suptitle('Distribuzione Sentiment', fontsize=13, fontweight='bold')

    all_sentiments = sorted(set(
        pt['sentiment'].dropna().unique().tolist() +
        sg['sentiment'].dropna().unique().tolist()
    ))

    for ax, df, label, color in [
        (axes[0], pt, 'Per Te', ACCENT_1),
        (axes[1], sg, 'Seguiti', ACCENT_2),
    ]:
        counts = df['sentiment'].value_counts()
        counts = counts.reindex(all_sentiments, fill_value=0)
        pct = counts / len(df) * 100

        bars = ax.bar(counts.index, pct.values, color=color, edgecolor='none')
        ax.set_title(label, fontsize=11)
        ax.set_ylabel('%')
        ax.tick_params(axis='x', rotation=30)

        for bar, val in zip(bars, pct.values):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                        f'{val:.1f}%', ha='center', fontsize=8, color='#e0e0e0')

        for s in all_sentiments:
            stats[f'{label.lower().replace(" ", "_")}_{s.lower()}_pct'] = round(
                counts.get(s, 0) / len(df) * 100, 2
            )

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '06_sentiment_comparison.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 06_sentiment_comparison.png')


def plot_emotions(pt, sg, stats):
    """2. Top emozioni per feed."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle('Top 12 Emozioni', fontsize=13, fontweight='bold')

    for ax, df, label, color in [
        (axes[0], pt, 'Per Te', ACCENT_1),
        (axes[1], sg, 'Seguiti', ACCENT_2),
    ]:
        emotions = explode_emotions(df)
        top = emotions.value_counts().head(12)
        pct = top / len(df) * 100

        ax.barh(top.index[::-1], pct.values[::-1], color=color, edgecolor='none')
        ax.set_xlabel('% tweet (un tweet puo\' avere piu\' emozioni)')
        ax.set_title(label, fontsize=11)

        stats[f'{label.lower().replace(" ", "_")}_top_emotion'] = top.index[0]
        stats[f'{label.lower().replace(" ", "_")}_n_unique_emotions'] = int(emotions.nunique())

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '07_emotions_comparison.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 07_emotions_comparison.png')


def plot_intensity(pt, sg, stats):
    """3. Distribuzione intensita'."""
    fig, ax = plt.subplots(figsize=(8, 4))

    intensity_order = ['Bassa', 'Media', 'Alta']
    x = np.arange(len(intensity_order))
    width = 0.35

    for i, (df, label, color) in enumerate([
        (pt, 'Per Te', ACCENT_1),
        (sg, 'Seguiti', ACCENT_2),
    ]):
        counts = df['intensity'].value_counts()
        vals = [counts.get(k, 0) / len(df) * 100 for k in intensity_order]
        bars = ax.bar(x + i * width, vals, width, label=label, color=color, edgecolor='none')

        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                    f'{val:.1f}%', ha='center', fontsize=9, color='#e0e0e0')

        for k, v in zip(intensity_order, vals):
            stats[f'{label.lower().replace(" ", "_")}_{k.lower()}_pct'] = round(v, 2)

    ax.set_xticks(x + width / 2)
    ax.set_xticklabels(intensity_order)
    ax.set_ylabel('%')
    ax.set_title('Distribuzione Intensita\' Emotiva', fontsize=13, fontweight='bold')
    ax.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '08_intensity_comparison.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 08_intensity_comparison.png')


def plot_emotion_intensity_heatmap(pt, sg, stats):
    """4. Heatmap: emozione x intensita' — delta tra Per Te e Seguiti."""
    intensity_order = ['Bassa', 'Media', 'Alta']

    def build_matrix(df):
        rows = []
        for _, row in df.iterrows():
            if pd.isna(row['emotions']) or pd.isna(row['intensity']):
                continue
            for emo in str(row['emotions']).split('|'):
                if emo:
                    rows.append({'emotion': emo, 'intensity': row['intensity']})
        if not rows:
            return pd.DataFrame()
        tmp = pd.DataFrame(rows)
        ct = pd.crosstab(tmp['emotion'], tmp['intensity'])
        ct = ct.reindex(columns=intensity_order, fill_value=0)
        return ct / ct.values.sum() * 100

    mat_pt = build_matrix(pt)
    mat_sg = build_matrix(sg)

    # Unisci le emozioni presenti in entrambi
    all_emotions = sorted(set(mat_pt.index.tolist() + mat_sg.index.tolist()))
    mat_pt = mat_pt.reindex(all_emotions, fill_value=0)
    mat_sg = mat_sg.reindex(all_emotions, fill_value=0)

    delta = mat_pt - mat_sg  # positivo = piu' nel "Per Te"

    # Top 15 emozioni per delta assoluto
    delta['abs_sum'] = delta[intensity_order].abs().sum(axis=1)
    top_emotions = delta.nlargest(15, 'abs_sum').index.tolist()
    delta_top = delta.loc[top_emotions, intensity_order]

    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(delta_top.values, cmap='RdBu_r', aspect='auto',
                   vmin=-delta_top.values.max(), vmax=delta_top.values.max())

    ax.set_xticks(range(len(intensity_order)))
    ax.set_xticklabels(intensity_order)
    ax.set_yticks(range(len(top_emotions)))
    ax.set_yticklabels(top_emotions)
    ax.set_title('Delta Emozione x Intensita\'\n(rosso = piu\' in Per Te, blu = piu\' in Seguiti)',
                 fontsize=11, fontweight='bold')

    for i in range(len(top_emotions)):
        for j in range(len(intensity_order)):
            val = delta_top.values[i, j]
            ax.text(j, i, f'{val:+.1f}%', ha='center', va='center',
                    fontsize=8, color='white' if abs(val) > 1 else '#888888')

    fig.colorbar(im, ax=ax, label='Delta %', shrink=0.8)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '09_emotion_intensity_heatmap.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 09_emotion_intensity_heatmap.png')


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    pt, sg = load_feeds()

    stats = {}
    plot_sentiment(pt, sg, stats)
    plot_emotions(pt, sg, stats)
    plot_intensity(pt, sg, stats)
    plot_emotion_intensity_heatmap(pt, sg, stats)

    with open(os.path.join(OUTPUT_DIR, 'stats_sentiment.json'), 'w') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f'[✓] Stats salvate in {OUTPUT_DIR}/stats_sentiment.json')


if __name__ == '__main__':
    main()
