#!/usr/bin/env python3
"""
07_cognomi.py — Distribuzione cognomi italiani per lettera iniziale
Dati: Cognomix.it (42,271 cognomi distinti)

Mostra lo sbilanciamento che rende la divisione alfabetica dei seggi
una pessima idea dal punto di vista della teoria delle code.

Output: output/11_cognomi.png, output/12_seggi_sim.png
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

OUTPUT_DIR = 'output'
os.makedirs(OUTPUT_DIR, exist_ok=True)

plt.rcParams.update({
    'figure.facecolor': '#0d1117',
    'axes.facecolor': '#0d1117',
    'axes.edgecolor': '#30363d',
    'axes.labelcolor': '#c9d1d9',
    'text.color': '#c9d1d9',
    'xtick.color': '#8b949e',
    'ytick.color': '#8b949e',
    'grid.color': '#21262d',
    'font.family': 'monospace',
    'font.size': 11,
})

# Cognomix.it — cognomi distinti per lettera
COGNOMI = {
    'A': 2671, 'B': 4730, 'C': 5484, 'D': 3118, 'E': 248,
    'F': 2214, 'G': 2826, 'H': 0, 'I': 655, 'J': 0,
    'K': 0, 'L': 1863, 'M': 3985, 'N': 660, 'O': 517,
    'P': 3611, 'Q': 161, 'R': 1797, 'S': 3367, 'T': 1934,
    'U': 175, 'V': 1353, 'W': 0, 'X': 0, 'Y': 0, 'Z': 902
}

# Filtra lettere con almeno 1 cognome
LETTERS = [l for l in sorted(COGNOMI.keys()) if COGNOMI[l] > 0]
COUNTS = [COGNOMI[l] for l in LETTERS]
TOTAL = sum(COUNTS)
PCTS = [c / TOTAL * 100 for c in COUNTS]


def plot_cognomi():
    """Plot 11: Distribuzione cognomi per iniziale."""
    fig, ax = plt.subplots(figsize=(14, 7))

    # Colora in base alla deviazione dalla media
    avg_pct = 100 / len(LETTERS)  # ~5% se fossero uniformi
    colors = []
    for p in PCTS:
        if p > avg_pct * 2:
            colors.append('#ff6b6b')  # molto sopra
        elif p > avg_pct * 1.2:
            colors.append('#ff8800')  # sopra
        elif p < avg_pct * 0.3:
            colors.append('#4ecdc4')  # molto sotto
        elif p < avg_pct * 0.6:
            colors.append('#7c4dff')  # sotto
        else:
            colors.append('#00ff88')  # circa giusto

    bars = ax.bar(LETTERS, PCTS, color=colors, alpha=0.85,
                  edgecolor='#0d1117', width=0.7)

    # Linea media uniforme
    ax.axhline(y=avg_pct, color='#ffcc00', linewidth=2, linestyle='--',
               label=f'distribuzione uniforme = {avg_pct:.1f}%')

    # Etichette percentuali
    for bar, pct, letter in zip(bars, PCTS, LETTERS):
        if pct > 0.5:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.15,
                    f'{pct:.1f}%', ha='center', fontsize=7.5, color='#c9d1d9')

    ax.set_xlabel('lettera iniziale del cognome', fontsize=13)
    ax.set_ylabel('% dei cognomi italiani', fontsize=13)
    ax.set_title('Distribuzione dei cognomi italiani per iniziale (42,271 cognomi)',
                 fontsize=14, fontweight='bold')
    ax.legend(fontsize=10, framealpha=0.3)
    ax.grid(True, alpha=0.3, axis='y')

    # Annotazioni
    c_idx = LETTERS.index('C')
    q_idx = LETTERS.index('Q')
    ax.annotate(f'C = {PCTS[c_idx]:.1f}%\n(34x la Q)',
                xy=(c_idx, PCTS[c_idx]),
                xytext=(c_idx + 2, PCTS[c_idx] + 1),
                fontsize=10, color='#ff6b6b',
                arrowprops=dict(arrowstyle='->', color='#ff6b6b', lw=1.5))

    ax.annotate(f'Q = {PCTS[q_idx]:.1f}%',
                xy=(q_idx, PCTS[q_idx]),
                xytext=(q_idx + 1.5, PCTS[q_idx] + 3),
                fontsize=10, color='#4ecdc4',
                arrowprops=dict(arrowstyle='->', color='#4ecdc4', lw=1.5))

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '11_cognomi.png'), dpi=180)
    print(f'[+] output/11_cognomi.png')
    plt.close()


def simulate_seggi():
    """
    Plot 12: Simulazione seggio elettorale.
    Confronto 3 strategie:
    1. Coda unica (il gold standard)
    2. Divisi M/F (due code ~50/50)
    3. Divisi per iniziale cognome (A-F, G-M, N-Z)

    Misura: tempo medio in coda per elettore.
    """
    np.random.seed(42)
    N_VOTERS = 900
    SERVICE_TIME = 2.5  # minuti medi per votare (identificazione + scheda + urna)
    HOURS_OPEN = 12
    TOTAL_MINUTES = HOURS_OPEN * 60

    # Distribuzione arrivi: picchi stretti mattina e tardo pomeriggio, buco dopo pranzo
    def generate_arrivals(n):
        """Genera arrivi non uniformi nel tempo (picchi realistici da seggio)."""
        # 40% mattina (9:30-11:00), 15% mezzogiorno, 10% primo pomeriggio, 35% tardo pomeriggio
        n1 = int(n * 0.40)
        n2 = int(n * 0.15)
        n3 = int(n * 0.10)
        n4 = n - n1 - n2 - n3
        morning = np.random.normal(150, 35, n1)     # picco a 2.5h (09:30)
        midday = np.random.normal(270, 40, n2)       # mezzogiorno
        early_pm = np.random.normal(360, 50, n3)     # primo pomeriggio (scarso)
        evening = np.random.normal(480, 40, n4)      # picco a 8h (15:00-16:00)
        arrivals = np.concatenate([morning, midday, early_pm, evening])
        arrivals = np.clip(arrivals, 0, TOTAL_MINUTES)
        arrivals.sort()
        return arrivals

    # Assegna lettere cognome secondo distribuzione reale
    letter_probs = np.array(COUNTS) / TOTAL
    voter_letters = np.random.choice(LETTERS, N_VOTERS, p=letter_probs)

    # Assegna genere ~50/50
    voter_gender = np.random.choice(['M', 'F'], N_VOTERS, p=[0.5, 0.5])

    arrivals = generate_arrivals(N_VOTERS)
    service_times = np.random.exponential(SERVICE_TIME, N_VOTERS)

    def simulate_single_queue(arrivals, stimes, n_servers):
        """Coda unica con n_servers sportelli."""
        server_free = np.zeros(n_servers)
        waits = np.zeros(len(arrivals))
        for i in range(len(arrivals)):
            # Assegna al server che si libera prima
            earliest = np.argmin(server_free)
            if arrivals[i] >= server_free[earliest]:
                waits[i] = 0
                server_free[earliest] = arrivals[i] + stimes[i]
            else:
                waits[i] = server_free[earliest] - arrivals[i]
                server_free[earliest] += stimes[i]
        return waits

    def simulate_split_queues(arrivals, stimes, assignments, groups, servers_per_group):
        """Code separate per gruppo."""
        all_waits = np.zeros(len(arrivals))
        for group in groups:
            mask = np.array([a in group for a in assignments])
            if mask.sum() == 0:
                continue
            idx = np.where(mask)[0]
            group_arrivals = arrivals[idx]
            group_stimes = stimes[idx]
            waits = simulate_single_queue(group_arrivals, group_stimes, servers_per_group)
            all_waits[idx] = waits
        return all_waits

    N_SERVERS_TOTAL = 4

    # Strategia 1: M/F, 2 sportelli ciascuno
    w1 = simulate_split_queues(arrivals, service_times, voter_gender,
                                [{'M'}, {'F'}], 2)

    # Strategia 2: Alfabetico naive A-L/M-Z, 3 sportelli ciascuno
    def letter_group_naive(letter):
        if letter <= 'L':
            return 'AL'
        else:
            return 'MZ'

    voter_alpha_naive = np.array([letter_group_naive(l) for l in voter_letters])

    print('  Alfabetico naive (A-L / M-Z):')
    for g in ['AL', 'MZ']:
        n = (voter_alpha_naive == g).sum()
        print(f'    Gruppo {g}: {n} elettori ({n/N_VOTERS*100:.1f}%)')

    w2 = simulate_split_queues(arrivals, service_times, voter_alpha_naive,
                                [{'AL'}, {'MZ'}], 2)

    w3 = None  # rimosso

    # === Plot rho istantaneo per tavolo (nuovo grafico) ===
    def compute_instantaneous_rho(arrivals, assignments, group_label, servers, window=30):
        """Calcola rho istantaneo in finestre di `window` minuti."""
        mask = np.array([a == group_label for a in assignments])
        group_arrivals = arrivals[mask]
        bins = np.arange(0, TOTAL_MINUTES + window, window)
        counts, _ = np.histogram(group_arrivals, bins=bins)
        # rho = (arrivi * service_time) / (servers * window)
        rho_instant = (counts * SERVICE_TIME) / (servers * window)
        centers = (bins[:-1] + bins[1:]) / 2
        return centers, rho_instant

    fig_rho, ax_rho = plt.subplots(figsize=(14, 6))

    # A-L
    cx, ry = compute_instantaneous_rho(arrivals, voter_alpha_naive, 'AL', 2)
    ax_rho.plot(cx / 60, ry, color='#ff6b6b', linewidth=2.5, label='Tavolo A-L (56% elettori, 2 sportelli)')
    # M-Z
    cx, ry = compute_instantaneous_rho(arrivals, voter_alpha_naive, 'MZ', 2)
    ax_rho.plot(cx / 60, ry, color='#4ecdc4', linewidth=2.5, label='Tavolo M-Z (44% elettori, 2 sportelli)')
    # M/F per confronto
    cx, ry_m = compute_instantaneous_rho(arrivals, voter_gender, 'M', 2)
    cx, ry_f = compute_instantaneous_rho(arrivals, voter_gender, 'F', 2)
    ax_rho.plot(cx / 60, (ry_m + ry_f) / 2, color='#7c4dff', linewidth=1.5, linestyle='--',
                label='Tavolo M o F (50% elettori, media)', alpha=0.7)

    ax_rho.axhline(y=1.0, color='#ff6b6b', linewidth=1, linestyle=':', alpha=0.5)
    ax_rho.axhline(y=0.8, color='#ffcc00', linewidth=1, linestyle=':', alpha=0.4)
    ax_rho.text(0.3, 1.02, 'saturazione', fontsize=8, color='#ff6b6b', alpha=0.7)
    ax_rho.text(0.3, 0.82, 'zona pericolo', fontsize=8, color='#ffcc00', alpha=0.7)

    ax_rho.axvspan(2, 4, alpha=0.06, color='#ff6b6b')
    ax_rho.text(3, ax_rho.get_ylim()[0] + 0.05 if ax_rho.get_ylim()[0] >= 0 else 0.05,
                'picco mattina', fontsize=8, color='#ff6b6b', ha='center', alpha=0.6)

    ax_rho.set_xlabel('ore dall\'apertura (07:00 = 0)', fontsize=12)
    ax_rho.set_ylabel('rho istantaneo (finestre 30 min)', fontsize=12)
    ax_rho.set_title('Utilizzazione istantanea per tavolo. Il picco uccide lo shard sbilanciato.',
                     fontsize=13, fontweight='bold')
    ax_rho.legend(fontsize=9, framealpha=0.3)
    ax_rho.grid(True, alpha=0.3)
    ax_rho.set_xlim(0, 12)
    ax_rho.set_ylim(0, max(1.5, ax_rho.get_ylim()[1]))

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '13_rho_istantaneo.png'), dpi=180)
    print(f'[+] output/13_rho_istantaneo.png')
    plt.close()

    # Plot: solo M/F vs A-L/M-Z
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6.5))

    # Box plot dei tempi di attesa
    data = [w1, w2]
    labels = ['M/F (prima)\n50% / 50%', 'A-L / M-Z (adesso)\n57% / 43%']
    bp = ax1.boxplot(data, labels=labels, patch_artist=True,
                      medianprops=dict(color='#ffcc00', linewidth=2),
                      whiskerprops=dict(color='#8b949e'),
                      capprops=dict(color='#8b949e'),
                      flierprops=dict(marker='o', markerfacecolor='#ff6b6b',
                                     markersize=3, alpha=0.3))

    box_colors = ['#00ff88', '#ff6b6b']
    for patch, color in zip(bp['boxes'], box_colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)

    ax1.set_ylabel('tempo in coda (minuti)', fontsize=12)
    ax1.set_title('Tempo di attesa per strategia', fontsize=13, fontweight='bold')
    ax1.grid(True, alpha=0.3, axis='y')

    # Medie e p95
    means = [np.mean(w) for w in data]
    p95s = [np.percentile(w, 95) for w in data]
    for i, (m, p) in enumerate(zip(means, p95s)):
        ax1.text(i + 1, p + 3, f'media: {m:.0f} min\np95: {p:.0f} min',
                 ha='center', fontsize=9, fontweight='bold', color='#c9d1d9')

    # Sbilanciamento A-L vs M-Z
    groups_naive = {'A-L': 0, 'M-Z': 0}
    for l, c in zip(LETTERS, COUNTS):
        g = 'A-L' if l <= 'L' else 'M-Z'
        groups_naive[g] += c
    total_alpha = sum(groups_naive.values())
    naive_pcts = [groups_naive[g] / total_alpha * 100 for g in groups_naive]

    x = np.arange(2)
    bar_colors = ['#ff6b6b', '#4ecdc4']
    bars = ax2.bar(x, naive_pcts, color=bar_colors, alpha=0.85,
                   edgecolor='#0d1117', width=0.5)

    ax2.axhline(y=50, color='#ffcc00', linewidth=2, linestyle='--',
                label='distribuzione ideale (50%)')

    for bar, pct in zip(bars, naive_pcts):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.8,
                 f'{pct:.1f}%', ha='center', fontsize=13, fontweight='bold', color='#c9d1d9')

    ax2.set_xticks(x)
    ax2.set_xticklabels(['A-L', 'M-Z'], fontsize=12)
    ax2.set_ylabel('% elettori', fontsize=12)
    ax2.set_title('Lo sbilanciamento reale', fontsize=13, fontweight='bold')
    ax2.legend(fontsize=9, framealpha=0.3)
    ax2.grid(True, alpha=0.3, axis='y')
    ax2.set_ylim(0, 65)

    fig.suptitle('Seggio elettorale: prima (M/F) vs adesso (A-L / M-Z)',
                 fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '12_seggi_sim.png'), dpi=180, bbox_inches='tight')
    print(f'[+] output/12_seggi_sim.png')
    plt.close()

    # Stampa risultati
    print(f'\n[*] Risultati simulazione ({N_VOTERS} elettori, {N_SERVERS_TOTAL} sportelli):')
    for label, w in zip(['M/F', 'A-L/M-Z'], data):
        print(f'    {label:20s}  media={np.mean(w):.1f} min  '
              f'p95={np.percentile(w, 95):.1f} min  max={np.max(w):.1f} min')


if __name__ == '__main__':
    plot_cognomi()
    simulate_seggi()
