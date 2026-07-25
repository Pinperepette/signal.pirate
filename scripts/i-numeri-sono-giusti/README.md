# I numeri sono giusti (la conclusione no) — dati e codice

Pacchetto di replicazione dell'articolo. Tutto quello che serve per rifare ogni conto da soli.

## Come si riproduce

```bash
python3 fetch.py     # scarica i tre dataset da ISTAT (SDMX) in data/
python3 analisi.py   # riproduce, sezione per sezione, ogni numero citato nell'articolo
```

`fetch.py` non ha dipendenze oltre alla libreria standard. `analisi.py` richiede `numpy` e `scipy`.
I CSV già scaricati sono inclusi in `data/`, quindi `analisi.py` funziona anche offline;
`fetch.py` serve a verificare che i dati siano davvero quelli di ISTAT.

## I dati

| file | contenuto | fonte |
|---|---|---|
| `data/delitti.csv` | delitti denunciati dalle forze di polizia per tipo di reato, Italia, 2006-2024 | ISTAT SDMX, flusso `73_67_DF_DCCV_DELITTIPS_1`, chiave `A.IT.CRIMEN..9.YRDUR` |
| `data/vittime_sesso.csv` | vittime di omicidio volontario per sesso ed età, 2007-2024 | ISTAT SDMX, flusso `73_230_DF_DCCV_AUTVITTPS_1`, `DATA_TYPE=VICTIM` |
| `data/denunciati_cittadinanza.csv` | autori di delitto denunciati per cittadinanza, sesso ed età, totale reati | stesso flusso, `DATA_TYPE=OFFEND` |

Endpoint: `https://esploradati.istat.it/SDMXWS/rest/`.

## Cosa riproduce `analisi.py`

- la partizione in 35 categorie di primo livello (verifica: somma esatta al totale su tutti i 19 anni);
- la scomposizione del calo 2007-2024: furti 109% del calo, veicoli 52%, ingiurie 11,6%, al netto dei furti +3,7% sul 2007 e +9,3% sul 2019;
- il cambio di segno con l'anno base: −18,2% sul 2007, +4,2% sul 2019, +26,2% sul 2020;
- la verifica della mossa «senza i reati digitali»: −25,7%;
- omicidi: Mann-Kendall e Theil-Sen sui due periodi, rottura strutturale sup-F (2018, p simulato 0,001, IC bootstrap 2018-2020), controfattuale (+29% sopra la traiettoria);
- consumati vs tentati (−47,5 vs −22,1), letalità (29,7% → 22,2%), vittime per sesso (−55,1 vs −23,6);
- quantità vs composizione: distanza in variazione totale 17,3% contro 18,2% (16,7 vs 16,4 senza ingiurie), rumore di Poisson 187 volte più piccolo, scomposizione delle quote;
- italiani/stranieri: 548.265 vs 270.567 denunciati nel 2022, tassi 1.015 vs 5.378 per 100k (5,3x; 5,6x sui maschi adulti);
- gli scippi: calo atteso dal solo cambio di propensione a denunciare (−23,3%) contro quello osservato (−24,6%);
- le variazioni 2019→2024 e l'effetto lockdown 2019→2020 per categoria.

## Numeri che vengono da rapporti in PDF (non scaricabili via API)

Questi valori sono usati come costanti, con la fonte esatta:

- **Propensione a denunciare** (scippi consumati 88,9% → 68,2%; reati informatici 18,4% → 24,1%), **rischio di borseggio 5x** per gli utenti quotidiani dei mezzi (2,8% vs 0,5%), **avvertenza sul periodo pandemico** (pag. 3), **+74% delle sottrazioni via home banking**, **stabilità degli scippi subìti**: ISTAT, *Reati contro la persona e la proprietà: vittime ed eventi, anno 2022-2023*, 9 giugno 2025 — https://www.istat.it/wp-content/uploads/2025/06/Report_REATI-CONTRO-LA-PERSONA-E-LA-PROPRIETA_VITTIME-ED-EVENTI.pdf
- **Donne uccise 2024** (111, di cui 96 in ambito familiare/affettivo e 59 da partner o ex): Ministero dell'Interno, report omicidi al 31/12/2024 — https://www.interno.gov.it/sites/default/files/2025-01/report_omicidi_al_31_12_2024.pdf
- **Femminicidi presunti 2024** (106 su 116 vittime donne; tasso partner/ex 0,21 per 100k): ISTAT, *Le vittime di omicidio, anno 2024*, 25 novembre 2025 — https://www.istat.it/wp-content/uploads/2025/11/Report_Le-vittime-di-omicidio_Anno-2024.pdf
- **Omicidi mafiosi 1991** (oltre 700 su 1.916): statistiche delle forze di polizia dell'epoca, riprese dalle ricostruzioni storiche; nell'articolo è dichiarato ordine di grandezza.
- **Popolazione residente 2022** usata come denominatore dei tassi (54.000.295 italiani, 5.030.716 stranieri; maschi adulti 22.149.339 e 1.924.838): ISTAT, popolazione residente. Come detto nell'articolo, gli irregolari non sono nel denominatore.

## Avvertenze

Le stesse dell'articolo: i flussi contano reati **denunciati**; il flusso vittime conta le persone, quello dei delitti conta i fatti, e i totali non coincidono; la propensione a denunciare cambia nel tempo e per reato, ed è il motivo per cui il correttivo del sommerso va applicato in entrambe le direzioni. Il seme del generatore casuale è fisso (`20260725`): sup-F, bootstrap e test del rumore danno gli stessi numeri a ogni esecuzione.

Articolo esaminato: [«L'Italia è un paese sempre più sicuro»](https://www.lorenzoruffino.it/p/litalia-e-un-paese-sempre-piu-sicuro), Lorenzo Ruffino, 23 luglio 2026.
