#!/usr/bin/env python3
"""
01_fabbisogno.py — Energia vs Potenza: il calcolo che cambia tutto
===================================================================
Calcola il fabbisogno energetico (TWh) e il picco di potenza (GW)
se l'intero parco auto italiano fosse elettrico.

Mostra che l'energia e' un problema gestibile (+24%),
ma la potenza e' un muro fisico (+80% sul picco serale).

Fonti:
  - ACI Annuario Statistico 2025: 40.3M autovetture
    https://aci.gov.it/comunicati-stampa/annuario-statistico-2025-tutti-i-numeri-delle-auto-in-italia/
  - ISTAT Percorrenze 2025: 10.231 km/anno media
    https://www.istat.it/wp-content/uploads/2025/06/Le-percorrenze-dei-veicoli-stradali-circolanti.pdf
  - Terna 2024: fabbisogno 312.2 TWh, picco 57.5 GW
    https://www.terna.it/it/media/comunicati-stampa/dettaglio/consumi-elettrici-2024
  - ENGIE/Sorgenia: consumo medio EV ~18 kWh/100km
    https://www.engie.it/casa/magazine/consumo-auto-elettrica/
  - ARERA: consumo domestico tipo 2700 kWh/anno
    https://web.archive.org/web/2024/https://www.arera.it/comunicati-stampa/dettaglio/elettricita-bollette-in-calo-del-198-nel-secondo-trimestre-2024

Output: output/01_energia_vs_potenza.png
        output/02_profilo_carico.png
        output/03_picco_confronto.png
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

# ─── PARAMETRI CON FONTI ─────────────────────────────────────────────

N_AUTO       = 40_300_000       # ACI 2025: autovetture circolanti
KM_ANNO      = 10_231           # ISTAT 2025: percorrenza media
KWH_100KM    = 18.0             # ENGIE/Sorgenia: consumo medio reale EV
FABBISOGNO_IT = 312.2           # Terna 2024: TWh/anno
PICCO_IT     = 57.5             # Terna 2024: GW picco orario (18 luglio)
P_WALLBOX    = 7.4              # kW, wallbox monofase standard (32A × 230V)
BATTERIA_MEDIA = 55.0           # kWh, media ponderata parco (city car 40, berlina 60-75)

# Consumo giornaliero reale: 10231 km/anno / 365 = 28 km/giorno
# 28 km × 18 kWh/100km = 5.04 kWh/giorno
KWH_GIORNO   = KM_ANNO / 365 * KWH_100KM / 100  # ~5.04 kWh

# Profilo arrivo a casa: distribuzione normale troncata
MU_ARRIVO    = 18.5             # ore (18:30)
SIGMA_ARRIVO = 1.5              # ore
DURATA_MEDIA_RICARICA = KWH_GIORNO / P_WALLBOX  # ore (~0.68h = ~41 min)

# Frazione auto che carica ogni giorno
# Non tutte caricano: chi ha fatto pochi km salta un giorno
# Modello: chi consuma > 20% della batteria carica. Con media 5 kWh su 55 kWh (9%),
# assumiamo distribuzione log-normale dei km giornalieri, ~70% carica ogni giorno
FRAZ_CARICA_GIORNO = 0.70

# Curva di carico base Italia (profilo giornaliero tipico invernale, Terna)
# Semplificato: 24 valori orari in GW
CARICO_BASE_GW = np.array([
    28, 26, 25, 24, 24, 25,     # 00-05: notte
    30, 38, 44, 48, 50, 51,     # 06-11: mattina
    49, 48, 47, 48, 50, 52,     # 12-17: pomeriggio
    55, 57, 54, 48, 42, 35,     # 18-23: sera (picco ~19:00)
], dtype=float)


# ─── CALCOLO 1: ENERGIA ──────────────────────────────────────────────

def calcola_energia():
    """Fabbisogno energetico annuo in TWh."""
    kwh_anno_totale = N_AUTO * KM_ANNO * (KWH_100KM / 100)
    twh = kwh_anno_totale / 1e9
    percentuale = (twh / FABBISOGNO_IT) * 100
    print(f'=== ENERGIA ===')
    print(f'Auto:              {N_AUTO:>14,}')
    print(f'km/anno:           {KM_ANNO:>14,}')
    print(f'kWh/100km:         {KWH_100KM:>14.1f}')
    print(f'Energia totale:    {twh:>14.1f} TWh/anno')
    print(f'Fabbisogno IT:     {FABBISOGNO_IT:>14.1f} TWh/anno')
    print(f'Incremento:        {percentuale:>14.1f} %')
    print()
    return twh, percentuale


# ─── CALCOLO 2: PROFILO DI POTENZA ──────────────────────────────────

def profilo_ricarica(dt=0.25):
    """
    Calcola il profilo di potenza aggiuntiva EV ora per ora.

    Modello:
    - Ogni auto arriva a casa secondo N(mu=18.5, sigma=1.5)
    - Attacca subito la wallbox a 7.4 kW
    - Ricarica per DURATA_MEDIA_RICARICA ore (consumo giornaliero medio × 55 kWh / 7.4 kW ≈ 3.7h)
    - Il profilo di potenza istantanea e' la convoluzione
      dell'arrivo con una finestra rettangolare di durata ricarica
    """
    t = np.arange(0, 24, dt)  # ore del giorno, step 15 min

    # distribuzione arrivi (PDF normalizzata)
    arrivi = np.exp(-0.5 * ((t - MU_ARRIVO) / SIGMA_ARRIVO)**2)
    # gestisci arrivi dopo mezzanotte (wrap-around)
    arrivi += np.exp(-0.5 * ((t - MU_ARRIVO + 24) / SIGMA_ARRIVO)**2)
    arrivi /= arrivi.sum()  # normalizza: ogni auto arriva esattamente una volta

    # finestra di ricarica: rettangolare, durata fissa
    n_slot_ricarica = int(DURATA_MEDIA_RICARICA / dt)
    finestra = np.ones(n_slot_ricarica)

    # convoluzione: quante auto stanno caricando in ogni istante
    # (convolve arrivi con finestra rettangolare)
    caricando = np.convolve(arrivi, finestra, mode='full')[:len(t)]

    # potenza totale in GW (solo la frazione che carica quel giorno)
    potenza_ev_gw = caricando * N_AUTO * FRAZ_CARICA_GIORNO * P_WALLBOX / 1e6

    print(f'=== POTENZA ===')
    print(f'Wallbox:           {P_WALLBOX:>14.1f} kW')
    print(f'Durata ricarica:   {DURATA_MEDIA_RICARICA:>14.1f} ore (consumo giornaliero medio)')
    print(f'Picco EV:          {potenza_ev_gw.max():>14.1f} GW')
    print(f'Picco base IT:     {PICCO_IT:>14.1f} GW')
    print(f'Picco combinato:   {potenza_ev_gw.max() + CARICO_BASE_GW.max():>14.1f} GW')
    print(f'Fattore picco:     {(potenza_ev_gw.max() + CARICO_BASE_GW.max()) / PICCO_IT:>14.2f}x')
    print()

    return t, potenza_ev_gw, arrivi


# ─── GRAFICI ─────────────────────────────────────────────────────────

def plot_energia_vs_potenza(twh, pct):
    """Grafico 1: confronto energia (gestibile) vs potenza (critico)."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # --- Pannello sinistro: Energia ---
    ax = axes[0]
    bars = ax.bar(['Fabbisogno\nattuale', 'Auto\nelettriche'],
                  [FABBISOGNO_IT, twh],
                  color=['#4ecdc4', '#00ff88'], width=0.5, edgecolor='none')
    ax.bar(['Fabbisogno\nattuale'], [FABBISOGNO_IT],
           bottom=[0], color='#4ecdc4', width=0.5)
    ax.set_ylabel('TWh / anno', fontsize=13)
    ax.set_title('ENERGIA\n(problema di pianificazione)', fontsize=14,
                 fontweight='bold', color='#00ff88')
    ax.text(1, twh + 3, f'+{pct:.0f}%', ha='center', fontsize=18,
            fontweight='bold', color='#00ff88')
    for bar, val in zip(bars, [FABBISOGNO_IT, twh]):
        ax.text(bar.get_x() + bar.get_width()/2, val/2, f'{val:.0f}',
                ha='center', va='center', fontsize=14, fontweight='bold',
                color='#0d1117')
    ax.set_ylim(0, FABBISOGNO_IT * 1.3)
    ax.grid(axis='y', alpha=0.3)

    # --- Pannello destro: Potenza ---
    ax = axes[1]
    t, potenza_ev, _ = profilo_ricarica()
    picco_ev = potenza_ev.max()
    bars = ax.bar(['Picco\nattuale', 'Picco EV\naggiuntivo'],
                  [PICCO_IT, picco_ev],
                  color=['#4ecdc4', '#ff6b6b'], width=0.5, edgecolor='none')
    ax.set_ylabel('GW (picco)', fontsize=13)
    ax.set_title('POTENZA\n(problema di fisica)', fontsize=14,
                 fontweight='bold', color='#ff6b6b')
    pct_pot = (picco_ev / PICCO_IT) * 100
    ax.text(1, picco_ev + 2, f'+{pct_pot:.0f}%', ha='center', fontsize=18,
            fontweight='bold', color='#ff6b6b')
    for bar, val in zip(bars, [PICCO_IT, picco_ev]):
        ax.text(bar.get_x() + bar.get_width()/2, val/2, f'{val:.0f}',
                ha='center', va='center', fontsize=14, fontweight='bold',
                color='#0d1117')
    ax.set_ylim(0, (PICCO_IT + picco_ev) * 1.15)
    ax.grid(axis='y', alpha=0.3)

    fig.suptitle("L'Italia non ha la spina: energia vs potenza",
                 fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/01_energia_vs_potenza.png', dpi=150,
                bbox_inches='tight', facecolor='#0d1117')
    plt.close()
    print(f'[OK] {OUTPUT_DIR}/01_energia_vs_potenza.png')


