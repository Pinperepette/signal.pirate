"""
01 — Analisi dei parametri
==========================
Sensibilita' ai parametri, forcing scaling, formule GHG,
stress test, Monte Carlo, reverse engineering, aerosol.

Grafici: 01-06, 11-12, 15-16
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


def sensibilita_ecs():
    """Stesso scenario SSP2-4.5, ECS diversa (2.0-5.0)."""
    configs = {
        'ECS_2.0': ([3.0, 50.0, 200.0], [1.7, 1.5, 0.4], 1.1),
        'ECS_3.0': ([8.0, 100.0, 300.0], [1.0, 2.0, 0.5], 1.28),
        'ECS_4.5': ([6.0, 80.0, 250.0], [0.6, 1.5, 0.4], 1.4),
        'ECS_5.0': ([5.0, 70.0, 220.0], [0.5, 1.3, 0.35], 1.5),
    }
    f = create_fair(['ssp245'], list(configs.keys()))
    for name, (ohc, oht, doe) in configs.items():
        set_climate(f, name, ohc, oht, doe)
    init_fair(f)
    f.run()

    fig, ax = plt.subplots(figsize=(12, 7))
    colors = ['#2196F3', '#4CAF50', '#FF9800', '#F44336']
    for i, name in enumerate(configs):
        temp = get_temp(f, 'ssp245', name)
        ax.plot(f.timebounds, temp,
                label=f'{name.replace("_", " = ")} °C',
                linewidth=2.5, color=colors[i])
    ax.set_xlabel('Anno', fontsize=14)
    ax.set_ylabel('Anomalia di temperatura (°C)', fontsize=14)
    ax.set_title('STESSO scenario (SSP2-4.5), parametri diversi\n'
                 'Tutti i valori sono dentro il range IPCC AR6',
                 fontsize=16, fontweight='bold')
    ax.legend(fontsize=13, title='Climate Sensitivity', title_fontsize=13)
    ax.grid(True, alpha=0.3)
    ax.axhline(y=1.5, color='red', linestyle='--', alpha=0.5)
    ax.axhline(y=2.0, color='darkred', linestyle='--', alpha=0.5)
    ax.text(2102, 1.5, '1.5°C', fontsize=11, color='red', va='center')
    ax.text(2102, 2.0, '2.0°C', fontsize=11, color='darkred', va='center')
    savefig('01_sensibilita_ecs.png')

    print('  Temperatura nel 2100:')
    for name in configs:
        print(f'    {name}: {get_temp(f, "ssp245", name)[-1]:.2f} °C')


def forcing_scaling():
    """Effetto del forcing_scale (±20%)."""
    scales = [0.8, 1.0, 1.2]
    names = [f'scale_{s}' for s in scales]
    f = create_fair(['ssp245'], names)
    for i, name in enumerate(names):
        set_climate(f, name, [8.0, 100.0, 300.0], [1.0, 2.0, 0.5])
        fill(f.species_configs['forcing_scale'], scales[i],
             specie='CO2', config=name)
    init_fair(f)
    f.run()

    fig, ax = plt.subplots(figsize=(12, 7))
    colors = ['#2196F3', '#4CAF50', '#F44336']
    for i, name in enumerate(names):
        ax.plot(f.timebounds, get_temp(f, 'ssp245', name),
                label=f'forcing_scale = {scales[i]}',
                linewidth=2.5, color=colors[i])
    ax.set_xlabel('Anno', fontsize=14)
    ax.set_ylabel('Anomalia di temperatura (°C)', fontsize=14)
    ax.set_title('Effetto del forcing_scaling sulla temperatura\n'
                 '±20% sul parametro, risultati completamente diversi',
                 fontsize=16, fontweight='bold')
    ax.legend(fontsize=13)
    ax.grid(True, alpha=0.3)
    savefig('02_forcing_scaling.png')


def formule_ghg():
    """4 formule diverse per il forcing GHG."""
    methods = ['myhre1998', 'etminan2016', 'meinshausen2020', 'leach2021']
    results = {}
    for method in methods:
        fm = FAIR(ghg_method=method)
        fm.define_time(1750, 2100, 1)
        fm.define_scenarios(['ssp245'])
        fm.define_configs(['default'])
        from fair.io import read_properties as rp
        sp, pr = rp()
        fm.define_species(sp, pr)
        fm.allocate()
        fm.fill_species_configs()
        fm.fill_from_rcmip()
        set_climate(fm, 'default', [8.0, 100.0, 300.0], [1.0, 2.0, 0.5])
        init_fair(fm)
        fm.run()
        results[method] = {
            'time': fm.timebounds if isinstance(fm.timebounds, np.ndarray)
                    else fm.timebounds,
            'temp': get_temp(fm, 'ssp245', 'default'),
            'forcing_co2': np.asarray(fm.forcing.loc[dict(
                scenario='ssp245', config='default', specie='CO2')]),
        }

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))
    colors = ['#9C27B0', '#2196F3', '#4CAF50', '#FF9800']
    for i, method in enumerate(methods):
        ax1.plot(results[method]['time'], results[method]['temp'],
                label=method, linewidth=2.5, color=colors[i])
        ax2.plot(results[method]['time'], results[method]['forcing_co2'],
                label=method, linewidth=2.5, color=colors[i])
    ax1.set_xlabel('Anno', fontsize=14)
    ax1.set_ylabel('Anomalia di temperatura (°C)', fontsize=14)
    ax1.set_title('4 formule diverse, stesso scenario\nTemperatura',
                  fontsize=14, fontweight='bold')
    ax1.legend(fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax2.set_xlabel('Anno', fontsize=14)
    ax2.set_ylabel('Forcing CO2 (W/m²)', fontsize=14)
    ax2.set_title('4 formule diverse, stesso scenario\nForcing radiativo CO2',
                  fontsize=14, fontweight='bold')
    ax2.legend(fontsize=12)
    ax2.grid(True, alpha=0.3)
    plt.suptitle('Stessi dati di input, formula diversa, output diverso',
                 fontsize=16, fontweight='bold', y=1.02)
    savefig('03_formule_diverse.png')


def stress_test():
    """Parametri ai bordi estremi."""
    configs = {
        'Ottimista estremo': ([3.5, 60.0, 250.0], [1.8, 1.8, 0.5], 1.1, 6.5, 0.75),
        'Default IPCC':      ([8.0, 100.0, 300.0], [1.0, 2.0, 0.5], 1.28, 8.0, 1.0),
        'Pessimista estremo':([4.0, 50.0, 150.0], [0.4, 1.0, 0.3], 1.6, 9.5, 1.25),
    }
    f = create_fair(['ssp245'], list(configs.keys()))
    for name, (ohc, oht, doe, f4co2, fs) in configs.items():
        set_climate(f, name, ohc, oht, doe, f4co2)
        fill(f.species_configs['forcing_scale'], fs, specie='CO2', config=name)
    init_fair(f)
    f.run()

    fig, ax = plt.subplots(figsize=(12, 8))
    colors = ['#2196F3', '#4CAF50', '#F44336']
    for i, name in enumerate(configs):
        temp = get_temp(f, 'ssp245', name)
        ax.plot(f.timebounds, temp, label=name, linewidth=3, color=colors[i])
    ax.fill_between(f.timebounds,
                    get_temp(f, 'ssp245', 'Ottimista estremo'),
                    get_temp(f, 'ssp245', 'Pessimista estremo'),
                    alpha=0.15, color='gray')
    ax.axhline(y=1.5, color='orange', linestyle=':', alpha=0.7)
    ax.axhline(y=2.0, color='red', linestyle=':', alpha=0.7)
    ax.set_xlabel('Anno', fontsize=14)
    ax.set_ylabel('Anomalia di temperatura (°C)', fontsize=14)
    ax.set_title('STRESS TEST: tutti i parametri ai bordi estremi\n'
                 'Stesso scenario SSP2-4.5, stesse emissioni',
                 fontsize=16, fontweight='bold')
    ax.legend(fontsize=14, loc='upper left')
    ax.grid(True, alpha=0.3)
    savefig('06_stress_test.png')

    for name in configs:
        print(f'  {name}: {get_temp(f, "ssp245", name)[-1]:.2f} °C')


def monte_carlo(n_batches=20, batch_size=500):
    """Monte Carlo: n_batches * batch_size run con parametri random."""
    np.random.seed(42)
    all_temps_2100 = []
    all_temps_2050 = []
    total = n_batches * batch_size
    print(f'  {total} run...')

    for batch in range(n_batches):
        configs = [f'mc_{batch}_{i}' for i in range(batch_size)]
        f = create_fair(['ssp245'], configs)
        for i, name in enumerate(configs):
            set_climate(f, name,
                       [np.random.uniform(3.0, 15.0),
                        np.random.uniform(40.0, 160.0),
                        np.random.uniform(100.0, 500.0)],
                       [np.random.uniform(0.3, 2.2),
                        np.random.uniform(0.8, 3.0),
                        np.random.uniform(0.2, 0.8)],
                       np.random.uniform(0.9, 1.7),
                       np.random.uniform(6.0, 10.0))
            fill(f.species_configs['forcing_scale'],
                 np.random.uniform(0.7, 1.3), specie='CO2', config=name)
            fill(f.species_configs['aci_scale'],
                 np.random.uniform(-2.5, -0.2), config=name)
        init_fair(f)
        try:
            f.run()
            for name in configs:
                temp = get_temp(f, 'ssp245', name)
                all_temps_2100.append(float(temp[-1]))
                all_temps_2050.append(float(temp[300]))
        except Exception:
            continue
        if (batch + 1) % 5 == 0:
            print(f'    {(batch+1)*batch_size} completate')

    t = np.array(all_temps_2100)
    t50 = np.array(all_temps_2050)
    valid = (t > -5) & (t < 15)
    t, t50 = t[valid], t50[valid]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))
    ax1.hist(t, bins=80, color='#1976D2', alpha=0.7, edgecolor='white', linewidth=0.5)
    ax1.axvline(x=2.78, color='green', linewidth=2.5, label=f'Default IPCC: 2.78°C')
    ax1.axvline(x=1.5, color='orange', linewidth=2, linestyle='--', label='1.5°C')
    ax1.axvline(x=2.0, color='red', linewidth=2, linestyle='--', label='2.0°C')
    ax1.axvline(x=np.median(t), color='purple', linewidth=2,
               label=f'Mediana: {np.median(t):.1f}°C')
    ax1.set_xlabel('Temperatura 2100 (°C)', fontsize=14)
    ax1.set_ylabel('Numero di run', fontsize=14)
    ax1.set_title(f'Monte Carlo: {len(t)} run\n'
                  f'Range: {t.min():.1f} a {t.max():.1f}°C',
                  fontsize=14, fontweight='bold')
    ax1.legend(fontsize=11)
    ax1.grid(True, alpha=0.3)

    ax2.scatter(t50, t, alpha=0.15, s=8, color='#1976D2')
    ax2.set_xlabel('Temperatura 2050 (°C)', fontsize=14)
    ax2.set_ylabel('Temperatura 2100 (°C)', fontsize=14)
    ax2.set_title('Anche conoscendo T(2050),\nT(2100) resta incerto',
                  fontsize=14, fontweight='bold')
    ax2.axhline(y=1.5, color='orange', linestyle='--', alpha=0.5)
    ax2.axhline(y=2.0, color='red', linestyle='--', alpha=0.5)
    ax2.grid(True, alpha=0.3)
    savefig('12_monte_carlo.png')

    print(f'  Range: {t.min():.2f} - {t.max():.2f}°C')
    print(f'  Mediana: {np.median(t):.2f}°C')
    print(f'  Sotto 1.5°C: {100*(t<1.5).mean():.1f}%')
    print(f'  Sotto 2.0°C: {100*(t<2.0).mean():.1f}%')


def reverse_engineering():
    """Da 1.3 a 8.8°C, stesse emissioni."""
    targets = {
        'Nessun problema':  ([4.0, 80.0, 350.0], [2.0, 2.0, 0.6], 1.0, 6.0, 0.7, -1.8),
        'Target Parigi':    ([5.0, 70.0, 280.0], [1.5, 1.8, 0.5], 1.1, 7.0, 0.85, -1.2),
        'Default IPCC':     ([8.0, 100.0, 300.0], [1.0, 2.0, 0.5], 1.28, 8.0, 1.0, -1.0),
        'Catastrofe':       ([4.5, 55.0, 180.0], [0.5, 1.2, 0.35], 1.4, 9.0, 1.15, -0.4),
        'Apocalisse':       ([3.5, 45.0, 140.0], [0.4, 0.9, 0.3], 1.5, 9.5, 1.25, -0.3),
    }
    fig, ax = plt.subplots(figsize=(14, 8))
    colors = ['#2196F3', '#4CAF50', '#FF9800', '#F44336', '#880E4F']
    for i, (label, params) in enumerate(targets.items()):
        temp, time = run_single(*params)
        t2100 = float(temp[-1])
        ax.plot(time, temp, label=f'{label} ({t2100:.1f}°C)',
                linewidth=2.5, color=colors[i])
        print(f'  {label}: {t2100:.2f}°C')
    ax.set_xlabel('Anno', fontsize=14)
    ax.set_ylabel('Anomalia di temperatura (°C)', fontsize=14)
    ax.set_title('Risultati molto diversi, parametri tutti plausibili\n'
                 'Stesso scenario SSP2-4.5',
                 fontsize=15, fontweight='bold')
    ax.legend(fontsize=11, loc='upper left')
    ax.grid(True, alpha=0.3)
    savefig('11_reverse_engineering.png')


def trucco_aerosol():
    """ERFaci: la principale fonte di spread."""
    aci_values = np.linspace(-3.0, 0.0, 20)
    temps_2100, temps_2050 = [], []
    for aci in aci_values:
        try:
            temp, _ = run_single([8.0, 100.0, 300.0], [1.0, 2.0, 0.5],
                                 1.28, 8.0, 1.0, aci)
            temps_2100.append(float(temp[-1]))
            temps_2050.append(float(temp[300]))
        except Exception:
            temps_2100.append(np.nan)
            temps_2050.append(np.nan)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))
    ax1.plot(aci_values, temps_2100, 'b-o', linewidth=2.5, markersize=6, label='T(2100)')
    ax1.plot(aci_values, temps_2050, 'g-s', linewidth=2, markersize=5, label='T(2050)')
    ax1.axhline(y=0, color='black', linewidth=1)
    ax1.axhline(y=1.5, color='orange', linestyle='--', alpha=0.7, label='1.5°C')
    ax1.axhline(y=2.0, color='red', linestyle='--', alpha=0.7, label='2.0°C')
    ax1.axvspan(-2.0, -0.5, alpha=0.1, color='green', label='Range IPCC AR6')
    ax1.set_xlabel('ERFaci (W/m²)', fontsize=14)
    ax1.set_ylabel('Temperatura (°C)', fontsize=14)
    ax1.set_title('Temperatura come funzione del parametro aerosol',
                  fontsize=14, fontweight='bold')
    ax1.legend(fontsize=11)
    ax1.grid(True, alpha=0.3)

    ghg_f = np.linspace(2, 6, 100)
    for aci_val in [-0.5, -1.0, -1.5, -2.0]:
        ax2.plot(ghg_f, ghg_f + aci_val, label=f'ERFaci = {aci_val} W/m²', linewidth=2)
    ax2.fill_between(ghg_f, ghg_f - 2.0, ghg_f - 0.5, alpha=0.1, color='blue',
                    label='Range incertezza aerosol')
    ax2.axhline(y=0, color='black', linewidth=1)
    ax2.set_xlabel('Forcing GHG (W/m²)', fontsize=14)
    ax2.set_ylabel('Forcing NETTO (W/m²)', fontsize=14)
    ax2.set_title('Forcing netto = GHG + Aerosol',
                  fontsize=14, fontweight='bold')
    ax2.legend(fontsize=11)
    ax2.grid(True, alpha=0.3)
    savefig('15_trucco_aerosol.png')


def muro_incertezza():
    """Grafico riassuntivo: ogni parametro sposta il risultato."""
    params = [
        ('Climate Sensitivity\n(ECS)', 2.38, 4.76, 2.78),
        ('Forcing 4xCO2', 2.3, 3.3, 2.78),
        ('forcing_scale CO2\n(±25%)', 2.1, 3.1, 2.78),
        ('Ocean parameters', 1.7, 3.5, 2.78),
        ('deep_ocean_efficacy', 2.4, 3.2, 2.78),
        ('ERFaci (aerosol)', 1.5, 4.5, 2.78),
        ('CO2 box partitions', 2.3, 3.3, 2.78),
        ('Formula GHG\n(4 opzioni)', 2.6, 2.9, 2.78),
        ('TUTTI INSIEME\n(stress test)', 1.71, 7.66, 2.78),
    ]
    fig, ax = plt.subplots(figsize=(14, 9))
    for i, (name, low, high, default) in enumerate(params):
        color = '#F44336' if i == len(params)-1 else '#1976D2'
        alpha = 1.0 if i == len(params)-1 else 0.7
        ax.barh(i, high - low, left=low, height=0.6,
               color=color, alpha=alpha, edgecolor='white')
        ax.plot(default, i, 'k|', markersize=20, markeredgewidth=2)
        ax.text(high + 0.1, i, f'{low:.1f} - {high:.1f}°C', fontsize=10, va='center')
    ax.set_yticks(range(len(params)))
    ax.set_yticklabels([p[0] for p in params], fontsize=11)
    ax.set_xlabel('Temperatura nel 2100, SSP2-4.5 (°C)', fontsize=14)
    ax.set_title('IL MURO DELL\'INCERTEZZA\n'
                 'Ogni parametro sposta il risultato',
                 fontsize=15, fontweight='bold')
    ax.axvline(x=1.5, color='orange', linestyle='--', alpha=0.7)
    ax.axvline(x=2.0, color='red', linestyle='--', alpha=0.7)
    ax.grid(True, alpha=0.2, axis='x')
    ax.invert_yaxis()
    savefig('16_muro_incertezza.png')


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    print('=== 01 — ANALISI DEI PARAMETRI ===\n')
    print('Sensibilita\' ECS...')
    sensibilita_ecs()
    print('\nForcing scaling...')
    forcing_scaling()
    print('\nFormule GHG...')
    formule_ghg()
    print('\nStress test...')
    stress_test()
    print('\nMonte Carlo...')
    monte_carlo()
    print('\nReverse engineering...')
    reverse_engineering()
    print('\nTrucco aerosol...')
    trucco_aerosol()
    print('\nMuro incertezza...')
    muro_incertezza()
    print('\nDone.')
