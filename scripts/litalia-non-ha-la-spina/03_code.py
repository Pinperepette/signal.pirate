#!/usr/bin/env python3
"""
03_code.py — La colonnina e' una coda: Erlang-C per le stazioni di ricarica
============================================================================
Modella le stazioni di ricarica pubblica come sistema a coda M/M/c (Erlang-C).

Mostra:
  1. Come il tempo di attesa ESPLODE quando rho -> 1
  2. Quante colonnine servono per garantire QoS (attesa < 10 min)
  3. Il dimensionamento nazionale: quante stazioni, quante colonnine

Modello:
  - Arrivi: Poisson con tasso lambda (auto/ora)
  - Servizio: esponenziale con media 1/mu (ore per ricarica)
  - c: numero di colonnine per stazione
  - rho = lambda / (c * mu)  (utilizzazione)
  - P(wait) = Erlang-C formula
  - E[W_q] = P(wait) / (c*mu - lambda)

Fonti:
  - MOTUS-E 2025: 73.047 punti di ricarica pubblici
    https://www.motus-e.org/news-associative/auto-elettriche-litalia-supera-la-soglia-dei-70-000-punti-di-ricarica-lappello-del-settore-senza-regole-chiare-e-collaborazione-la-crescita-rischia-di-fermarsi/
  - ACI 2025: 40.3M autovetture
  - Tempo ricarica DC 50kW: ~30-45 min (20-80% su 55 kWh)
  - Tempo ricarica AC 22kW: ~1.5-2h

Output: output/07_erlang_c_esplosione.png
        output/08_colonnine_qos.png
        output/09_dimensionamento_nazionale.png
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from math import factorial, exp, log
from scipy.special import gammaincc
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

# ─── PARAMETRI ───────────────────────────────────────────────────────

N_AUTO         = 40_300_000
PUNTI_RICARICA = 73_047         # MOTUS-E 2025: punti pubblici attuali

# Scenario ricarica pubblica:
# Non tutti usano le colonnine pubbliche. Stima: ~30% del fabbisogno
# (il resto carica a casa o al lavoro)
FRAZ_PUBBLICA  = 0.30

# Tempo medio di servizio (ricarica) per tipo
T_SERVIZIO_DC50  = 0.60         # ore (36 min: 20-80% su 55 kWh a 50 kW)
T_SERVIZIO_DC150 = 0.25         # ore (15 min: 20-80% su 55 kWh a 150 kW)
T_SERVIZIO_AC22  = 1.50         # ore (90 min: ricarica lenta)

# Mix colonnine (scenario futuro)
# 40% DC 50kW, 30% DC 150kW, 30% AC 22kW
T_SERVIZIO_MEDIO = 0.40 * T_SERVIZIO_DC50 + 0.30 * T_SERVIZIO_DC150 + 0.30 * T_SERVIZIO_AC22
# = 0.24 + 0.075 + 0.45 = 0.765 ore ~ 46 min

# Domanda giornaliera
KM_ANNO        = 10_231
KWH_100KM      = 18.0
KWH_GIORNO     = KM_ANNO / 365 * KWH_100KM / 100  # ~5 kWh/giorno/auto

# Ore operative effettive di una stazione
ORE_PUNTA      = 12             # ore/giorno con domanda significativa


# ─── ERLANG-C ────────────────────────────────────────────────────────

def erlang_c(c, rho_total):
    """
    Probabilita' di attesa in coda M/M/c (formula di Erlang-C).

    c:         numero di server (colonnine)
    rho_total: carico totale = lambda / mu  (adimensionale)
    rho:       utilizzazione per server = rho_total / c  (deve essere < 1)

    P(wait) = [A^c / c! * 1/(1-rho)] / [sum_{k=0}^{c-1} A^k/k! + A^c/c! * 1/(1-rho)]

    dove A = rho_total = lambda/mu
    """
    rho = rho_total / c
    if rho >= 1:
        return 1.0  # sistema instabile

    # Calcolo in log per evitare overflow
    # A^c / c!
    log_num = c * log(rho_total) - sum(log(i) for i in range(1, c + 1))

    # Sommatoria denominatore
    terms = []
    for k in range(c):
        if k == 0:
            log_term = 0
        else:
            log_term = k * log(rho_total) - sum(log(i) for i in range(1, k + 1))
        terms.append(exp(log_term))

    denom_sum = sum(terms)
    num = exp(log_num)
    last_term = num / (1 - rho)

    p_wait = last_term / (denom_sum + last_term)
    return p_wait


def tempo_attesa_medio(c, lam, mu):
    """
    Tempo medio di attesa in coda (E[W_q]) in un sistema M/M/c.

    E[W_q] = P(wait) / (c*mu - lambda)
    """
    rho_total = lam / mu
    rho = rho_total / c

    if rho >= 1:
        return float('inf')

    pw = erlang_c(c, rho_total)
    wq = pw / (c * mu - lam)
    return wq


# ─── GRAFICI ─────────────────────────────────────────────────────────

def plot_esplosione():
    """Grafico 7: tempo di attesa vs utilizzazione — l'esplosione."""
    fig, ax = plt.subplots(figsize=(14, 7))

    rho_values = np.linspace(0.05, 0.99, 500)
    mu = 1.0 / T_SERVIZIO_MEDIO  # tasso di servizio (auto/ora)

    for c in [2, 4, 8, 16, 32]:
        wait_times = []
        for rho in rho_values:
            lam = rho * c * mu
            wq = tempo_attesa_medio(c, lam, mu)
            wait_times.append(wq * 60)  # converti in minuti
        ax.plot(rho_values, wait_times, linewidth=2,
                label=f'c = {c} colonnine')

    ax.axhline(y=10, color='#f5c518', linestyle='--', linewidth=2, alpha=0.7)
    ax.text(0.15, 12, 'QoS target: attesa < 10 min', color='#f5c518',
            fontsize=11)

    ax.set_xlabel('Utilizzazione (rho = lambda / c*mu)', fontsize=13)
    ax.set_ylabel('Tempo medio di attesa (minuti)', fontsize=13)
    ax.set_title('Erlang-C: il tempo di attesa ESPLODE prima della saturazione\n'
                 f'(tempo servizio medio: {T_SERVIZIO_MEDIO*60:.0f} min)',
                 fontsize=14, fontweight='bold')
    ax.set_ylim(0, 60)
    ax.set_xlim(0.05, 0.99)
    ax.legend(fontsize=11, title='Colonnine per stazione')
    ax.grid(True, alpha=0.3)

    # annotazione zona critica
    ax.axvspan(0.85, 1.0, alpha=0.1, color='#ff6b6b')
    ax.text(0.92, 55, 'ZONA\nCRITICA', ha='center', fontsize=11,
            color='#ff6b6b', fontweight='bold')

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/07_erlang_c_esplosione.png', dpi=150,
                bbox_inches='tight', facecolor='#0d1117')
    plt.close()
    print(f'[OK] {OUTPUT_DIR}/07_erlang_c_esplosione.png')


