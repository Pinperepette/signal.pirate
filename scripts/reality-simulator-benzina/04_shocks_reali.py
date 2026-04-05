#!/usr/bin/env python3
"""
04_shocks_reali.py — Eventi shock veri e risposta del sistema.

Identifico automaticamente gli shock storici reali sul Brent (drawup o
drawdown > 20% in 60 giorni) e mostro come ha risposto la benzina Italia.

Eventi attesi:
  - 2008 H1: bolla speculativa Brent $147
  - 2008 H2: crollo Lehman
  - 2011: primavera araba / Libia
  - 2014: shale oil glut
  - 2016: recovery post-crash
  - 2020: COVID crash Brent a $9
  - 2022: invasione Ucraina
  - 2025/2026: eventi recenti

Per ogni evento misuro: ampiezza shock Brent, ampiezza risposta benzina,
half-life di trasmissione, asimmetria tra shock positivi/negativi.

Output: output/08_shocks_reali.png
        output/09_event_study.png
"""
import csv
from datetime import datetime, timedelta
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os

OUTPUT_DIR = 'output'
os.makedirs(OUTPUT_DIR, exist_ok=True)

plt.rcParams.update({
    'figure.facecolor': '#0d1117', 'axes.facecolor': '#0d1117',
    'axes.edgecolor': '#30363d', 'axes.labelcolor': '#c9d1d9',
    'text.color': '#c9d1d9', 'xtick.color': '#8b949e',
    'ytick.color': '#8b949e', 'grid.color': '#21262d',
    'font.family': 'monospace', 'font.size': 10,
})


def load_data():
    with open('data/brent.csv') as f:
        brent = [(datetime.strptime(r['observation_date'], '%Y-%m-%d'),
                  float(r['DCOILBRENTEU'])) for r in csv.DictReader(f)
                 if r['DCOILBRENTEU'] not in ('', '.')]
    with open('data/italy_prices_wo_tax.csv') as f:
        net = [(datetime.strptime(r['date'], '%Y-%m-%d'),
                float(r['benzina_net_eur_L'])) for r in csv.DictReader(f)
               if r['benzina_net_eur_L']]
    net.sort(key=lambda x: x[0])
    return brent, net


def detect_shocks(brent, window=60, threshold=0.20):
    """Identifica shock: variazione > threshold in 'window' giorni."""
    brent.sort(key=lambda x: x[0])
    dates = [b[0] for b in brent]
    vals = np.array([b[1] for b in brent])
    shocks = []
    i = 0
    while i < len(vals) - window:
        start_val = vals[i]
        end_val = vals[i + window]
        change = (end_val - start_val) / start_val
        if abs(change) >= threshold:
            # Trova il minimo/massimo locale
            segment = vals[i:i+window+1]
            if change > 0:
                peak_idx = i + int(np.argmax(segment))
            else:
                peak_idx = i + int(np.argmin(segment))
            shocks.append({
                'start_date': dates[i],
                'peak_date': dates[peak_idx],
                'start_val': float(start_val),
                'peak_val': float(vals[peak_idx]),
                'change': float((vals[peak_idx] - start_val) / start_val),
                'direction': 'UP' if change > 0 else 'DN',
            })
            i = peak_idx + 30  # skip ahead per evitare overlap
        else:
            i += 10
    return shocks


