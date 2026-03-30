"""
02 — Analisi strutturale
========================
Linearita', tipping points, path dependency, zero dimensioni,
ECS collapse, smooth by construction, incertezza strutturale,
distribuzioni, hindcast/forecast, error compensation, non-identificabilita'.

Grafici: 17-27
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import matplotlib.pyplot as plt
from fair import FAIR
from fair.io import read_properties
from fair.interface import fill
from fair_utils import (create_fair, set_climate, init_fair,
                        run_single, get_temp, savefig, OUT)


def linearita():
    """R² forcing-temperatura: quasi perfettamente lineare."""
    scenarios = ['ssp119', 'ssp245', 'ssp585']
    f = create_fair(scenarios, ['default'])
    set_climate(f, 'default', [8.0, 100.0, 300.0], [1.0, 2.0, 0.5])
    init_fair(f)
    f.run()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))
    colors = ['#2196F3', '#4CAF50', '#F44336']
    all_f, all_t = [], []
    for i, scen in enumerate(scenarios):
        forcing = np.asarray(f.forcing_sum.loc[dict(scenario=scen, config='default')])
        temp = get_temp(f, scen, 'default')
        ax1.scatter(forcing[100:], temp[100:], alpha=0.5, s=10,
                   color=colors[i], label=scen.upper())
        all_f.extend(forcing[100:].tolist())
        all_t.extend(temp[100:].tolist())

    all_f, all_t = np.array(all_f), np.array(all_t)
    valid = np.isfinite(all_f) & np.isfinite(all_t)
    coeffs = np.polyfit(all_f[valid], all_t[valid], 1)
    r2 = 1 - np.sum((all_t[valid] - np.polyval(coeffs, all_f[valid]))**2) / \
             np.sum((all_t[valid] - np.mean(all_t[valid]))**2)
    fit_x = np.linspace(np.nanmin(all_f), np.nanmax(all_f), 100)
    ax1.plot(fit_x, np.polyval(coeffs, fit_x), 'k--', linewidth=2)
    ax1.set_xlabel('Forcing radiativo totale (W/m²)', fontsize=13)
    ax1.set_ylabel('Temperatura (°C)', fontsize=13)
    ax1.set_title(f'FaIR: risposta quasi perfettamente lineare\nR² = {r2:.4f}',
                  fontsize=14, fontweight='bold')
    ax1.legend(fontsize=11)
    ax1.grid(True, alpha=0.3)

    forcing_range = np.linspace(0, 8, 200)
    temp_lin = coeffs[0] * forcing_range + coeffs[1]
    temp_nonlin = temp_lin.copy()
    mask = forcing_range > 3
    temp_nonlin[mask] = temp_lin[mask] * (1 + 0.15 * (forcing_range[mask] - 3))
    ax2.plot(forcing_range, temp_lin, 'b-', linewidth=2.5, label='FaIR (lineare)')
    ax2.plot(forcing_range, temp_nonlin, 'r--', linewidth=2.5,
            label='Ipotetico non lineare')
    ax2.fill_between(forcing_range, temp_lin, temp_nonlin,
                    where=forcing_range > 3, alpha=0.15, color='red',
                    label='Zona ignorata dal modello')
    ax2.set_xlabel('Forcing (W/m²)', fontsize=13)
    ax2.set_ylabel('Temperatura (°C)', fontsize=13)
    ax2.set_title('Cosa manca: feedback non lineari', fontsize=14, fontweight='bold')
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    savefig('17_linearita.png')
    print(f'  R² = {r2:.6f}')


def tipping_points():
    """Curve sempre lisce, nessun salto di regime."""
    scenarios = ['ssp119', 'ssp126', 'ssp245', 'ssp370', 'ssp585']
    f = create_fair(scenarios, ['default'])
    set_climate(f, 'default', [8.0, 100.0, 300.0], [1.0, 2.0, 0.5])
    init_fair(f)
    f.run()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))
    colors = ['#2196F3', '#4CAF50', '#FFC107', '#FF5722', '#D32F2F']
    for i, scen in enumerate(scenarios):
        ax1.plot(f.timebounds, get_temp(f, scen, 'default'),
                label=scen.upper(), linewidth=2.5, color=colors[i])
    ax1.set_xlabel('Anno', fontsize=13)
    ax1.set_ylabel('Temperatura (°C)', fontsize=13)
    ax1.set_title('FaIR: curve sempre lisce', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=11)
    ax1.grid(True, alpha=0.3)

    t_arr = np.linspace(2000, 2100, 200)
    t_smooth = 0.8 + 0.025 * (t_arr - 2000)
    t_tipping = t_smooth.copy()
    tip = t_arr > 2060
    t_tipping[tip] += 0.8 * (1 - np.exp(-(t_arr[tip] - 2060) / 10))
    ax2.plot(t_arr, t_smooth, 'b-', linewidth=2.5, label='FaIR (smooth)')
    ax2.plot(t_arr, t_tipping, 'r-', linewidth=2.5, label='Con tipping point')
    ax2.axvline(x=2060, color='red', linestyle=':', alpha=0.5)
    ax2.set_xlabel('Anno', fontsize=13)
    ax2.set_ylabel('Temperatura (°C)', fontsize=13)
    ax2.set_title('Cosa manca: transizioni di regime', fontsize=14, fontweight='bold')
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    savefig('18_tipping_points.png')

    for scen in scenarios:
        d2t = np.diff(get_temp(f, scen, 'default'), n=2)
        print(f'  {scen.upper()}: max |d²T/dt²| = {np.max(np.abs(d2t)):.6f}')


def path_dependency():
    """Stesse emissioni cumulative, percorso diverso."""
    f = create_fair(['ssp245', 'ssp585'], ['default'])
    set_climate(f, 'default', [8.0, 100.0, 300.0], [1.0, 2.0, 0.5])
    init_fair(f)
    f.run()

    cum_245 = np.asarray(f.cumulative_emissions.loc[dict(
        scenario='ssp245', config='default', specie='CO2')])
    cum_585 = np.asarray(f.cumulative_emissions.loc[dict(
        scenario='ssp585', config='default', specie='CO2')])
    temp_245 = get_temp(f, 'ssp245', 'default')
    temp_585 = get_temp(f, 'ssp585', 'default')

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(20, 7))
    ax1.plot(f.timebounds, cum_245, 'b-', linewidth=2.5, label='SSP2-4.5')
    ax1.plot(f.timebounds, cum_585, 'r-', linewidth=2.5, label='SSP5-8.5')
    ax1.set_xlabel('Anno', fontsize=13)
    ax1.set_ylabel('Emissioni cumulative (GtCO2)', fontsize=13)
    ax1.set_title('Percorsi diversi', fontsize=14, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    ax2.plot(f.timebounds, temp_245, 'b-', linewidth=2.5, label='SSP2-4.5')
    ax2.plot(f.timebounds, temp_585, 'r-', linewidth=2.5, label='SSP5-8.5')
    ax2.set_xlabel('Anno', fontsize=13)
    ax2.set_ylabel('Temperatura (°C)', fontsize=13)
    ax2.set_title('Temperatura nel tempo', fontsize=14, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    ax3.plot(cum_245[100:], temp_245[100:], 'b-', linewidth=2.5, label='SSP2-4.5')
    ax3.plot(cum_585[100:], temp_585[100:], 'r-', linewidth=2.5, label='SSP5-8.5')
    ax3.set_xlabel('Emissioni cumulative (GtCO2)', fontsize=13)
    ax3.set_ylabel('Temperatura (°C)', fontsize=13)
    ax3.set_title('T vs cumulative (TCRE)\nSe coincidono = path independent',
                  fontsize=14, fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    savefig('19_path_dependency.png')

    idx = np.argmin(np.abs(cum_585 - cum_245[-1]))
    print(f'  SSP245 cumulative 2100: {cum_245[-1]:.0f} GtCO2')
    print(f'  SSP585 raggiunge lo stesso nell\'anno {f.timebounds[idx]:.0f}')
    print(f'  Differenza T: {abs(temp_245[-1] - temp_585[idx]):.2f}°C')


def zero_dimensioni():
    """FaIR: 1 numero per anno, nessuna geografia."""
    f = create_fair(['ssp245'], ['default'])
    set_climate(f, 'default', [8.0, 100.0, 300.0], [1.0, 2.0, 0.5])
    init_fair(f)
    f.run()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))
    ax1.plot(f.timebounds, get_temp(f, 'ssp245', 'default'), 'b-', linewidth=3)
    ax1.set_xlabel('Anno', fontsize=13)
    ax1.set_ylabel('Temperatura media globale (°C)', fontsize=13)
    ax1.set_title('Cosa produce FaIR:\nUN numero per anno. Nessuna geografia.',
                 fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    for x, y, t in [(1900, 1.8, 'Nessuna latitudine'), (1850, 1.4, 'Nessun oceano separato'),
                     (1900, 1.0, 'Nessun continente'), (1850, 0.6, 'Nessuna stagione')]:
        ax1.text(x, y, '✗ ' + t, fontsize=11, color='#F44336', fontfamily='monospace')

    ax2.set_xlim(0, 10)
    ax2.set_ylim(0, 10)
    ax2.axis('off')
    ax2.text(2, 8, 'FaIR', fontsize=20, fontweight='bold', color='#2196F3', ha='center')
    ax2.text(2, 7, '0 dimensioni\n1 numero/anno\n~2000 righe', fontsize=11, ha='center',
            color='gray', bbox=dict(boxstyle='round', facecolor='#E3F2FD', edgecolor='#2196F3'))
    ax2.text(5, 7.5, 'vs', fontsize=16, ha='center', fontweight='bold')
    ax2.text(8, 8, 'GCM (CMIP6)', fontsize=20, fontweight='bold', color='#F44336', ha='center')
    ax2.text(8, 7, '3 dimensioni\n~100km griglia\n~1M righe', fontsize=11, ha='center',
            color='gray', bbox=dict(boxstyle='round', facecolor='#FFEBEE', edgecolor='#F44336'))
    lost = ['Amplificazione polare (2-4x)', 'Pattern precipitazione', 'Correnti oceaniche',
            'Interazioni terra-oceano', 'Gradienti che guidano feedback', 'Estremi locali']
    ax2.text(5, 5.5, 'Perso nella compressione:', fontsize=13, ha='center', fontweight='bold')
    for i, item in enumerate(lost):
        ax2.text(5, 4.8 - i*0.6, f'• {item}', fontsize=10, ha='center', color='#D32F2F')
    ax2.set_title('Da 3D a 0D', fontsize=14, fontweight='bold', pad=20)
    savefig('20_zero_dimensioni.png')


def ecs_collapse():
    """Stessa ECS, dinamica transitoria diversa."""
    configs = {
        'Oceano poco profondo': ([6.0, 80.0, 250.0], [0.85, 1.5, 0.4], 1.2, 7.5),
        'Oceano profondo':      ([12.0, 150.0, 400.0], [1.3, 2.5, 0.6], 1.35, 8.5),
        'Default IPCC':         ([8.0, 100.0, 300.0], [1.0, 2.0, 0.5], 1.28, 8.0),
    }
    f = create_fair(['ssp245'], list(configs.keys()))
    for name, (ohc, oht, doe, f4) in configs.items():
        set_climate(f, name, ohc, oht, doe, f4)
    init_fair(f)
    f.run()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))
    colors = ['#2196F3', '#F44336', '#4CAF50']
    for i, name in enumerate(configs):
        temp = get_temp(f, 'ssp245', name)
        ax1.plot(f.timebounds, temp,
                label=f'{name} ({temp[-1]:.2f}°C)',
                linewidth=2.5, color=colors[i])
        rate = np.convolve(np.diff(temp) * 10, np.ones(10)/10, mode='valid')
        ax2.plot(f.timebounds[5:5+len(rate)], rate, label=name, linewidth=2.5, color=colors[i])
    ax1.set_xlabel('Anno', fontsize=13)
    ax1.set_ylabel('Temperatura (°C)', fontsize=13)
    ax1.set_title('Parametri diversi, risposta diversa', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax2.set_xlabel('Anno', fontsize=13)
    ax2.set_ylabel('°C/decade', fontsize=13)
    ax2.set_title('Tasso di riscaldamento\nL\'ECS non cattura questa differenza',
                  fontsize=14, fontweight='bold')
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    ax2.axhline(y=0, color='black', linewidth=0.5)
    savefig('21_ecs_collapse.png')


def smooth():
    """Derivata seconda sempre piccola."""
    scenarios = ['ssp119', 'ssp126', 'ssp245', 'ssp370', 'ssp585']
    f = create_fair(scenarios, ['default'])
    set_climate(f, 'default', [8.0, 100.0, 300.0], [1.0, 2.0, 0.5])
    init_fair(f)
    f.run()

    fig, ax = plt.subplots(figsize=(14, 7))
    colors = ['#2196F3', '#4CAF50', '#FFC107', '#FF5722', '#D32F2F']
    for i, scen in enumerate(scenarios):
        d2t = np.diff(get_temp(f, scen, 'default'), n=2)
        d2t_s = np.convolve(d2t, np.ones(5)/5, mode='valid')
        ax.plot(f.timebounds[3:-3], d2t_s, label=scen.upper(),
               linewidth=2, color=colors[i])
    ax.axhline(y=0, color='black', linewidth=0.5)
    ax.set_xlabel('Anno', fontsize=13)
    ax.set_ylabel('d²T/dt² (°C/anno²)', fontsize=13)
    ax.set_title('Accelerazione: sempre piccola e liscia\n'
                 'Nessun salto di regime possibile', fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    savefig('22_smooth.png')


def incertezza_strutturale():
    """Parametrica vs strutturale vs non esplorata."""
    param_configs = {
        'low':  ([5.0, 70.0, 250.0], [1.5, 2.0, 0.5], 1.1, 7.0),
        'mid':  ([8.0, 100.0, 300.0], [1.0, 2.0, 0.5], 1.28, 8.0),
        'high': ([4.5, 55.0, 180.0], [0.6, 1.3, 0.35], 1.4, 9.0),
    }
    f = create_fair(['ssp245'], list(param_configs.keys()))
    for name, (ohc, oht, doe, f4) in param_configs.items():
        set_climate(f, name, ohc, oht, doe, f4)
    init_fair(f)
    f.run()
    param_temps = [float(get_temp(f, 'ssp245', n)[-1]) for n in param_configs]

    methods = ['myhre1998', 'etminan2016', 'meinshausen2020', 'leach2021']
    struct_temps = []
    for method in methods:
        fm = FAIR(ghg_method=method)
        fm.define_time(1750, 2100, 1)
        fm.define_scenarios(['ssp245'])
        fm.define_configs(['d'])
        sp, pr = read_properties()
        fm.define_species(sp, pr)
        fm.allocate()
        fm.fill_species_configs()
        fm.fill_from_rcmip()
        set_climate(fm, 'd', [8.0, 100.0, 300.0], [1.0, 2.0, 0.5])
        init_fair(fm)
        fm.run()
        struct_temps.append(float(get_temp(fm, 'ssp245', 'd')[-1]))

    fig, ax = plt.subplots(figsize=(14, 8))
    pr = max(param_temps) - min(param_temps)
    sr = max(struct_temps) - min(struct_temps)
    ax.barh(0, pr, left=min(param_temps), height=0.4,
           color='#1976D2', alpha=0.7, label='Parametrica (esplorata)')
    ax.plot(param_temps, [0]*3, 'ko', markersize=8)
    ax.barh(1, sr, left=min(struct_temps), height=0.4,
           color='#F44336', alpha=0.7, label='Strutturale (4 formule)')
    ax.plot(struct_temps, [1]*4, 'ko', markersize=8)
    ax.barh(2, 3.0, left=1.5, height=0.4,
           color='#9E9E9E', alpha=0.4, label='Strutturale non esplorata')
    ax.text(3.0, 2, '?', fontsize=20, ha='center', va='center',
           fontweight='bold', color='white')
    ax.set_yticks([0, 1, 2])
    ax.set_yticklabels(['Parametrica\n(esplorata)', 'Strutturale\n(4 formule)',
                        'Strutturale\n(non esplorata)'], fontsize=12)
    ax.set_xlabel('Temperatura 2100, SSP2-4.5 (°C)', fontsize=13)
    ax.set_title('Incertezza parametrica vs strutturale', fontsize=14, fontweight='bold')
    ax.legend(fontsize=11, loc='lower right')
    ax.grid(True, alpha=0.3, axis='x')
    savefig('23_incertezza_strutturale.png')
    print(f'  Parametrica: {pr:.2f}°C, Strutturale (formule): {sr:.2f}°C')


def distribuzioni():
    """Stessa ECS range, forma diversa, probabilita' diverse."""
    np.random.seed(42)
    N = 300
    dists = {
        'Uniforme':       (np.random.uniform(2.0, 5.0, N), '#2196F3'),
        'Gauss(3, 0.5)':  (np.clip(np.random.normal(3.0, 0.5, N), 2.0, 5.0), '#4CAF50'),
        'Gauss(3.5, 0.8)':(np.clip(np.random.normal(3.5, 0.8, N), 2.0, 5.0), '#FF9800'),
        'Log-normale':    (np.clip(np.random.lognormal(np.log(3.0), 0.3, N), 2.0, 5.0), '#F44336'),
    }
    all_results = {}
    for dist_name, (samples, color) in dists.items():
        print(f'    {dist_name}...')
        configs = [f'd_{i}' for i in range(N)]
        f = create_fair(['ssp245'], configs)
        for i, name in enumerate(configs):
            ecs = samples[i]
            set_climate(f, name, [8.0/(ecs/3.0), 100.0, 300.0],
                       [1.0/(ecs/3.0), 2.0, 0.5])
        init_fair(f)
        try:
            f.run()
            temps = [float(get_temp(f, 'ssp245', n)[-1]) for n in configs]
            all_results[dist_name] = np.array(temps)
        except Exception:
            continue

    fig, axes = plt.subplots(2, 2, figsize=(18, 14))
    for dist_name, (samples, color) in dists.items():
        axes[0, 0].hist(samples, bins=30, alpha=0.5, color=color,
                       label=dist_name, edgecolor='white')
    axes[0, 0].set_xlabel('ECS (°C)', fontsize=13)
    axes[0, 0].set_title('INPUT: distribuzioni ECS', fontsize=14, fontweight='bold')
    axes[0, 0].legend(fontsize=9)
    axes[0, 0].grid(True, alpha=0.3)

    for dist_name, (_, color) in dists.items():
        if dist_name in all_results:
            v = all_results[dist_name][(all_results[dist_name] > 0) & (all_results[dist_name] < 10)]
            axes[0, 1].hist(v, bins=30, alpha=0.5, color=color,
                           label=dist_name, edgecolor='white')
    axes[0, 1].set_xlabel('Temperatura 2100 (°C)', fontsize=13)
    axes[0, 1].set_title('OUTPUT: temperature risultanti', fontsize=14, fontweight='bold')
    axes[0, 1].legend(fontsize=9)
    axes[0, 1].grid(True, alpha=0.3)

    pcts = [5, 25, 50, 75, 95]
    x_pos = np.arange(len(pcts))
    w = 0.18
    for j, (dist_name, (_, color)) in enumerate(dists.items()):
        if dist_name in all_results:
            v = all_results[dist_name][(all_results[dist_name] > 0) & (all_results[dist_name] < 10)]
            axes[1, 0].bar(x_pos + (j-1.5)*w, [np.percentile(v, p) for p in pcts],
                          w, color=color, alpha=0.7, label=dist_name)
    axes[1, 0].set_xticks(x_pos)
    axes[1, 0].set_xticklabels([f'{p}°' for p in pcts])
    axes[1, 0].set_title('Percentili a confronto', fontsize=14, fontweight='bold')
    axes[1, 0].legend(fontsize=8)
    axes[1, 0].grid(True, alpha=0.3, axis='y')

    thresholds = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
    for dist_name, (_, color) in dists.items():
        if dist_name in all_results:
            v = all_results[dist_name][(all_results[dist_name] > 0) & (all_results[dist_name] < 10)]
            axes[1, 1].plot(thresholds, [100*np.mean(v > t) for t in thresholds],
                           'o-', color=color, linewidth=2.5, markersize=8, label=dist_name)
    axes[1, 1].set_xlabel('Soglia (°C)', fontsize=13)
    axes[1, 1].set_ylabel('Probabilita\' superamento (%)', fontsize=13)
    axes[1, 1].set_title('Cambia distribuzione, cambia probabilita\'',
                        fontsize=14, fontweight='bold')
    axes[1, 1].legend(fontsize=9)
    axes[1, 1].grid(True, alpha=0.3)
    savefig('24_distribuzioni.png')


