#!/usr/bin/env python3
"""
14_hawkes_process.py — Processi di Hawkes: auto-eccitazione nel feed.

Modella il flusso dei tweet come processo auto-eccitante:
  lambda(t) = mu + sum_{ti<t} alpha * exp(-beta * (t - ti))

Un tweet genera engagement, aumenta la probabilita' di essere mostrato,
genera altro engagement. Il "Per Te" dovrebbe avere alpha piu' alta
(piu' auto-eccitazione), il "Seguiti" dovrebbe essere piu' Poisson.

Calcola:
  1. Fit parametri mu, alpha, beta per ciascun feed
  2. Intensita' stimata lambda(t) nel tempo
  3. Branching ratio n = alpha/beta (se > 1 = supercritico)
  4. Confronto visuale processo reale vs Poisson

Output:
    output/62_hawkes_intensity.png
    output/63_hawkes_branching_ratio.png
    output/64_hawkes_interevent.png
    output/65_hawkes_qq_poisson.png
    output/stats_hawkes.json
"""

import json
import os
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from scipy.optimize import minimize

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


def extract_event_times():
    """Estrai timestamp di comparsa nel feed (collected_at) come eventi."""
    from pymongo import MongoClient
    client = MongoClient('mongodb://localhost:27017')
    db = client['SnareData']

    feeds = {}
    for feed_label, coll_name in [('per_te', 'twitter_per-te'), ('seguiti', 'twitter_seguiti')]:
        times = []
        for doc in db[coll_name].find().limit(800):
            data = doc.get('data', {})
            ts = data.get('timestamp_collected')
            if ts:
                try:
                    times.append(int(ts) / 1000.0)  # epoch seconds
                except Exception:
                    pass
        times.sort()
        feeds[feed_label] = np.array(times)

    client.close()
    return feeds


def hawkes_loglik(params, times):
    """Log-likelihood negativa per processo Hawkes univariato."""
    mu, alpha, beta = params
    if mu <= 0 or alpha < 0 or beta <= 0 or alpha >= beta:
        return 1e10

    T = times[-1] - times[0]
    n = len(times)

    # Intensita' cumulata
    loglik = 0
    A = 0  # somma dei kernel
    for i in range(n):
        if i > 0:
            A = np.exp(-beta * (times[i] - times[i-1])) * (1 + A)
        lam = mu + alpha * A
        if lam <= 0:
            return 1e10
        loglik += np.log(lam)

    # Termine integrale
    integral = mu * T
    for i in range(n):
        integral += (alpha / beta) * (1 - np.exp(-beta * (times[-1] - times[i])))

    return -(loglik - integral)


def fit_hawkes(times):
    """Fitta parametri Hawkes via MLE."""
    # Normalizza tempi a partire da 0
    t0 = times[0]
    times_norm = times - t0

    # Rate empirico come init per mu
    T = times_norm[-1]
    n = len(times_norm)
    mu0 = n / T * 0.5
    alpha0 = 0.5
    beta0 = 1.0

    result = minimize(
        hawkes_loglik,
        [mu0, alpha0, beta0],
        args=(times_norm,),
        method='Nelder-Mead',
        options={'maxiter': 5000, 'xatol': 1e-8, 'fatol': 1e-8}
    )

    mu, alpha, beta = result.x
    branching_ratio = alpha / beta if beta > 0 else 0

    return {
        'mu': float(mu),
        'alpha': float(alpha),
        'beta': float(beta),
        'branching_ratio': float(branching_ratio),
        'loglik': float(-result.fun),
        'success': result.success,
    }


def compute_intensity(times, mu, alpha, beta, n_points=500):
    """Calcola lambda(t) su una griglia."""
    t0 = times[0]
    times_norm = times - t0
    T = times_norm[-1]

    t_grid = np.linspace(0, T, n_points)
    lam = np.zeros(n_points)

    for i, t in enumerate(t_grid):
        past = times_norm[times_norm < t]
        lam[i] = mu + alpha * np.sum(np.exp(-beta * (t - past)))

    return t_grid, lam


def plot_hawkes_intensity(feeds, params, stats):
    """1. Intensita' stimata lambda(t)."""
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=False)
    fig.suptitle('Intensita\' Hawkes lambda(t): Auto-Eccitazione nel Feed',
                 fontsize=14, fontweight='bold')

    for ax, (feed, label, color) in zip(axes, [
        ('per_te', 'Per Te', ACCENT_1),
        ('seguiti', 'Seguiti', ACCENT_2),
    ]):
        times = feeds[feed]
        p = params[feed]

        t_grid, lam = compute_intensity(times, p['mu'], p['alpha'], p['beta'])

        ax.plot(t_grid, lam, color=color, linewidth=1, alpha=0.8)
        ax.axhline(y=p['mu'], color='#ffffff', linestyle='--', alpha=0.3,
                   label=f'mu (base) = {p["mu"]:.2f}')
        ax.fill_between(t_grid, p['mu'], lam, alpha=0.15, color=color)

        ax.set_ylabel('lambda(t) (eventi/sec)')
        ax.set_title(f'{label} — alpha={p["alpha"]:.3f}, beta={p["beta"]:.3f}, '
                     f'n*={p["branching_ratio"]:.3f}',
                     fontsize=10)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.2)

    axes[1].set_xlabel('Tempo (secondi dall\'inizio dello scroll)')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '62_hawkes_intensity.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 62_hawkes_intensity.png')


