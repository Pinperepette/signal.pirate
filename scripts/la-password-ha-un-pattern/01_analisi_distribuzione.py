#!/usr/bin/env python3
"""
01_analisi_distribuzione.py
Analisi della distribuzione delle password nel dataset RockYou.

Uso:
    python 01_analisi_distribuzione.py [percorso_wordlist]

Se non viene fornito un file, usa le statistiche note di RockYou
per generare un dataset sintetico rappresentativo.

Output:
    output/01_distribuzione_lunghezze.png
    output/02_top30_password.png
    output/03_composizione_charset.png
    output/stats_distribuzione.json
"""

import sys
import os
import json
import math
from collections import Counter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

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

# ── Top 200 password reali da RockYou (documentate pubblicamente) ──
ROCKYOU_TOP200 = [
    '123456', '12345', '123456789', 'password', 'iloveyou',
    'princess', '1234567', 'rockyou', '12345678', 'abc123',
    'nicole', 'daniel', 'babygirl', 'monkey', 'lovely',
    'jessica', '654321', 'michael', 'ashley', 'qwerty',
    '111111', 'iloveu', '000000', 'michelle', 'tigger',
    'sunshine', 'chocolate', 'password1', 'soccer', 'anthony',
    'friends', 'butterfly', 'purple', 'angel', 'jordan',
    'liverpool', 'justin', 'loveme', '123123', 'football',
    'secret', 'andrea', 'carlos', 'jennifer', 'joshua',
    'bubbles', '1234567890', 'superman', 'hannah', 'amanda',
    'loveyou', 'pretty', 'basketball', 'andrew', 'angels',
    'tweety', 'flower', 'playboy', 'hello', 'elizabeth',
    'hottie', 'tinkerbell', 'charlie', 'samantha', 'barbie',
    'chelsea', 'lovers', 'teamo', 'jasmine', 'brandon',
    'rachel', 'summer', 'abcdef', 'harley', '123456a',
    'matthew', 'buster', 'jenny', 'dragon', 'robert',
    'starwars', 'thomas', 'george', 'sexy', 'love123',
    'shadow', 'master', 'qwerty123', 'kitty', 'jesus',
    'peanut', 'trustno1', 'corvette', 'blondie', 'midnight',
    '0987654321', 'ginger', '22222', 'hunter', 'cutiepie',
    'pepper', 'letmein', 'freedom', 'computer', 'love',
    'sunshine1', 'soccer1', 'flower1', 'tigger1', 'princess1',
    'morgan', 'diamond', '121212', 'blink182', 'whatever',
    'nicole1', 'junior', 'mike', 'orange', 'lucky',
    'sparky', 'pumpkin', 'smokey', 'angel1', 'asshole',
    'chicken', 'maggie', 'hockey', 'cheese', 'killer',
    'mother', 'bailey', 'dakota', 'alex', 'maria',
    'taylor', 'pass', 'rangers', 'eminem', 'banana',
    'yankees', 'nathan', 'forever', 'summer1', 'alexis',
    'cookie', 'money', 'merlin', 'sammy', 'lovely1',
    'brittany', 'patrick', 'william', 'victoria', 'swimming',
    'matrix', 'yellow', 'steven', 'testing', 'scooter',
    'thunder', 'turtle', 'blowme', 'asdfgh', 'james',
    'samsung', 'melissa', '212121', 'purple1', 'panther',
    'wolf', 'paradise', 'pokemon', 'creative', 'jasmine1',
    'richard', 'david', 'scott', 'heaven', 'crystal',
    'soccer2', 'batman', 'peter', 'mustang', 'johnson',
    'cancer', 'robert1', 'prince', 'london', 'denise',
    'destiny', 'christian', 'beach', 'jackson', 'guitar',
    'fisher', 'golfer', 'love12', 'cassie', 'pookie',
]

# ── Statistiche reali documentate di RockYou ──
ROCKYOU_STATS = {
    'total': 32603388,
    'unique': 14344391,
    'length_distribution': {
        1: 0.001, 2: 0.005, 3: 0.015, 4: 0.042, 5: 0.068,
        6: 0.201, 7: 0.189, 8: 0.224, 9: 0.128, 10: 0.072,
        11: 0.028, 12: 0.014, 13: 0.006, 14: 0.004, 15: 0.003,
    },
    'top1_pct': 0.91,     # "123456" = ~290k su 32M
    'top10_pct': 2.85,
    'top100_pct': 6.24,
    'top1000_pct': 11.82,
    'only_lower_pct': 42.0,
    'only_digits_pct': 28.0,
    'lower_digits_pct': 18.0,
    'has_upper_pct': 8.0,
    'has_special_pct': 3.5,
    'other_pct': 0.5,
}


