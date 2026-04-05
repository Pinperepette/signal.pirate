#!/usr/bin/env python3
"""
03_rockets_feathers.py — Test empirico dell'asimmetria su dati veri.

Il fenomeno "rockets and feathers" dice che i prezzi salgono in fretta e
scendono piano. Stimo il modello direttamente sui dati Italia 2005-2026.

Test 1 — Pass-through asimmetrico (regressione sui rendimenti settimanali):
    delta_net[t] = alpha + beta_up * max(delta_brent_eur[t], 0)
                         + beta_dn * min(delta_brent_eur[t], 0) + eps

Test 2 — Velocita' di aggiustamento asimmetrica (Error Correction):
    Stima cointegrazione netto-brent, poi:
    delta_net[t] = ... + gamma_up * max(ECM[t-1], 0)
                       + gamma_dn * min(ECM[t-1], 0)

Se beta_up > |beta_dn| -> pass-through al rialzo piu' forte.
Se |gamma_up| > |gamma_dn| -> il netto corregge piu' in fretta quando e'
sotto equilibrio (benzina bassa, sale di corsa) rispetto a quando e'
sopra (benzina alta, scende adagio).

Output: output/06_rockets_feathers_reale.png
        output/07_pass_through_scatter.png
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


def load_data():
    with open('data/brent.csv') as f:
        brent = [(datetime.strptime(r['observation_date'], '%Y-%m-%d'),
                  float(r['DCOILBRENTEU'])) for r in csv.DictReader(f)
                 if r['DCOILBRENTEU'] not in ('', '.')]
    with open('data/eurusd.csv') as f:
        fx = [(datetime.strptime(r['observation_date'], '%Y-%m-%d'),
               float(r['DEXUSEU'])) for r in csv.DictReader(f)
              if r['DEXUSEU'] not in ('', '.')]
    with open('data/italy_prices_wo_tax.csv') as f:
        net = [(datetime.strptime(r['date'], '%Y-%m-%d'),
                float(r['benzina_net_eur_L'])) for r in csv.DictReader(f)
               if r['benzina_net_eur_L']]
    return brent, fx, net


def build_weekly_panel(brent, fx, net):
    """Allinea tutto alla cadenza settimanale della serie benzina (lunedi')."""
    net_sorted = sorted(net)
    brent_d = dict(brent)
    fx_d = dict(fx)
    # per ogni data settimanale, calcolo brent_eur medio dei 7 giorni precedenti
    panel = []
    for d, n in net_sorted:
        start = d - timedelta(days=7)
        b_vals, f_vals = [], []
        for delta in range(8):
            dd = start + timedelta(days=delta)
            if dd in brent_d:
                b_vals.append(brent_d[dd])
            if dd in fx_d:
                f_vals.append(fx_d[dd])
        if not b_vals or not f_vals:
            continue
        b = float(np.mean(b_vals))
        f = float(np.mean(f_vals))
        b_eur_l = (b / f) / 158.987    # EUR/L equivalente greggio
        panel.append({'date': d, 'net': n, 'brent_eur_l': b_eur_l})
    return panel


def estimate_ecm(panel):
    """Error Correction Model asimmetrico stimato con OLS."""
    net = np.array([p['net'] for p in panel])
    brent = np.array([p['brent_eur_l'] for p in panel])
    log_net = np.log(net)
    log_brent = np.log(brent)

    # Relazione di lungo periodo: log_net = a + b * log_brent (OLS)
    X = np.column_stack([np.ones(len(log_brent)), log_brent])
    beta_lr, *_ = np.linalg.lstsq(X, log_net, rcond=None)
    a_lr, b_lr = beta_lr
    residuals = log_net - (a_lr + b_lr * log_brent)  # ECM term
    print(f'    Long-run: log(netto) = {a_lr:.3f} + {b_lr:.3f} * log(brent_eur_L)')
    print(f'    R² lungo periodo: '
          f'{1 - residuals.var()/log_net.var():.3f}')

    # Rendimenti
    d_net = np.diff(log_net)
    d_brent = np.diff(log_brent)
    ecm_lag = residuals[:-1]

    # Variabili asimmetriche
    d_brent_up = np.maximum(d_brent, 0)
    d_brent_dn = np.minimum(d_brent, 0)
    ecm_up = np.maximum(ecm_lag, 0)    # netto sopra equilibrio
    ecm_dn = np.minimum(ecm_lag, 0)    # netto sotto equilibrio

    # OLS: d_net = c + b_up*d_brent_up + b_dn*d_brent_dn + g_up*ecm_up + g_dn*ecm_dn
    X2 = np.column_stack([np.ones(len(d_net)), d_brent_up, d_brent_dn,
                          ecm_up, ecm_dn])
    coefs, resid_sum, *_ = np.linalg.lstsq(X2, d_net, rcond=None)
    c, b_up, b_dn, g_up, g_dn = coefs
    yhat = X2 @ coefs
    ss_res = float(np.sum((d_net - yhat) ** 2))
    ss_tot = float(np.sum((d_net - d_net.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot

    # Standard errors: OLS, poi HAC (Newey-West) per robustezza a
    # eteroschedasticita' e autocorrelazione (rilevante con kurtosis 32+).
    n, k = X2.shape
    resid = d_net - yhat
    XtX_inv = np.linalg.inv(X2.T @ X2)
    sigma2 = ss_res / (n - k)
    se_ols = np.sqrt(sigma2 * np.diag(XtX_inv))

    # Newey-West: Omega = X'X * sigma2 + sum_lag w_l * (Gamma_l + Gamma_l')
    # con w_l = 1 - l/(L+1), L = floor(4*(n/100)^(2/9))
    L = int(np.floor(4 * (n / 100) ** (2/9)))
    S = (X2.T * (resid ** 2)) @ X2  # lag 0
    for lag in range(1, L + 1):
        w = 1.0 - lag / (L + 1)
        Gamma = (X2[lag:].T * (resid[lag:] * resid[:-lag])) @ X2[:-lag]
        S = S + w * (Gamma + Gamma.T)
    V_hac = XtX_inv @ S @ XtX_inv
    se_hac = np.sqrt(np.diag(V_hac))
    tstat_ols = coefs / se_ols
    tstat = coefs / se_hac   # reported

    print(f'    Short-run pass-through (rendimenti log):')
    print(f'      beta_up  = {b_up:+.3f}  t_HAC={tstat[1]:+.2f}  (t_OLS={tstat_ols[1]:+.2f})')
    print(f'      beta_dn  = {b_dn:+.3f}  t_HAC={tstat[2]:+.2f}  (t_OLS={tstat_ols[2]:+.2f})')
    if abs(b_dn) > 0:
        print(f'      asimmetria: {b_up/abs(b_dn):.2f}x (>1 = rockets & feathers)')
        # Wald test H0: b_up + b_dn = 0 (simmetria)
        R = np.array([[0, 1, 1, 0, 0]])
        diff = (R @ coefs)[0]
        var_diff = (R @ V_hac @ R.T)[0, 0]
        z_sym = diff / np.sqrt(var_diff)
        print(f'      H0 simmetria (b_up=-b_dn): z={z_sym:+.2f}  '
              f'(|z|>1.96 -> rigetto)')
    print(f'    Adjustment asimmetrico verso equilibrio:')
    print(f'      gamma_up = {g_up:+.3f}  t_HAC={tstat[3]:+.2f}')
    print(f'      gamma_dn = {g_dn:+.3f}  t_HAC={tstat[4]:+.2f}')
    print(f'    R² breve periodo: {r2:.3f}  (HAC lag L={L})')

    return {
        'b_up': b_up, 'b_dn': b_dn, 'g_up': g_up, 'g_dn': g_dn,
        'c': c, 'tstat': tstat, 'r2': r2,
        'd_net': d_net, 'd_brent': d_brent,
        'residuals': residuals, 'net': net, 'brent': brent,
        'dates': [p['date'] for p in panel],
    }


def plot_asymmetry(res):
    fig = plt.figure(figsize=(14, 9))
    gs = fig.add_gridspec(2, 2)
    ax1 = fig.add_subplot(gs[0, :])
    ax2 = fig.add_subplot(gs[1, 0])
    ax3 = fig.add_subplot(gs[1, 1])

    # Bar chart coefficienti
    coef_names = ['β_up\n(Brent sale)', 'β_dn\n(Brent scende)',
                  'γ_up\n(sopra eq)', 'γ_dn\n(sotto eq)']
    coef_vals = [res['b_up'], res['b_dn'], res['g_up'], res['g_dn']]
    tstats = res['tstat'][1:5]
    colors = ['#ff6b6b' if v > 0 else '#00ff88' for v in coef_vals]
    bars = ax1.bar(coef_names, coef_vals, color=colors, edgecolor='#0d1117',
                   linewidth=2, width=0.55)
    ax1.axhline(0, color='#c9d1d9', linewidth=0.8)
    for bar, v, t in zip(bars, coef_vals, tstats):
        y = v + (0.015 if v >= 0 else -0.035)
        ax1.text(bar.get_x() + bar.get_width()/2, y,
                 f'{v:+.3f}\nt={t:+.1f}',
                 ha='center', color='#c9d1d9', fontsize=10)
    asymm = res['b_up'] / abs(res['b_dn']) if res['b_dn'] != 0 else 0
    ax1.set_title(f'Rockets & Feathers empirico (benzina netto Italia vs Brent EUR, 2005-2026)\n'
                  f'Asimmetria pass-through: β_up/|β_dn| = {asymm:.2f}x  —  '
                  f'R² = {res["r2"]:.3f}',
                  color='#00ff88', fontsize=12)
    ax1.set_ylabel('Coefficiente')
    ax1.grid(axis='y', alpha=0.3)

    # Scatter: delta_net vs delta_brent (colorato per segno)
    d_net = res['d_net']; d_brent = res['d_brent']
    ax2.scatter(d_brent[d_brent > 0]*100, d_net[d_brent > 0]*100,
                s=8, alpha=0.4, color='#ff6b6b', label='Brent sale')
    ax2.scatter(d_brent[d_brent < 0]*100, d_net[d_brent < 0]*100,
                s=8, alpha=0.4, color='#00ff88', label='Brent scende')
    # Lines with estimated slopes
    xs_pos = np.linspace(0, d_brent.max(), 50)
    xs_neg = np.linspace(d_brent.min(), 0, 50)
    ax2.plot(xs_pos*100, res['b_up']*xs_pos*100, color='#ff6b6b',
             linewidth=2.5, label=f'β_up={res["b_up"]:.3f}')
    ax2.plot(xs_neg*100, res['b_dn']*xs_neg*100, color='#00ff88',
             linewidth=2.5, label=f'β_dn={res["b_dn"]:.3f}')
    ax2.axhline(0, color='#30363d', linewidth=0.5)
    ax2.axvline(0, color='#30363d', linewidth=0.5)
    ax2.set_xlabel('Δlog(Brent EUR) settimanale (%)')
    ax2.set_ylabel('Δlog(benzina netto) settimanale (%)')
    ax2.set_title('Pass-through settimanale condizionato al segno',
                  color='#00ff88', fontsize=11)
    ax2.legend(facecolor='#161b22', edgecolor='#30363d',
               labelcolor='#c9d1d9', fontsize=9)
    ax2.grid(alpha=0.3)

    # ECM residuals nel tempo (squilibrio)
    ax3.plot(res['dates'], res['residuals'], color='#7c4dff', linewidth=0.8)
    ax3.fill_between(res['dates'], 0, res['residuals'],
                     where=(res['residuals'] > 0), color='#ff6b6b', alpha=0.3,
                     label='netto sopra equilibrio (caro)')
    ax3.fill_between(res['dates'], 0, res['residuals'],
                     where=(res['residuals'] < 0), color='#00ff88', alpha=0.3,
                     label='netto sotto equilibrio (a buon mercato)')
    ax3.axhline(0, color='#c9d1d9', linewidth=0.8)
    ax3.set_xlabel('Data')
    ax3.set_ylabel('ECM (log-gap)')
    ax3.set_title('Squilibrio netto/Brent nel tempo',
                  color='#00ff88', fontsize=11)
    ax3.legend(facecolor='#161b22', edgecolor='#30363d',
               labelcolor='#c9d1d9', fontsize=9, loc='upper left')
    ax3.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/06_rockets_feathers_reale.png', dpi=120,
                facecolor='#0d1117', bbox_inches='tight')
    plt.close()
    print(f'[+] {OUTPUT_DIR}/06_rockets_feathers_reale.png')


def simulate_shock_with_real_betas(res):
    """Simula uno shock su Brent usando i coefficienti stimati."""
    n = 80
    brent = np.full(n, 0.50)  # 0.50 EUR/L equivalente (~80$/bbl)
    # Shock +25% al giorno 15, rientro pari e opposto al giorno 45
    for i in range(5):
        brent[15+i] = 0.50 * (1 + 0.25 * (i+1)/5)
    for i in range(15, 45):
        brent[i] = 0.625  # plateau
    for i in range(5):
        brent[45+i] = 0.625 * (1 - 0.2*(i+1)/5)   # rientro
    brent[50:] = 0.50
    log_b = np.log(brent)
    d_log_b = np.diff(log_b, prepend=log_b[0])

    # Simula netto con betas reali
    log_net_asym = np.log(0.85 * np.ones(n))  # base
    log_net_sym = np.log(0.85 * np.ones(n))
    beta_avg = (res['b_up'] + abs(res['b_dn'])) / 2
    for t in range(1, n):
        log_net_asym[t] = log_net_asym[t-1] + \
            res['b_up'] * max(d_log_b[t], 0) + \
            res['b_dn'] * min(d_log_b[t], 0)
        log_net_sym[t] = log_net_sym[t-1] + beta_avg * d_log_b[t]

    net_asym = np.exp(log_net_asym)
    net_sym = np.exp(log_net_sym)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 8), sharex=True)
    days = np.arange(n)
    ax1.plot(days, brent, color='#ff8800', linewidth=2, label='Brent (EUR/L eq.)')
    ax1.set_ylabel('Brent EUR/L')
    ax1.set_title('Shock simmetrico sul Brent (+25% poi rientro)',
                  color='#00ff88', fontsize=12)
    ax1.legend(facecolor='#161b22', edgecolor='#30363d', labelcolor='#c9d1d9')
    ax1.grid(alpha=0.3)

    ax2.plot(days, net_sym, color='#4ecdc4', linewidth=2,
             label='netto simulato (trasmissione simmetrica)')
    ax2.plot(days, net_asym, color='#ff6b6b', linewidth=2.5,
             label='netto simulato (betas empirici asimmetrici)')
    ax2.fill_between(days, net_sym, net_asym,
                     where=(net_asym > net_sym),
                     color='#ff6b6b', alpha=0.2,
                     label='extra costo da asimmetria')
    ax2.set_ylabel('Benzina netto (EUR/L)')
    ax2.set_xlabel('Settimane')
    ax2.set_title(f'Stesso shock, due mondi (betas reali: '
                  f'β_up={res["b_up"]:.3f}, β_dn={res["b_dn"]:.3f})',
                  color='#00ff88', fontsize=12)
    ax2.legend(facecolor='#161b22', edgecolor='#30363d',
               labelcolor='#c9d1d9', fontsize=9)
    ax2.grid(alpha=0.3)

    # Area di extra-costo
    extra = np.sum(np.maximum(net_asym - net_sym, 0))
    ax2.text(0.02, 0.02,
             f'Extra cumulato asimmetria: {extra*100:.2f} EUR-settimane/L',
             transform=ax2.transAxes, fontsize=10, color='#ffcc00',
             bbox=dict(boxstyle='round', facecolor='#161b22',
                       edgecolor='#30363d'))

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/07_pass_through_scatter.png', dpi=120,
                facecolor='#0d1117', bbox_inches='tight')
    plt.close()
    print(f'[+] {OUTPUT_DIR}/07_pass_through_scatter.png')
    print(f'    Extra costo cumulato da asimmetria: '
          f'{extra*100:.2f} EUR-settimane/L')


if __name__ == '__main__':
    print('=' * 60)
    print(' ECM asimmetrico stimato su dati reali Italia 2005-2026')
    print('=' * 60)
    brent, fx, net = load_data()
    panel = build_weekly_panel(brent, fx, net)
    print(f'[i] panel settimanale: {len(panel)} osservazioni')
    res = estimate_ecm(panel)
    plot_asymmetry(res)
    simulate_shock_with_real_betas(res)
    print('=' * 60)
