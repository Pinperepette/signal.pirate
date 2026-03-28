#!/usr/bin/env python3
"""
05_analisi_topic_hashtag.py — Analisi argomenti e hashtag tra feed.

Legge i CSV prodotti da 00_extract.py e analizza:
  1. Topic modeling con TF-IDF + KMeans clustering
  2. Top hashtag per feed e overlap
  3. Word cloud dei termini piu' frequenti (bar chart)
  4. KL divergence sulle distribuzioni topic

Uso:
    python 05_analisi_topic_hashtag.py

Output:
    output/17_topic_clusters.png
    output/18_hashtag_comparison.png
    output/19_top_terms.png
    output/20_topic_kl_divergence.png
    output/stats_topic.json
"""

import json
import os
import re
import pandas as pd
import numpy as np
from collections import Counter

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

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
N_CLUSTERS = 8

# Stop words IT + EN minimali (no dipendenze esterne)
STOP_WORDS = set("""
a about above after again against all am an and any are as at be because been
before being below between both but by can could did do does doing down during
each few for from further get got had has have having he her here hers herself
him himself his how i if in into is it its itself just let like me more most
my myself no nor not now of off on once only or other our ours ourselves out
over own re s same she should so some such t than that the their theirs them
themselves then there these they this those through to too under until up us
very was we were what when where which while who whom why will with would you
your yours yourself yourselves
a al alla alle allo anche che chi ci come con cosa da dal dalla dalle dallo
dei del della delle dello di dove e era erano esse essere fatto fra gli ha
hai hanno ho i il in io la le lei lo loro lui ma me mi mia mie miei mio
molto molta nei nel nella nelle nello no noi non nostra nostre nostri nostro
o ogni per piu poco prima quale quando quello questa queste questi questo qui
se si sia siamo siete solo sono sta state stati stato su sua sue sui sul
sulla sulle sullo suo suoi tra tu tua tue tuoi tuo tutti tutto un una uno
vi voi vostra vostre vostri vostro gia puo cosi ancora gia mai sempre solo
essere avere fare dire andare potere volere dovere sapere vedere dare stare
dopo poi dove come quando perche quindi anche dove pero
rt https http co www via ed ne se
""".split())


def clean_text(text):
    """Pulisci testo tweet per analisi."""
    if pd.isna(text):
        return ''
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'@\w+', '', text)
    text = re.sub(r'#(\w+)', r'\1', text)  # tieni il testo dell'hashtag
    text = re.sub(r'&amp;', ' ', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\d+', '', text)
    text = text.lower().strip()
    words = [w for w in text.split() if w not in STOP_WORDS and len(w) > 2]
    return ' '.join(words)


def load_feeds():
    pt = pd.read_csv(os.path.join(DATA_DIR, 'per_te.csv'))
    sg = pd.read_csv(os.path.join(DATA_DIR, 'seguiti.csv'))
    return pt, sg


def topic_modeling(pt, sg, stats):
    """1. TF-IDF + KMeans su tutti i tweet, poi distribuzione cluster per feed."""
    pt_clean = pt['full_text'].apply(clean_text)
    sg_clean = sg['full_text'].apply(clean_text)

    all_texts = pd.concat([pt_clean, sg_clean], ignore_index=True)
    labels = ['per_te'] * len(pt) + ['seguiti'] * len(sg)

    # Filtra testi vuoti
    mask = all_texts.str.len() > 0
    all_texts = all_texts[mask]
    labels = [l for l, m in zip(labels, mask) if m]

    vectorizer = TfidfVectorizer(max_features=2000, min_df=3, max_df=0.8)
    tfidf = vectorizer.fit_transform(all_texts)

    km = KMeans(n_clusters=N_CLUSTERS, random_state=42, n_init=10)
    clusters = km.fit_predict(tfidf)

    # Termini top per cluster
    terms = vectorizer.get_feature_names_out()
    cluster_terms = {}
    for i in range(N_CLUSTERS):
        center = km.cluster_centers_[i]
        top_idx = center.argsort()[-5:][::-1]
        cluster_terms[i] = [terms[j] for j in top_idx]

    # Distribuzione cluster per feed
    pt_clusters = [c for c, l in zip(clusters, labels) if l == 'per_te']
    sg_clusters = [c for c, l in zip(clusters, labels) if l == 'seguiti']

    pt_dist = Counter(pt_clusters)
    sg_dist = Counter(sg_clusters)

    # ── Plot 1: distribuzione cluster ──
    fig, ax = plt.subplots(figsize=(12, 5))
    x = np.arange(N_CLUSTERS)
    width = 0.35

    pt_vals = [pt_dist.get(i, 0) / len(pt_clusters) * 100 for i in range(N_CLUSTERS)]
    sg_vals = [sg_dist.get(i, 0) / len(sg_clusters) * 100 for i in range(N_CLUSTERS)]

    ax.bar(x - width/2, pt_vals, width, label='Per Te', color=ACCENT_1, edgecolor='none')
    ax.bar(x + width/2, sg_vals, width, label='Seguiti', color=ACCENT_2, edgecolor='none')

    cluster_labels = [', '.join(cluster_terms[i][:3]) for i in range(N_CLUSTERS)]
    ax.set_xticks(x)
    ax.set_xticklabels(cluster_labels, rotation=35, ha='right', fontsize=8)
    ax.set_ylabel('% tweet')
    ax.set_title(f'Distribuzione Topic ({N_CLUSTERS} cluster KMeans su TF-IDF)',
                 fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '17_topic_clusters.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 17_topic_clusters.png')

    # ── Plot 4: PCA 2D dei cluster ──
    pca = PCA(n_components=2, random_state=42)
    coords = pca.fit_transform(tfidf.toarray())

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle('Topic nello spazio PCA', fontsize=13, fontweight='bold')

    pt_mask = [l == 'per_te' for l in labels]
    sg_mask = [l == 'seguiti' for l in labels]

    for ax, mask, label, color in [
        (axes[0], pt_mask, 'Per Te', ACCENT_1),
        (axes[1], sg_mask, 'Seguiti', ACCENT_2),
    ]:
        m = np.array(mask)
        ax.scatter(coords[m, 0], coords[m, 1], c=np.array(clusters)[m],
                   cmap='Set2', alpha=0.3, s=5, edgecolors='none')
        ax.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)')
        ax.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)')
        ax.set_title(label)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '20_topic_pca.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 20_topic_pca.png')

    # KL divergence topic
    eps = 1e-10
    p = np.array(pt_vals) + eps
    q = np.array(sg_vals) + eps
    p = p / p.sum()
    q = q / q.sum()
    kl = float(np.sum(p * np.log2(p / q)))
    stats['kl_topic_pt_vs_sg'] = round(kl, 6)
    stats['cluster_terms'] = {str(k): v for k, v in cluster_terms.items()}

    for i in range(N_CLUSTERS):
        stats[f'per_te_cluster_{i}_pct'] = round(pt_vals[i], 2)
        stats[f'seguiti_cluster_{i}_pct'] = round(sg_vals[i], 2)

    return vectorizer, all_texts


