#!/usr/bin/env python3
"""
04_costi.py — Il conto finale: quanto costa elettrificare l'Italia
===================================================================
Somma tutti i costi: generazione, rete, colonnine, smart charging.
Confronta con la spesa attuale per carburanti.

Fonti:
  - Energy & Strategy (Politecnico di Milano) 2024: LCOE Italia
    Fotovoltaico: 65-80 EUR/MWh, Eolico: 90-100 EUR/MWh
    https://www.rinnovabili.it/energia/fotovoltaico/lcoe-rinnovabili-costo-livellato-energia/
  - Phase S.r.l.: costo cabina MT/BT 40k-120k EUR
    https://www.phasesrl.com/quanto-costa-una-cabina-elettrica/
  - MOTUS-E 2025: costo installazione colonnina DC 50kW ~40-60k EUR
  - Il Sole 24 Ore 2024: spesa carburanti autotrazione 69.8 mld EUR
    https://en.ilsole24ore.com/art/benzina-e-gasolio-autotrazione-2024-spesi-italia-quasi-70-miliardi-AGM6LqmD
  - I-Com 2024: fattura energetica 48.5 mld EUR (petrolio + gas)
    https://www.i-com.it/2025/07/04/fattura-energetica-italiana-spesa-in-calo-nel-2024-grazie-a-minori-importazioni-ed-euro-piu-forte/
  - Ingenio 2025: wallbox domestica 700-1300 EUR
    https://www.ingenio-web.it/articoli/guida-2025-alle-wallbox-che-cosa-sono-le-caratteristiche-quali-scegliere/

Output: output/10_costi_breakdown.png
        output/11_confronto_carburante.png
        output/12_smart_vs_dumb.png
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


# ─── PARAMETRI ───────────────────────────────────────────────────────

N_AUTO         = 40_300_000
KM_ANNO        = 10_231
KWH_100KM      = 18.0
FABBISOGNO_EV  = N_AUTO * KM_ANNO * KWH_100KM / 100 / 1e9  # TWh/anno

# === 1. GENERAZIONE ===
# LCOE medio ponderato (mix 60% FV + 30% eolico + 10% gas)
LCOE_FV        = 72.5           # EUR/MWh (media 65-80, Polimi)
LCOE_EOLICO    = 95.0           # EUR/MWh (media 90-100, Polimi)
LCOE_GAS       = 95.0           # EUR/MWh (CCGT, BNEF 2025)
LCOE_MIX       = 0.60 * LCOE_FV + 0.30 * LCOE_EOLICO + 0.10 * LCOE_GAS
# = 43.5 + 28.5 + 9.5 = 81.5 EUR/MWh

# Costo CAPEX generazione (impianti nuovi)
# FV: ~800 EUR/kW installato, CF 15% → 1 GW produce ~1.3 TWh/anno
# Eolico: ~1400 EUR/kW, CF 25% → 1 GW produce ~2.2 TWh/anno
CAPEX_FV_EUR_KW     = 800       # EUR/kW installato (utility scale Italia)
CAPEX_EOLICO_EUR_KW = 1400      # EUR/kW installato
CF_FV               = 0.15      # capacity factor FV Italia
CF_EOLICO           = 0.25      # capacity factor eolico Italia

# === 2. RETE DISTRIBUZIONE ===
N_CABINE_TOTALI     = 524_000   # cabine secondarie (stima nazionale)
COSTO_CABINA_UPGRADE = 80_000   # EUR media (Phase S.r.l.)
FRAZ_CABINE_UPGRADE  = 0.85     # ~85% va potenziata (da calcolo 02_cabina.py)
COSTO_LINEE_BT_KM   = 50_000   # EUR/km (cavi BT interrati)
KM_LINEE_BT_UPGRADE  = 150_000  # km di linee BT da potenziare (stima: ~20% di 791k km)
COSTO_SMART_GRID     = 5e9      # EUR: digitalizzazione, contatori, gestione (stima RSE)

# === 3. COLONNINE PUBBLICHE ===
N_PUNTI_NECESSARI    = 200_000  # da calcolo 03_code.py
PUNTI_ATTUALI        = 73_047   # MOTUS-E
PUNTI_DA_INSTALLARE  = N_PUNTI_NECESSARI - PUNTI_ATTUALI
# Costi per tipo
COSTO_DC_50KW        = 50_000   # EUR per punto (hardware + installazione)
COSTO_DC_150KW       = 100_000  # EUR per punto
COSTO_AC_22KW        = 15_000   # EUR per punto
# Mix: 30% DC50, 20% DC150, 50% AC22
COSTO_MEDIO_PUNTO    = 0.30 * COSTO_DC_50KW + 0.20 * COSTO_DC_150KW + 0.50 * COSTO_AC_22KW
# = 15000 + 20000 + 7500 = 42500 EUR

# === 4. WALLBOX DOMESTICHE ===
N_WALLBOX            = int(N_AUTO * 0.60)  # 60% delle auto avrà wallbox
COSTO_WALLBOX_MEDIO  = 1_000    # EUR (Ingenio 2025: 700-1300)
COSTO_INSTALLAZIONE  = 500      # EUR (elettricista, pratica)

# === 5. STORAGE (per coprire intermittenza rinnovabili) ===
# Per il 60% di FV servono ~4h di storage per coprire la sera
# GW storage = picco serale EV * copertura
GW_STORAGE           = 15       # GW di batterie grid-scale
ORE_STORAGE          = 4        # ore di autonomia
COSTO_BESS_EUR_KWH   = 250      # EUR/kWh (BNEF 2025, Li-ion utility)

# === CONFRONTO ===
SPESA_CARBURANTI     = 69.8e9   # EUR/anno (Il Sole 24 Ore 2024)
SPESA_ACCISE_IVA     = 38.5e9   # EUR/anno affluiti allo Stato
FATTURA_PETROLIO     = 22.2e9   # EUR/anno importazioni greggio
PREZZO_ELETTRICITA   = 0.28     # EUR/kWh (prezzo medio consumatore, ARERA)


# ─── CALCOLI ─────────────────────────────────────────────────────────

def calcola_costi():
    """Calcola tutti i costi di transizione."""

    costi = {}

    # 1. Generazione: CAPEX impianti
    # Servono ~74 TWh/anno aggiuntivi
    twh_fv = FABBISOGNO_EV * 0.60       # 60% da FV
    twh_eol = FABBISOGNO_EV * 0.30      # 30% da eolico
    # GW necessari
    gw_fv = twh_fv / (CF_FV * 8760 / 1000)
    gw_eol = twh_eol / (CF_EOLICO * 8760 / 1000)
    costo_fv = gw_fv * 1e6 * CAPEX_FV_EUR_KW        # EUR
    costo_eol = gw_eol * 1e6 * CAPEX_EOLICO_EUR_KW   # EUR
    costi['Generazione\n(FV + eolico)'] = (costo_fv + costo_eol, '#00ff88')

    print(f'=== 1. GENERAZIONE ===')
    print(f'TWh aggiuntivi:            {FABBISOGNO_EV:>10.1f} TWh/anno')
    print(f'  di cui FV:               {twh_fv:>10.1f} TWh ({gw_fv:.1f} GW installati)')
    print(f'  di cui eolico:           {twh_eol:>10.1f} TWh ({gw_eol:.1f} GW installati)')
    print(f'LCOE mix:                  {LCOE_MIX:>10.1f} EUR/MWh')
    print(f'CAPEX FV:                  {costo_fv/1e9:>10.1f} mld EUR')
    print(f'CAPEX eolico:              {costo_eol/1e9:>10.1f} mld EUR')
    print(f'CAPEX totale generazione:  {(costo_fv+costo_eol)/1e9:>10.1f} mld EUR')
    print()

    # 2. Rete distribuzione
    costo_cabine = N_CABINE_TOTALI * FRAZ_CABINE_UPGRADE * COSTO_CABINA_UPGRADE
    costo_linee = KM_LINEE_BT_UPGRADE * COSTO_LINEE_BT_KM
    costo_rete = costo_cabine + costo_linee + COSTO_SMART_GRID
    costi['Rete distribuzione\n(cabine + linee + smart)'] = (costo_rete, '#f5c518')

    print(f'=== 2. RETE DISTRIBUZIONE ===')
    print(f'Cabine da potenziare:      {int(N_CABINE_TOTALI*FRAZ_CABINE_UPGRADE):>10,}')
    print(f'Costo cabine:              {costo_cabine/1e9:>10.1f} mld EUR')
    print(f'Costo linee BT:            {costo_linee/1e9:>10.1f} mld EUR')
    print(f'Costo smart grid:          {COSTO_SMART_GRID/1e9:>10.1f} mld EUR')
    print(f'TOTALE rete:               {costo_rete/1e9:>10.1f} mld EUR')
    print()

    # 3. Colonnine pubbliche
    costo_colonnine = PUNTI_DA_INSTALLARE * COSTO_MEDIO_PUNTO
    costi['Colonnine\npubbliche'] = (costo_colonnine, '#4ecdc4')

    print(f'=== 3. COLONNINE PUBBLICHE ===')
    print(f'Punti da installare:       {PUNTI_DA_INSTALLARE:>10,}')
    print(f'Costo medio/punto:         {COSTO_MEDIO_PUNTO:>10,.0f} EUR')
    print(f'TOTALE colonnine:          {costo_colonnine/1e9:>10.1f} mld EUR')
    print()

    # 4. Wallbox domestiche
    costo_wallbox = N_WALLBOX * (COSTO_WALLBOX_MEDIO + COSTO_INSTALLAZIONE)
    costi['Wallbox\ndomestiche'] = (costo_wallbox, '#7c4dff')

    print(f'=== 4. WALLBOX DOMESTICHE ===')
    print(f'Wallbox da installare:     {N_WALLBOX:>10,}')
    print(f'Costo unitario:            {COSTO_WALLBOX_MEDIO + COSTO_INSTALLAZIONE:>10,} EUR')
    print(f'TOTALE wallbox:            {costo_wallbox/1e9:>10.1f} mld EUR')
    print()

    # 5. Storage
    kwh_storage = GW_STORAGE * 1e6 * ORE_STORAGE  # kWh
    costo_storage = kwh_storage * COSTO_BESS_EUR_KWH
    costi['Storage\n(batterie grid)'] = (costo_storage, '#ff8800')

    print(f'=== 5. STORAGE ===')
    print(f'Capacita:                  {GW_STORAGE} GW / {GW_STORAGE * ORE_STORAGE} GWh')
    print(f'Costo BESS:                {COSTO_BESS_EUR_KWH} EUR/kWh')
    print(f'TOTALE storage:            {costo_storage/1e9:>10.1f} mld EUR')
    print()

    # TOTALE
    totale = sum(v[0] for v in costi.values())
    print(f'{"="*50}')
    print(f'TOTALE INVESTIMENTO:       {totale/1e9:>10.1f} mld EUR')
    print(f'{"="*50}')
    print()

    # Costo operativo annuo (energia)
    costo_energia_annuo = FABBISOGNO_EV * 1e6 * LCOE_MIX  # EUR
    # Confronto onesto: lo Stato perderebbe 38.5 mld di accise/IVA carburanti
    # e dovrebbe recuperarli tassando l'elettricita'. Costo reale per il consumatore:
    costo_en_retail = FABBISOGNO_EV * 1e6 * PREZZO_ELETTRICITA * 1000  # EUR (a prezzo retail)

    print(f'=== CONFRONTO ===')
    print(f'Costo energia annuo (LCOE):    {costo_energia_annuo/1e9:>8.1f} mld EUR/anno')
    print(f'Costo energia annuo (retail):  {costo_en_retail/1e9:>8.1f} mld EUR/anno')
    print(f'Spesa carburanti attuale:      {SPESA_CARBURANTI/1e9:>8.1f} mld EUR/anno')
    print(f'  di cui accise + IVA:         {SPESA_ACCISE_IVA/1e9:>8.1f} mld EUR/anno')
    print(f'  costo netto carburante:      {(SPESA_CARBURANTI-SPESA_ACCISE_IVA)/1e9:>8.1f} mld EUR/anno')
    print()
    print(f'Scenario A (confronto LCOE):')
    print(f'  Risparmio annuo:             {(SPESA_CARBURANTI - costo_energia_annuo)/1e9:>8.1f} mld EUR/anno')
    print(f'  Payback:                     {totale / (SPESA_CARBURANTI - costo_energia_annuo):>8.1f} anni')
    print(f'Scenario B (confronto retail, tasse invariate):')
    risparmio_retail = SPESA_CARBURANTI - costo_en_retail
    print(f'  Risparmio annuo:             {risparmio_retail/1e9:>8.1f} mld EUR/anno')
    if risparmio_retail > 0:
        print(f'  Payback:                     {totale / risparmio_retail:>8.1f} anni')
    else:
        print(f'  Payback:                     MAI (costo maggiore)')
    print(f'NOTA: il confronto reale e tra A e B. Lo Stato deve recuperare')
    print(f'      le accise perse: la verita e nel mezzo.')
    print()

    return costi, totale, costo_energia_annuo


def plot_breakdown(costi, totale):
    """Grafico 10: breakdown dei costi di investimento."""
    fig, ax = plt.subplots(figsize=(14, 7))

    labels = list(costi.keys())
    values = [v[0] / 1e9 for v in costi.values()]
    colors = [v[1] for v in costi.values()]

    bars = ax.barh(range(len(labels)), values, color=colors, height=0.6,
                   edgecolor='none')

    for i, (bar, val) in enumerate(zip(bars, values)):
        pct = val / (totale / 1e9) * 100
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                f'{val:.1f} mld EUR ({pct:.0f}%)',
                va='center', fontsize=12, fontweight='bold', color=colors[i])

    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=11)
    ax.set_xlabel('Miliardi di EUR', fontsize=13)
    ax.set_title(f'Investimento totale: {totale/1e9:.0f} miliardi EUR\n'
                 f'per elettrificare 40.3 milioni di auto',
                 fontsize=14, fontweight='bold')
    ax.grid(axis='x', alpha=0.3)
    ax.invert_yaxis()

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/10_costi_breakdown.png', dpi=150,
                bbox_inches='tight', facecolor='#0d1117')
    plt.close()
    print(f'[OK] {OUTPUT_DIR}/10_costi_breakdown.png')


def plot_confronto(totale, costo_energia_annuo):
    """Grafico 11: confronto con spesa carburante — payback."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 7))

    # --- Pannello sinistro: costi annui ---
    ax = axes[0]
    categorie = ['Carburanti\n(oggi)', 'Elettricita\n(100% EV)']
    valori = [SPESA_CARBURANTI / 1e9, costo_energia_annuo / 1e9]
    colors = ['#ff6b6b', '#00ff88']

    bars = ax.bar(range(2), valori, color=colors, width=0.5)
    for bar, val in zip(bars, valori):
        ax.text(bar.get_x() + bar.get_width()/2, val + 1,
                f'{val:.1f} mld', ha='center', fontsize=14,
                fontweight='bold', color=bar.get_facecolor())

    risparmio = valori[0] - valori[1]
    ax.annotate(f'Risparmio: {risparmio:.0f} mld/anno',
                xy=(0.5, valori[1]), xytext=(0.5, (valori[0] + valori[1]) / 2),
                ha='center', fontsize=13, fontweight='bold', color='#f5c518',
                arrowprops=dict(arrowstyle='<->', color='#f5c518', lw=2))

    ax.set_ylabel('Miliardi EUR / anno', fontsize=13)
    ax.set_title('Costo annuo energia per trasporto', fontsize=14,
                 fontweight='bold')
    ax.set_xticks(range(2))
    ax.set_xticklabels(categorie, fontsize=11)
    ax.grid(axis='y', alpha=0.3)

    # --- Pannello destro: payback ---
    ax = axes[1]
    anni = np.arange(0, 21)
    # Cumulativo: investimento iniziale - risparmi annui
    risparmio_annuo = SPESA_CARBURANTI - costo_energia_annuo
    cumulativo = totale - risparmio_annuo * anni

    ax.plot(anni, cumulativo / 1e9, color='#4ecdc4', linewidth=2.5)
    ax.fill_between(anni, 0, cumulativo / 1e9,
                    where=cumulativo > 0, alpha=0.2, color='#ff6b6b')
    ax.fill_between(anni, 0, cumulativo / 1e9,
                    where=cumulativo <= 0, alpha=0.2, color='#00ff88')
    ax.axhline(y=0, color='#f5c518', linewidth=2, linestyle='-')

    payback = totale / risparmio_annuo
    ax.axvline(x=payback, color='#f5c518', linewidth=1.5, linestyle='--')
    ax.text(payback + 0.5, totale / 1e9 * 0.7,
            f'Payback:\n{payback:.1f} anni',
            fontsize=13, fontweight='bold', color='#f5c518')

    ax.set_xlabel('Anni', fontsize=13)
    ax.set_ylabel('Saldo netto (mld EUR)', fontsize=13)
    ax.set_title('Payback investimento', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/11_confronto_carburante.png', dpi=150,
                bbox_inches='tight', facecolor='#0d1117')
    plt.close()
    print(f'[OK] {OUTPUT_DIR}/11_confronto_carburante.png')


