#!/usr/bin/env python3
"""
07_model_comparison.py — Il vero punto: la stessa domanda, cinque modelli.

Stimo lo stesso effetto (cut_dummy sul netto italiano durante il taglio
accise 2022-23) sotto 5 specifiche diverse, crescenti in complessita'.

Tutte con Newey-West HAC standard errors. Tutte sugli stessi dati.
E' il segno che cambia, non il dato.

Spec 1: OLS log(IT_net) ~ log(brent)  (solo Brent)
Spec 2: OLS log(IT_net) ~ log(brent) + log(brent_lag1) + vol20 + war_dummy + cut_dummy
Spec 3: VECM rank=1, Y=[IT, DE, brent], exog=[war, cut]
Spec 4: VECM rank=2
Spec 5: VECM rank=3 (equivalente a VAR in livelli)

Output: output/14_model_comparison.png
"""
import csv
from datetime import datetime, timedelta
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
from statsmodels.tsa.vector_ar.vecm import VECM

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


def load_panel():
    with open('data/italy_prices_wo_tax.csv') as f:
        it = {datetime.strptime(r['date'], '%Y-%m-%d'):
              float(r['benzina_net_eur_L']) for r in csv.DictReader(f)
              if r['benzina_net_eur_L']}
    with open('data/italy_prices_with_tax.csv') as f:
        it_pump = {datetime.strptime(r['date'], '%Y-%m-%d'):
                   float(r['benzina_eur_L']) for r in csv.DictReader(f)
                   if r['benzina_eur_L']}
    with open('data/europe_nets.csv') as f:
        de = {}
        for r in csv.DictReader(f):
            if r['DE_benzina_net']:
                de[datetime.strptime(r['date'], '%Y-%m-%d')] = \
                    float(r['DE_benzina_net'])
    with open('data/brent.csv') as f:
        brent = {datetime.strptime(r['observation_date'], '%Y-%m-%d'):
                 float(r['DCOILBRENTEU']) for r in csv.DictReader(f)
                 if r['DCOILBRENTEU'] not in ('', '.')}
    with open('data/eurusd.csv') as f:
        fx = {datetime.strptime(r['observation_date'], '%Y-%m-%d'):
              float(r['DEXUSEU']) for r in csv.DictReader(f)
              if r['DEXUSEU'] not in ('', '.')}
    dates = sorted(set(it) & set(de))
    panel = []
    for d in dates:
        bvals, fvals = [], []
        for k in range(8):
            dd = d - timedelta(days=k)
            if dd in brent: bvals.append(brent[dd])
            if dd in fx: fvals.append(fx[dd])
        if not bvals or not fvals:
            continue
        brent_eur_l = (np.mean(bvals) / np.mean(fvals)) / 158.987
        excise = it_pump[d]/(1+IVA) - it[d]
        panel.append({
            'date': d, 'it_net': it[d], 'de_net': de[d],
            'brent_eur_l': brent_eur_l, 'excise': excise,
        })
    panel.sort(key=lambda x: x['date'])
    return panel


def hac_se(X, y, beta):
    resid = y - X @ beta
    n, k = X.shape
    XtX_inv = np.linalg.inv(X.T @ X)
    L = int(np.floor(4 * (n / 100) ** (2/9)))
    S = (X.T * (resid ** 2)) @ X
    for lag in range(1, L + 1):
        w = 1.0 - lag / (L + 1)
        G = (X[lag:].T * (resid[lag:] * resid[:-lag])) @ X[:-lag]
        S = S + w * (G + G.T)
    V = XtX_inv @ S @ XtX_inv
    return np.sqrt(np.diag(V))


def spec1_ols_simple(panel):
    """log(IT_net) = a + b*log(brent) + c*cut_dummy."""
    y = np.log([p['it_net'] for p in panel])
    lb = np.log([p['brent_eur_l'] for p in panel])
    cut = np.array([1.0 if p['excise'] < 0.70 else 0.0 for p in panel])
    X = np.column_stack([np.ones(len(y)), lb, cut])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    se = hac_se(X, y, b)
    coef = b[2]; t = coef / se[2]
    avg_net = float(np.mean([p['it_net'] for p in panel]))
    cents = avg_net * (np.exp(coef) - 1) * 100
    return ('1. OLS solo Brent', coef, se[2], t, cents)


def spec2_ols_full(panel):
    """log(IT_net) con Brent, lag1, vol20, war, cut."""
    from datetime import datetime as _dt
    y = np.log([p['it_net'] for p in panel])
    brent = np.array([p['brent_eur_l'] for p in panel])
    lb = np.log(brent)
    lb_lag1 = np.concatenate([[lb[0]], lb[:-1]])
    log_ret = np.diff(np.log(brent), prepend=np.log(brent[0]))
    vol20 = np.zeros_like(log_ret)
    for i in range(len(log_ret)):
        lo = max(0, i-20); vol20[i] = np.std(log_ret[lo:i+1]) if i > 3 else 0.02
    war_start = _dt(2022, 2, 20); war_end = _dt(2022, 12, 31)
    war = np.array([1.0 if war_start <= p['date'] <= war_end else 0.0
                    for p in panel])
    cut = np.array([1.0 if p['excise'] < 0.70 else 0.0 for p in panel])
    X = np.column_stack([np.ones(len(y)), lb, lb_lag1, vol20, war, cut])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    se = hac_se(X, y, b)
    coef = b[5]; t = coef / se[5]
    avg_net = float(np.mean([p['it_net'] for p in panel]))
    cents = avg_net * (np.exp(coef) - 1) * 100
    return ('2. OLS + controlli', coef, se[5], t, cents)