def hindcast_forecast():
    """Calibrato su periodi diversi, futuro diverso."""
    configs = {
        'Calibrato 1850-2020': ([8.0, 100.0, 300.0], [1.0, 2.0, 0.5], 1.28, 8.0),
        'Calibrato 1850-1980': ([10.0, 130.0, 380.0], [1.3, 2.2, 0.55], 1.15, 7.2),
        'Calibrato 1980-2020': ([5.5, 65.0, 200.0], [0.7, 1.5, 0.4], 1.4, 8.8),
    }
    f = create_fair(['ssp245'], list(configs.keys()))
    for name, (ohc, oht, doe, f4) in configs.items():
        set_climate(f, name, ohc, oht, doe, f4)
    init_fair(f)
    f.run()

    obs = {1850:-0.04, 1860:0.00, 1870:0.04, 1880:0.06, 1890:0.02, 1900:0.07,
           1910:0.00, 1920:0.12, 1930:0.19, 1940:0.32, 1950:0.30, 1960:0.32,
           1970:0.32, 1980:0.42, 1990:0.59, 2000:0.75, 2010:0.96, 2020:1.23}

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))
    colors = ['#4CAF50', '#2196F3', '#F44336']
    for i, name in enumerate(configs):
        temp = get_temp(f, 'ssp245', name)
        bl = np.mean(temp[100:150])
        adj = temp - bl
        ax1.plot(f.timebounds[100:270], adj[100:270], label=name,
                linewidth=2, color=colors[i])
        t2100 = float(adj[-1])
        ax2.plot(f.timebounds[270:], adj[270:],
                label=f'{name} -> {t2100:.1f}°C',
                linewidth=2.5, color=colors[i])
    ax1.scatter(list(obs.keys()), list(obs.values()), color='black', s=50,
               zorder=5, label='Osservati')
    ax1.set_title('Hindcast: tutte fittano il passato', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(1850, 2020)
    ax2.set_title('Forecast: divergono\nValidare sul passato non garantisce il futuro',
                  fontsize=14, fontweight='bold')
    ax2.legend(fontsize=11)
    ax2.grid(True, alpha=0.3)
    savefig('25_hindcast_forecast.png')

    for name in configs:
        temp = get_temp(f, 'ssp245', name)
        bl = np.mean(temp[100:150])
        print(f'  {name}: T(2100) = {temp[-1]-bl:.2f}°C')


def error_compensation():
    """Giusto per i motivi sbagliati."""
    configs = {
        'Default':          ([8.0, 100.0, 300.0], [1.0, 2.0, 0.5], 1.28, 8.0, 1.0, -1.0),
        'Compensato +CO2':  ([8.0, 100.0, 300.0], [1.0, 2.0, 0.5], 1.28, 8.0, 1.3, -1.8),
        'Compensato -CO2':  ([8.0, 100.0, 300.0], [1.0, 2.0, 0.5], 1.28, 8.0, 0.75, -0.3),
    }
    f = create_fair(['ssp245'], list(configs.keys()))
    for name, (ohc, oht, doe, f4, fs, aci) in configs.items():
        set_climate(f, name, ohc, oht, doe, f4)
        fill(f.species_configs['forcing_scale'], fs, specie='CO2', config=name)
        fill(f.species_configs['aci_scale'], aci, config=name)
    init_fair(f)
    f.run()

    obs = {1850:-0.04, 1860:0.00, 1870:0.04, 1880:0.06, 1890:0.02, 1900:0.07,
           1910:0.00, 1920:0.12, 1930:0.19, 1940:0.32, 1950:0.30, 1960:0.32,
           1970:0.32, 1980:0.42, 1990:0.59, 2000:0.75, 2010:0.96, 2020:1.23}

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))
    colors = ['#4CAF50', '#2196F3', '#F44336']
    for i, name in enumerate(configs):
        temp = get_temp(f, 'ssp245', name)
        bl = np.mean(temp[100:150])
        adj = temp - bl
        ax1.plot(f.timebounds[100:270], adj[100:270], label=name,
                linewidth=2.5, color=colors[i])
        ax2.plot(f.timebounds[270:], adj[270:],
                label=f'{name} ({adj[-1]:.1f}°C)',
                linewidth=2.5, color=colors[i])
    ax1.scatter(list(obs.keys()), list(obs.values()), color='black', s=40, zorder=5)
    ax1.set_title('Passato: convergono (error compensation)',
                 fontsize=14, fontweight='bold')
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(1850, 2020)
    ax2.set_title('Futuro: divergono (la compensazione salta)',
                 fontsize=14, fontweight='bold')
    ax2.legend(fontsize=11)
    ax2.grid(True, alpha=0.3)
    savefig('26_error_compensation.png')


