#!/usr/bin/env python3
"""
05_simulation.py — Simulazioni Monte Carlo
1. Paradosso dell'autobus (inspection paradox)
2. Priority queue con starvation
3. Confronto teoria vs simulazione per M/M/1

Output: output/07_inspection_paradox.png
        output/08_priority_starvation.png
        output/09_mm1_simulation.png
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

OUTPUT_DIR = 'output'
os.makedirs(OUTPUT_DIR, exist_ok=True)
np.random.seed(42)

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


def simulate_inspection_paradox():
    """
    Paradosso dell'autobus: se gli autobus arrivano ogni E[H] minuti in media,
    il tuo tempo di attesa medio NON e' E[H]/2.
    E' E[H]/2 * (1 + CV^2), dove CV = sigma/mu.

    Con intervalli esponenziali (CV=1): attesa media = E[H] (non E[H]/2!)
    Con intervalli deterministici (CV=0): attesa media = E[H]/2 (come ti aspetti)
    """
    N_SIM = 100_000
    MEAN_HEADWAY = 10.0  # minuti

    scenarios = {
        'Deterministico\n(CV=0)': lambda: np.full(1000, MEAN_HEADWAY),
        'Uniforme\n(CV=0.29)': lambda: np.random.uniform(5, 15, 1000),
        'Esponenziale\n(CV=1)': lambda: np.random.exponential(MEAN_HEADWAY, 1000),
        'Erlang-2\n(CV=0.71)': lambda: np.random.gamma(2, MEAN_HEADWAY / 2, 1000),
        'Hyperexp.\n(CV=2)': lambda: np.where(
            np.random.random(1000) < 0.5,
            np.random.exponential(2, 1000),
            np.random.exponential(18, 1000)
        ),
    }

    results = {}

    for name, gen_headways in scenarios.items():
        waits = []
        for _ in range(200):
            headways = gen_headways()
            # Tempo cumulativo degli arrivi
            arrivals = np.cumsum(headways)
            total_time = arrivals[-1]

            # Passeggero arriva in un momento casuale
            for _ in range(500):
                t = np.random.uniform(0, total_time)
                # Prossimo arrivo
                idx = np.searchsorted(arrivals, t)
                if idx < len(arrivals):
                    wait = arrivals[idx] - t
                    waits.append(wait)

        waits = np.array(waits)
        results[name] = {
            'mean': np.mean(waits),
            'median': np.median(waits),
            'waits': waits
        }

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Bar chart: attesa media vs E[H]/2
    names = list(results.keys())
    means = [results[n]['mean'] for n in names]
    expected_naive = MEAN_HEADWAY / 2

    x = np.arange(len(names))
    bars = ax1.bar(x, means, color=['#00ff88', '#4ecdc4', '#7c4dff', '#ff8800', '#ff6b6b'],
                   alpha=0.85, edgecolor='#0d1117', width=0.6)

    ax1.axhline(y=expected_naive, color='#ffcc00', linewidth=2, linestyle='--',
                label=f'attesa "intuitiva" = E[H]/2 = {expected_naive:.1f} min')
    ax1.axhline(y=MEAN_HEADWAY, color='#ff6b6b', linewidth=1.5, linestyle=':',
                label=f'E[H] = {MEAN_HEADWAY:.0f} min', alpha=0.6)

    ax1.set_xticks(x)
    ax1.set_xticklabels(names, fontsize=9)
    ax1.set_ylabel('tempo di attesa medio (min)', fontsize=12)
    ax1.set_title('Il paradosso dell\'autobus', fontsize=13, fontweight='bold')
    ax1.legend(fontsize=9, framealpha=0.3)
    ax1.grid(True, alpha=0.3, axis='y')

    # Aggiungi valori sulle barre
    for bar, mean in zip(bars, means):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                 f'{mean:.1f}', ha='center', fontsize=10, fontweight='bold', color='#c9d1d9')

    # Distribuzione attese per exp vs deterministic
    ax2.hist(results['Deterministico\n(CV=0)']['waits'], bins=50, density=True,
             color='#00ff88', alpha=0.6, label='Deterministico')
    ax2.hist(results['Esponenziale\n(CV=1)']['waits'], bins=50, density=True,
             color='#7c4dff', alpha=0.6, label='Esponenziale')
    ax2.hist(results['Hyperexp.\n(CV=2)']['waits'], bins=50, density=True,
             color='#ff6b6b', alpha=0.4, label='Hyperesponenziale')

    ax2.axvline(x=expected_naive, color='#ffcc00', linewidth=2, linestyle='--',
                label=f'E[H]/2 = {expected_naive:.1f}')
    ax2.set_xlabel('tempo di attesa (min)', fontsize=12)
    ax2.set_ylabel('densita\'', fontsize=12)
    ax2.set_title('Distribuzione dei tempi di attesa', fontsize=13, fontweight='bold')
    ax2.legend(fontsize=9, framealpha=0.3)
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(0, 40)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '07_inspection_paradox.png'), dpi=180)
    print(f'[+] output/07_inspection_paradox.png')
    plt.close()


def simulate_priority_starvation():
    """
    Coda con priorita': due classi di traffico.
    High priority: servite prima. Low priority: dopo.
    Al crescere di rho, le low priority vengono affamate.
    """
    rho_values = np.linspace(0.1, 0.95, 30)
    HIGH_FRACTION = 0.6  # 60% del traffico e' high priority
    N_CUSTOMERS = 10_000
    SERVICE_RATE = 1.0

    high_waits = []
    low_waits = []

    for rho in rho_values:
        arrival_rate = rho * SERVICE_RATE
        high_rate = arrival_rate * HIGH_FRACTION
        low_rate = arrival_rate * (1 - HIGH_FRACTION)

        # Genera arrivi
        high_arrivals = np.cumsum(np.random.exponential(1 / high_rate, N_CUSTOMERS))
        low_arrivals = np.cumsum(np.random.exponential(1 / low_rate, N_CUSTOMERS))

        # Merge e simula
        events = (
            [(t, 'H', np.random.exponential(1 / SERVICE_RATE)) for t in high_arrivals] +
            [(t, 'L', np.random.exponential(1 / SERVICE_RATE)) for t in low_arrivals]
        )
        events.sort(key=lambda x: x[0])

        # Simulazione con 2 code
        high_queue = []
        low_queue = []
        server_free_at = 0
        h_waits = []
        l_waits = []

        for arrival_time, priority, service_time in events:
            if arrival_time >= server_free_at:
                # Server libero
                if priority == 'H':
                    # Serve subito
                    wait = 0
                    server_free_at = arrival_time + service_time
                    h_waits.append(wait)
                else:
                    # Controlla se ci sono high in attesa
                    if high_queue:
                        ht, hs = high_queue.pop(0)
                        h_waits.append(arrival_time - ht)
                        server_free_at = arrival_time + hs
                        low_queue.append((arrival_time, service_time))
                    else:
                        wait = 0
                        server_free_at = arrival_time + service_time
                        l_waits.append(wait)
            else:
                # Server occupato, accoda
                if priority == 'H':
                    high_queue.append((arrival_time, service_time))
                else:
                    low_queue.append((arrival_time, service_time))

            # Drena code quando il server si libera
            while server_free_at <= arrival_time:
                if high_queue:
                    ht, hs = high_queue.pop(0)
                    h_waits.append(max(0, server_free_at - ht))
                    server_free_at += hs
                elif low_queue:
                    lt, ls = low_queue.pop(0)
                    l_waits.append(max(0, server_free_at - lt))
                    server_free_at += ls
                else:
                    break

        high_waits.append(np.mean(h_waits) if h_waits else 0)
        low_waits.append(np.mean(l_waits) if l_waits else 0)

    fig, ax = plt.subplots(figsize=(12, 7))

    ax.plot(rho_values, high_waits, color='#00ff88', linewidth=2.5,
            label='High priority (60%)', marker='o', markersize=3)
    ax.plot(rho_values, low_waits, color='#ff6b6b', linewidth=2.5,
            label='Low priority (40%)', marker='s', markersize=3)

    # Rapporto
    ratio = [l / h if h > 0.01 else 0 for h, l in zip(high_waits, low_waits)]

    ax.axvspan(0.8, 1.0, alpha=0.12, color='#ff6b6b')
    ax.set_xlabel('rho (utilizzazione totale)', fontsize=13)
    ax.set_ylabel('tempo medio in coda', fontsize=13)
    ax.set_title('Priority Queue — la bassa priorita\' muore di fame',
                 fontsize=14, fontweight='bold')
    ax.legend(fontsize=11, framealpha=0.3)
    ax.grid(True, alpha=0.3)

    # Annotazione
    if len(low_waits) > 25 and low_waits[25] > 0:
        ax.annotate(f'rapporto: {ratio[25]:.0f}x', xy=(rho_values[25], low_waits[25]),
                    xytext=(rho_values[25] - 0.15, low_waits[25] * 0.7),
                    fontsize=11, color='#ff6b6b',
                    arrowprops=dict(arrowstyle='->', color='#ff6b6b', lw=1.5))

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '08_priority_starvation.png'), dpi=180)
    print(f'[+] output/08_priority_starvation.png')
    plt.close()


def simulate_mm1_vs_theory():
    """
    Confronto: simulazione M/M/1 vs formula teorica E[W] = rho / (mu * (1-rho)).
    """
    rho_values = np.linspace(0.1, 0.95, 18)
    SERVICE_RATE = 1.0
    N_CUSTOMERS = 50_000

    sim_waits = []
    theory_waits = []

    for rho in rho_values:
        arrival_rate = rho * SERVICE_RATE

        # Teoria
        ew_theory = rho / (SERVICE_RATE * (1 - rho))
        theory_waits.append(ew_theory)

        # Simulazione
        inter_arrivals = np.random.exponential(1 / arrival_rate, N_CUSTOMERS)
        service_times = np.random.exponential(1 / SERVICE_RATE, N_CUSTOMERS)
        arrivals = np.cumsum(inter_arrivals)

        waits = np.zeros(N_CUSTOMERS)
        departure = 0

        for i in range(N_CUSTOMERS):
            if arrivals[i] < departure:
                waits[i] = departure - arrivals[i]
            departure = arrivals[i] + waits[i] + service_times[i]

        # Scarta warm-up
        sim_waits.append(np.mean(waits[1000:]))

    fig, ax = plt.subplots(figsize=(12, 7))

    ax.plot(rho_values, theory_waits, color='#7c4dff', linewidth=2.5,
            label='Teoria M/M/1: E[W] = rho / mu(1-rho)', linestyle='--')
    ax.scatter(rho_values, sim_waits, color='#00ff88', s=60, zorder=5,
               label='Simulazione Monte Carlo (50k clienti)', edgecolors='white', linewidth=0.5)

    ax.set_xlabel('rho', fontsize=13)
    ax.set_ylabel('tempo medio in coda', fontsize=13)
    ax.set_title('Teoria vs Simulazione — M/M/1', fontsize=14, fontweight='bold')
    ax.legend(fontsize=10, framealpha=0.3)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, max(theory_waits) * 1.1)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '09_mm1_simulation.png'), dpi=180)
    print(f'[+] output/09_mm1_simulation.png')
    plt.close()


if __name__ == '__main__':
    simulate_inspection_paradox()
    simulate_priority_starvation()
    simulate_mm1_vs_theory()