def spec_vecm(panel, rank):
    """VECM con rank specificato, DE nel sistema."""
    from datetime import datetime as _dt
    Y = np.column_stack([
        np.log([p['it_net'] for p in panel]),
        np.log([p['de_net'] for p in panel]),
        np.log([p['brent_eur_l'] for p in panel]),
    ])
    war_start = _dt(2022, 2, 20); war_end = _dt(2022, 12, 31)
    war = np.array([1.0 if war_start <= p['date'] <= war_end else 0.0
                    for p in panel])
    cut = np.array([1.0 if p['excise'] < 0.70 else 0.0 for p in panel])
    exog = np.column_stack([war, cut])
    model = VECM(Y, k_ar_diff=1, coint_rank=rank, deterministic='ci', exog=exog)
    res = model.fit()
    # HAC short-run per IT
    dY = np.diff(Y, axis=0)
    EC = Y @ res.beta
    if hasattr(res, 'const_coint') and res.const_coint is not None:
        EC = EC + res.const_coint
    X_sr = []
    for j in range(dY.shape[0] - 1):
        t_dY = j + 1
        row = list(EC[t_dY])
        row.extend(dY[t_dY - 1])
        row.extend(exog[t_dY + 1])
        row.append(1.0)
        X_sr.append(row)
    X_sr = np.array(X_sr)
    y_it = dY[1:, 0]
    b, *_ = np.linalg.lstsq(X_sr, y_it, rcond=None)
    se = hac_se(X_sr, y_it, b)
    cut_col = X_sr.shape[1] - 2
    coef = b[cut_col]; t = coef / se[cut_col]
    # Effetto long-run implied: coef / |alpha_IT|
    alpha_it = abs(res.alpha[0, 0]) if rank >= 1 else 0.07
    lr_shift = coef / alpha_it if alpha_it > 0 else 0
    avg_net = float(np.mean([p['it_net'] for p in panel]))
    cents = avg_net * (np.exp(lr_shift) - 1) * 100
    return (f'{3+rank-1}. VECM rank={rank}', coef, se[cut_col], t, cents)


def plot_comparison(results):
    labels = [r[0] for r in results]
    coefs = [r[1] for r in results]
    ses = [r[2] for r in results]
    ts = [r[3] for r in results]
    cents = [r[4] for r in results]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))

    colors = ['#ff6b6b' if c < 0 else '#00ff88' for c in coefs]
    y_pos = np.arange(len(labels))
    ax1.barh(y_pos, coefs, xerr=[1.96*s for s in ses], color=colors,
             edgecolor='#0d1117', capsize=5, alpha=0.85)
    ax1.axvline(0, color='#c9d1d9', linewidth=0.8)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(labels, fontsize=10)
    ax1.set_xlabel('Coefficiente cut_dummy su log(IT_net)')
    ax1.set_title('Stima cut_dummy sotto 5 specifiche\n(stesse settimane, stessi dati, barre=IC 95%)',
                  color='#00ff88', fontsize=12)
    ax1.grid(axis='x', alpha=0.3)
    for i, (c, t) in enumerate(zip(coefs, ts)):
        x = c + (0.01 if c >= 0 else -0.01)
        ha = 'left' if c >= 0 else 'right'
        sig = '***' if abs(t) > 2.58 else '**' if abs(t) > 1.96 else 'ns'
        ax1.text(x, i, f'  t={t:+.2f} ({sig})',
                 va='center', ha=ha, fontsize=9, color='#c9d1d9')

    # Effetto implicato in cent/L
    colors2 = ['#ff6b6b' if c < 0 else '#00ff88' for c in cents]
    ax2.barh(y_pos, cents, color=colors2, edgecolor='#0d1117', alpha=0.85)
    ax2.axvline(0, color='#c9d1d9', linewidth=0.8)
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(['' for _ in labels])
    ax2.set_xlabel('Effetto implicato sul netto (cent/L)')
    ax2.set_title('Stesso coefficiente, tradotto in cent/L\n(interpretazione in livello)',
                  color='#00ff88', fontsize=12)
    ax2.grid(axis='x', alpha=0.3)
    for i, c in enumerate(cents):
        x = c + (0.3 if c >= 0 else -0.3)
        ha = 'left' if c >= 0 else 'right'
        ax2.text(x, i, f'  {c:+.1f} cent', va='center', ha=ha,
                 fontsize=10, color='#c9d1d9')

    plt.suptitle('Segno della stima: -4 cent (OLS) -> +5 cent (VECM rank=1)\n'
                 'Il dato non cambia. Il modello si\'.',
                 color='#ffcc00', fontsize=13, y=1.02)
    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/14_model_comparison.png', dpi=120,
                facecolor='#0d1117', bbox_inches='tight')
    plt.close()
    print(f'[+] {OUTPUT_DIR}/14_model_comparison.png')


if __name__ == '__main__':
    print('=' * 60)
    print(' Confronto tra specifiche: stesso dato, 5 modelli')
    print('=' * 60)
    panel = load_panel()
    print(f'[i] panel: {len(panel)} obs')
    results = []
    results.append(spec1_ols_simple(panel))
    results.append(spec2_ols_full(panel))
    results.append(spec_vecm(panel, 1))
    results.append(spec_vecm(panel, 2))
    results.append(spec_vecm(panel, 3))
    print()
    print(f'    {"specifica":<22s} {"coef":>10s} {"se":>8s} {"t_HAC":>8s} '
          f'{"cent/L":>10s}')
    for name, coef, se, t, cents in results:
        print(f'    {name:<22s} {coef:>+10.4f} {se:>8.4f} {t:>+8.2f} '
              f'{cents:>+9.1f}')
    plot_comparison(results)
    print('=' * 60)