def plot_smart_vs_dumb():
    """Grafico 12: costo della rete con/senza smart charging."""
    from matplotlib.patches import FancyBboxPatch

    # Senza smart charging: devi potenziare tutto
    costo_dumb = {
        'Cabine MT/BT': N_CABINE_TOTALI * FRAZ_CABINE_UPGRADE * COSTO_CABINA_UPGRADE,
        'Linee BT': KM_LINEE_BT_UPGRADE * COSTO_LINEE_BT_KM,
        'Generazione picco': 10e9,  # 10 GW gas peaker per coprire picchi
    }

    # Con smart charging: riduci il picco del 50%
    costo_smart = {
        'Cabine MT/BT': N_CABINE_TOTALI * FRAZ_CABINE_UPGRADE * 0.4 * COSTO_CABINA_UPGRADE,
        'Linee BT': KM_LINEE_BT_UPGRADE * 0.3 * COSTO_LINEE_BT_KM,
        'Smart grid + IT': COSTO_SMART_GRID,
        'Generazione picco': 3e9,  # molto meno peaker
    }

    fig, ax = plt.subplots(figsize=(14, 7))

    # Barre impilate
    x = [0, 1]
    labels_x = ['Dumb charging\n(tutti alle 19:00)', 'Smart charging\n(carica ottimizzata)']

    bottom_dumb = 0
    bottom_smart = 0
    colors = ['#ff6b6b', '#f5c518', '#4ecdc4', '#7c4dff']

    all_keys = list(set(list(costo_dumb.keys()) + list(costo_smart.keys())))
    all_keys.sort()

    for i, key in enumerate(all_keys):
        vd = costo_dumb.get(key, 0) / 1e9
        vs = costo_smart.get(key, 0) / 1e9
        color = colors[i % len(colors)]

        ax.bar(0, vd, bottom=bottom_dumb, color=color, width=0.5,
               label=key if i < len(all_keys) else None)
        ax.bar(1, vs, bottom=bottom_smart, color=color, width=0.5, alpha=0.7)

        if vd > 1:
            ax.text(0, bottom_dumb + vd/2, f'{vd:.0f}', ha='center', va='center',
                    fontsize=10, color='#0d1117', fontweight='bold')
        if vs > 1:
            ax.text(1, bottom_smart + vs/2, f'{vs:.0f}', ha='center', va='center',
                    fontsize=10, color='#0d1117', fontweight='bold')

        bottom_dumb += vd
        bottom_smart += vs

    totale_dumb = sum(costo_dumb.values()) / 1e9
    totale_smart = sum(costo_smart.values()) / 1e9
    risparmio = totale_dumb - totale_smart

    ax.text(0, totale_dumb + 2, f'{totale_dumb:.0f} mld', ha='center',
            fontsize=14, fontweight='bold', color='#ff6b6b')
    ax.text(1, totale_smart + 2, f'{totale_smart:.0f} mld', ha='center',
            fontsize=14, fontweight='bold', color='#00ff88')

    ax.annotate(f'Risparmio: {risparmio:.0f} mld EUR',
                xy=(0.5, totale_smart), xytext=(0.5, (totale_dumb + totale_smart) / 2),
                ha='center', fontsize=13, fontweight='bold', color='#f5c518')

    ax.set_ylabel('Miliardi EUR', fontsize=13)
    ax.set_title('Smart charging: l\'intelligenza costa meno del rame',
                 fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(labels_x, fontsize=12)
    ax.legend(fontsize=10, loc='upper right')
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/12_smart_vs_dumb.png', dpi=150,
                bbox_inches='tight', facecolor='#0d1117')
    plt.close()
    print(f'[OK] {OUTPUT_DIR}/12_smart_vs_dumb.png')


# ─── MAIN ────────────────────────────────────────────────────────────

if __name__ == '__main__':
    costi, totale, costo_en = calcola_costi()
    plot_breakdown(costi, totale)
    plot_confronto(totale, costo_en)
    plot_smart_vs_dumb()