def plot_profilo_carico():
    """Grafico 2: profilo giornaliero con e senza EV."""
    t_ev, potenza_ev, arrivi = profilo_ricarica(dt=0.25)

    # interpola carico base su stessa griglia
    t_base = np.arange(0, 24, 1) + 0.5  # centro di ogni ora
    carico_interp = np.interp(t_ev, t_base, CARICO_BASE_GW)

    carico_totale = carico_interp + potenza_ev

    fig, ax = plt.subplots(figsize=(14, 7))

    ax.fill_between(t_ev, 0, carico_interp, alpha=0.4, color='#4ecdc4',
                    label=f'Carico base (picco {CARICO_BASE_GW.max():.0f} GW)')
    ax.fill_between(t_ev, carico_interp, carico_totale, alpha=0.5,
                    color='#ff6b6b',
                    label=f'+ Ricarica EV (picco +{potenza_ev.max():.0f} GW)')
    ax.plot(t_ev, carico_totale, color='#ff6b6b', linewidth=2)
    ax.plot(t_ev, carico_interp, color='#4ecdc4', linewidth=2)

    # linea picco attuale
    ax.axhline(y=PICCO_IT, color='#f5c518', linestyle='--', alpha=0.7,
               linewidth=1.5)
    ax.text(1, PICCO_IT + 1.5, f'Picco attuale: {PICCO_IT} GW',
            color='#f5c518', fontsize=11)

    # linea picco combinato
    picco_comb = carico_totale.max()
    ax.axhline(y=picco_comb, color='#ff6b6b', linestyle='--', alpha=0.7,
               linewidth=1.5)
    ax.text(1, picco_comb + 1.5, f'Picco con EV: {picco_comb:.0f} GW',
            color='#ff6b6b', fontsize=11)

    # annotazione arrivi
    ax2 = ax.twinx()
    ax2.plot(t_ev, arrivi * 100, color='#7c4dff', linewidth=1.5,
             linestyle=':', alpha=0.6, label='Distribuzione arrivi a casa')
    ax2.set_ylabel('Arrivi a casa (%)', color='#7c4dff', fontsize=12)
    ax2.tick_params(axis='y', colors='#7c4dff')
    ax2.set_ylim(0, arrivi.max() * 100 * 3)

    ax.set_xlabel('Ora del giorno', fontsize=13)
    ax.set_ylabel('Potenza (GW)', fontsize=13)
    ax.set_title('Profilo di carico giornaliero: "tutti attaccano alle 19"',
                 fontsize=14, fontweight='bold')
    ax.set_xlim(0, 24)
    ax.set_xticks(range(0, 25, 2))
    ax.set_xticklabels([f'{h:02d}:00' for h in range(0, 25, 2)])
    ax.legend(loc='upper left', fontsize=11)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/02_profilo_carico.png', dpi=150,
                bbox_inches='tight', facecolor='#0d1117')
    plt.close()
    print(f'[OK] {OUTPUT_DIR}/02_profilo_carico.png')


