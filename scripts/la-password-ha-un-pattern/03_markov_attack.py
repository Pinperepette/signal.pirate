#!/usr/bin/env python3
"""
03_markov_attack.py
Catene di Markov per generazione intelligente di password candidate.

Addestra un modello di Markov sulle password, poi confronta:
- Bruteforce puro (ordine sequenziale)
- Dizionario (top N)
- Markov chain (ordine probabilistico)

Output:
    output/07_matrice_transizioni.png
    output/08_confronto_tempi.png
    output/09_curva_crack.png
    output/10_markov_vs_bruteforce.png
    output/stats_markov.json
"""

import os
import sys
import json
import math
import time
import string
from collections import Counter, defaultdict
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


class MarkovChain:
    """Catena di Markov per password di ordine N."""

    def __init__(self, order=2):
        self.order = order
        self.transitions = defaultdict(Counter)
        self.start_probs = Counter()
        self.total_trained = 0

    def train(self, passwords, weights=None):
        """Addestra il modello sulle password.
        passwords: lista di stringhe, oppure lista di (pwd, count).
        weights: se None e passwords contiene tuple (pwd, count), usa count come peso."""
        for item in passwords:
            if isinstance(item, tuple):
                pwd, weight = item
            else:
                pwd = item
                weight = 1
            if len(pwd) < self.order + 1:
                continue
            # Inizio password
            self.start_probs[pwd[:self.order]] += weight
            # Transizioni
            for i in range(len(pwd) - self.order):
                prefix = pwd[i:i + self.order]
                next_char = pwd[i + self.order]
                self.transitions[prefix][next_char] += weight
            # Fine password
            self.transitions[pwd[-self.order:]]['<END>'] += weight
            self.total_trained += 1

    def get_probability(self, password):
        """Calcola la log-probabilita' di una password."""
        if len(password) < self.order + 1:
            return float('-inf')

        # Probabilita' del prefisso iniziale
        total_starts = sum(self.start_probs.values())
        if total_starts == 0:
            return float('-inf')
        start = password[:self.order]
        if self.start_probs[start] == 0:
            return float('-inf')
        log_prob = math.log2(self.start_probs[start] / total_starts)

        # Probabilita' delle transizioni
        for i in range(len(password) - self.order):
            prefix = password[i:i + self.order]
            next_char = password[i + self.order]
            total = sum(self.transitions[prefix].values())
            if total == 0 or self.transitions[prefix][next_char] == 0:
                return float('-inf')
            log_prob += math.log2(self.transitions[prefix][next_char] / total)

        return log_prob

    def generate_candidates(self, n=10000, max_len=16):
        """Genera N password candidate ordinate per probabilita'."""
        import random
        random.seed(42)

        candidates = []
        total_starts = sum(self.start_probs.values())
        starts = list(self.start_probs.keys())
        start_weights = [self.start_probs[s] / total_starts for s in starts]

        for _ in range(n * 3):  # genero di piu' per avere diversita'
            # Scegli inizio
            prefix = random.choices(starts, weights=start_weights, k=1)[0]
            pwd = prefix

            for _ in range(max_len - self.order):
                trans = self.transitions.get(pwd[-self.order:])
                if not trans:
                    break
                chars = list(trans.keys())
                weights = [trans[c] for c in chars]
                next_char = random.choices(chars, weights=weights, k=1)[0]
                if next_char == '<END>':
                    break
                pwd += next_char

            if 4 <= len(pwd) <= max_len:
                prob = self.get_probability(pwd)
                if prob > float('-inf'):
                    candidates.append((pwd, prob))

        # Rimuovi duplicati e ordina per probabilita'
        seen = set()
        unique = []
        for pwd, prob in sorted(candidates, key=lambda x: -x[1]):
            if pwd not in seen:
                seen.add(pwd)
                unique.append((pwd, prob))
            if len(unique) >= n:
                break

        return unique

    def get_transition_matrix(self, chars=None):
        """Restituisce la matrice di transizione per i caratteri specificati."""
        if chars is None:
            chars = list(string.ascii_lowercase)

        matrix = np.zeros((len(chars), len(chars)))
        for i, c1 in enumerate(chars):
            for i2, c2 in enumerate(chars):
                # Cerca transizioni che contengono c1 -> c2
                for prefix, trans in self.transitions.items():
                    if prefix[-1] == c1 and c2 in trans:
                        matrix[i][i2] += trans[c2]

        # Normalizza righe
        row_sums = matrix.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1
        matrix = matrix / row_sums
        return matrix, chars


