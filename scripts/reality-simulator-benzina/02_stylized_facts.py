#!/usr/bin/env python3
"""
02_stylized_facts.py — Fatti stilizzati empirici su dati veri.

Cosa fa:
  1) Serie Brent (FRED, daily 1987-2026) vs benzina pompa Italia (EU bulletin,
     weekly 2005-2026) vs netto (pre-tasse).
  2) Distribuzione dei rendimenti: gaussiana? No. Fat tails, skew positivo.
  3) Correlazione Brent -> pompa, con lag.
  4) Volatility clustering: i periodi turbolenti si aggregano.

Output: output/03_serie_storiche.png
        output/04_rendimenti_distribuzione.png
        output/05_correlazione_lag.png
"""
import csv
from datetime import datetime, timedelta
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
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


def load_all():
    with open('data/brent.csv') as f:
        brent = [(datetime.strptime(r['observation_date'], '%Y-%m-%d'),
                  float(r['DCOILBRENTEU'])) for r in csv.DictReader(f)
                 if r['DCOILBRENTEU'] not in ('', '.')]
    with open('data/eurusd.csv') as f:
        fx = {datetime.strptime(r['observation_date'], '%Y-%m-%d'):
              float(r['DEXUSEU']) for r in csv.DictReader(f)
              if r['DEXUSEU'] not in ('', '.')}
    with open('data/italy_prices_with_tax.csv') as f:
        pump = [(datetime.strptime(r['date'], '%Y-%m-%d'),
                 float(r['benzina_eur_L'])) for r in csv.DictReader(f)
                if r['benzina_eur_L']]
    with open('data/italy_prices_wo_tax.csv') as f:
        net = [(datetime.strptime(r['date'], '%Y-%m-%d'),
                float(r['benzina_net_eur_L'])) for r in csv.DictReader(f)
               if r['benzina_net_eur_L']]
    return brent, fx, pump, net


def weekly_brent_eur(brent_list, fx_dict, weekly_dates):
    """Per ogni data settimanale della serie benzina, prendi il Brent in EUR
    della settimana precedente (average)."""
    brent_by_date = dict(brent_list)
    out = []
    sorted_brent = sorted(brent_list, key=lambda x: x[0])
    brent_dates = [b[0] for b in sorted_brent]
    brent_vals = [b[1] for b in sorted_brent]
    for wd in weekly_dates:
        # Brent media dei 7 giorni precedenti
        window_end = wd
        window_start = wd - timedelta(days=7)
        vals_in = [v for d, v in zip(brent_dates, brent_vals)
                   if window_start <= d <= window_end]
        if not vals_in:
            out.append(None)
            continue
        mean_usd = float(np.mean(vals_in))
        # fx media
        fx_in = [fx_dict[d] for d in fx_dict
                 if window_start <= d <= window_end]
        mean_fx = float(np.mean(fx_in)) if fx_in else 1.1
        out.append(mean_usd / mean_fx)  # EUR/bbl
    return out