def plot_picco_confronto():
    """Grafico 3: barre impilate — dove va la potenza."""
    t_ev, potenza_ev, _ = profilo_ricarica()

    # Trova il valore all'ora del picco serale (~19:00)
    idx_19 = np.argmin(np.abs(t_ev - 19.0))
    ev_at_peak = potenza_ev[idx_19]

    # Potenza installata necessaria per scenari
    scenari = {
        'Oggi\n(no EV)': (PICCO_IT, 0),
        'Dumb charging\n(tutti alle 19)': (PICCO_IT, ev_at_peak),
        'Smart charging\n(appiattito)': (PICCO_IT, ev_at_peak * 0.35),
        'V2G\n(auto = batteria)': (PICCO_IT - 5, ev_at_peak * 0.2),
    }

    fig, ax = plt.subplots(figsize=(12, 7))
    x = np.arange(len(scenari))
    labels = list(scenari.keys())
    base = [v[0] for v in scenari.values()]
    ev = [v[1] for v in scenari.values()]

    ax.bar(x, base, color='#4ecdc4', label='Carico base', width=0.5)
    ax.bar(x, ev, bottom=base, color='#ff6b6b', label='Carico EV', width=0.5)

    for i, (b, e) in enumerate(zip(base, ev)):
        total = b + e
        ax.text(i, total + 1.5, f'{total:.0f} GW', ha='center',
                fontsize=13, fontweight='bold',
                color='#ff6b6b' if e > 10 else '#00ff88')

    ax.axhline(y=PICCO_IT, color='#f5c518', linestyle='--', alpha=0.5)
    ax.text(len(scenari) - 0.5, PICCO_IT + 1, f'Capacita attuale: {PICCO_IT} GW',
            ha='right', color='#f5c518', fontsize=10)

    ax.set_ylabel('Potenza di picco (GW)', fontsize=13)
    ax.set_title('Scenari di gestione ricarica: la potenza decide tutto',
                 fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11)
    ax.legend(fontsize=12)
    ax.grid(axis='y', alpha=0.3)
    ax.set_ylim(0, max(b + e for b, e in zip(base, ev)) * 1.15)

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/03_picco_confronto.png', dpi=150,
                bbox_inches='tight', facecolor='#0d1117')
    plt.close()
    print(f'[OK] {OUTPUT_DIR}/03_picco_confronto.png')


# ─── MAIN ────────────────────────────────────────────────────────────

if __name__ == '__main__':
    twh, pct = calcola_energia()
    plot_energia_vs_potenza(twh, pct)
    plot_profilo_carico()
    plot_picco_confronto()