def plot_shocks_overview(brent, net, shocks):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 9), sharex=True)
    b_dates = [b[0] for b in brent if b[0].year >= 2005]
    b_vals = [b[1] for b in brent if b[0].year >= 2005]
    ax1.plot(b_dates, b_vals, color='#ff8800', linewidth=0.8)
    ax1.fill_between(b_dates, 0, b_vals, color='#ff8800', alpha=0.1)

    # Marca shocks
    for s in shocks:
        if s['start_date'].year < 2005:
            continue
        color = '#ff6b6b' if s['direction'] == 'UP' else '#00ff88'
        ax1.axvspan(s['start_date'], s['peak_date'], color=color, alpha=0.15)
        y = s['peak_val']
        ax1.annotate(f'{s["change"]*100:+.0f}%',
                     xy=(s['peak_date'], y),
                     xytext=(s['peak_date'], y + 15),
                     color=color, fontsize=8, ha='center',
                     arrowprops=dict(arrowstyle='->', color=color, lw=0.5))
    ax1.set_ylabel('Brent (USD/bbl)')
    ax1.set_title(f'Shock reali identificati 2005-2026 '
                  f'(drawup/drawdown >20% in 60gg) — n={sum(1 for s in shocks if s["start_date"].year>=2005)}',
                  color='#00ff88', fontsize=12)
    ax1.grid(alpha=0.3)

    n_dates = [x[0] for x in net]
    n_vals = [x[1] for x in net]
    ax2.plot(n_dates, n_vals, color='#7c4dff', linewidth=1.2,
             label='benzina netto Italia')
    for s in shocks:
        if s['start_date'].year < 2005:
            continue
        color = '#ff6b6b' if s['direction'] == 'UP' else '#00ff88'
        ax2.axvspan(s['start_date'], s['peak_date'], color=color, alpha=0.15)
    ax2.set_ylabel('Benzina netto (EUR/L)')
    ax2.set_xlabel('Data')
    ax2.set_title('Risposta benzina netto Italia (bande = periodi shock)',
                  color='#00ff88', fontsize=12)
    ax2.legend(facecolor='#161b22', edgecolor='#30363d', labelcolor='#c9d1d9')
    ax2.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/08_shocks_reali.png', dpi=120,
                facecolor='#0d1117', bbox_inches='tight')
    plt.close()
    print(f'[+] {OUTPUT_DIR}/08_shocks_reali.png')


