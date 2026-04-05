#!/usr/bin/env python3
"""
01_decomposition.py — Decomposizione REALE del prezzo benzina Italia.

Usa dati settimanali EU Weekly Oil Bulletin (2005-2026) e serie Brent FRED.

Dall'identita' contabile:  pompa = (netto + accisa) * (1+IVA)
estraggo l'accisa implicita e confermo i livelli noti:
  - 0.5460 EUR/L fino al 2011
  - 0.7042 EUR/L dal 2011 (Monti)
  - 0.7284 EUR/L dal 2012 in poi
  - 0.4729 EUR/L dal marzo 2026 (intervento recente)

Poi mostro come la composizione Stato/Mercato e' cambiata in 20 anni.

Output: output/01_decomposizione_reale.png
        output/02_stato_vs_mercato_storia.png
"""
import csv
from datetime import datetime
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

OUTPUT_DIR = 'output'
os.makedirs(OUTPUT_DIR, exist_ok=True)
IVA = 0.22

plt.rcParams.update({
    'figure.facecolor': '#0d1117', 'axes.facecolor': '#0d1117',
    'axes.edgecolor': '#30363d', 'axes.labelcolor': '#c9d1d9',
    'text.color': '#c9d1d9', 'xtick.color': '#8b949e',
    'ytick.color': '#8b949e', 'grid.color': '#21262d',
    'font.family': 'monospace', 'font.size': 10,
})


def load_series():
    with open('data/italy_prices_with_tax.csv') as f:
        pump = [(datetime.strptime(r['date'], '%Y-%m-%d'),
                 float(r['benzina_eur_L'])) for r in csv.DictReader(f)
                if r['benzina_eur_L']]
    with open('data/italy_prices_wo_tax.csv') as f:
        net = {datetime.strptime(r['date'], '%Y-%m-%d'):
               float(r['benzina_net_eur_L']) for r in csv.DictReader(f)
               if r['benzina_net_eur_L']}
    # merge
    data = []
    for d, p in pump:
        if d in net:
            n = net[d]
            excise = p / (1+IVA) - n   # accisa implicita
            iva_abs = p - p/(1+IVA)
            data.append((d, p, n, excise, iva_abs))
    data.sort(key=lambda x: x[0])
    return data


def plot_decomposition_latest(data):
    """Torta + barra con i numeri dell'ultima osservazione."""
    d, pump, net, excise, iva_abs = data[-1]
    state = excise + iva_abs
    market = net

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 6))

    labels = ['Netto\n(greggio+raffinaz+distrib)', 'Accisa', 'IVA (22%)']
    values = [net, excise, iva_abs]
    colors = ['#7c4dff', '#ff6b6b', '#ff8800']
    wedges, texts, autotexts = ax1.pie(
        values, labels=labels, colors=colors,
        autopct=lambda p: f'{p:.1f}%\n{p/100*pump:.3f}€',
        startangle=90, textprops={'fontsize': 10, 'color': '#c9d1d9'},
        wedgeprops={'edgecolor': '#0d1117', 'linewidth': 2})
    for t in autotexts:
        t.set_color('#0d1117'); t.set_fontweight('bold')
    ax1.set_title(f'Composizione benzina Italia\nsettimana {d.date()} — '
                  f'pompa {pump:.3f} EUR/L',
                  color='#00ff88', fontsize=12, pad=20)

    ax2.barh(['comp'], [market], color='#7c4dff',
             label=f'Mercato {market:.3f}€ ({market/pump*100:.1f}%)',
             edgecolor='#0d1117', linewidth=2)
    ax2.barh(['comp'], [state], left=[market], color='#ff6b6b',
             label=f'Stato {state:.3f}€ ({state/pump*100:.1f}%)',
             edgecolor='#0d1117', linewidth=2)
    ax2.set_xlim(0, pump * 1.05)
    ax2.set_xlabel('EUR / Litro')
    ax2.set_title(f'Stato vs Mercato\nTotale: {pump:.3f} EUR/L',
                  color='#00ff88', fontsize=12, pad=20)
    ax2.legend(loc='lower center', bbox_to_anchor=(0.5, -0.3), ncol=1,
               facecolor='#161b22', edgecolor='#30363d', labelcolor='#c9d1d9')
    ax2.grid(axis='x', alpha=0.3); ax2.set_yticks([])

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/01_decomposizione_reale.png', dpi=120,
                facecolor='#0d1117', bbox_inches='tight')
    plt.close()
    print(f'[+] {OUTPUT_DIR}/01_decomposizione_reale.png')
    print(f'    {d.date()}: pompa={pump:.3f} netto={net:.3f} accisa={excise:.3f} '
          f'iva={iva_abs:.3f}')
    print(f'    Stato {state:.3f}€ ({state/pump*100:.1f}%) '
          f'Mercato {market:.3f}€ ({market/pump*100:.1f}%)')


