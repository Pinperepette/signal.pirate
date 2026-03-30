"""
03 — Convergenza e genealogia delle formule
===========================================
Le 4 formule GHG derivano tutte da Myhre 1998.
La convergenza non e' indipendenza, e' genealogia.

Grafici: 05, 14b
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from fair_utils import savefig, OUT

FAIR_SRC = os.path.dirname(__import__('fair').__file__)


def ciclo_carbonio():
    """Box fittizi: la curva di decadimento della CO2."""
    lifetimes = np.array([1e9, 394.4, 36.54, 4.304])
    partitions = np.array([0.2173, 0.224, 0.2824, 0.2763])
    t = np.linspace(0, 500, 1000)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

    remaining = np.zeros_like(t)
    for i in range(4):
        remaining += partitions[i] * np.exp(-t / lifetimes[i])
    ax1.plot(t, remaining * 100, 'b-', linewidth=2.5, label='Default AR6')
    for factor, color, label in [(0.7, 'g', 'Lifetime -30%'), (1.3, 'r', 'Lifetime +30%')]:
        r = np.zeros_like(t)
        for i in range(4):
            lt = lifetimes[i] if i == 0 else lifetimes[i] * factor
            r += partitions[i] * np.exp(-t / lt)
        ax1.plot(t, r * 100, color=color, linewidth=2, linestyle='--', label=label)
    ax1.set_xlabel('Anni dopo l\'emissione', fontsize=13)
    ax1.set_ylabel('CO2 ancora in atmosfera (%)', fontsize=13)
    ax1.set_title('Quanto dura la CO2?\nDipende dai parametri', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(0, 105)

    psets = {'Default (22%)': [0.2173, 0.224, 0.2824, 0.2763],
             'Piu\' permanente (35%)': [0.35, 0.20, 0.25, 0.20],
             'Meno permanente (10%)': [0.10, 0.25, 0.30, 0.35]}
    colors = ['b', 'r', 'g']
    for (name, parts), color in zip(psets.items(), colors):
        r = np.zeros_like(t)
        for i in range(4):
            r += parts[i] * np.exp(-t / lifetimes[i])
        ax2.plot(t, r * 100, color=color, linewidth=2,
                linestyle='-' if 'Default' in name else '--', label=name)
    ax2.set_xlabel('Anni dopo l\'emissione', fontsize=13)
    ax2.set_ylabel('CO2 ancora in atmosfera (%)', fontsize=13)
    ax2.set_title('Cambiando la partition fraction', fontsize=14, fontweight='bold')
    ax2.legend(fontsize=12)
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(0, 105)
    savefig('05_ciclo_carbonio.png')


def convergenza_formule():
    """Le 4 formule GHG sono variazioni della stessa curva."""
    co2 = np.linspace(280, 1200, 500)
    co2_base, n2o = 278.3, 270

    f_myhre = 5.35 * np.log(co2 / co2_base)

    a1, b1, c1, d1 = -2.4e-7, 7.2e-4, -2.1e-4, 5.36
    f_etminan = (a1*(co2-co2_base)**2 + b1*np.abs(co2-co2_base) + c1*0.5*(n2o+n2o) + d1) * np.log(co2/co2_base)

    a1m, b1m, c1m, d1m = -2.4785e-07, 0.00075906, -0.0021492, 5.2488
    ca_max = co2_base - b1m/(2*a1m)
    alpha_p = np.where(co2 <= co2_base, d1m,
              np.where(co2 <= ca_max, d1m + a1m*(co2-co2_base)**2 + b1m*(co2-co2_base),
                       d1m - b1m**2/(4*a1m)))
    f_meins = (alpha_p + c1m * np.sqrt(n2o)) * np.log(co2/co2_base)

    f_leach = 4.57 * np.log(co2/co2_base) + 0.086 * (np.sqrt(co2) - np.sqrt(co2_base))

    fig = plt.figure(figsize=(18, 14))

    ax1 = fig.add_subplot(2, 2, 1)
    for data, name, color in [(f_myhre, 'Myhre 1998', 'purple'),
                               (f_etminan, 'Etminan 2016', 'blue'),
                               (f_meins, 'Meinshausen 2020', 'green'),
                               (f_leach, 'Leach 2021', 'orange')]:
        ax1.plot(co2, data, color, linewidth=2.5, label=name)
    ax1.set_xlabel('CO2 (ppm)', fontsize=13)
    ax1.set_ylabel('Forcing (W/m²)', fontsize=13)
    ax1.set_title('4 formule "diverse": quasi identiche', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=11)
    ax1.grid(True, alpha=0.3)

    ax2 = fig.add_subplot(2, 2, 2)
    ax2.plot(co2, f_etminan - f_myhre, 'blue', linewidth=2, label='Etminan - Myhre')
    ax2.plot(co2, f_meins - f_myhre, 'green', linewidth=2, label='Meinshausen - Myhre')
    ax2.plot(co2, f_leach - f_myhre, 'orange', linewidth=2, label='Leach - Myhre')
    ax2.axhline(y=0, color='black', linewidth=0.5)
    ax2.axvspan(280, 420, alpha=0.15, color='green')
    ax2.text(350, 0.3, 'Zona\ncalibrata', fontsize=10, ha='center', color='darkgreen', fontweight='bold')
    ax2.axvspan(420, 1200, alpha=0.08, color='red')
    ax2.text(800, 0.3, 'ESTRAPOLAZIONE', fontsize=10, ha='center', color='darkred', fontweight='bold')
    ax2.set_xlabel('CO2 (ppm)', fontsize=13)
    ax2.set_ylabel('Differenza (W/m²)', fontsize=13)
    ax2.set_title('Differenze: minime in zona calibrata, divergono fuori',
                  fontsize=14, fontweight='bold')
    ax2.legend(fontsize=11)
    ax2.grid(True, alpha=0.3)

    ax3 = fig.add_subplot(2, 2, 3)
    ax3.set_xlim(0, 10)
    ax3.set_ylim(0, 10)
    ax3.axis('off')
    boxes = [(5, 8.5, 'Myhre 1998\n\u03b1·ln(C/C\u2080)\n\u03b1=5.35', '#E1BEE7'),
             (3, 6, 'Etminan 2016\n"Aggiornamento di Myhre"', '#BBDEFB'),
             (2, 3.5, 'Meinshausen 2020\n"Rescaled Etminan"\n(codice sorgente)', '#C8E6C9'),
             (5, 3.5, 'Leach 2021\n"Re-fit of Etminan"\n(codice sorgente)', '#FFE0B2')]
    for x, y, text, color in boxes:
        ax3.text(x, y, text, fontsize=10, ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.5', facecolor=color, edgecolor='gray', linewidth=2))
    ax3.annotate('', xy=(3, 6.8), xytext=(5, 7.8), arrowprops=dict(arrowstyle='->', color='gray', lw=2))
    ax3.annotate('', xy=(2, 4.3), xytext=(3, 5.2), arrowprops=dict(arrowstyle='->', color='gray', lw=2))
    ax3.annotate('', xy=(5, 4.3), xytext=(3, 5.2), arrowprops=dict(arrowstyle='->', color='gray', lw=2))
    ax3.text(5, 1.5, 'TUTTE derivano da Myhre 1998.\nLa convergenza non e\' indipendenza.\nE\' genealogia.',
             fontsize=12, ha='center', va='center', fontweight='bold',
             bbox=dict(boxstyle='round', facecolor='#FFCDD2', edgecolor='red', linewidth=2))
    ax3.set_title('Genealogia delle formule', fontsize=14, fontweight='bold')

    ax4 = fig.add_subplot(2, 2, 4)
    d1_values = [5.35, 5.36, 5.25, 4.57]
    labels = ['Myhre\n1998', 'Etminan\n2016', 'Meinshausen\n2020', 'Leach\n2021']
    colors = ['#9C27B0', '#2196F3', '#4CAF50', '#FF9800']
    bars = ax4.bar(labels, d1_values, color=colors, width=0.6, edgecolor='white')
    for bar, val in zip(bars, d1_values):
        ax4.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.03,
                f'{val}', ha='center', va='bottom', fontsize=13, fontweight='bold')
    ax4.set_ylabel('Coefficiente principale', fontsize=12)
    ax4.set_title('Coefficiente dominante: quasi lo stesso', fontsize=14, fontweight='bold')
    ax4.grid(True, alpha=0.3, axis='y')
    ax4.set_ylim(4, 5.6)
    ax4.axhline(y=np.mean(d1_values), color='red', linestyle='--', alpha=0.5)

    plt.suptitle('PERCHE\' LE FORMULE CONVERGONO: NON SONO INDIPENDENTI',
                fontsize=18, fontweight='bold', y=1.01)
    savefig('14b_convergenza_trucco.png')


def anatomia_codice():
    """Conta righe di codice vs parametri."""
    total_code = 0
    for root, dirs, files in os.walk(FAIR_SRC):
        for fname in files:
            if fname.endswith('.py'):
                with open(os.path.join(root, fname)) as fh:
                    for line in fh:
                        s = line.strip()
                        if s and not s.startswith('#') and not s.startswith('"""') and not s.startswith("'''"):
                            total_code += 1

    csv_path = os.path.join(FAIR_SRC, 'defaults', 'data', 'ar6', 'species_configs_properties.csv')
    df = pd.read_csv(csv_path)
    n_values = df.iloc[:, 1:].notna().sum().sum()

    print(f'  Righe di codice: {total_code}')
    print(f'  Parametri (valori nel CSV): {n_values}')
    print(f'  Specie: {len(df)}, Parametri per specie: {len(df.columns)-1}')


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    print('=== 03 — CONVERGENZA E GENEALOGIA ===\n')
    print('Anatomia codice...')
    anatomia_codice()
    print('\nCiclo carbonio...')
    ciclo_carbonio()
    print('\nConvergenza formule...')
    convergenza_formule()
    print('\nDone.')