def classifica_charset(pwd):
    """Classifica una password per composizione caratteri."""
    has_lower = any(c.islower() for c in pwd)
    has_upper = any(c.isupper() for c in pwd)
    has_digit = any(c.isdigit() for c in pwd)
    has_special = any(not c.isalnum() for c in pwd)

    if has_lower and not has_upper and not has_digit and not has_special:
        return 'solo_lower'
    elif has_digit and not has_lower and not has_upper and not has_special:
        return 'solo_digits'
    elif has_lower and has_digit and not has_upper and not has_special:
        return 'lower+digits'
    elif has_upper and (has_lower or has_digit):
        if has_special:
            return 'ha_speciali'
        return 'ha_upper'
    elif has_special:
        return 'ha_speciali'
    return 'altro'


def entropia_shannon(pwd):
    """Calcola l'entropia di Shannon per singola password."""
    if len(pwd) == 0:
        return 0.0
    freq = Counter(pwd)
    n = len(pwd)
    return -sum((c / n) * math.log2(c / n) for c in freq.values())


def carica_wordlist(path):
    """Carica password da file. Supporta formato 'count password' (rockyou-withcount)
    e formato semplice (una password per riga)."""
    passwords = []
    is_counted = False

    with open(path, 'r', encoding='latin-1', errors='ignore') as f:
        # Leggi prima riga per capire il formato
        first = f.readline()
        f.seek(0)
        stripped = first.lstrip()
        if stripped and stripped[0].isdigit() and len(stripped.split(None, 1)) == 2:
            try:
                int(stripped.split(None, 1)[0])
                is_counted = True
            except ValueError:
                pass

        if is_counted:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(None, 1)
                if len(parts) == 2:
                    try:
                        count = int(parts[0])
                        pwd = parts[1]
                        # Espandi: aggiungi la password 'count' volte
                        passwords.extend([pwd] * count)
                    except ValueError:
                        continue
        else:
            for line in f:
                pwd = line.strip()
                if pwd:
                    passwords.append(pwd)
    return passwords


def carica_wordlist_conteggi(path):
    """Carica password con conteggi. Restituisce lista di (password, count).
    Per il formato 'count password'. Se il formato e' semplice, count=1."""
    result = []
    with open(path, 'r', encoding='latin-1', errors='ignore') as f:
        first = f.readline()
        f.seek(0)
        stripped = first.lstrip()
        is_counted = False
        if stripped and stripped[0].isdigit() and len(stripped.split(None, 1)) == 2:
            try:
                int(stripped.split(None, 1)[0])
                is_counted = True
            except ValueError:
                pass

        if is_counted:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(None, 1)
                if len(parts) == 2:
                    try:
                        count = int(parts[0])
                        pwd = parts[1]
                        result.append((pwd, count))
                    except ValueError:
                        continue
        else:
            counts = Counter()
            for line in f:
                pwd = line.strip()
                if pwd:
                    counts[pwd] += 1
            result = [(pwd, c) for pwd, c in counts.most_common()]
    return result


def genera_dataset_sintetico(n=500000):
    """Genera dataset sintetico basato sulle statistiche RockYou."""
    import random
    random.seed(42)

    passwords = []
    dist = ROCKYOU_STATS['length_distribution']
    lengths = list(dist.keys())
    weights = list(dist.values())

    # 30% dalle top 200 reali (con frequenze decrescenti)
    n_top = int(n * 0.30)
    top_weights = [1.0 / (i + 1) ** 0.8 for i in range(len(ROCKYOU_TOP200))]
    total_w = sum(top_weights)
    top_weights = [w / total_w for w in top_weights]

    for _ in range(n_top):
        passwords.append(random.choices(ROCKYOU_TOP200, weights=top_weights, k=1)[0])

    # 28% solo cifre
    n_digits = int(n * 0.15)
    for _ in range(n_digits):
        l = random.choices(lengths, weights=weights, k=1)[0]
        passwords.append(''.join(random.choices('0123456789', k=l)))

    # 25% solo lowercase
    n_lower = int(n * 0.25)
    common_words = [
        'love', 'baby', 'angel', 'star', 'cool', 'sexy', 'sweet',
        'hot', 'pink', 'blue', 'red', 'king', 'queen', 'rock',
        'fire', 'ice', 'moon', 'sun', 'dark', 'wolf', 'bear',
    ]
    for _ in range(n_lower):
        base = random.choice(common_words)
        suffix = random.choice(['', 'y', 'ie', 's', 'er', 'man', 'girl', 'boy'])
        passwords.append(base + suffix)

    # 20% lower + digits (pattern comune: parola + numeri)
    n_mixed = int(n * 0.20)
    for _ in range(n_mixed):
        base = random.choice(common_words + ROCKYOU_TOP200[:50])
        num = random.choice(['1', '12', '123', '21', '13', '69', '07', '99', '01', '11', '22', '2'])
        passwords.append(base + num)

    # 10% con maiuscole
    n_upper = int(n * 0.10)
    for _ in range(n_upper):
        base = random.choice(common_words)
        passwords.append(base.capitalize() + str(random.randint(1, 999)))

    random.shuffle(passwords)
    return passwords


