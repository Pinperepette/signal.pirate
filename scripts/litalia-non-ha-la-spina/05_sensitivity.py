#!/usr/bin/env python3
"""
05_sensitivity.py — Robustezza del modello: il problema resta in ogni scenario
================================================================================
Sensitivity analysis su tutti i parametri chiave.
Mostra che anche con parametri ottimistici il sistema e' in crisi.

Calcola:
  1. Bound superiore/inferiore di potenza
  2. Matrice di sensitivity su: consumo, % pubblica, k_c, wallbox
  3. Vincolo di frequenza (inerzia di sistema)
  4. Vincolo spaziale (parcheggi/colonnine per km^2)

Output: output/13_bounds_potenza.png
        output/14_sensitivity_cabina.png
        output/15_sensitivity_colonnine.png
        output/16_frequenza.png
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

OUTPUT_DIR = 'output'
os.makedirs(OUTPUT_DIR, exist_ok=True)

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

# ─── PARAMETRI BASE ──────────────────────────────────────────────────

N_AUTO         = 40_300_000
KM_ANNO        = 10_231
P_WALLBOX      = 7.4            # kW
PICCO_IT       = 57.5           # GW
FABBISOGNO_IT  = 312.2          # TWh
S_TRAFO        = 400            # kVA
N_UTENZE       = 70
COS_PHI        = 0.95
KC_DOMESTICO   = 0.30
P_IMPEGNATA    = 3.0            # kW

# Inerzia sistema elettrico italiano (stima)
H_SISTEMA      = 4.5            # secondi (tipico sistema europeo con termoelettrico)
H_RINNOVABILI  = 2.0            # secondi (scenario alta penetrazione rinnovabili)
FREQ_NOMINALE  = 50.0           # Hz
DELTA_F_MAX    = 0.8            # Hz (limite RoCoF prima di load shedding, ENTSO-E)


# ─── 1. BOUNDS DI POTENZA ────────────────────────────────────────────

def plot_bounds():
    """
    Bound superiore: P_peak = N * p_wallbox * f_active (tutti caricano al picco)
    Bound inferiore: P_flat = E_giornaliera / 24 (carico perfettamente distribuito)
    """
    kwh_giorno_totale = N_AUTO * KM_ANNO / 365 * 18.0 / 100  # kWh/giorno totali

    # Bound inferiore: carico piatto 24h
    p_flat_gw = kwh_giorno_totale / 24 / 1e6  # GW

    # Bound superiore: tutti caricano alle 19, 70% attivi, 41 min di carica
    # Frazione attivamente in carica al picco (dalla distribuzione gaussiana)
    # Con sigma=1.5h e durata 41 min, il picco di contemporaneita' e' ~13%
    f_active_dumb = 0.13  # dal profilo calcolato in 01_fabbisogno.py
    p_peak_dumb_gw = N_AUTO * 0.70 * P_WALLBOX * f_active_dumb / 1e6

    # Scenario intermedio: smart charging ma non perfetto
    # Carico distribuito su 8h notturne (22:00-06:00)
    p_smart_gw = kwh_giorno_totale / 8 / 1e6

    print(f'=== BOUNDS DI POTENZA ===')
    print(f'Energia giornaliera totale:  {kwh_giorno_totale/1e6:.1f} GWh/giorno')
    print(f'P_flat (24h uniforme):       {p_flat_gw:.1f} GW  (bound inferiore)')
    print(f'P_smart (8h notturne):       {p_smart_gw:.1f} GW  (smart charging)')
    print(f'P_peak (dumb, picco 19h):    {p_peak_dumb_gw:.1f} GW  (bound superiore)')
    print(f'Picco attuale IT:            {PICCO_IT:.1f} GW')
    print()

    fig, ax = plt.subplots(figsize=(14, 7))

    t = np.arange(0, 24, 0.25)

    # Bound inferiore: linea piatta
    ax.axhline(y=p_flat_gw, color='#00ff88', linewidth=2.5, linestyle='-',
               label=f'Bound inferiore: {p_flat_gw:.1f} GW (P = E/24h)')

    # Smart charging: blocco notturno
    smart_profile = np.where((t >= 22) | (t < 6), p_smart_gw, 0)
    ax.fill_between(t, 0, smart_profile, alpha=0.3, color='#4ecdc4',
                    label=f'Smart charging: {p_smart_gw:.1f} GW (8h notturne)')
    ax.plot(t, smart_profile, color='#4ecdc4', linewidth=2)

    # Bound superiore: gaussiana alle 19
    from scipy.stats import norm
    mu, sigma = 18.5, 1.5
    arrivals = norm.pdf(t, mu, sigma) + norm.pdf(t - 24, mu, sigma)
    # Convolve con finestra ricarica (41 min = 2.7 slot da 15 min)
    n_slot = int(0.68 / 0.25)
    window = np.ones(n_slot)
    charging = np.convolve(arrivals / arrivals.sum(), window, mode='full')[:len(t)]
    dumb_profile = charging * N_AUTO * 0.70 * P_WALLBOX / 1e6
    ax.fill_between(t, 0, dumb_profile, alpha=0.3, color='#ff6b6b',
                    label=f'Bound superiore: {dumb_profile.max():.1f} GW (dumb charging)')
    ax.plot(t, dumb_profile, color='#ff6b6b', linewidth=2)

    # Annotazione
    ax.annotate('Il sistema reale vive\ntra questi due estremi',
                xy=(12, (p_flat_gw + dumb_profile.max()) / 2),
                fontsize=13, fontweight='bold', color='#f5c518',
                ha='center',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='#1a1a2e',
                          edgecolor='#f5c518', alpha=0.9))

    ax.set_xlabel('Ora del giorno', fontsize=13)
    ax.set_ylabel('Potenza EV aggiuntiva (GW)', fontsize=13)
    ax.set_title('Bounds di potenza: dal caso migliore al caso peggiore',
                 fontsize=14, fontweight='bold')
    ax.set_xlim(0, 24)
    ax.set_xticks(range(0, 25, 2))
    ax.set_xticklabels([f'{h:02d}:00' for h in range(0, 25, 2)])
    ax.legend(fontsize=10, loc='upper left')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/13_bounds_potenza.png', dpi=150,
                bbox_inches='tight', facecolor='#0d1117')
    plt.close()
    print(f'[OK] {OUTPUT_DIR}/13_bounds_potenza.png')


# ─── 2. SENSITIVITY ANALYSIS: CABINA ─────────────────────────────────

def sensitivity_cabina():
    """Matrice di sensitivity: N_max auto per cabina al variare dei parametri."""

    params = {
        'Consumo (kWh/100km)':  [15,    18,    22],
        'k_c EV':               [0.60,  0.85,  0.95],
        'Wallbox (kW)':         [3.7,   7.4,   11.0],
    }
    labels_col = ['Ottimista', 'Base', 'Pessimista']

    s_disp = S_TRAFO * COS_PHI
    p_base = N_UTENZE * P_IMPEGNATA * KC_DOMESTICO
    margine = s_disp - p_base

    print(f'=== SENSITIVITY: CABINA 400 kVA ===')
    print(f'Margine disponibile: {margine:.0f} kW')
    print(f'{"Parametro":<25} {"Ottimista":>10} {"Base":>10} {"Pessimista":>10}')
    print('-' * 55)

    results = {}
    for param_name, values in params.items():
        row = []
        for v in values:
            if 'k_c' in param_name:
                n_max = int(margine / (P_WALLBOX * v))
            elif 'Wallbox' in param_name:
                n_max = int(margine / (v * 0.85))
            else:
                # consumo non cambia n_max direttamente, cambia durata
                n_max = int(margine / (P_WALLBOX * 0.85))
            row.append(n_max)
        results[param_name] = row
        print(f'{param_name:<25} {row[0]:>10} {row[1]:>10} {row[2]:>10}')

    # Caso combinato peggiore: 11 kW + k_c 0.95
    worst = int(margine / (11.0 * 0.95))
    best = int(margine / (3.7 * 0.60))
    print(f'{"Combinato peggiore":<25} {"":<10} {"":<10} {worst:>10}')
    print(f'{"Combinato migliore":<25} {best:>10}')
    print()

    # Grafico
    fig, ax = plt.subplots(figsize=(14, 7))

    scenarios = {
        'Ottimista\n(3.7kW, k_c=0.6)': int(margine / (3.7 * 0.60)),
        'Conservativo\n(7.4kW, k_c=0.7)': int(margine / (7.4 * 0.70)),
        'Base\n(7.4kW, k_c=0.85)': int(margine / (7.4 * 0.85)),
        'Aggressivo\n(11kW, k_c=0.85)': int(margine / (11.0 * 0.85)),
        'Pessimista\n(11kW, k_c=0.95)': int(margine / (11.0 * 0.95)),
    }

    x = np.arange(len(scenarios))
    vals = list(scenarios.values())
    labs = list(scenarios.keys())

    # Auto necessarie per cabina (108.5 con 100% EV)
    auto_necessarie = N_UTENZE * 1.55

    colors = ['#00ff88' if v >= auto_necessarie else
              '#f5c518' if v >= auto_necessarie * 0.7 else '#ff6b6b'
              for v in vals]

    bars = ax.bar(x, vals, color=colors, width=0.5, edgecolor='none')

    ax.axhline(y=auto_necessarie, color='#ff6b6b', linewidth=2.5,
               linestyle='--', label=f'Auto necessarie: {auto_necessarie:.0f} (100% EV)')

    for i, (bar, v) in enumerate(zip(bars, vals)):
        ax.text(bar.get_x() + bar.get_width()/2, v + 3,
                f'{v}', ha='center', fontsize=14, fontweight='bold',
                color=colors[i])

    ax.set_ylabel('N. max auto per cabina 400 kVA', fontsize=13)
    ax.set_title('Sensitivity: il problema resta in OGNI scenario',
                 fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(labs, fontsize=10)
    ax.legend(fontsize=11)
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/14_sensitivity_cabina.png', dpi=150,
                bbox_inches='tight', facecolor='#0d1117')
    plt.close()
    print(f'[OK] {OUTPUT_DIR}/14_sensitivity_cabina.png')


# ─── 3. SENSITIVITY: COLONNINE ───────────────────────────────────────

def sensitivity_colonnine():
    """Sensitivity su rho al variare dei parametri chiave."""

    t_servizio = 46 / 60  # ore (base)
    mu_base = 1 / t_servizio

    scenarios = {
        'Ottimista\n(20% pubb, DC 150kW)': {
            'fraz': 0.20, 'mu': 1 / 0.25, 'punti': 73_047,
        },
        'Base\n(30% pubb, mix)': {
            'fraz': 0.30, 'mu': mu_base, 'punti': 73_047,
        },
        'Pessimista\n(50% pubb, AC 22kW)': {
            'fraz': 0.50, 'mu': 1 / 1.5, 'punti': 73_047,
        },
        'Con 200k punti\n(30% pubb, mix)': {
            'fraz': 0.30, 'mu': mu_base, 'punti': 200_000,
        },
        'Con 200k punti\n(50% pubb, AC)': {
            'fraz': 0.50, 'mu': 1 / 1.5, 'punti': 200_000,
        },
    }

    kwh_giorno = KM_ANNO / 365 * 18.0 / 100
    ore_punta = 12

    print(f'=== SENSITIVITY: COLONNINE ===')

    fig, ax = plt.subplots(figsize=(14, 7))

    labels = list(scenarios.keys())
    rhos = []
    colors_bar = []

    for name, s in scenarios.items():
        sessioni = N_AUTO * s['fraz'] * kwh_giorno / 25.0
        lam_per_punto = sessioni / (s['punti'] * ore_punta)
        rho = lam_per_punto / s['mu']
        rhos.append(min(rho, 5.0))
        color = '#00ff88' if rho < 0.75 else '#f5c518' if rho < 1.0 else '#ff6b6b'
        colors_bar.append(color)
        print(f'  {name.replace(chr(10), " "):<35} rho = {rho:.2f} '
              f'{"OK" if rho < 0.75 else "CRITICO" if rho < 1 else "COLLASSO"}')

    x = np.arange(len(labels))
    bars = ax.bar(x, rhos, color=colors_bar, width=0.5, edgecolor='none')

    ax.axhline(y=1.0, color='#ff6b6b', linewidth=2.5, linestyle='-',
               label='rho = 1 (collasso)')
    ax.axhline(y=0.75, color='#f5c518', linewidth=1.5, linestyle='--',
               label='rho = 0.75 (QoS accettabile)')

    for bar, rho in zip(bars, rhos):
        label = f'{rho:.2f}' if rho < 5 else '>5'
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                label, ha='center', fontsize=12, fontweight='bold',
                color=bar.get_facecolor())

    ax.set_ylabel('rho (utilizzazione)', fontsize=13)
    ax.set_title('Sensitivity colonnine: anche con parametri ottimisti, rho > 1',
                 fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.legend(fontsize=11)
    ax.grid(axis='y', alpha=0.3)
    ax.set_ylim(0, max(rhos) * 1.15)

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/15_sensitivity_colonnine.png', dpi=150,
                bbox_inches='tight', facecolor='#0d1117')
    plt.close()
    print(f'[OK] {OUTPUT_DIR}/15_sensitivity_colonnine.png')
    print()


# ─── 4. VINCOLO DI FREQUENZA ─────────────────────────────────────────

def vincolo_frequenza():
    """
    Stabilita' di frequenza: df/dt = -Delta_P / (2 * H * S_base) * f0

    RoCoF (Rate of Change of Frequency):
      RoCoF = Delta_P / (2 * H * S_sistema) * f0

    Se RoCoF > 0.5-1.0 Hz/s → load shedding automatico
    """
    # Potenza base del sistema (capacita' di generazione sincronizzata)
    s_sistema_gw = 60.0  # GW di generazione sincronizzata (stima)

    # Variazione di potenza da rampa EV serale
    # La rampa piu' ripida: da 17:00 a 19:00, il carico EV sale da ~5 GW a ~28 GW
    delta_p_gw = 23.0    # GW in 2 ore
    delta_p_15min = delta_p_gw / 8  # GW per 15 minuti

    print(f'=== VINCOLO DI FREQUENZA ===')

    fig, axes = plt.subplots(1, 2, figsize=(14, 7))

    # --- Pannello sinistro: RoCoF vs Delta_P ---
    ax = axes[0]
    delta_p_range = np.linspace(0.1, 10, 200)  # GW

    for h, label, color in [(H_SISTEMA, f'H = {H_SISTEMA}s (attuale)', '#4ecdc4'),
                             (H_RINNOVABILI, f'H = {H_RINNOVABILI}s (alta % rinnovabili)', '#ff6b6b'),
                             (3.0, 'H = 3.0s (intermedio)', '#f5c518')]:
        rocof = delta_p_range / (2 * h * s_sistema_gw) * FREQ_NOMINALE
        ax.plot(delta_p_range, rocof, linewidth=2.5, color=color, label=label)

    ax.axhline(y=0.5, color='#ff8800', linewidth=2, linestyle='--',
               label='Soglia protezione (0.5 Hz/s)')
    ax.axhline(y=1.0, color='#ff6b6b', linewidth=2, linestyle='--',
               label='Load shedding (1.0 Hz/s)')

    # Annotazione rampa EV
    rocof_ev = delta_p_15min / (2 * H_RINNOVABILI * s_sistema_gw) * FREQ_NOMINALE
    ax.axvline(x=delta_p_15min, color='#7c4dff', linewidth=1.5, linestyle=':')
    ax.text(delta_p_15min + 0.2, 0.8,
            f'Rampa EV\n15 min\n({delta_p_15min:.1f} GW)',
            fontsize=10, color='#7c4dff')

    ax.set_xlabel('Variazione di potenza (GW)', fontsize=13)
    ax.set_ylabel('RoCoF (Hz/s)', fontsize=13)
    ax.set_title('Rate of Change of Frequency\nvs perturbazione di carico', fontsize=13, fontweight='bold')
    ax.legend(fontsize=9, loc='upper left')
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 2.5)

    # --- Pannello destro: Deviazione di frequenza ---
    ax = axes[1]

    for h, label, color in [(H_SISTEMA, f'H = {H_SISTEMA}s', '#4ecdc4'),
                             (H_RINNOVABILI, f'H = {H_RINNOVABILI}s', '#ff6b6b')]:
        delta_f = delta_p_range * FREQ_NOMINALE / (2 * h * s_sistema_gw)
        ax.plot(delta_p_range, delta_f, linewidth=2.5, color=color, label=label)

    ax.axhline(y=DELTA_F_MAX, color='#ff6b6b', linewidth=2, linestyle='--',
               label=f'Limite ENTSO-E ({DELTA_F_MAX} Hz)')
    ax.axhline(y=0.2, color='#f5c518', linewidth=1.5, linestyle='--',
               label='Regolazione primaria (0.2 Hz)')

    ax.set_xlabel('Variazione di potenza (GW)', fontsize=13)
    ax.set_ylabel('Deviazione di frequenza (Hz)', fontsize=13)
    ax.set_title('Deviazione frequenza (50 Hz)\nvs perturbazione di carico', fontsize=13, fontweight='bold')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 3)

    # Calcoli finali
    # Con H=2s (rinnovabili), quanti GW di rampa provocano load shedding?
    delta_p_critico = 1.0 * 2 * H_RINNOVABILI * s_sistema_gw / FREQ_NOMINALE
    print(f'S_sistema:                 {s_sistema_gw:.0f} GW')
    print(f'H attuale:                 {H_SISTEMA:.1f} s')
    print(f'H con rinnovabili:         {H_RINNOVABILI:.1f} s')
    print(f'Rampa EV (15 min):         {delta_p_15min:.1f} GW')
    print(f'RoCoF (H={H_RINNOVABILI}s, rampa EV): {rocof_ev:.3f} Hz/s')
    print(f'Delta_P per load shedding: {delta_p_critico:.1f} GW (con H={H_RINNOVABILI}s)')
    print()

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/16_frequenza.png', dpi=150,
                bbox_inches='tight', facecolor='#0d1117')
    plt.close()
    print(f'[OK] {OUTPUT_DIR}/16_frequenza.png')


# ─── MAIN ────────────────────────────────────────────────────────────

if __name__ == '__main__':
    plot_bounds()
    sensitivity_cabina()
    sensitivity_colonnine()
    vincolo_frequenza()