def event_study(brent, net, shocks):
    """Per shock UP vs DN, stima la risposta media normalizzata."""
    brent.sort(key=lambda x: x[0])
    b_dict = dict(brent)
    b_dates_sorted = sorted(b_dict.keys())

    def brent_at(d):
        # trova Brent a data d (o piu' vicino)
        for offset in range(10):
            for sign in [0, -1, 1]:
                dd = d + timedelta(days=sign*offset)
                if dd in b_dict:
                    return b_dict[dd]
        return None

    # Normalize curves: T0 = start_date, guarda +/- 90gg
    def build_event_curves(event_list, series, window_days=120):
        curves = []
        for s in event_list:
            t0 = s['start_date']
            vals_rel = []
            dates_rel = []
            # series is a list of (date, val)
            for d, v in series:
                delta = (d - t0).days
                if -20 <= delta <= window_days:
                    dates_rel.append(delta)
                    vals_rel.append(v)
            if not vals_rel:
                continue
            # normalize to 100 at day 0 (closest)
            base_idx = int(np.argmin([abs(dd) for dd in dates_rel]))
            base = vals_rel[base_idx]
            vals_norm = [v/base*100 for v in vals_rel]
            curves.append(list(zip(dates_rel, vals_norm)))
        return curves

    shocks_recent = [s for s in shocks if s['start_date'].year >= 2005]
    up_shocks = [s for s in shocks_recent if s['direction'] == 'UP']
    dn_shocks = [s for s in shocks_recent if s['direction'] == 'DN']

    brent_list = [(d, v) for d, v in brent if d.year >= 2004]
    up_brent_curves = build_event_curves(up_shocks, brent_list)
    dn_brent_curves = build_event_curves(dn_shocks, brent_list)
    up_net_curves = build_event_curves(up_shocks, net)
    dn_net_curves = build_event_curves(dn_shocks, net)

    def avg_curve(curves, grid=None):
        """Interpola ogni curva su una griglia regolare e media."""
        if grid is None:
            grid = np.arange(-20, 121, 1)
        valid_curves = []
        for c in curves:
            xs = [x for x, _ in c]
            ys = [v for _, v in c]
            if len(xs) < 3:
                continue
            order = np.argsort(xs)
            xs = [xs[i] for i in order]
            ys = [ys[i] for i in order]
            # interpola
            interp = np.interp(grid, xs, ys, left=np.nan, right=np.nan)
            valid_curves.append(interp)
        if not valid_curves:
            return [], []
        arr = np.array(valid_curves)
        with np.errstate(all='ignore'):
            means = np.nanmean(arr, axis=0)
        mask = ~np.isnan(means)
        return list(grid[mask]), list(means[mask])

    ub_x, ub_y = avg_curve(up_brent_curves)
    un_x, un_y = avg_curve(up_net_curves)
    db_x, db_y = avg_curve(dn_brent_curves)
    dn_x, dn_y = avg_curve(dn_net_curves)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), sharey=True)

    ax1.plot(ub_x, ub_y, color='#ff8800', linewidth=2.5, label='Brent')
    ax1.plot(un_x, un_y, color='#7c4dff', linewidth=2.5,
             label='benzina netto Italia')
    ax1.axhline(100, color='#30363d', linewidth=0.8)
    ax1.axvline(0, color='#ffcc00', linewidth=1, linestyle='--',
                label='inizio shock')
    ax1.set_xlabel('Giorni dall\'inizio shock')
    ax1.set_ylabel('Livello normalizzato (T0=100)')
    ax1.set_title(f'SHOCK POSITIVI (Brent sale) — n={len(up_shocks)}',
                  color='#ff6b6b', fontsize=12)
    ax1.legend(facecolor='#161b22', edgecolor='#30363d', labelcolor='#c9d1d9')
    ax1.grid(alpha=0.3)

    ax2.plot(db_x, db_y, color='#ff8800', linewidth=2.5, label='Brent')
    ax2.plot(dn_x, dn_y, color='#7c4dff', linewidth=2.5,
             label='benzina netto Italia')
    ax2.axhline(100, color='#30363d', linewidth=0.8)
    ax2.axvline(0, color='#ffcc00', linewidth=1, linestyle='--',
                label='inizio shock')
    ax2.set_xlabel('Giorni dall\'inizio shock')
    ax2.set_title(f'SHOCK NEGATIVI (Brent scende) — n={len(dn_shocks)}',
                  color='#00ff88', fontsize=12)
    ax2.legend(facecolor='#161b22', edgecolor='#30363d', labelcolor='#c9d1d9')
    ax2.grid(alpha=0.3)

    # Calcola risposta media a 30gg
    def val_at(xs, ys, target):
        if not xs: return None
        idx = int(np.argmin([abs(x-target) for x in xs]))
        return ys[idx]

    b30_up = val_at(ub_x, ub_y, 30)
    n30_up = val_at(un_x, un_y, 30)
    b30_dn = val_at(db_x, db_y, 30)
    n30_dn = val_at(dn_x, dn_y, 30)
    has_all = all(v is not None for v in [b30_up, n30_up, b30_dn, n30_dn])
    if has_all:
        print(f'    A 30gg da shock UP: Brent {b30_up:.1f}  netto {n30_up:.1f}  '
              f'trasmissione {(n30_up-100)/(b30_up-100)*100:.0f}%')
        print(f'    A 30gg da shock DN: Brent {b30_dn:.1f}  netto {n30_dn:.1f}  '
              f'trasmissione {(n30_dn-100)/(b30_dn-100)*100:.0f}%')
        ax1.annotate(f'+30gg:\nBrent {b30_up-100:+.0f}%  netto {n30_up-100:+.0f}%\n'
                     f'trasmissione {(n30_up-100)/(b30_up-100)*100:.0f}%',
                     xy=(30, n30_up), xytext=(50, 108),
                     color='#ffcc00', fontsize=9,
                     arrowprops=dict(arrowstyle='->', color='#ffcc00'))
        ax2.annotate(f'+30gg:\nBrent {b30_dn-100:+.0f}%  netto {n30_dn-100:+.0f}%\n'
                     f'trasmissione {(n30_dn-100)/(b30_dn-100)*100:.0f}%',
                     xy=(30, n30_dn), xytext=(50, 92),
                     color='#ffcc00', fontsize=9,
                     arrowprops=dict(arrowstyle='->', color='#ffcc00'))

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/09_event_study.png', dpi=120,
                facecolor='#0d1117', bbox_inches='tight')
    plt.close()
    print(f'[+] {OUTPUT_DIR}/09_event_study.png')


if __name__ == '__main__':
    print('=' * 60)
    print(' Event study: shock reali Brent e risposta benzina')
    print('=' * 60)
    brent, net = load_data()
    shocks = detect_shocks(brent, window=60, threshold=0.20)
    print(f'[i] {len(shocks)} shock totali (|Δ|>20% in 60gg)')
    for s in shocks[-10:]:
        print(f'    {s["start_date"].date()} -> {s["peak_date"].date()}: '
              f'{s["direction"]} {s["change"]*100:+.1f}%')
    plot_shocks_overview(brent, net, shocks)
    event_study(brent, net, shocks)
    print('=' * 60)