def plot_distribuzione_lunghezze(pwd_counts, total, outdir):
    """Grafico 01: distribuzione delle lunghezze.
    pwd_counts: lista di (password, count)."""
    len_counter = Counter()
    for pwd, count in pwd_counts:
        len_counter[len(pwd)] += count

    x = sorted(len_counter.keys())
    x = [l for l in x if l <= 20]
    y = [len_counter.get(l, 0) for l in x]
    total_y = sum(y)
    y_pct = [v / total_y * 100 for v in y]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(x, y_pct, color='#00ff88', alpha=0.85, edgecolor='#00cc6a', linewidth=0.5)

    peak = x[y_pct.index(max(y_pct))]
    for bar, xi, yi in zip(bars, x, y_pct):
        if xi == peak:
            bar.set_color('#ff6b6b')
            bar.set_edgecolor('#cc4444')
        ax.text(xi, yi + 0.5, f'{yi:.1f}%', ha='center', va='bottom',
                fontsize=7, color='#e0e0e0', fontfamily='monospace')

    ax.set_xlabel('Lunghezza password')
    ax.set_ylabel('Percentuale (%)')
    ax.set_title(f'Distribuzione lunghezze — picco a {peak} caratteri', fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(outdir, '01_distribuzione_lunghezze.png'), dpi=150)
    plt.close()
    print(f'  [+] 01_distribuzione_lunghezze.png — picco: {peak} caratteri')
    return peak


def plot_top30(pwd_counts, total, outdir):
    """Grafico 02: top 30 password piu' usate.
    pwd_counts: lista di (password, count), gia' ordinata per count desc."""
    top30 = pwd_counts[:30]

    labels = [p for p, _ in top30]
    values = [c for _, c in top30]
    pcts = [v / total * 100 for v in values]

    fig, ax = plt.subplots(figsize=(10, 7))
    colors = ['#ff6b6b' if i < 3 else '#ff8800' if i < 10 else '#00ff88' for i in range(30)]
    bars = ax.barh(range(29, -1, -1), pcts, color=colors, alpha=0.85, height=0.7)

    for i, (bar, label, pct) in enumerate(zip(bars, reversed(labels), reversed(pcts))):
        ax.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height() / 2,
                f'{pct:.2f}%', va='center', fontsize=7, color='#8888aa', fontfamily='monospace')

    ax.set_yticks(range(30))
    ax.set_yticklabels(reversed(labels), fontsize=8)
    ax.set_xlabel('Percentuale del dataset (%)')
    ax.set_title('Top 30 password — le solite sospette', fontsize=13, fontweight='bold')
    ax.grid(axis='x', alpha=0.3)

    top10_pct = sum(pcts[:10])
    ax.text(0.98, 0.02, f'Top 10 = {top10_pct:.1f}% del dataset',
            transform=ax.transAxes, ha='right', va='bottom',
            fontsize=9, color='#ff6b6b', fontfamily='monospace',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='#1a1a2e', edgecolor='#ff6b6b', alpha=0.8))

    plt.tight_layout()
    plt.savefig(os.path.join(outdir, '02_top30_password.png'), dpi=150)
    plt.close()
    print(f'  [+] 02_top30_password.png — #1: "{top30[0][0]}" ({pcts[0]:.2f}%)')
    return top30