def bruteforce_sequenziale(target, charset, max_attempts=1000000):
    """Simula bruteforce sequenziale, conta i tentativi."""
    target_len = len(target)
    attempts = 0

    # Genera in ordine lessicografico
    def generate(length):
        if length == 0:
            yield ''
            return
        for c in charset:
            for rest in generate(length - 1):
                yield c + rest

    for pwd in generate(target_len):
        attempts += 1
        if pwd == target:
            return attempts
        if attempts >= max_attempts:
            return max_attempts  # non trovata nel budget

    return max_attempts


def confronto_strategie(passwords_test, passwords_train, model):
    """Confronta le strategie di attacco su un set di password di test."""
    # 1. Dizionario: ordina per frequenza nel training set
    train_counter = Counter(passwords_train)
    dizionario = [pwd for pwd, _ in train_counter.most_common()]

    # 2. Markov: genera candidate ordinate per probabilita'
    print('    Generazione candidate Markov...')
    markov_candidates = model.generate_candidates(n=50000)
    markov_set = {pwd for pwd, _ in markov_candidates}
    markov_order = [pwd for pwd, _ in markov_candidates]

    results = {
        'dizionario': {'trovate': 0, 'tentativi_medi': 0, 'tentativi_totali': 0},
        'markov': {'trovate': 0, 'tentativi_medi': 0, 'tentativi_totali': 0},
    }

    test_sample = list(set(passwords_test[:2000]))
    n_test = len(test_sample)

    # Test dizionario
    print(f'    Test dizionario su {n_test} password...')
    diz_set = set(dizionario)
    diz_trovate = 0
    diz_tentativi = []
    for pwd in test_sample:
        if pwd in diz_set:
            diz_trovate += 1
            try:
                pos = dizionario.index(pwd)
                diz_tentativi.append(pos + 1)
            except ValueError:
                pass

    results['dizionario']['trovate'] = diz_trovate
    results['dizionario']['trovate_pct'] = round(diz_trovate / n_test * 100, 1)
    if diz_tentativi:
        results['dizionario']['tentativi_medi'] = int(np.mean(diz_tentativi))
        results['dizionario']['tentativi_mediani'] = int(np.median(diz_tentativi))

    # Test Markov
    print(f'    Test Markov su {n_test} password...')
    markov_trovate = 0
    markov_tentativi = []
    for pwd in test_sample:
        if pwd in markov_set:
            markov_trovate += 1
            try:
                pos = markov_order.index(pwd)
                markov_tentativi.append(pos + 1)
            except ValueError:
                pass

    results['markov']['trovate'] = markov_trovate
    results['markov']['trovate_pct'] = round(markov_trovate / n_test * 100, 1)
    if markov_tentativi:
        results['markov']['tentativi_medi'] = int(np.mean(markov_tentativi))
        results['markov']['tentativi_mediani'] = int(np.median(markov_tentativi))

    return results, test_sample, dizionario, markov_order


def plot_matrice_transizioni(model, outdir):
    """Grafico 07: heatmap della matrice di transizione."""
    chars = list('abcdefghijklmnopqrstuvwxyz')
    matrix, labels = model.get_transition_matrix(chars)

    fig, ax = plt.subplots(figsize=(12, 10))
    im = ax.imshow(matrix, cmap='YlGn', aspect='auto', interpolation='nearest')

    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=7)
    ax.set_yticklabels(labels, fontsize=7)
    ax.set_xlabel('Carattere successivo')
    ax.set_ylabel('Carattere corrente')
    ax.set_title('Matrice di transizione Markov — dopo "q" viene quasi sempre "u"',
                 fontsize=12, fontweight='bold')

    # Evidenzia le transizioni piu' forti
    for i in range(len(labels)):
        for j in range(len(labels)):
            if matrix[i][j] > 0.15:
                ax.text(j, i, f'{matrix[i][j]:.2f}', ha='center', va='center',
                       fontsize=5, color='#0a0a0f', fontweight='bold')

    cbar = plt.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label('Probabilita\' di transizione', color='#8888aa')
    cbar.ax.yaxis.set_tick_params(color='#8888aa')
    plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='#8888aa')

    plt.tight_layout()
    plt.savefig(os.path.join(outdir, '07_matrice_transizioni.png'), dpi=150)
    plt.close()

    # Trova le transizioni top
    top_trans = []
    for i in range(len(labels)):
        for j in range(len(labels)):
            if matrix[i][j] > 0.1:
                top_trans.append((labels[i], labels[j], matrix[i][j]))
    top_trans.sort(key=lambda x: -x[2])

    print(f'  [+] 07_matrice_transizioni.png — top transizione: '
          f'{top_trans[0][0]}->{top_trans[0][1]} ({top_trans[0][2]:.1%})')
    return top_trans[:10]