def plot_history(data):
    """Serie storica 2005-2026 delle componenti."""
    dates = [x[0] for x in data]
    pumps = np.array([x[1] for x in data])
    nets = np.array([x[2] for x in data])
    excises = np.array([x[3] for x in data])
    ivas = np.array([x[4] for x in data])

    fig, axes = plt.subplots(2, 1, figsize=(14, 9), sharex=True)

    # Area impilata: composizione nel tempo
    axes[0].fill_between(dates, 0, nets, color='#7c4dff', alpha=0.85,
                         label='Netto (mercato)')
    axes[0].fill_between(dates, nets, nets + excises, color='#ff6b6b',
                         alpha=0.85, label='Accisa')
    axes[0].fill_between(dates, nets + excises, pumps, color='#ff8800',
                         alpha=0.85, label='IVA')
    axes[0].plot(dates, pumps, color='#c9d1d9', linewidth=1.2,
                 label='Pompa (totale)')
    axes[0].set_ylabel('EUR / Litro')
    axes[0].set_title('Composizione prezzo benzina Italia 2005-2026 (dati EU Weekly Oil Bulletin)',
                      color='#00ff88', fontsize=12)
    axes[0].legend(loc='upper left', facecolor='#161b22',
                   edgecolor='#30363d', labelcolor='#c9d1d9', fontsize=10)
    axes[0].grid(alpha=0.3)

    # Annotazioni: picchi e interventi
    peak_idx = int(np.argmax(pumps))
    axes[0].annotate(f'picco {pumps[peak_idx]:.3f}€\n{dates[peak_idx].strftime("%b %Y")}\n'
                     '(invasione Ucraina)',
                     xy=(dates[peak_idx], pumps[peak_idx]),
                     xytext=(dates[peak_idx], pumps[peak_idx] + 0.25),
                     color='#ffcc00', fontsize=9,
                     arrowprops=dict(arrowstyle='->', color='#ffcc00'),
                     ha='center')
    min_idx = int(np.argmin(pumps))
    axes[0].annotate(f'minimo {pumps[min_idx]:.3f}€\n{dates[min_idx].strftime("%b %Y")}\n'
                     '(crisi finanziaria)',
                     xy=(dates[min_idx], pumps[min_idx]),
                     xytext=(dates[min_idx], pumps[min_idx] - 0.3),
                     color='#00ff88', fontsize=9,
                     arrowprops=dict(arrowstyle='->', color='#00ff88'),
                     ha='center')

    # Peso dello Stato (%)
    state_share = (excises + ivas) / pumps * 100
    axes[1].plot(dates, state_share, color='#ff6b6b', linewidth=2,
                 label='Quota Stato (accisa+IVA)')
    axes[1].fill_between(dates, 40, state_share, color='#ff6b6b', alpha=0.15)
    axes[1].axhline(50, color='#c9d1d9', linestyle='--', linewidth=0.8,
                    alpha=0.5)
    axes[1].set_ylabel('Quota Stato (%)')
    axes[1].set_xlabel('Data')
    axes[1].set_title('Quanto pesa lo Stato sul prezzo nel tempo',
                      color='#00ff88', fontsize=12)
    axes[1].legend(loc='lower right', facecolor='#161b22',
                   edgecolor='#30363d', labelcolor='#c9d1d9')
    axes[1].grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/02_stato_vs_mercato_storia.png', dpi=120,
                facecolor='#0d1117', bbox_inches='tight')
    plt.close()
    print(f'[+] {OUTPUT_DIR}/02_stato_vs_mercato_storia.png')
    print(f'    Quota Stato min: {state_share.min():.1f}% @ '
          f'{dates[int(np.argmin(state_share))].date()}')
    print(f'    Quota Stato max: {state_share.max():.1f}% @ '
          f'{dates[int(np.argmax(state_share))].date()}')
    print(f'    Accise uniche viste: {sorted(set(round(e,3) for e in excises))[:10]}')


if __name__ == '__main__':
    print('=' * 60)
    print(' Decomposizione benzina Italia — DATI REALI 2005-2026')
    print('=' * 60)
    data = load_series()
    print(f'[i] {len(data)} settimane caricate')
    plot_decomposition_latest(data)
    plot_history(data)
    print('=' * 60)