def plot_qos():
    """Grafico 8: colonnine necessarie per garantire attesa < X min."""
    fig, ax = plt.subplots(figsize=(14, 7))

    mu = 1.0 / T_SERVIZIO_MEDIO
    target_wait_min = [5, 10, 15, 20]  # minuti
    lambda_range = np.arange(1, 80, 1)  # auto/ora che arrivano alla stazione

    colors = ['#ff6b6b', '#f5c518', '#4ecdc4', '#00ff88']

    for target, color in zip(target_wait_min, colors):
        target_h = target / 60  # converti in ore
        c_needed = []
        for lam in lambda_range:
            # trova il minimo c tale che E[Wq] < target
            for c in range(1, 200):
                rho = lam / (c * mu)
                if rho >= 1:
                    continue
                wq = tempo_attesa_medio(c, lam, mu)
                if wq < target_h:
                    c_needed.append(c)
                    break
            else:
                c_needed.append(200)
        ax.plot(lambda_range, c_needed, linewidth=2.5, color=color,
                label=f'Attesa < {target} min')

    # linea di riferimento: c = lambda/mu (minimo teorico, 100% utilizzo)
    c_min_teorico = lambda_range / mu
    ax.plot(lambda_range, c_min_teorico, linewidth=1.5, color='#8b949e',
            linestyle=':', label='Minimo teorico (rho=1)')

    ax.set_xlabel('Tasso di arrivo (auto/ora)', fontsize=13)
    ax.set_ylabel('Colonnine necessarie', fontsize=13)
    ax.set_title('Dimensionamento stazione: quante colonnine per ogni livello di QoS?\n'
                 f'(tempo servizio medio: {T_SERVIZIO_MEDIO*60:.0f} min)',
                 fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(1, 79)
    ax.set_ylim(0, 100)

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/08_colonnine_qos.png', dpi=150,
                bbox_inches='tight', facecolor='#0d1117')
    plt.close()
    print(f'[OK] {OUTPUT_DIR}/08_colonnine_qos.png')


