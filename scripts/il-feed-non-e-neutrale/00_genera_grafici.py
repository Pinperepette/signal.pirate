#!/usr/bin/env python3
"""
Genera tutti i grafici per l'articolo "Nature Non È Neutrale"
Dati: replication folder dello studio Zhuravskaya et al. (2026)
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.patches import FancyBboxPatch
from collections import Counter
import warnings
warnings.filterwarnings('ignore')

# === STILE ===
plt.rcParams.update({
    'figure.facecolor': '#0d1117',
    'axes.facecolor': '#0d1117',
    'axes.edgecolor': '#30363d',
    'axes.labelcolor': '#c9d1d9',
    'text.color': '#c9d1d9',
    'xtick.color': '#8b949e',
    'ytick.color': '#8b949e',
    'grid.color': '#21262d',
    'grid.alpha': 0.6,
    'font.family': 'monospace',
    'font.size': 11,
    'figure.dpi': 150,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.3,
})

GREEN = '#00ff88'
RED = '#ff6b6b'
CYAN = '#00d4ff'
ORANGE = '#ff8c00'
PURPLE = '#7c4dff'
YELLOW = '#ffd700'
GRAY = '#8b949e'
WHITE = '#c9d1d9'

OUT = '/Users/pinperepette/Github/blog/immagini/nature-non-e-neutrale'
DATA = 'replication_folder_public_14112025/data'

print('[+] Caricamento dati...')
df = pd.read_stata(f'{DATA}/main_data_and_newsfeed_data.dta')
eval_df = pd.read_csv(f'{DATA}/evaluation_dataset_human_and_llm.csv')
survey_df = pd.read_stata(f'{DATA}/survey_data_and_followings_data.dta')
print(f'    main_data: {df.shape[0]:,} righe, {df.shape[1]} colonne')
print(f'    eval_data: {eval_df.shape[0]} righe')
print(f'    survey_data: {survey_df.shape[0]:,} righe')


# ================================================================
# GRAFICO 01 - Proporzione nel feed: Cons vs Lib vs N/A
# ================================================================
print('[+] Grafico 01: Proporzione nel feed')
fig, ax = plt.subplots(figsize=(10, 6))

feeds = ['Algorithm', 'Chrono']
labels = ['Conservative', 'Liberal', 'Cannot say']
colors = [RED, CYAN, GRAY]

x = np.arange(len(feeds))
width = 0.25

for i, (label, color) in enumerate(zip(labels, colors)):
    vals = []
    for feed in feeds:
        sub = df[df['treat_algo'] == feed]
        pct = (sub['account_slant_llama3'] == label).mean() * 100
        vals.append(pct)
    bars = ax.bar(x + i * width, vals, width, label=label, color=color, alpha=0.85, edgecolor='#30363d')
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f'{v:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold', color=color)

ax.set_xticks(x + width)
ax.set_xticklabels(['Feed Algoritmico', 'Feed Cronologico'], fontsize=13)
ax.set_ylabel('% dei post nel feed', fontsize=12)
ax.set_title('PROPORZIONE PER ORIENTAMENTO NEL FEED\nI conservatori sono MENO presenti nel feed algoritmico',
             fontsize=14, fontweight='bold', color=GREEN)
ax.legend(loc='upper right', fontsize=10)
ax.grid(axis='y', alpha=0.3)
ax.set_ylim(0, 60)

# Annotazione
ax.annotate('Cons: -0.6pp\nLib: +1.7pp', xy=(0.5, 0.85), xycoords='axes fraction',
            fontsize=11, color=YELLOW, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#161b22', edgecolor=YELLOW, alpha=0.9),
            ha='center')

plt.savefig(f'{OUT}/01_proporzione_feed.png')
plt.close()


# ================================================================
# GRAFICO 02 - Engagement mediano per slant
# ================================================================
print('[+] Grafico 02: Engagement per slant')
fig, axes = plt.subplots(1, 3, figsize=(15, 6))

metrics = [('Numberoflikes', 'Likes'), ('Numberofretweets', 'Retweet'), ('Numberofcomments', 'Commenti')]
slants = ['Conservative', 'Liberal', 'Cannot say']
slant_colors = [RED, CYAN, GRAY]

for ax, (col, name) in zip(axes, metrics):
    medians = []
    for slant in slants:
        med = df[df['account_slant_llama3'] == slant][col].median()
        medians.append(med)

    bars = ax.bar(range(3), medians, color=slant_colors, alpha=0.85, edgecolor='#30363d')
    for bar, v, c in zip(bars, medians, slant_colors):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(medians)*0.02,
                f'{v:,.0f}', ha='center', va='bottom', fontsize=11, fontweight='bold', color=c)

    ax.set_xticks(range(3))
    ax.set_xticklabels(['Cons', 'Lib', 'N/A'], fontsize=10)
    ax.set_title(name, fontsize=13, fontweight='bold', color=WHITE)
    ax.grid(axis='y', alpha=0.3)

fig.suptitle('ENGAGEMENT MEDIANO PER ORIENTAMENTO POLITICO (Llama 3)\nIl contenuto conservatore ha 2-3x più interazioni',
             fontsize=14, fontweight='bold', color=GREEN, y=1.02)
plt.tight_layout()
plt.savefig(f'{OUT}/02_engagement_per_slant.png')
plt.close()


# ================================================================
# GRAFICO 03 - Engagement per tipo account
# ================================================================
print('[+] Grafico 03: Engagement per tipo account')
fig, ax = plt.subplots(figsize=(10, 6))

types = ['Official', 'Political activist', 'Entertainment', 'News', 'Other']
type_colors = [PURPLE, RED, ORANGE, CYAN, GRAY]

meds = []
for t in types:
    meds.append(df[df['account_type_llama3'] == t]['Numberoflikes'].median())

bars = ax.barh(range(len(types)), meds, color=type_colors, alpha=0.85, edgecolor='#30363d', height=0.6)
for bar, v, c in zip(bars, meds, type_colors):
    ax.text(v + 20, bar.get_y() + bar.get_height()/2,
            f'{v:,.0f}', va='center', fontsize=12, fontweight='bold', color=c)

ax.set_yticks(range(len(types)))
ax.set_yticklabels(types, fontsize=12)
ax.set_xlabel('Likes mediani', fontsize=12)
ax.set_title('PERCHÉ LE NEWS SCOMPAIONO DAL FEED ALGORITMICO\nNon censura politica. Engagement 16x inferiore.',
             fontsize=14, fontweight='bold', color=GREEN)
ax.grid(axis='x', alpha=0.3)

# Annotazione ratio
ax.annotate('News: 39 likes\nAttivisti: 632 likes\nRatio: 16.2x',
            xy=(0.75, 0.75), xycoords='axes fraction',
            fontsize=11, color=YELLOW, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#161b22', edgecolor=YELLOW, alpha=0.9))

plt.savefig(f'{OUT}/03_engagement_per_tipo.png')
plt.close()


# ================================================================
# GRAFICO 04 - Distribuzione likes (log scale) per slant
# ================================================================
print('[+] Grafico 04: Distribuzione likes')
fig, ax = plt.subplots(figsize=(12, 6))

for slant, color in zip(['Conservative', 'Liberal', 'Cannot say'], [RED, CYAN, GRAY]):
    sub = df[df['account_slant_llama3'] == slant]['Numberoflikes'].dropna()
    sub = sub[sub > 0]
    ax.hist(np.log10(sub), bins=80, alpha=0.5, color=color, label=slant, density=True, edgecolor='none')

ax.set_xlabel('log₁₀(Likes)', fontsize=12)
ax.set_ylabel('Densità', fontsize=12)
ax.set_title('DISTRIBUZIONE LIKES PER ORIENTAMENTO (LOG SCALE)\nI conservatori hanno la coda destra più pesante',
             fontsize=14, fontweight='bold', color=GREEN)
ax.legend(fontsize=11)
ax.grid(alpha=0.3)
plt.savefig(f'{OUT}/04_distribuzione_likes.png')
plt.close()


# ================================================================
# GRAFICO 05 - Engagement algoritmico vs cronologico PER slant
# ================================================================
print('[+] Grafico 05: Algo vs Chrono per slant')
fig, axes = plt.subplots(1, 3, figsize=(15, 6))

for ax, slant, color in zip(axes, ['Conservative', 'Liberal', 'Cannot say'], [RED, CYAN, GRAY]):
    algo_med = df[(df['treat_algo'] == 'Algorithm') & (df['account_slant_llama3'] == slant)]['Numberoflikes'].median()
    chro_med = df[(df['treat_algo'] == 'Chrono') & (df['account_slant_llama3'] == slant)]['Numberoflikes'].median()

    bars = ax.bar(['Algo', 'Chrono'], [algo_med, chro_med], color=[color, color],
                  alpha=0.85, edgecolor='#30363d')
    bars[1].set_alpha(0.4)

    for bar, v in zip(bars, [algo_med, chro_med]):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
                f'{v:,.0f}', ha='center', va='bottom', fontsize=12, fontweight='bold', color=color)

    diff = algo_med - chro_med
    pct = (diff / chro_med) * 100
    sign = '+' if diff > 0 else ''
    ax.set_title(f'{slant}\n{sign}{pct:.1f}%', fontsize=13, fontweight='bold', color=color)
    ax.grid(axis='y', alpha=0.3)

fig.suptitle('LIKES MEDIANI: FEED ALGORITMICO vs CRONOLOGICO\nI conservatori NON vengono amplificati più dei liberali',
             fontsize=14, fontweight='bold', color=GREEN, y=1.02)
plt.tight_layout()
plt.savefig(f'{OUT}/05_algo_vs_chrono_slant.png')
plt.close()


# ================================================================
# GRAFICO 06 - Validazione Llama 3 - Matrice di confusione
# ================================================================
print('[+] Grafico 06: Matrice confusione Llama 3')
fig, ax = plt.subplots(figsize=(8, 7))

human_labels = ['cannot say', 'conservative', 'liberal']
llama_labels = ['Cannot say', 'Conservative', 'Liberal']

matrix = np.zeros((3, 3))
for _, row in eval_df.iterrows():
    h = row['human_average_slant'].lower().strip()
    l = row['account_slant_llama3'].strip()
    if h in human_labels and l in llama_labels:
        hi = human_labels.index(h)
        li = llama_labels.index(l)
        matrix[hi][li] += 1

im = ax.imshow(matrix, cmap='YlOrRd', aspect='auto')
for i in range(3):
    for j in range(3):
        val = int(matrix[i][j])
        color = '#0d1117' if val > 50 else WHITE
        ax.text(j, i, str(val), ha='center', va='center', fontsize=18, fontweight='bold', color=color)

ax.set_xticks(range(3))
ax.set_yticks(range(3))
ax.set_xticklabels(['Cannot say', 'Conservative', 'Liberal'], fontsize=11)
ax.set_yticklabels(['Cannot say', 'Conservative', 'Liberal'], fontsize=11)
ax.set_xlabel('Llama 3', fontsize=13, fontweight='bold', color=PURPLE)
ax.set_ylabel('Annotatori Umani', fontsize=13, fontweight='bold', color=GREEN)
ax.set_title('MATRICE DI CONFUSIONE: LLAMA 3 vs UMANI\nAccuratezza: 80.2% — Il 20% dei post è classificato male',
             fontsize=14, fontweight='bold', color=GREEN)

plt.colorbar(im, ax=ax, shrink=0.8)
plt.savefig(f'{OUT}/06_confusion_matrix.png')
plt.close()


# ================================================================
# GRAFICO 07 - Accordo tra annotatori umani
# ================================================================
print('[+] Grafico 07: Accordo umani')
fig, ax = plt.subplots(figsize=(10, 6))

human_cols = ['account_slant_human_1', 'account_slant_human_2', 'account_slant_human_3', 'account_slant_human_4']
agreement_levels = {'4/4 unanimi': 0, '3/4 maggioranza': 0, '2/2 split': 0}

for _, row in eval_df.iterrows():
    vals = [str(row[c]).lower().strip() for c in human_cols if pd.notna(row[c])]
    counts = Counter(vals)
    max_count = max(counts.values())
    if max_count == 4:
        agreement_levels['4/4 unanimi'] += 1
    elif max_count >= 3:
        agreement_levels['3/4 maggioranza'] += 1
    else:
        agreement_levels['2/2 split'] += 1

cats = list(agreement_levels.keys())
vals = list(agreement_levels.values())
pcts = [v/sum(vals)*100 for v in vals]
bar_colors = [GREEN, ORANGE, RED]

bars = ax.bar(cats, pcts, color=bar_colors, alpha=0.85, edgecolor='#30363d', width=0.5)
for bar, v, p, c in zip(bars, vals, pcts, bar_colors):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
            f'{p:.1f}%\n({v})', ha='center', va='bottom', fontsize=12, fontweight='bold', color=c)

ax.set_ylabel('% dei casi', fontsize=12)
ax.set_title('ACCORDO TRA 4 ANNOTATORI UMANI (500 POST)\nSe gli umani non concordano, perché fidarsi di un LLM?',
             fontsize=14, fontweight='bold', color=GREEN)
ax.grid(axis='y', alpha=0.3)
ax.set_ylim(0, 75)
plt.savefig(f'{OUT}/07_accordo_umani.png')
plt.close()


# ================================================================
# GRAFICO 08 - Effect size a confronto (Cohen's d)
# ================================================================
print('[+] Grafico 08: Effect sizes')
fig, ax = plt.subplots(figsize=(12, 7))

effects = [
    ('Conservative policy\npriorities', 0.111, 0.02, 0.20, RED),
    ('Trump investigations\nunacceptable', 0.083, 0.01, 0.16, RED),
    ('Pro-Kremlin attitudes\nUkraine', 0.123, 0.03, 0.21, RED),
    ('All attitudes PCA', 0.124, 0.03, 0.21, RED),
    ('User engagement\nPCA', 0.140, 0.03, 0.25, ORANGE),
    ('Partisanship &\naff. polarization', -0.004, -0.10, 0.09, GREEN),
    ('Low well-being', 0.033, -0.06, 0.13, GRAY),
]

y_pos = range(len(effects))
for i, (name, est, lo, hi, color) in enumerate(effects):
    ax.errorbar(est, i, xerr=[[est-lo], [hi-est]], fmt='o', color=color,
                markersize=10, capsize=5, linewidth=2, markeredgecolor='white', markeredgewidth=1)
    ax.text(hi + 0.015, i, f'{est:.3f}', va='center', fontsize=10, color=color, fontweight='bold')

ax.axvline(x=0, color=WHITE, linestyle='--', alpha=0.5, linewidth=1)
ax.axvline(x=0.2, color=YELLOW, linestyle=':', alpha=0.4, linewidth=1)
ax.text(0.2, len(effects)-0.3, 'Small effect\n(Cohen)', fontsize=9, color=YELLOW, ha='center', alpha=0.7)

ax.set_yticks(y_pos)
ax.set_yticklabels([e[0] for e in effects], fontsize=10)
ax.set_xlabel('Effect Size (Standard Deviations)', fontsize=12)
ax.set_title('EFFECT SIZES DELLO STUDIO: TUTTI SOTTO "SMALL"\nCI 95% che rasenta lo zero. p-values appena sotto 0.05',
             fontsize=14, fontweight='bold', color=GREEN)
ax.grid(axis='x', alpha=0.3)
ax.set_xlim(-0.2, 0.35)
plt.savefig(f'{OUT}/08_effect_sizes.png')
plt.close()


# ================================================================
# GRAFICO 09 - Campione demografico vs popolazione USA
# ================================================================
print('[+] Grafico 09: Campione vs popolazione')
fig, axes = plt.subplots(1, 3, figsize=(15, 6))

# Razza
ax = axes[0]
cats = ['White', 'Non-White']
sample = [78, 22]
usa = [58, 42]
x = np.arange(2)
bars1 = ax.bar(x - 0.15, sample, 0.3, label='Campione', color=PURPLE, alpha=0.85)
bars2 = ax.bar(x + 0.15, usa, 0.3, label='USA', color=GRAY, alpha=0.6)
for b, v in zip(bars1, sample):
    ax.text(b.get_x()+b.get_width()/2, v+1, f'{v}%', ha='center', fontsize=11, color=PURPLE, fontweight='bold')
for b, v in zip(bars2, usa):
    ax.text(b.get_x()+b.get_width()/2, v+1, f'{v}%', ha='center', fontsize=11, color=GRAY, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(cats)
ax.set_title('Razza', fontsize=13, fontweight='bold')
ax.legend(fontsize=9)
ax.grid(axis='y', alpha=0.3)

# Educazione
ax = axes[1]
cats = ['College 4y+', 'No college']
sample = [58, 42]
usa = [33, 67]
x = np.arange(2)
bars1 = ax.bar(x - 0.15, sample, 0.3, label='Campione', color=PURPLE, alpha=0.85)
bars2 = ax.bar(x + 0.15, usa, 0.3, label='USA', color=GRAY, alpha=0.6)
for b, v in zip(bars1, sample):
    ax.text(b.get_x()+b.get_width()/2, v+1, f'{v}%', ha='center', fontsize=11, color=PURPLE, fontweight='bold')
for b, v in zip(bars2, usa):
    ax.text(b.get_x()+b.get_width()/2, v+1, f'{v}%', ha='center', fontsize=11, color=GRAY, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(cats)
ax.set_title('Educazione', fontsize=13, fontweight='bold')
ax.legend(fontsize=9)
ax.grid(axis='y', alpha=0.3)

# Affiliazione politica
ax = axes[2]
cats = ['Dem', 'Ind', 'Rep']
sample = [46, 30, 21]
usa = [28, 41, 28]
x = np.arange(3)
bars1 = ax.bar(x - 0.15, sample, 0.3, label='Campione', color=PURPLE, alpha=0.85)
bars2 = ax.bar(x + 0.15, usa, 0.3, label='USA (Gallup)', color=GRAY, alpha=0.6)
for b, v in zip(bars1, sample):
    ax.text(b.get_x()+b.get_width()/2, v+1, f'{v}%', ha='center', fontsize=11, color=PURPLE, fontweight='bold')
for b, v in zip(bars2, usa):
    ax.text(b.get_x()+b.get_width()/2, v+1, f'{v}%', ha='center', fontsize=11, color=GRAY, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(cats)
ax.set_title('Affiliazione Politica', fontsize=13, fontweight='bold')
ax.legend(fontsize=9)
ax.grid(axis='y', alpha=0.3)

fig.suptitle('CAMPIONE DELLO STUDIO vs POPOLAZIONE USA\n78% bianchi, 58% laureati, Dem 2:1 vs Rep — non è rappresentativo',
             fontsize=14, fontweight='bold', color=GREEN, y=1.02)
plt.tight_layout()
plt.savefig(f'{OUT}/09_campione_vs_usa.png')
plt.close()


# ================================================================
# GRAFICO 10 - Engagement totale: distribuzione skewed
# ================================================================
print('[+] Grafico 10: Distribuzione engagement')
fig, ax = plt.subplots(figsize=(12, 6))

total_eng = df['Numberoflikes'].fillna(0) + df['Numberofretweets'].fillna(0) + df['Numberofcomments'].fillna(0)
total_eng = total_eng[total_eng > 0]

ax.hist(np.log10(total_eng), bins=100, color=GREEN, alpha=0.7, edgecolor='none')
ax.axvline(np.log10(total_eng.median()), color=YELLOW, linestyle='--', linewidth=2, label=f'Mediana: {total_eng.median():,.0f}')
ax.axvline(np.log10(total_eng.mean()), color=RED, linestyle='--', linewidth=2, label=f'Media: {total_eng.mean():,.0f}')

ax.set_xlabel('log₁₀(Likes + Retweet + Commenti)', fontsize=12)
ax.set_ylabel('Conteggio', fontsize=12)
ax.set_title('DISTRIBUZIONE ENGAGEMENT TOTALE (268K POST)\nMedia 42x la mediana. Pochi post dominano tutto.',
             fontsize=14, fontweight='bold', color=GREEN)
ax.legend(fontsize=11)
ax.grid(alpha=0.3)
plt.savefig(f'{OUT}/10_distribuzione_engagement.png')
plt.close()


# ================================================================
# GRAFICO 11 - Post con engagement alto per slant (%)
# ================================================================
print('[+] Grafico 11: % post alto engagement')
fig, ax = plt.subplots(figsize=(12, 6))

thresholds = [100, 500, 1000, 5000, 10000, 50000]
slants = ['Conservative', 'Liberal', 'Cannot say']
slant_colors = [RED, CYAN, GRAY]

for slant, color in zip(slants, slant_colors):
    sub = df[df['account_slant_llama3'] == slant]
    pcts = []
    for t in thresholds:
        pcts.append((sub['Numberoflikes'] > t).mean() * 100)
    ax.plot(range(len(thresholds)), pcts, 'o-', color=color, label=slant, linewidth=2, markersize=8)

ax.set_xticks(range(len(thresholds)))
ax.set_xticklabels([f'>{t:,}' for t in thresholds], fontsize=10)
ax.set_xlabel('Soglia Likes', fontsize=12)
ax.set_ylabel('% post sopra soglia', fontsize=12)
ax.set_title('% DI POST AD ALTO ENGAGEMENT PER ORIENTAMENTO\nI conservatori hanno più viralità perché sono più provocatori',
             fontsize=14, fontweight='bold', color=GREEN)
ax.legend(fontsize=11)
ax.grid(alpha=0.3)
plt.savefig(f'{OUT}/11_alto_engagement_per_slant.png')
plt.close()


# ================================================================
# GRAFICO 12 - Timeline: dati 2023, paper 2026
# ================================================================
print('[+] Grafico 12: Timeline')
fig, ax = plt.subplots(figsize=(14, 5))

events = [
    ('Ott 2022', 'Musk acquisisce\nTwitter', RED, 0.3),
    ('Mar 2023', 'Algoritmo\nopen source v1', GREEN, 0.6),
    ('Lug 2023', 'Inizio\nesperimento', PURPLE, 0.9),
    ('Set 2023', 'Fine\nesperimento', PURPLE, 0.6),
    ('Nov 2024', 'Elezioni\nUSA 2024', ORANGE, 0.9),
    ('Gen 2026', 'Algoritmo\nopen source v2\n(Grok-based)', GREEN, 0.6),
    ('Feb 2026', 'Paper su\nNature', RED, 0.9),
]

dates_num = [0, 1, 1.7, 2.0, 4.3, 6.5, 7.0]

ax.plot(dates_num, [0]*len(dates_num), '-', color=GRAY, alpha=0.5, linewidth=2)

for (label, desc, color, height), x in zip(events, dates_num):
    ax.plot(x, 0, 'o', color=color, markersize=12, zorder=5)
    direction = 1 if height > 0.7 else -1
    y = height * direction
    ax.annotate(f'{label}\n{desc}', xy=(x, 0), xytext=(x, y),
                fontsize=9, fontweight='bold', color=color, ha='center', va='center',
                arrowprops=dict(arrowstyle='->', color=color, lw=1.5),
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#161b22', edgecolor=color, alpha=0.9))

# Brace per "dati vecchi di 3 anni"
ax.annotate('', xy=(1.7, -1.1), xytext=(7.0, -1.1),
            arrowprops=dict(arrowstyle='<->', color=YELLOW, lw=2))
ax.text(4.35, -1.25, '3 ANNI TRA I DATI E LA PUBBLICAZIONE\n2 aggiornamenti algoritmo nel frattempo',
        fontsize=10, color=YELLOW, ha='center', fontweight='bold')

ax.set_xlim(-0.5, 7.8)
ax.set_ylim(-1.6, 1.4)
ax.axis('off')
ax.set_title('TIMELINE: I DATI SONO OBSOLETI\nL\'algoritmo è cambiato 2 volte da quando lo studio ha raccolto i dati',
             fontsize=14, fontweight='bold', color=GREEN)
plt.savefig(f'{OUT}/12_timeline.png')
plt.close()


# ================================================================
# GRAFICO 13 - Cross-tab: Tipo x Slant nel feed algoritmico
# ================================================================
print('[+] Grafico 13: Heatmap tipo x slant')
fig, ax = plt.subplots(figsize=(10, 7))

algo = df[df['treat_algo'] == 'Algorithm']
types = ['Entertainment', 'Political activist', 'News', 'Official', 'Other']
slants = ['Conservative', 'Liberal', 'Cannot say']

matrix = np.zeros((len(types), len(slants)))
for i, t in enumerate(types):
    for j, s in enumerate(slants):
        matrix[i][j] = ((algo['account_type_llama3'] == t) & (algo['account_slant_llama3'] == s)).sum()

# Normalizza per riga
row_sums = matrix.sum(axis=1, keepdims=True)
matrix_pct = matrix / row_sums * 100

im = ax.imshow(matrix_pct, cmap='magma', aspect='auto')
for i in range(len(types)):
    for j in range(len(slants)):
        val = matrix_pct[i][j]
        n = int(matrix[i][j])
        color = '#0d1117' if val > 50 else WHITE
        ax.text(j, i, f'{val:.1f}%\n({n:,})', ha='center', va='center', fontsize=10, fontweight='bold', color=color)

ax.set_xticks(range(len(slants)))
ax.set_yticks(range(len(types)))
ax.set_xticklabels(slants, fontsize=11)
ax.set_yticklabels(types, fontsize=11)
ax.set_title('COMPOSIZIONE FEED ALGORITMICO: TIPO x ORIENTAMENTO\nL\'entertainment domina. La politica è una frazione.',
             fontsize=14, fontweight='bold', color=GREEN)

plt.colorbar(im, ax=ax, shrink=0.8, label='% del tipo')
plt.savefig(f'{OUT}/13_heatmap_tipo_slant.png')
plt.close()


# ================================================================
# GRAFICO 14 - Errori di Llama 3: dove sbaglia e in che direzione
# ================================================================
print('[+] Grafico 14: Direzione errori Llama 3')
fig, ax = plt.subplots(figsize=(10, 6))

error_types = {
    'Umani: cons\nLlama: cannot say': 0,
    'Umani: cons\nLlama: liberal': 0,
    'Umani: liberal\nLlama: cannot say': 0,
    'Umani: liberal\nLlama: cons': 0,
    'Umani: N/A\nLlama: cons': 0,
    'Umani: N/A\nLlama: liberal': 0,
}

for _, row in eval_df.iterrows():
    h = row['human_average_slant'].lower().strip()
    l = row['account_slant_llama3'].strip().lower()
    if h == 'conservative' and l == 'cannot say':
        error_types['Umani: cons\nLlama: cannot say'] += 1
    elif h == 'conservative' and l == 'liberal':
        error_types['Umani: cons\nLlama: liberal'] += 1
    elif h == 'liberal' and l == 'cannot say':
        error_types['Umani: liberal\nLlama: cannot say'] += 1
    elif h == 'liberal' and l == 'conservative':
        error_types['Umani: liberal\nLlama: cons'] += 1
    elif h == 'cannot say' and l == 'conservative':
        error_types['Umani: N/A\nLlama: cons'] += 1
    elif h == 'cannot say' and l == 'liberal':
        error_types['Umani: N/A\nLlama: liberal'] += 1

cats = list(error_types.keys())
vals = list(error_types.values())
bar_colors = [RED, RED, CYAN, CYAN, ORANGE, ORANGE]

bars = ax.barh(range(len(cats)), vals, color=bar_colors, alpha=0.85, edgecolor='#30363d', height=0.6)
for bar, v, c in zip(bars, vals, bar_colors):
    ax.text(v + 0.5, bar.get_y() + bar.get_height()/2,
            str(v), va='center', fontsize=12, fontweight='bold', color=c)

ax.set_yticks(range(len(cats)))
ax.set_yticklabels(cats, fontsize=10)
ax.set_xlabel('Numero errori (su 500)', fontsize=12)
ax.set_title('DOVE SBAGLIA LLAMA 3: DIREZIONE DEGLI ERRORI\n27 conservatori nascosti, 40 liberali diluiti in "cannot say"',
             fontsize=14, fontweight='bold', color=GREEN)
ax.grid(axis='x', alpha=0.3)
plt.savefig(f'{OUT}/14_errori_llama3.png')
plt.close()


# ================================================================
# GRAFICO 15 - Engagement mediano per tipo+slant (il vero driver)
# ================================================================
print('[+] Grafico 15: Engagement per tipo+slant')
fig, ax = plt.subplots(figsize=(14, 7))

combos = []
meds = []
colors_list = []

for t in ['Political activist', 'News', 'Entertainment']:
    for s, c in [('Conservative', RED), ('Liberal', CYAN)]:
        sub = df[(df['account_type_llama3'] == t) & (df['account_slant_llama3'] == s)]
        combos.append(f'{t[:4]}.\n{s[:4]}.')
        meds.append(sub['Numberoflikes'].median())
        colors_list.append(c)

bars = ax.bar(range(len(combos)), meds, color=colors_list, alpha=0.85, edgecolor='#30363d', width=0.6)
for bar, v, c in zip(bars, meds, colors_list):
    ax.text(bar.get_x() + bar.get_width()/2, v + max(meds)*0.02,
            f'{v:,.0f}', ha='center', va='bottom', fontsize=11, fontweight='bold', color=c)

ax.set_xticks(range(len(combos)))
ax.set_xticklabels(combos, fontsize=9)
ax.set_ylabel('Likes mediani', fontsize=12)
ax.set_title('ENGAGEMENT PER TIPO + ORIENTAMENTO\nGli attivisti conservatori hanno 2.3x i likes degli attivisti liberali',
             fontsize=14, fontweight='bold', color=GREEN)
ax.grid(axis='y', alpha=0.3)

# Separatori verticali per tipo
for x in [1.5, 3.5]:
    ax.axvline(x, color=GRAY, linestyle=':', alpha=0.3)
ax.text(0.5, max(meds)*0.9, 'ATTIVISTI', ha='center', fontsize=10, color=YELLOW, fontweight='bold')
ax.text(2.5, max(meds)*0.9, 'NEWS', ha='center', fontsize=10, color=YELLOW, fontweight='bold')
ax.text(4.5, max(meds)*0.9, 'ENTERTAINMENT', ha='center', fontsize=10, color=YELLOW, fontweight='bold')

plt.savefig(f'{OUT}/15_engagement_tipo_slant.png')
plt.close()


# ================================================================
# GRAFICO 16 - Funnel: 13K → 6K → 5K (dropout massivo)
# ================================================================
print('[+] Grafico 16: Funnel partecipanti')
fig, ax = plt.subplots(figsize=(10, 7))

stages = ['Entrati survey\n(YouGov)', 'Screened\n(attivi X)', 'Consenso\ninformato', 'Pre-treatment\nsurvey', 'Desktop\nusers', 'Chrome\nextension', 'Post-treatment\nsurvey']
values = [13265, 9831, 8363, 6043, 2518, 784, 4965]
bar_colors = [GRAY, GRAY, GRAY, CYAN, ORANGE, RED, GREEN]

bars = ax.barh(range(len(stages)), values, color=bar_colors, alpha=0.85, edgecolor='#30363d', height=0.6)
for bar, v, c in zip(bars, values, bar_colors):
    ax.text(v + 100, bar.get_y() + bar.get_height()/2,
            f'{v:,}', va='center', fontsize=12, fontweight='bold', color=c)

ax.set_yticks(range(len(stages)))
ax.set_yticklabels(stages, fontsize=10)
ax.set_xlabel('Partecipanti', fontsize=12)
ax.set_title('FUNNEL PARTECIPANTI: DA 13K A 784 CON CHROME EXTENSION\nSolo 784 utenti (6%) hanno installato il tracker del feed',
             fontsize=14, fontweight='bold', color=GREEN)
ax.invert_yaxis()
ax.grid(axis='x', alpha=0.3)

# Annotazione
ax.annotate('Solo il 6% dei partecipanti\nha fornito dati reali del feed\n(Chrome extension)',
            xy=(784, 5), xytext=(5000, 5),
            fontsize=11, color=RED, fontweight='bold',
            arrowprops=dict(arrowstyle='->', color=RED, lw=2),
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#161b22', edgecolor=RED, alpha=0.9))

plt.savefig(f'{OUT}/16_funnel_partecipanti.png')
plt.close()


# ================================================================
# GRAFICO 17 - Compliance auto-dichiarata
# ================================================================
print('[+] Grafico 17: Compliance')
fig, ax = plt.subplots(figsize=(10, 6))

compliance_cats = ['Always', 'Most of the time', 'Sometimes', 'Rarely', 'Never']
compliance_vals = [58.09, 27.29, 9.49, 3.85, 1.29]
comp_colors = [GREEN, CYAN, ORANGE, RED, RED]

bars = ax.bar(range(len(compliance_cats)), compliance_vals, color=comp_colors, alpha=0.85,
              edgecolor='#30363d', width=0.6)
for bar, v, c in zip(bars, compliance_vals, comp_colors):
    ax.text(bar.get_x() + bar.get_width()/2, v + 1,
            f'{v:.1f}%', ha='center', va='bottom', fontsize=12, fontweight='bold', color=c)

ax.set_xticks(range(len(compliance_cats)))
ax.set_xticklabels(compliance_cats, fontsize=10)
ax.set_ylabel('% partecipanti', fontsize=12)
ax.set_title('COMPLIANCE AUTO-DICHIARATA\nIl 14.6% ammette di non aver seguito le istruzioni',
             fontsize=14, fontweight='bold', color=GREEN)
ax.grid(axis='y', alpha=0.3)

# Highlight
ax.annotate('14.6% non compliant\n→ auto-dichiarato\n→ il vero dato è peggiore',
            xy=(3, 3.85), xytext=(3.5, 30),
            fontsize=11, color=RED, fontweight='bold',
            arrowprops=dict(arrowstyle='->', color=RED, lw=2),
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#161b22', edgecolor=RED, alpha=0.9))

plt.savefig(f'{OUT}/17_compliance.png')
plt.close()


# ================================================================
# GRAFICO 18 - Extended Data Fig 4: Dem vs Rep breakdown
# ================================================================
print('[+] Grafico 18: Dem vs Rep effect sizes')
fig, axes = plt.subplots(1, 2, figsize=(14, 8))

# Rep + Ind
outcomes_ri = [
    ('Engagement', 0.124, 0.104),
    ('Partisanship', -0.036, 0.476),
    ('Cons. priorities', 0.142, 0.050),
    ('Trump invest.', 0.171, 0.013),
    ('Pro-Kremlin', 0.224, 0.003),
    ('All attitudes', 0.206, 0.006),
    ('Well-being', 0.091, 0.067),
]

ax = axes[0]
for i, (name, est, p) in enumerate(outcomes_ri):
    color = RED if p < 0.05 else GRAY
    marker = 'o' if p < 0.05 else 'x'
    ax.plot(est, i, marker, color=color, markersize=10)
    ax.text(est + 0.02, i, f'{est:.3f} (p={p:.3f})', va='center', fontsize=9, color=color)

ax.axvline(0, color=WHITE, linestyle='--', alpha=0.3)
ax.set_yticks(range(len(outcomes_ri)))
ax.set_yticklabels([o[0] for o in outcomes_ri], fontsize=10)
ax.set_title('Repubblicani + Indipendenti\nChrono → Algo', fontsize=12, fontweight='bold', color=RED)
ax.set_xlim(-0.15, 0.35)
ax.grid(axis='x', alpha=0.3)

# Dem
outcomes_d = [
    ('Engagement', 0.157, 0.065),
    ('Partisanship', 0.009, 0.600),
    ('Cons. priorities', 0.075, 0.164),
    ('Trump invest.', 0, 1),  # insufficient variation
    ('Pro-Kremlin', 0.009, 0.842),
    ('All attitudes', 0.053, 0.238),
    ('Well-being', -0.032, 0.504),
]

ax = axes[1]
for i, (name, est, p) in enumerate(outcomes_d):
    color = RED if p < 0.05 else GRAY
    marker = 'o' if p < 0.05 else 'x'
    ax.plot(est, i, marker, color=color, markersize=10)
    label = 'insuff. var.' if name == 'Trump invest.' else f'{est:.3f} (p={p:.3f})'
    ax.text(est + 0.02, i, label, va='center', fontsize=9, color=color)

ax.axvline(0, color=WHITE, linestyle='--', alpha=0.3)
ax.set_yticks(range(len(outcomes_d)))
ax.set_yticklabels([o[0] for o in outcomes_d], fontsize=10)
ax.set_title('Democratici\nChrono → Algo', fontsize=12, fontweight='bold', color=CYAN)
ax.set_xlim(-0.15, 0.35)
ax.grid(axis='x', alpha=0.3)

fig.suptitle('BREAKDOWN PER PARTITO: I DEMOCRATICI NON MOSTRANO NESSUN EFFETTO\nTutti i p > 0.05. L\'effetto è guidato solo da Repubblicani e Indipendenti.',
             fontsize=13, fontweight='bold', color=GREEN, y=1.02)
plt.tight_layout()
plt.savefig(f'{OUT}/18_dem_vs_rep.png')
plt.close()


# ================================================================
# GRAFICO 19 - Architettura algoritmo: segnali nascosti + predictions
# ================================================================
print('[+] Grafico 19: Architettura algoritmo X')
fig, axes = plt.subplots(1, 2, figsize=(16, 8))

# Pannello sinistro: 7 segnali nascosti di Phoenix (dal codice sorgente)
ax = axes[0]
hidden_signals = [
    ('dwellTimeMs', 'continuo (ms)', 'Tempo fermo sul post'),
    ('isDetailExpanded', 'binario', 'Ha espanso il thread'),
    ('isPhotoExpanded', 'binario', 'Ha allargato la foto'),
    ('isVideoPlayback50', 'binario', 'Ha visto 50%+ del video'),
    ('isProfileClicked', 'binario', 'Ha visitato il profilo'),
    ('isBookmarked', 'binario', 'Ha salvato il post'),
    ('isOpenLinked', 'binario', 'Ha cliccato link esterno'),
]

sig_colors_list = [GREEN, CYAN, CYAN, CYAN, PURPLE, ORANGE, RED]
y_positions = range(len(hidden_signals))

for i, ((name, stype, desc), color) in enumerate(zip(hidden_signals, sig_colors_list)):
    ax.barh(i, 1, color=color, alpha=0.7, edgecolor='#30363d', height=0.6)
    weight_label = 'NEGATIVO' if name == 'isOpenLinked' else ''
    ax.text(0.05, i, f'{name}', va='center', fontsize=10, fontweight='bold', color='#0d1117')
    ax.text(1.05, i, f'{desc}', va='center', fontsize=9, color=color)

ax.set_yticks([])
ax.set_xticks([])
ax.set_xlim(0, 2.5)
ax.set_title('7 SEGNALI NASCOSTI DI PHOENIX\n(dal codice sorgente)', fontsize=12, fontweight='bold', color=GREEN)

# Annotazione isOpenLinked
ax.annotate('PESO NEGATIVO\nLink esterno = utente esce\n= revenue persa',
            xy=(1, 6), xytext=(1.5, 5),
            fontsize=9, color=RED, fontweight='bold',
            arrowprops=dict(arrowstyle='->', color=RED, lw=1.5),
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#161b22', edgecolor=RED, alpha=0.9))

# Pannello destro: 15 prediction targets del transformer
ax = axes[1]
predictions = [
    ('P(favorite)', GREEN),
    ('P(reply)', GREEN),
    ('P(repost)', GREEN),
    ('P(quote)', GREEN),
    ('P(click)', CYAN),
    ('P(profile_click)', CYAN),
    ('P(video_view)', CYAN),
    ('P(photo_expand)', CYAN),
    ('P(share)', CYAN),
    ('P(dwell)', PURPLE),
    ('P(follow_author)', PURPLE),
    ('P(not_interested)', RED),
    ('P(block_author)', RED),
    ('P(mute_author)', RED),
    ('P(report)', RED),
]

for i, (name, color) in enumerate(predictions):
    weight_sign = '-' if color == RED else '+'
    ax.barh(i, 1, color=color, alpha=0.6, edgecolor='#30363d', height=0.55)
    ax.text(0.05, i, name, va='center', fontsize=9, fontweight='bold', color='#0d1117')
    ax.text(1.05, i, f'weight: {weight_sign}', va='center', fontsize=9, color=color, fontweight='bold')

ax.set_yticks([])
ax.set_xticks([])
ax.set_xlim(0, 2)
ax.set_title('15 PREDICTION TARGETS\nScore = Σ(weight × P(action))', fontsize=12, fontweight='bold', color=GREEN)
ax.invert_yaxis()

# Annotazione
ax.annotate('Zero classificazione politica\nSolo probabilità di interazione',
            xy=(0.5, 0.95), xycoords='axes fraction',
            fontsize=10, color=YELLOW, fontweight='bold', ha='center',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#161b22', edgecolor=YELLOW, alpha=0.9))

fig.suptitle('ARCHITETTURA DELL\'ALGORITMO X (CODICE SORGENTE)\nMisura quanto stai fermo, cosa espandi, cosa allarghi. Non cosa pensi.',
             fontsize=14, fontweight='bold', color=GREEN, y=1.02)
plt.tight_layout()
plt.savefig(f'{OUT}/19_pesi_algoritmo.png')
plt.close()


# ================================================================
# GRAFICO 20 - Il vero split: Entertainment domina tutto
# ================================================================
print('[+] Grafico 20: Composizione feed per tipo')
fig, axes = plt.subplots(1, 2, figsize=(14, 7))

for ax, feed, title in zip(axes, ['Algorithm', 'Chrono'], ['Feed Algoritmico', 'Feed Cronologico']):
    sub = df[df['treat_algo'] == feed]
    type_counts = sub['account_type_llama3'].value_counts()
    total = len(sub)

    types_ordered = ['Entertainment', 'Political activist', 'News', 'Official', 'Other']
    t_colors = [ORANGE, RED, CYAN, PURPLE, GRAY]
    sizes = [type_counts.get(t, 0)/total*100 for t in types_ordered]

    wedges, texts, autotexts = ax.pie(sizes, labels=types_ordered, colors=t_colors,
                                       autopct='%1.1f%%', startangle=90, textprops={'fontsize': 10},
                                       pctdistance=0.75)
    for t in autotexts:
        t.set_color(WHITE)
        t.set_fontweight('bold')
    ax.set_title(title, fontsize=13, fontweight='bold', color=WHITE)

fig.suptitle('COMPOSIZIONE DEL FEED PER TIPO DI ACCOUNT\nL\'entertainment è quasi la metà. La politica è una bolla nella bolla.',
             fontsize=14, fontweight='bold', color=GREEN, y=1.02)
plt.tight_layout()
plt.savefig(f'{OUT}/20_composizione_tipo.png')
plt.close()


print(f'\n[+] Tutti i grafici salvati in {OUT}/')
print(f'[+] Totale: 20 grafici')