def plot_composizione_charset(pwd_counts, total, outdir):
    """Grafico 03: composizione del charset.
    pwd_counts: lista di (password, count)."""
    cats = Counter()
    for pwd, count in pwd_counts:
        cats[classifica_charset(pwd)] += count

    total = sum(cats.values())
    labels_map = {
        'solo_lower': 'Solo lowercase',
        'solo_digits': 'Solo cifre',
        'lower+digits': 'Lower + cifre',
        'ha_upper': 'Con maiuscole',
        'ha_speciali': 'Con speciali',
        'altro': 'Altro',
    }
    colors_map = {
        'solo_lower': '#00ff88',
        'solo_digits': '#ff6b6b',
        'lower+digits': '#ff8800',
        'ha_upper': '#7c4dff',
        'ha_speciali': '#4ecdc4',
        'altro': '#8888aa',
    }

    order = ['solo_lower', 'solo_digits', 'lower+digits', 'ha_upper', 'ha_speciali', 'altro']
    labels = [labels_map[k] for k in order if k in cats]
    sizes = [cats[k] / total * 100 for k in order if k in cats]
    colors = [colors_map[k] for k in order if k in cats]

    fig, ax = plt.subplots(figsize=(8, 6))
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=colors, autopct='%1.1f%%',
        startangle=90, pctdistance=0.75,
        wedgeprops=dict(edgecolor='#0a0a0f', linewidth=2),
        textprops=dict(fontsize=9, fontfamily='monospace'),
    )
    for t in autotexts:
        t.set_color('#0a0a0f')
        t.set_fontweight('bold')
        t.set_fontsize(8)

    simple_pct = sum(cats.get(k, 0) for k in ['solo_lower', 'solo_digits']) / total * 100
    ax.set_title(f'Composizione charset — {simple_pct:.0f}% usa solo lettere o solo cifre',
                 fontsize=12, fontweight='bold')

    plt.tight_layout()
    plt.savefig(os.path.join(outdir, '03_composizione_charset.png'), dpi=150)
    plt.close()
    print(f'  [+] 03_composizione_charset.png — {simple_pct:.0f}% solo lower/digits')
    return cats


def main():
    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
    os.makedirs(outdir, exist_ok=True)

    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        print(f'[*] Carico wordlist: {sys.argv[1]}')
        pwd_counts = carica_wordlist_conteggi(sys.argv[1])
        total = sum(c for _, c in pwd_counts)
        unique = len(pwd_counts)
        print(f'    {total:,} password totali ({unique:,} uniche)')
        source = sys.argv[1]
    else:
        print('[*] Nessun file fornito, genero dataset sintetico (statistiche RockYou)')
        passwords = genera_dataset_sintetico(500000)
        counter = Counter(passwords)
        pwd_counts = counter.most_common()
        total = len(passwords)
        unique = len(counter)
        print(f'    {total:,} password generate ({unique:,} uniche)')
        source = 'sintetico (basato su RockYou)'

    # Ordina per count decrescente
    pwd_counts.sort(key=lambda x: -x[1])

    print()
    print('[*] Generazione grafici...')
    peak = plot_distribuzione_lunghezze(pwd_counts, total, outdir)
    top30 = plot_top30(pwd_counts, total, outdir)
    cats = plot_composizione_charset(pwd_counts, total, outdir)

    # Calcola statistiche
    lens_weighted = []
    entropie = []
    for pwd, count in pwd_counts[:50000]:
        lens_weighted.extend([len(pwd)] * min(count, 100))  # campiona per media
        entropie.append(entropia_shannon(pwd))

    stats = {
        'source': source,
        'totale': total,
        'uniche': unique,
        'duplicati_pct': round((1 - unique / total) * 100, 2),
        'lunghezza_media': round(np.mean(lens_weighted), 2),
        'lunghezza_picco': peak,
        'entropia_media': round(np.mean(entropie), 3),
        'top1': pwd_counts[0][0],
        'top1_pct': round(pwd_counts[0][1] / total * 100, 3),
        'top10_pct': round(sum(c for _, c in pwd_counts[:10]) / total * 100, 2),
    }

    with open(os.path.join(outdir, 'stats_distribuzione.json'), 'w') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    print()
    print(f'[*] Risultati:')
    print(f'    Password totali:    {stats["totale"]:,}')
    print(f'    Uniche:             {stats["uniche"]:,} ({stats["duplicati_pct"]}% duplicati)')
    print(f'    Lunghezza media:    {stats["lunghezza_media"]}')
    print(f'    Entropia media:     {stats["entropia_media"]} bit')
    print(f'    #1 password:        "{stats["top1"]}" ({stats["top1_pct"]}%)')
    print(f'    Top 10 coprono:     {stats["top10_pct"]}% del dataset')
    print()
    print('[+] Done. Output in:', outdir)


if __name__ == '__main__':
    main()