def plot_branching_ratio(params, stats):
    """2. Branching ratio confronto."""
    fig, ax = plt.subplots(figsize=(8, 5))

    feeds_list = [('per_te', 'Per Te', ACCENT_1), ('seguiti', 'Seguiti', ACCENT_2)]
    names = [l for _, l, _ in feeds_list]
    ratios = [params[f]['branching_ratio'] for f, _, _ in feeds_list]
    colors = [c for _, _, c in feeds_list]

    bars = ax.bar(names, ratios, color=colors, edgecolor='none', width=0.4)
    for bar, val in zip(bars, ratios):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                f'{val:.3f}', ha='center', fontsize=12, color='#e0e0e0')

    ax.axhline(y=1.0, color='#ff6b6b', linestyle='--', alpha=0.5,
               label='n* = 1 (soglia critica)')
    ax.set_ylabel('Branching Ratio n* = alpha / beta')
    ax.set_title('Branching Ratio: Quanto il Feed Si Auto-Amplifica\n'
                 '(n* > 1 = processo esplosivo, n* < 1 = stazionario)',
                 fontsize=12, fontweight='bold')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '63_hawkes_branching_ratio.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 63_hawkes_branching_ratio.png')


def plot_interevent(feeds, stats):
    """3. Distribuzione inter-event times vs esponenziale (Poisson)."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Tempi Inter-Evento: Hawkes vs Poisson',
                 fontsize=13, fontweight='bold')

    for ax, (feed, label, color) in zip(axes, [
        ('per_te', 'Per Te', ACCENT_1),
        ('seguiti', 'Seguiti', ACCENT_2),
    ]):
        times = feeds[feed]
        iet = np.diff(times)
        iet = iet[iet > 0]

        # Istogramma empirico
        bins = np.linspace(0, np.percentile(iet, 95), 40)
        ax.hist(iet, bins=bins, density=True, alpha=0.5, color=color, label='Dati')

        # Esponenziale attesa (Poisson)
        lam = 1.0 / np.mean(iet)
        x_exp = np.linspace(0, bins[-1], 100)
        ax.plot(x_exp, lam * np.exp(-lam * x_exp), color='#ffffff', linewidth=2,
                linestyle='--', label=f'Poisson (lambda={lam:.2f})')

        ax.set_xlabel('Tempo inter-evento (sec)')
        ax.set_ylabel('Densita\'')
        ax.set_title(label, fontsize=11)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.2)

        # Coefficiente di variazione (CV > 1 = clustering)
        cv = np.std(iet) / np.mean(iet)
        stats[f'{feed}_cv_interevent'] = round(float(cv), 4)
        ax.text(0.95, 0.95, f'CV = {cv:.2f}\n(>1 = clustering)',
                transform=ax.transAxes, fontsize=9, ha='right', va='top',
                bbox=dict(boxstyle='round', facecolor='#1a1a2e', alpha=0.8))

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '64_hawkes_interevent.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 64_hawkes_interevent.png')


def plot_qq_poisson(feeds, stats):
    """4. QQ plot: tempi riscalati vs Exp(1) — test di Poissonianita'."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle('QQ Plot: Tempi Riscalati vs Esponenziale\n'
                 '(se Poisson: punti sulla diagonale)',
                 fontsize=12, fontweight='bold')

    for ax, (feed, label, color) in zip(axes, [
        ('per_te', 'Per Te', ACCENT_1),
        ('seguiti', 'Seguiti', ACCENT_2),
    ]):
        times = feeds[feed]
        iet = np.diff(times)
        iet = iet[iet > 0]

        # Riscala per rate medio
        lam = 1.0 / np.mean(iet)
        rescaled = np.sort(lam * iet)
        n = len(rescaled)
        theoretical = -np.log(1 - np.arange(1, n + 1) / (n + 1))

        ax.scatter(theoretical, rescaled, alpha=0.3, s=5, color=color, edgecolors='none')
        max_val = max(theoretical.max(), rescaled.max())
        ax.plot([0, max_val], [0, max_val], color='#ffffff', linestyle='--', alpha=0.5)

        ax.set_xlabel('Quantili teorici Exp(1)')
        ax.set_ylabel('Quantili empirici')
        ax.set_title(label, fontsize=11)
        ax.grid(True, alpha=0.2)
        ax.set_aspect('equal')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '65_hawkes_qq_poisson.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('[+] 65_hawkes_qq_poisson.png')


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print('[*] Estrazione tempi eventi...')
    feeds = extract_event_times()
    for feed, times in feeds.items():
        print(f'    {feed}: {len(times)} eventi, span {times[-1]-times[0]:.1f}s')

    print('[*] Fit Hawkes...')
    params = {}
    stats = {}
    for feed in ['per_te', 'seguiti']:
        p = fit_hawkes(feeds[feed])
        params[feed] = p
        print(f'    {feed}: mu={p["mu"]:.4f}, alpha={p["alpha"]:.4f}, '
              f'beta={p["beta"]:.4f}, n*={p["branching_ratio"]:.4f}')
        for k, v in p.items():
            stats[f'{feed}_{k}'] = v if isinstance(v, bool) else round(float(v), 6) if isinstance(v, float) else v

    plot_hawkes_intensity(feeds, params, stats)
    plot_branching_ratio(params, stats)
    plot_interevent(feeds, stats)
    plot_qq_poisson(feeds, stats)

    with open(os.path.join(OUTPUT_DIR, 'stats_hawkes.json'), 'w') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f'[✓] Stats salvate in {OUTPUT_DIR}/stats_hawkes.json')


if __name__ == '__main__':
    main()