def plot_series(brent, pump, net):
    dates_p = [x[0] for x in pump]
    vals_p = np.array([x[1] for x in pump])
    vals_n = np.array([x[1] for x in net])
    dates_b = [x[0] for x in brent if x[0].year >= 2005]
    vals_b = np.array([x[1] for x in brent if x[0].year >= 2005])

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    axes[0].plot(dates_b, vals_b, color='#ff8800', linewidth=0.8)
    axes[0].fill_between(dates_b, 0, vals_b, color='#ff8800', alpha=0.15)
    axes[0].set_ylabel('Brent (USD/bbl)')
    axes[0].set_title('Dati reali: Brent (FRED daily) vs benzina Italia '
                      '(EU Weekly Oil Bulletin 2005-2026)',
                      color='#00ff88', fontsize=12)
    axes[0].grid(alpha=0.3)

    axes[1].plot(dates_p, vals_p, color='#7c4dff', linewidth=1.2,
                 label='pompa (con tasse)')
    axes[1].plot(dates_p, vals_n, color='#00ff88', linewidth=1.2,
                 label='netto (senza tasse)')
    axes[1].set_ylabel('EUR / Litro')
    axes[1].legend(loc='upper left', facecolor='#161b22',
                   edgecolor='#30363d', labelcolor='#c9d1d9')
    axes[1].grid(alpha=0.3)

    # Rapporto pompa/netto (proxy della quota fiscale)
    ratio = vals_p / vals_n
    axes[2].plot(dates_p, ratio, color='#ff6b6b', linewidth=1.5)
    axes[2].fill_between(dates_p, 1, ratio, color='#ff6b6b', alpha=0.15)
    axes[2].set_ylabel('Pompa / Netto')
    axes[2].set_xlabel('Data')
    axes[2].set_title('Moltiplicatore fiscale: quante volte la pompa supera il netto',
                      color='#00ff88', fontsize=12)
    axes[2].grid(alpha=0.3)
    axes[2].annotate(f'max {ratio.max():.2f}x\n'
                     f'({dates_p[int(np.argmax(ratio))].strftime("%b %Y")})',
                     xy=(dates_p[int(np.argmax(ratio))], ratio.max()),
                     xytext=(dates_p[int(np.argmax(ratio))],
                             ratio.max() + 0.3),
                     color='#ffcc00', fontsize=9,
                     arrowprops=dict(arrowstyle='->', color='#ffcc00'),
                     ha='center')

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/03_serie_storiche.png', dpi=120,
                facecolor='#0d1117', bbox_inches='tight')
    plt.close()
    print(f'[+] {OUTPUT_DIR}/03_serie_storiche.png')
    print(f'    Moltiplicatore fiscale: min {ratio.min():.2f}x, '
          f'max {ratio.max():.2f}x, mediana {np.median(ratio):.2f}x')


def plot_returns_distribution(brent, pump, net):
    # Rendimenti settimanali
    vals_p = np.array([x[1] for x in pump])
    vals_n = np.array([x[1] for x in net])
    # Brent settimanale: media ogni 7gg
    brent_sorted = sorted(brent)
    brent_weekly = []
    for i in range(0, len(brent_sorted) - 7, 7):
        brent_weekly.append(np.mean([b[1] for b in brent_sorted[i:i+7]]))
    brent_weekly = np.array(brent_weekly)

    ret_brent = np.diff(np.log(brent_weekly)) * 100
    ret_pump = np.diff(np.log(vals_p[::-1])) * 100  # oldest first
    ret_net = np.diff(np.log(vals_n[::-1])) * 100

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    for ax, data, title, color in [
        (axes[0], ret_brent, 'Brent settimanale', '#ff8800'),
        (axes[1], ret_net, 'Benzina netto', '#00ff88'),
        (axes[2], ret_pump, 'Benzina pompa', '#7c4dff'),
    ]:
        mu = float(np.mean(data))
        sigma = float(np.std(data))
        skew = float(np.mean(((data - mu) / sigma) ** 3))
        kurt = float(np.mean(((data - mu) / sigma) ** 4))
        ax.hist(data, bins=70, color=color, alpha=0.7,
                edgecolor='#0d1117', density=True)
        # Gaussian overlay
        x = np.linspace(data.min(), data.max(), 200)
        gauss = np.exp(-0.5 * ((x - mu) / sigma) ** 2) / \
                (sigma * np.sqrt(2 * np.pi))
        ax.plot(x, gauss, color='#c9d1d9', linewidth=2,
                label='gaussiana (stesso μ,σ)')
        ax.set_title(f'{title}\n'
                     f'σ={sigma:.2f}%  skew={skew:+.2f}  kurtosis={kurt:.1f}',
                     color='#00ff88', fontsize=11)
        ax.set_xlabel('Rendimento settimanale log (%)')
        ax.set_ylabel('Densita\'')
        ax.legend(facecolor='#161b22', edgecolor='#30363d',
                  labelcolor='#c9d1d9', fontsize=9)
        ax.grid(alpha=0.3)
        print(f'    {title}: σ={sigma:.2f}% skew={skew:+.2f} kurt={kurt:.1f}')

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/04_rendimenti_distribuzione.png', dpi=120,
                facecolor='#0d1117', bbox_inches='tight')
    plt.close()
    print(f'[+] {OUTPUT_DIR}/04_rendimenti_distribuzione.png')