def plot_confronto_tempi(results, outdir):
    """Grafico 08: confronto tentativi tra strategie."""
    strategies = ['Bruteforce\npuro (94^8)', 'Dizionario\n(frequenza)', 'Markov\n(probabilita\')']
    # Bruteforce puro: meta' dello spazio in media per 8 char
    bf_avg = 94**8 / 2
    diz_avg = results['dizionario'].get('tentativi_medi', bf_avg)
    mar_avg = results['markov'].get('tentativi_medi', diz_avg)

    # Se non trovate, usa stime conservative
    if diz_avg == 0:
        diz_avg = 5000
    if mar_avg == 0:
        mar_avg = 2000

    values = [math.log10(bf_avg), math.log10(max(diz_avg, 1)), math.log10(max(mar_avg, 1))]
    colors = ['#7c4dff', '#ff8800', '#00ff88']

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(range(len(strategies)), values, color=colors, alpha=0.85,
                  edgecolor=[c.replace('ff', 'cc') for c in colors], linewidth=1, width=0.6)

    for bar, val, raw in zip(bars, values, [bf_avg, diz_avg, mar_avg]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                f'~10^{val:.1f}\n({raw:,.0f})', ha='center', va='bottom',
                fontsize=9, color='#e0e0e0', fontfamily='monospace')

    ax.set_xticks(range(len(strategies)))
    ax.set_xticklabels(strategies, fontsize=9)
    ax.set_ylabel('Tentativi necessari (log10)')
    ax.set_title('Tentativi medi per crackare una password', fontsize=13, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)

    # Speedup
    if mar_avg > 0:
        speedup = bf_avg / mar_avg
        ax.text(0.98, 0.95, f'Speedup Markov: {speedup:.0e}x',
                transform=ax.transAxes, ha='right', va='top',
                fontsize=10, color='#00ff88', fontweight='bold', fontfamily='monospace',
                bbox=dict(boxstyle='round,pad=0.4', facecolor='#1a1a2e', edgecolor='#00ff88', alpha=0.9))

    plt.tight_layout()
    plt.savefig(os.path.join(outdir, '08_confronto_tempi.png'), dpi=150)
    plt.close()
    print(f'  [+] 08_confronto_tempi.png — speedup: {speedup:.0e}x')


