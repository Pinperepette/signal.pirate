# Non è un esodo (e non è il lavoro) — dati e codice

Materiale per rifare da zero i conti dell'articolo
[Non è un esodo (e non è il lavoro)](https://pinperepette.github.io/signal.pirate/articoli/non-e-un-esodo.html).

Come al solito: metto tutto, così chiunque può riaprire i numeri invece di fidarsi.

## Cosa c'è

- **`analisi.py`** — un unico script, con i **dati incorporati dentro** (31 paesi europei, un indicatore per colonna). Rifà, nell'ordine: la regressione multipla (la tabella con β e p-value), la PCA (il 52% su un asse solo, l'Italia a sinistra), il clustering KMeans (i gruppi deboli, l'Italia col Sud-Est) e il bootstrap / Monte Carlo con 100.000 ricampionamenti (la distribuzione dei coefficienti). Cipro e Macedonia del Nord non hanno l'indice culturale di Hofstede, quindi le analisi girano su 29 paesi.

## Come si esegue

```bash
pip install pandas numpy statsmodels scikit-learn
python3 analisi.py
```

Il bootstrap a 100.000 giri richiede un minuto o due. Il seed è fisso (`20260721`), quindi i numeri escono identici a ogni esecuzione.

## Le colonne e le fonti

| colonna | cos'è | fonte |
|---|---|---|
| `eta_uscita` | età media di uscita dalla casa dei genitori | Eurostat `yth_demo_030`, 2023 |
| `proprieta_casa` | quota di persone che vivono in una casa di proprietà (%) | Eurostat `ilc_lvho02`, 2023 |
| `disoccupazione` | tasso di disoccupazione giovanile 15-24 (%) | Eurostat `yth_empl_090`, 2023 |
| `neet` | quota di giovani NEET 15-29 (%) | Eurostat `edat_lfse_20`, 2023 |
| `pil_pps_ue100` | PIL pro capite in PPS, indice con media UE27 = 100 | Eurostat `sdg_10_10`, 2023 |
| `affitti_livprezzi` | livello prezzi dell'alloggio (categoria A0104), indice EU = 100 (proxy del costo della casa) | Eurostat `prc_ppp_ind`, 2023 |
| `individualismo_hofstede` | indice di individualismo (IDV) | Hofstede Insights, geerthofstede.com |

## Cosa NON è qui dentro

La prima parte dell'articolo (esodo, chi parte, PCA, clustering, bootstrap) è tutta qui e la rifai da questo `dati.csv`.

La seconda parte (perché l'Italia è scivolata: euro, Romania, delocalizzazione, marchi, cuneo, morti sul lavoro, AI) usa numeri da fonti diverse, citate una per una nell'articolo: rapporto Draghi 2024, UNCTAD, Banca Mondiale, EU Tax Observatory, CLEPA, INAIL, OCSE, Stanford HAI. Quelli sono singoli dati pubblici, non un dataset unico, e i link stanno nel testo.