def non_identificabilita():
    """Problema inverso mal posto: 457/1000 fittano, range 1.8-4.6°C."""
    np.random.seed(123)
    N = 1000
    tolerance = 0.3
    obs_2020 = 1.23

    configs = [f'c_{i}' for i in range(N)]
    f = create_fair(['ssp245'], configs)
    param_sets = []
    for i, name in enumerate(configs):
        p = {'ohc': np.random.uniform(4.0, 14.0),
             'oht': np.random.uniform(0.4, 2.0),
             'doe': np.random.uniform(1.0, 1.6),
             'f4co2': np.random.uniform(6.5, 9.5),
             'fs': np.random.uniform(0.7, 1.3),
             'aci': np.random.uniform(-2.0, -0.3)}
        set_climate(f, name, [p['ohc'], 100.0, 300.0],
                   [p['oht'], 2.0, 0.5], p['doe'], p['f4co2'])
        fill(f.species_configs['forcing_scale'], p['fs'], specie='CO2', config=name)
        fill(f.species_configs['aci_scale'], p['aci'], config=name)
        param_sets.append(p)
    init_fair(f)
    f.run()

    good_idx, good_t2100 = [], []
    for i, name in enumerate(configs):
        temp = get_temp(f, 'ssp245', name)
        bl = np.mean(temp[100:150])
        adj = temp - bl
        t2020, t2100 = float(adj[270]), float(adj[-1])
        if abs(t2020 - obs_2020) < tolerance and 0 < t2100 < 10:
            good_idx.append(i)
            good_t2100.append(t2100)
    good_t2100 = np.array(good_t2100)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))
    ax1.hist(good_t2100, bins=25, color='#1976D2', alpha=0.7, edgecolor='white')
    ax1.axvline(x=2.78, color='green', linewidth=2.5, label='Default IPCC')
    ax1.axvline(x=np.median(good_t2100), color='purple', linewidth=2, linestyle='--',
               label=f'Mediana: {np.median(good_t2100):.1f}°C')
    ax1.set_xlabel('Temperatura 2100 (°C)', fontsize=13)
    ax1.set_title(f'NON-IDENTIFICABILITA\'\n{len(good_t2100)} config fittano T(2020)±{tolerance}°C\n'
                  f'Range: {good_t2100.min():.1f} a {good_t2100.max():.1f}°C',
                  fontsize=14, fontweight='bold')
    ax1.legend(fontsize=11)
    ax1.grid(True, alpha=0.3)

    gp = [param_sets[i] for i in good_idx]
    scatter = ax2.scatter([p['aci'] for p in gp],
                         [p['f4co2']/(2*p['oht']) for p in gp],
                         c=good_t2100, cmap='RdYlBu_r', s=30, alpha=0.7)
    plt.colorbar(scatter, ax=ax2, label='T(2100) °C')
    ax2.set_xlabel('Parametro aerosol', fontsize=13)
    ax2.set_ylabel('Proxy ECS', fontsize=13)
    ax2.set_title('Spazio parametri: tutte fittano il passato\nma futuri diversi',
                  fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    savefig('27_non_identificabilita.png')
    print(f'  {len(good_t2100)}/{N} fittano. Range: {good_t2100.min():.1f}-{good_t2100.max():.1f}°C')


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    print('=== 02 — ANALISI STRUTTURALE ===\n')
    print('Linearita\'...')
    linearita()
    print('\nTipping points...')
    tipping_points()
    print('\nPath dependency...')
    path_dependency()
    print('\nZero dimensioni...')
    zero_dimensioni()
    print('\nECS collapse...')
    ecs_collapse()
    print('\nSmooth...')
    smooth()
    print('\nIncertezza strutturale...')
    incertezza_strutturale()
    print('\nDistribuzioni...')
    distribuzioni()
    print('\nHindcast/forecast...')
    hindcast_forecast()
    print('\nError compensation...')
    error_compensation()
    print('\nNon-identificabilita\'...')
    non_identificabilita()
    print('\nDone.')