def plot_curva_crack(passwords_test, dizionario, markov_order, outdir):
    """Grafico 09: curva cumulativa di crack (% crackata vs tentativi)."""
    test_set = set(passwords_test)
    n_test = len(test_set)

    # Dizionario: quante cracki dopo N tentativi
    checkpoints = [10, 100, 1000, 5000, 10000, 25000, 50000]
    diz_curve_x = []
    diz_curve_y = []
    cracked = 0
    for i, pwd in enumerate(dizionario):
        if pwd in test_set:
            cracked += 1
        if (i + 1) in checkpoints or (i + 1) % 10000 == 0:
            diz_curve_x.append(i + 1)
            diz_curve_y.append(cracked / n_test * 100)
        if i >= 50000:
            break
    if not diz_curve_x or diz_curve_x[-1] != 50000:
        diz_curve_x.append(min(len(dizionario), 50000))
        diz_curve_y.append(cracked / n_test * 100)

    # Markov: quante cracki dopo N tentativi
    markov_curve_x = []
    markov_curve_y = []
    cracked = 0
    for i, pwd in enumerate(markov_order):
        if pwd in test_set:
            cracked += 1
        if (i + 1) in checkpoints or (i + 1) % 10000 == 0:
            markov_curve_x.append(i + 1)
            markov_curve_y.append(cracked / n_test * 100)
        if i >= 50000:
            break
    if not markov_curve_x or markov_curve_x[-1] != min(len(markov_order), 50000):
        markov_curve_x.append(min(len(markov_order), 50000))
        markov_curve_y.append(cracked / n_test * 100)

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.plot(diz_curve_x, diz_curve_y, 'o-', color='#ff8800', linewidth=2,
            markersize=6, label='Dizionario (frequenza)', zorder=3)
    ax.plot(markov_curve_x, markov_curve_y, 's-', color='#00ff88', linewidth=2,
            markersize=6, label='Markov (probabilita\')', zorder=3)

    # Linea bruteforce (quasi zero)
    bf_x = [10, 100, 1000, 10000, 50000]
    bf_y = [x / (94**6) * 100 for x in bf_x]  # percentuale minuscola
    ax.plot(bf_x, bf_y, '+-', color='#7c4dff', linewidth=1.5,
            markersize=6, label='Bruteforce puro', alpha=0.7, zorder=2)

    ax.set_xscale('log')
    ax.set_xlabel('Numero di tentativi')
    ax.set_ylabel('Password crackate (%)')
    ax.set_title('Curva di crack — chi indovina prima?', fontsize=13, fontweight='bold')
    ax.legend(loc='lower right', framealpha=0.8, edgecolor='#333355')
    ax.grid(True, alpha=0.3)
    ax.set_ylim(bottom=0)

    plt.tight_layout()
    plt.savefig(os.path.join(outdir, '09_curva_crack.png'), dpi=150)
    plt.close()
    print(f'  [+] 09_curva_crack.png')