def plot_lag_correlation(brent, fx, pump, net):
    """Cross-correlation tra rendimenti Brent-EUR e rendimenti netto benzina."""
    dates_p = [x[0] for x in pump][::-1]  # oldest first
    vals_p = np.array([x[1] for x in pump[::-1]])
    vals_n = np.array([x[1] for x in net[::-1]])
    brent_eur = weekly_brent_eur(brent, fx, dates_p)
    # filter where all exist
    mask = np.array([b is not None for b in brent_eur])
    brent_eur = np.array([b for b in brent_eur if b is not None])
    vals_p = vals_p[mask]; vals_n = vals_n[mask]

    ret_b = np.diff(np.log(brent_eur))
    ret_p = np.diff(np.log(vals_p))
    ret_n = np.diff(np.log(vals_n))

    # Correlazioni condizionate per segno del delta Brent
    max_lag = 12
    lags = np.arange(0, max_lag + 1)
    corr_up_net = []; corr_dn_net = []
    corr_up_pump = []; corr_dn_pump = []
    for lag in lags:
        if lag == 0:
            rb, rp, rn = ret_b, ret_p, ret_n
        else:
            rb = ret_b[:-lag]; rp = ret_p[lag:]; rn = ret_n[lag:]
        mup = rb > 0; mdn = rb < 0
        corr_up_net.append(np.corrcoef(rb[mup], rn[mup])[0, 1]
                           if mup.sum() > 5 else 0)
        corr_dn_net.append(np.corrcoef(rb[mdn], rn[mdn])[0, 1]
                           if mdn.sum() > 5 else 0)
        corr_up_pump.append(np.corrcoef(rb[mup], rp[mup])[0, 1]
                            if mup.sum() > 5 else 0)
        corr_dn_pump.append(np.corrcoef(rb[mdn], rp[mdn])[0, 1]
                            if mdn.sum() > 5 else 0)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    w = 0.35
    for ax, up, dn, title in [
        (ax1, corr_up_net, corr_dn_net, 'Netto (pre-tasse)'),
        (ax2, corr_up_pump, corr_dn_pump, 'Pompa (con tasse)'),
    ]:
        ax.bar(lags - w/2, up, w, color='#ff6b6b', edgecolor='#0d1117',
               label='Brent SALE')
        ax.bar(lags + w/2, dn, w, color='#00ff88', edgecolor='#0d1117',
               label='Brent SCENDE')
        ax.set_xlabel('Lag (settimane)')
        ax.set_ylabel('Correlazione condizionata')
        ax.set_title(f'Risposta benzina {title} al Brent',
                     color='#00ff88', fontsize=11)
        ax.legend(facecolor='#161b22', edgecolor='#30363d',
                  labelcolor='#c9d1d9')
        ax.grid(alpha=0.3); ax.axhline(0, color='#30363d', linewidth=0.8)

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/05_correlazione_lag.png', dpi=120,
                facecolor='#0d1117', bbox_inches='tight')
    plt.close()
    print(f'[+] {OUTPUT_DIR}/05_correlazione_lag.png')
    # Indici di asimmetria
    avg_up = float(np.mean(corr_up_net[:4]))
    avg_dn = float(np.mean(corr_dn_net[:4]))
    print(f'    Correlazione media (0-3 wk lag) netto: '
          f'UP={avg_up:.3f} DN={avg_dn:.3f} asimm={avg_up/abs(avg_dn):.2f}x'
          if abs(avg_dn) > 0 else '')


if __name__ == '__main__':
    print('=' * 60)
    print(' Fatti stilizzati su dati reali')
    print('=' * 60)
    brent, fx, pump, net = load_all()
    print(f'[i] {len(brent)} daily Brent, {len(pump)} settimane Italia')
    plot_series(brent, pump, net)
    plot_returns_distribution(brent, pump, net)
    plot_lag_correlation(brent, fx, pump, net)
    print('=' * 60)
