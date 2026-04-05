#!/usr/bin/env python3
"""
05_intervento_reale.py — Efficacia del taglio accise: dati veri.

L'Italia ha tagliato le accise in due episodi (almeno) nell'ultimo ciclo:
  1) Marzo-Novembre 2022 (governo Draghi, poi esteso Meloni): da 0.7284 a
     ~0.4784 EUR/L sulla benzina (-25 centesimi). Il mancato gettito fu
     stimato ~10 miliardi.
  2) Marzo 2026: nuovo taglio a 0.4729 EUR/L (circa -25.5 centesimi).

Dalla serie EU Weekly Oil Bulletin posso derivare l'accisa implicita
settimana per settimana:
    accisa_t = pompa_t / (1+IVA) - netto_t

Cosi' vedo:
  - Quando l'accisa e' stata realmente tagliata
  - Quanto del taglio e' arrivato al consumatore (pompa)
  - Quanto e' stato assorbito dall'allargamento dei margini (netto)

Test controfattuale: cosa sarebbe successo alla pompa se avessimo
lasciato accisa a 0.7284 EUR/L con gli stessi netti osservati?

Output: output/10_intervento_2022.png
        output/11_cattura_margine.png
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
    from datetime import timedelta
    with open('data/italy_prices_with_tax.csv') as f:
        pump = {datetime.strptime(r['date'], '%Y-%m-%d'):
                float(r['benzina_eur_L']) for r in csv.DictReader(f)
                if r['benzina_eur_L']}
    with open('data/italy_prices_wo_tax.csv') as f:
        net = {datetime.strptime(r['date'], '%Y-%m-%d'):
               float(r['benzina_net_eur_L']) for r in csv.DictReader(f)
               if r['benzina_net_eur_L']}
    with open('data/brent.csv') as f:
        brent = {datetime.strptime(r['observation_date'], '%Y-%m-%d'):
                 float(r['DCOILBRENTEU']) for r in csv.DictReader(f)
                 if r['DCOILBRENTEU'] not in ('', '.')}
    with open('data/eurusd.csv') as f:
        fx = {datetime.strptime(r['observation_date'], '%Y-%m-%d'):
              float(r['DEXUSEU']) for r in csv.DictReader(f)
              if r['DEXUSEU'] not in ('', '.')}
    dates = sorted(set(pump) & set(net))
    arr = []
    for d in dates:
        p, n = pump[d], net[d]
        excise = p/(1+IVA) - n
        # Brent EUR/L equivalente: media 7gg precedenti
        bvals, fvals = [], []
        for k in range(8):
            dd = d - timedelta(days=k)
            if dd in brent: bvals.append(brent[dd])
            if dd in fx: fvals.append(fx[dd])
        if bvals and fvals:
            brent_eur_l = (np.mean(bvals) / np.mean(fvals)) / 158.987
        else:
            brent_eur_l = None
        arr.append({'date': d, 'pump': p, 'net': n, 'excise': excise,
                    'brent_eur_l': brent_eur_l})
    return arr


def plot_2022_intervention(data):
    # Focus: gennaio 2022 - aprile 2023
    mask = [(x['date'] >= datetime(2021, 11, 1)) and
            (x['date'] <= datetime(2023, 6, 1)) for x in data]
    d = [x for x, m in zip(data, mask) if m]
    if not d:
        print('    [!] nessun dato nel range 2021-2023')
        return

    dates = [x['date'] for x in d]
    pump = np.array([x['pump'] for x in d])
    net = np.array([x['net'] for x in d])
    excise = np.array([x['excise'] for x in d])

    # Controfattuale: accisa tenuta fissa a 0.7284
    excise_pre = 0.7284
    pump_counterfactual = (net + excise_pre) * (1 + IVA)
    savings = pump_counterfactual - pump  # risparmio del consumatore

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)

    # Pump actual vs controfattuale
    axes[0].plot(dates, pump_counterfactual, color='#ff6b6b', linewidth=2,
                 linestyle='--', label='pompa controfattuale (accisa piena 0.728)')
    axes[0].plot(dates, pump, color='#00ff88', linewidth=2,
                 label='pompa reale osservata')
    axes[0].fill_between(dates, pump, pump_counterfactual,
                         where=(pump_counterfactual > pump),
                         color='#00ff88', alpha=0.2,
                         label='risparmio consumatore')
    axes[0].set_ylabel('Pompa (EUR/L)')
    axes[0].set_title('Intervento 2022: accisa tagliata durante shock Ucraina\n'
                      '(dati veri EU Weekly Oil Bulletin — Italia benzina)',
                      color='#00ff88', fontsize=12)
    axes[0].legend(loc='upper right', facecolor='#161b22',
                   edgecolor='#30363d', labelcolor='#c9d1d9')
    axes[0].grid(alpha=0.3)

    # Accisa implicita
    axes[1].plot(dates, excise * 100, color='#ff6b6b', linewidth=2)
    axes[1].fill_between(dates, 0, excise * 100, color='#ff6b6b', alpha=0.15)
    axes[1].axhline(72.84, color='#c9d1d9', linestyle='--', linewidth=0.8,
                    alpha=0.5, label='accisa standard 72.84 cent')
    axes[1].set_ylabel('Accisa implicita (cent/L)')
    axes[1].set_title('Accisa benzina settimana per settimana '
                      '(derivata da pompa/(1+IVA) - netto)',
                      color='#00ff88', fontsize=12)
    axes[1].legend(facecolor='#161b22', edgecolor='#30363d', labelcolor='#c9d1d9')
    axes[1].grid(alpha=0.3)

    # Risparmio effettivo
    axes[2].plot(dates, savings * 100, color='#00ff88', linewidth=2)
    axes[2].fill_between(dates, 0, savings * 100,
                         where=(savings > 0), color='#00ff88', alpha=0.25)
    axes[2].axhline(0, color='#30363d', linewidth=0.8)
    axes[2].set_ylabel('Risparmio vs scenario no-taglio (cent/L)')
    axes[2].set_xlabel('Data')
    axes[2].set_title('Quanto hanno risparmiato davvero gli italiani per ogni litro',
                      color='#00ff88', fontsize=12)
    axes[2].grid(alpha=0.3)

    # Stats
    cut_period = [i for i, x in enumerate(d)
                  if excise[i] < 0.70]  # quando c'era il taglio
    if cut_period:
        avg_cut = float(0.7284 - excise[cut_period].mean())
        avg_saving = float(savings[cut_period].mean())
        print(f'    Taglio medio accisa (2022-23): {avg_cut*100:.1f} cent/L')
        print(f'    Risparmio medio consumatore: {avg_saving*100:.1f} cent/L')
        print(f'    Efficienza trasferimento: '
              f'{avg_saving*(1+IVA)/avg_cut*100:.0f}%')
        # Stima valore totale: ~20 Mrd L benzina/anno in Italia,
        # tagliamo per frazione dell'anno coperta dal taglio
        weeks = len(cut_period)
        litri_sett = 20e9 / 52
        valore_tot_gettito = avg_cut * (1 + IVA) * litri_sett * weeks / 1e9
        valore_tot_conss = avg_saving * litri_sett * weeks / 1e9
        print(f'    Durata taglio osservato: {weeks} settimane')
        print(f'    Mancato gettito stimato: {valore_tot_gettito:.1f} Mrd €')
        print(f'    Beneficio tot consumatore: {valore_tot_conss:.1f} Mrd €')

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/10_intervento_2022.png', dpi=120,
                facecolor='#0d1117', bbox_inches='tight')
    plt.close()
    print(f'[+] {OUTPUT_DIR}/10_intervento_2022.png')


def plot_margin_capture(data):
    """Durante il taglio, il netto si allarga? (cattura margine)"""
    # Focus 2021-2023 per il 2022 cut
    d = [x for x in data
         if datetime(2021, 1, 1) <= x['date'] <= datetime(2023, 12, 31)]
    if not d:
        return
    dates = [x['date'] for x in d]
    net = np.array([x['net'] for x in d])
    excise = np.array([x['excise'] for x in d])

    # "Regime cut" vs "no cut"
    in_cut = excise < 0.70

    fig, ax = plt.subplots(1, 1, figsize=(13, 6))
    # netto in nero con overlay colorato durante cut
    ax.plot(dates, net, color='#c9d1d9', linewidth=1.5, label='netto benzina')
    # Evidenzia periodo di taglio
    for i in range(len(dates) - 1):
        if in_cut[i]:
            ax.axvspan(dates[i], dates[i+1], color='#ffcc00', alpha=0.12)
    ax.set_ylabel('Netto benzina (EUR/L)')
    ax.set_xlabel('Data')
    ax.set_title('Il netto (pre-tasse) durante il taglio accise 2022-23 '
                 '(fascia gialla = periodo taglio)',
                 color='#00ff88', fontsize=12)
    ax.grid(alpha=0.3)

    # --- Controfattuale con controlli aggiuntivi ---
    # Modello: log(net) = a + b*log(brent) + c*log(brent_lag1) + d*vol20
    #                     + e*war_dummy + f*cut_dummy + eps
    # vol20 = rolling std 20sett dei rendimenti Brent (proxy stress raffinazione
    # in assenza di dati diretti sul crack spread).
    # war_dummy = 1 da Feb 2022 a Dic 2022 (shock Ucraina, indipendente dal cut).
    # cut_dummy = 1 durante il taglio accise: stima diretta dell'effetto
    # controllato per tutto il resto.
    rows = [x for x in data if x['brent_eur_l'] is not None]
    brent_arr = np.array([x['brent_eur_l'] for x in rows])
    net_arr = np.array([x['net'] for x in rows])
    excise_arr = np.array([x['excise'] for x in rows])
    dates_arr = [x['date'] for x in rows]
    # lag1 brent
    brent_lag1 = np.concatenate([[brent_arr[0]], brent_arr[:-1]])
    # rolling vol 20sett dei log-returns del Brent
    log_ret = np.diff(np.log(brent_arr), prepend=np.log(brent_arr[0]))
    vol20 = np.zeros_like(log_ret)
    for i in range(len(log_ret)):
        lo = max(0, i - 20)
        vol20[i] = np.std(log_ret[lo:i+1]) if i > 3 else 0.02
    # war dummy: Feb 2022 - Dic 2022
    from datetime import datetime as _dt
    war_start = _dt(2022, 2, 20); war_end = _dt(2022, 12, 31)
    war = np.array([1.0 if war_start <= d <= war_end else 0.0
                    for d in dates_arr])
    cut = (excise_arr < 0.70).astype(float)

    X = np.column_stack([
        np.ones(len(net_arr)),
        np.log(brent_arr),
        np.log(brent_lag1),
        vol20,
        war,
        cut,
    ])
    y = np.log(net_arr)
    coefs, *_ = np.linalg.lstsq(X, y, rcond=None)
    yhat = X @ coefs
    resid = y - yhat
    n, k = X.shape
    ss_res = float(np.sum(resid ** 2))
    XtX_inv = np.linalg.inv(X.T @ X)

    # Newey-West HAC SE
    L = int(np.floor(4 * (n / 100) ** (2/9)))
    S = (X.T * (resid ** 2)) @ X
    for lag in range(1, L + 1):
        w = 1.0 - lag / (L + 1)
        Gamma = (X[lag:].T * (resid[lag:] * resid[:-lag])) @ X[:-lag]
        S = S + w * (Gamma + Gamma.T)
    V_hac = XtX_inv @ S @ XtX_inv
    se_hac = np.sqrt(np.diag(V_hac))
    tstat = coefs / se_hac
    r2 = 1 - ss_res / float(np.sum((y - y.mean()) ** 2))

    names = ['const', 'log(brent)', 'log(brent_lag1)', 'vol20',
             'war_dummy', 'cut_dummy']
    print(f'    [Modello controllato con Newey-West HAC, L={L}]')
    print(f'    R² = {r2:.3f}  n={n}')
    for name, c, t in zip(names, coefs, tstat):
        print(f'      {name:<16s} = {c:+.4f}  t_HAC={t:+.2f}')
    # Cut dummy e' il coeff di interesse: effetto sul log(netto) ceteris paribus
    cut_effect_pct = (np.exp(coefs[5]) - 1) * 100
    # Effetto sul netto medio in cent
    avg_net = float(net_arr[cut == 1].mean())
    cut_effect_cents = avg_net * (np.exp(coefs[5]) - 1) * 100
    print(f'    Effetto CUT_DUMMY sul log(netto): {coefs[5]:+.4f}')
    print(f'    -> variazione relativa netto: {cut_effect_pct:+.2f}%')
    print(f'    -> variazione assoluta netto: {cut_effect_cents:+.2f} cent/L')
    print(f'    -> t_HAC = {tstat[5]:+.2f}  '
          f'{"(significativo)" if abs(tstat[5])>1.96 else "(NON significativo)"}')

    txt = (f'Controllato per Brent, lag, volatilita\', war dummy:\n'
           f'Effetto cut su log(netto): {coefs[5]:+.4f} '
           f'({cut_effect_pct:+.2f}%)\n'
           f'Effetto assoluto: {cut_effect_cents:+.2f} cent/L  '
           f'(t_HAC={tstat[5]:+.2f})\n'
           f'R² = {r2:.3f}, n = {n}')
    ax.text(0.02, 0.98, txt, transform=ax.transAxes, va='top',
            fontsize=9, color='#c9d1d9', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='#161b22',
                      edgecolor='#30363d'))

    ax.legend(facecolor='#161b22', edgecolor='#30363d', labelcolor='#c9d1d9')
    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/11_cattura_margine.png', dpi=120,
                facecolor='#0d1117', bbox_inches='tight')
    plt.close()
    print(f'[+] {OUTPUT_DIR}/11_cattura_margine.png')


if __name__ == '__main__':
    print('=' * 60)
    print(' Intervento accise 2022: analisi controfattuale')
    print('=' * 60)
    data = load_series()
    plot_2022_intervention(data)
    plot_margin_capture(data)
    print('=' * 60)