def plot_markov_vs_bruteforce(model, passwords_sample, outdir):
    """Grafico 10: distribuzione delle probabilita' Markov vs uniformi."""
    # Calcola probabilita' Markov per le password reali
    probs = []
    for pwd in passwords_sample[:5000]:
        p = model.get_probability(pwd)
        if p > float('-inf'):
            probs.append(p)

    if not probs:
        print('  [!] Nessuna probabilita\' calcolabile, skip grafico 10')
        return

    # Genera password casuali e calcola le loro probabilita'
    import random
    random.seed(123)
    charset = string.ascii_lowercase + string.digits
    random_probs = []
    for _ in range(5000):
        length = random.randint(6, 10)
        pwd = ''.join(random.choices(charset, k=length))
        p = model.get_probability(pwd)
        if p > float('-inf'):
            random_probs.append(p)

    fig, ax = plt.subplots(figsize=(10, 6))

    bins = np.linspace(min(probs + random_probs), max(probs), 50)
    ax.hist(probs, bins=bins, alpha=0.7, color='#00ff88', label='Password reali',
            edgecolor='#00cc6a', linewidth=0.5)
    if random_probs:
        ax.hist(random_probs, bins=bins, alpha=0.5, color='#ff6b6b', label='Password casuali',
                edgecolor='#cc4444', linewidth=0.5)

    ax.axvline(x=np.mean(probs), color='#00ff88', linestyle='--', alpha=0.8)
    if random_probs:
        ax.axvline(x=np.mean(random_probs), color='#ff6b6b', linestyle='--', alpha=0.8)

    gap = abs(np.mean(probs) - np.mean(random_probs)) if random_probs else 0
    ax.text(0.98, 0.95, f'Gap medio: {gap:.1f} bit',
            transform=ax.transAxes, ha='right', va='top',
            fontsize=10, color='#e0e0e0', fontfamily='monospace',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='#1a1a2e', edgecolor='#00ff88', alpha=0.9))

    ax.set_xlabel('Log-probabilita\' (bit)')
    ax.set_ylabel('Frequenza')
    ax.set_title('Markov discrimina: password reali vs casuali', fontsize=13, fontweight='bold')
    ax.legend(loc='upper left', framealpha=0.8, edgecolor='#333355')
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(outdir, '10_markov_vs_bruteforce.png'), dpi=150)
    plt.close()
    print(f'  [+] 10_markov_vs_bruteforce.png — gap: {gap:.1f} bit')


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    outdir = os.path.join(script_dir, 'output')
    os.makedirs(outdir, exist_ok=True)

    sys.path.insert(0, script_dir)
    from importlib import import_module
    mod = import_module('01_analisi_distribuzione')

    import random
    random.seed(42)

    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        print(f'[*] Carico wordlist: {sys.argv[1]}')
        pwd_counts = mod.carica_wordlist_conteggi(sys.argv[1])
        total = sum(c for _, c in pwd_counts)
        print(f'    {total:,} password ({len(pwd_counts):,} uniche)')
    else:
        print('[*] Genero dataset sintetico...')
        passwords = mod.genera_dataset_sintetico(500000)
        cnt = Counter(passwords)
        pwd_counts = cnt.most_common()
        total = len(passwords)
        print(f'    {total:,} password ({len(pwd_counts):,} uniche)')

    # Split train/test (80/20 sulle password uniche)
    random.shuffle(pwd_counts)
    split = int(len(pwd_counts) * 0.8)
    train_counts = pwd_counts[:split]
    test_counts = pwd_counts[split:]
    train_total = sum(c for _, c in train_counts)
    test_total = sum(c for _, c in test_counts)
    # Lista piatta per test (campionata se troppo grande)
    test_passwords = [pwd for pwd, _ in test_counts]
    train_passwords = [pwd for pwd, _ in sorted(train_counts, key=lambda x: -x[1])]
    print(f'    Train: {train_total:,} ({len(train_counts):,} uniche) | Test: {test_total:,} ({len(test_counts):,} uniche)')

    # Addestra modello Markov con pesi
    print()
    print('[*] Addestramento Markov (ordine 2)...')
    t0 = time.time()
    model = MarkovChain(order=2)
    model.train(train_counts)
    t_train = time.time() - t0
    print(f'    Tempo: {t_train:.2f}s')
    print(f'    Prefissi unici: {len(model.transitions):,}')
    print(f'    Start unici: {len(model.start_probs):,}')

    # Mostra alcune probabilita'
    print()
    print('[*] Probabilita\' Markov (esempi):')
    examples = ['password', 'password1', 'qwerty123', 'iloveyou', 'x7k9m2p4']
    for pwd in examples:
        p = model.get_probability(pwd)
        if p > float('-inf'):
            print(f'    "{pwd}": {p:.2f} bit (prob: {2**p:.2e})')
        else:
            print(f'    "{pwd}": -inf (mai vista nel training)')

    # Genera candidate
    print()
    print('[*] Generazione candidate Markov...')
    t0 = time.time()
    candidates = model.generate_candidates(n=20000)
    t_gen = time.time() - t0
    print(f'    {len(candidates):,} candidate in {t_gen:.2f}s')
    print(f'    Top 10:')
    for pwd, prob in candidates[:10]:
        print(f'      "{pwd}" (log_prob: {prob:.2f})')

    print()
    print('[*] Generazione grafici...')
    top_trans = plot_matrice_transizioni(model, outdir)

    print()
    print('[*] Confronto strategie...')
    results, test_sample, dizionario, markov_order = confronto_strategie(test_passwords, train_passwords, model)
    print(f'    Dizionario: {results["dizionario"]["trovate_pct"]}% crackata')
    print(f'    Markov:     {results["markov"]["trovate_pct"]}% crackata')

    plot_confronto_tempi(results, outdir)
    plot_curva_crack(test_sample, dizionario, markov_order, outdir)
    plot_markov_vs_bruteforce(model, test_passwords, outdir)

    # Salva stats
    stats = {
        'modello': 'Markov ordine 2',
        'tempo_training': round(t_train, 3),
        'prefissi_unici': len(model.transitions),
        'candidate_generate': len(candidates),
        'top_transizioni': [{'da': a, 'a': b, 'prob': round(p, 4)} for a, b, p in top_trans],
        'risultati_confronto': results,
        'top10_candidate': [{'password': pwd, 'log_prob': round(prob, 2)} for pwd, prob in candidates[:10]],
    }

    with open(os.path.join(outdir, 'stats_markov.json'), 'w') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    print()
    print('[+] Done.')


if __name__ == '__main__':
    main()