def hashtag_analysis(pt, sg, stats):
    """2. Confronto hashtag."""
    def get_hashtags(df):
        all_h = []
        for h in df['hashtags'].dropna():
            for tag in str(h).split('|'):
                if tag:
                    all_h.append(tag.lower())
        return Counter(all_h)

    ht_pt = get_hashtags(pt)
    ht_sg = get_hashtags(sg)

    stats['per_te_tweets_with_hashtags'] = int((pt['hashtags'].fillna('') != '').sum())
    stats['seguiti_tweets_with_hashtags'] = int((sg['hashtags'].fillna('') != '').sum())
    stats['per_te_unique_hashtags'] = len(ht_pt)
    stats['seguiti_unique_hashtags'] = len(ht_sg)

    # Overlap
    common = set(ht_pt.keys()) & set(ht_sg.keys())
    all_tags = set(ht_pt.keys()) | set(ht_sg.keys())
    jaccard = len(common) / len(all_tags) if all_tags else 0
    stats['hashtag_jaccard_similarity'] = round(jaccard, 4)
    stats['hashtag_common_count'] = len(common)

    # Solo nel Per Te / solo nei Seguiti
    only_pt = set(ht_pt.keys()) - set(ht_sg.keys())
    only_sg = set(ht_sg.keys()) - set(ht_pt.keys())
    stats['hashtag_only_per_te'] = len(only_pt)
    stats['hashtag_only_seguiti'] = len(only_sg)

    # Plot
    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    fig.suptitle('Top 15 Hashtag', fontsize=13, fontweight='bold')

    for ax, ht, label, color in [
        (axes[0], ht_pt, 'Per Te', ACCENT_1),
        (axes[1], ht_sg, 'Seguiti', ACCENT_2),
    ]:
        top = ht.most_common(15)
        if not top:
            ax.set_title(f'{label}\n(nessun hashtag)')
            continue
        tags, counts = zip(*top)
        ax.barh(list(tags)[::-1], list(counts)[::-1], color=color, edgecolor='none')
        ax.set_xlabel('Occorrenze')
        ax.set_title(label, fontsize=11)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '18_hashtag_comparison.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 18_hashtag_comparison.png')


def top_terms_analysis(pt, sg, stats):
    """3. Termini piu' frequenti per feed (dopo pulizia)."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    fig.suptitle('Top 20 Termini (TF-IDF pesati)', fontsize=13, fontweight='bold')

    for ax, df, label, color in [
        (axes[0], pt, 'Per Te', ACCENT_1),
        (axes[1], sg, 'Seguiti', ACCENT_2),
    ]:
        texts = df['full_text'].apply(clean_text)
        texts = texts[texts.str.len() > 0]

        vec = TfidfVectorizer(max_features=500, min_df=2, max_df=0.8)
        tfidf = vec.fit_transform(texts)
        terms = vec.get_feature_names_out()

        # Media TF-IDF per termine
        mean_tfidf = np.array(tfidf.mean(axis=0)).flatten()
        top_idx = mean_tfidf.argsort()[-20:][::-1]

        top_terms = [terms[i] for i in top_idx]
        top_vals = [mean_tfidf[i] for i in top_idx]

        ax.barh(top_terms[::-1], top_vals[::-1], color=color, edgecolor='none')
        ax.set_xlabel('TF-IDF medio')
        ax.set_title(label, fontsize=11)

        stats[f'{label.lower().replace(" ", "_")}_top5_terms'] = top_terms[:5]

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '19_top_terms.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 19_top_terms.png')


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    pt, sg = load_feeds()

    stats = {}
    topic_modeling(pt, sg, stats)
    hashtag_analysis(pt, sg, stats)
    top_terms_analysis(pt, sg, stats)

    with open(os.path.join(OUTPUT_DIR, 'stats_topic.json'), 'w') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f'[✓] Stats salvate in {OUTPUT_DIR}/stats_topic.json')


if __name__ == '__main__':
    main()