def plot_dimensionamento():
    """Grafico 9: dimensionamento nazionale — stazioni e colonnine."""

    # Quante ricariche pubbliche al giorno servono?
    ricariche_giorno = N_AUTO * FRAZ_PUBBLICA  # 30% carica al pubblico
    # Ma non tutti i giorni: media 5 kWh/giorno, ricarica pubblica media 25 kWh
    # → una sessione pubblica ogni 5 giorni per chi usa il pubblico
    kwh_sessione_pubblica = 25.0  # kWh per sessione (tipico: 20-80% parziale)
    sessioni_giorno = ricariche_giorno * KWH_GIORNO / kwh_sessione_pubblica

    # Tasso di arrivo per colonnina (attuale)
    mu = 1.0 / T_SERVIZIO_MEDIO
    lam_per_punto_attuale = sessioni_giorno / PUNTI_RICARICA / ORE_PUNTA

    print(f'=== DIMENSIONAMENTO NAZIONALE ===')
    print(f'Auto totali:               {N_AUTO:>12,}')
    print(f'Frazione pubblica:         {FRAZ_PUBBLICA*100:>12.0f}%')
    print(f'kWh/giorno/auto:           {KWH_GIORNO:>12.1f}')
    print(f'kWh/sessione pubblica:     {kwh_sessione_pubblica:>12.1f}')
    print(f'Sessioni/giorno totali:    {sessioni_giorno:>12,.0f}')
    print(f'Punti ricarica attuali:    {PUNTI_RICARICA:>12,}')
    print(f'lambda/punto (attuale):    {lam_per_punto_attuale:>12.2f} auto/h')
    print(f'mu (tasso servizio):       {mu:>12.2f} auto/h')
    print(f'rho attuale:               {lam_per_punto_attuale/mu:>12.2f}')
    print()

    # Scenari di dimensionamento
    # Stazioni da 8 colonnine, obiettivo rho < 0.75
    rho_target = 0.75
    target_wait = 10 / 60  # 10 minuti in ore

    scenari = {
        '100% EV\nrete attuale': {
            'punti': PUNTI_RICARICA,
            'color': '#ff6b6b',
        },
        '100% EV\nrho < 0.85': {
            'punti': int(sessioni_giorno / (ORE_PUNTA * mu * 0.85)),
            'color': '#f5c518',
        },
        '100% EV\nrho < 0.75': {
            'punti': int(sessioni_giorno / (ORE_PUNTA * mu * 0.75)),
            'color': '#4ecdc4',
        },
        '100% EV\nattesa < 10min\n(staz. da 8)': {
            'punti': None,  # calcolato sotto
            'color': '#00ff88',
        },
    }

    # Per l'ultimo scenario: stazioni da 8 colonnine
    c_stazione = 8
    # Trova lambda max per stazione con attesa < 10 min
    lam_max_stazione = 0
    for lam_test in np.arange(0.1, 100, 0.1):
        wq = tempo_attesa_medio(c_stazione, lam_test, mu)
        if wq > target_wait:
            lam_max_stazione = lam_test - 0.1
            break

    n_stazioni_necessarie = int(sessioni_giorno / (ORE_PUNTA * lam_max_stazione)) + 1
    scenari['100% EV\nattesa < 10min\n(staz. da 8)']['punti'] = n_stazioni_necessarie * c_stazione

    print(f'Lambda max per stazione da {c_stazione}: {lam_max_stazione:.1f} auto/h')
    print(f'Stazioni necessarie:       {n_stazioni_necessarie:>12,}')
    print(f'Punti totali:              {n_stazioni_necessarie * c_stazione:>12,}')
    print()

    # Grafico
    fig, ax = plt.subplots(figsize=(14, 7))

    labels = list(scenari.keys())
    punti = [s['punti'] for s in scenari.values()]
    colors = [s['color'] for s in scenari.values()]

    # Calcola rho effettivo per ogni scenario
    rhos = []
    for p in punti:
        lam_p = sessioni_giorno / (p * ORE_PUNTA) if p > 0 else float('inf')
        rhos.append(min(lam_p / mu, 5.0))

    x = np.arange(len(labels))
    bars = ax.bar(x, [p / 1000 for p in punti], color=colors, width=0.5,
                  edgecolor='none')

    for i, (bar, p, rho) in enumerate(zip(bars, punti, rhos)):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                f'{p:,}\n(rho={rho:.2f})',
                ha='center', fontsize=10, fontweight='bold', color=colors[i])

    ax.axhline(y=PUNTI_RICARICA / 1000, color='#ff6b6b', linestyle='--',
               alpha=0.5, linewidth=1.5)
    ax.text(len(labels) - 0.5, PUNTI_RICARICA / 1000 + 2,
            f'Oggi: {PUNTI_RICARICA:,}', ha='right', color='#ff6b6b',
            fontsize=10)

    ax.set_ylabel('Punti di ricarica (migliaia)', fontsize=13)
    ax.set_title('Quanti punti di ricarica servono con 40M auto elettriche?',
                 fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/09_dimensionamento_nazionale.png', dpi=150,
                bbox_inches='tight', facecolor='#0d1117')
    plt.close()
    print(f'[OK] {OUTPUT_DIR}/09_dimensionamento_nazionale.png')


# ─── MAIN ────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print(f'Tempo servizio medio: {T_SERVIZIO_MEDIO*60:.1f} min')
    print(f'mu = {1/T_SERVIZIO_MEDIO:.2f} auto/ora')
    print()
    plot_esplosione()
    plot_qos()
    plot_dimensionamento()
