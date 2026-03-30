# Analisi FaIR 2.2.4

Analisi tecnica indipendente del modello climatico FaIR, usato dall'IPCC AR6.

## Setup

```bash
python3 -m venv env
source env/bin/activate
pip install FaIR matplotlib
```

## Script

| Script | Cosa fa | Grafici |
|--------|---------|---------|
| `fair_utils.py` | Modulo condiviso (helper) | - |
| `01_parametri.py` | Sensibilita' ai parametri, Monte Carlo, stress test | 01-03, 06, 11-12, 15-16 |
| `02_struttura.py` | Critiche strutturali: linearita', tipping points, non-identificabilita' | 17-27 |
| `03_convergenza.py` | Genealogia delle formule, ciclo del carbonio | 05, 14b |

## Esecuzione

```bash
cd src
python 01_parametri.py
python 02_struttura.py
python 03_convergenza.py
```

I grafici vengono salvati in `output/`.

## Grafici prodotti

| # | Nome | Cosa mostra |
|---|------|-------------|
| 01 | sensibilita_ecs | ECS 2.0-5.0: da 2.38 a 4.76°C |
| 02 | forcing_scaling | ±20% su forcing_scale |
| 03 | formule_diverse | 4 formule, 4 risultati |
| 05 | ciclo_carbonio | Box fittizi, lifetime e partition |
| 06 | stress_test | Da 1.71 a 7.66°C |
| 11 | reverse_engineering | Da 1.3 a 8.8°C a scelta |
| 12 | monte_carlo | 10.000 run, range 1-9°C |
| 14b | convergenza_trucco | Genealogia formule, non indipendenti |
| 15 | trucco_aerosol | ERFaci controlla lo spread |
| 16 | muro_incertezza | Ogni parametro sposta il risultato |
| 17 | linearita | R²=0.978, risposta lineare |
| 18 | tipping_points | Curve sempre lisce |
| 19 | path_dependency | Stesse cumulative, T quasi uguale |
| 20 | zero_dimensioni | 0D vs 3D |
| 21 | ecs_collapse | Stessa ECS, dinamica diversa |
| 22 | smooth | Derivata seconda sempre piccola |
| 23 | incertezza_strutturale | Parametrica vs strutturale |
| 24 | distribuzioni | La forma della distribuzione cambia i percentili |
| 25 | hindcast_forecast | Calibrato sul passato, diverge nel futuro |
| 26 | error_compensation | Giusto per i motivi sbagliati |
| 27 | non_identificabilita | 457/1000 fittano, range 1.8-4.6°C |

## Dipendenze

- FaIR 2.2.4
- matplotlib
- numpy
- scipy
- pandas
- xarray
