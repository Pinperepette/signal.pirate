# L'Italia che non c'è stata — dati e codice

Materiale per rifare da zero i conti dell'articolo
[L'Italia che non c'è stata](https://pinperepette.github.io/signal.pirate/articoli/l-italia-che-non-c-e-stata.html).

Come al solito metto tutto, così chiunque può riaprire i numeri invece di fidarsi.
Anche le regressioni che non funzionano: sono dentro, non le ho tolte.

## Cosa c'è

- **`sintetico.py`** — il controllo sintetico, cioè il pezzo grosso. Costruisce
  l'Italia finta coi dodici paesi fuori dall'euro, stampa i pesi, il divario anno
  per anno, il placebo su ogni paese di controllo e il p-value per permutazione.
- **`motore.py`** — Bai-Perron e filtro di Kalman scritti da zero, con dentro i
  loro test di verifica. Lanciandolo da solo controlla che funzionino su dati
  simulati di cui conosce la risposta.
- **`analisi.py`** — le rotture strutturali sulle otto serie storiche, gli
  intervalli col bootstrap a blocchi, la prova di robustezza al variare della
  lunghezza minima dei segmenti, il co-movimento col Kalman e i conti finali su
  salari, quota salari e partite correnti.
- **`dati/`** — i CSV già scaricati, così tutto gira anche offline.

## Come si esegue

```bash
pip install pandas numpy scipy
python3 motore.py       # i test del motore matematico
python3 sintetico.py    # il controllo sintetico e i placebo
python3 analisi.py      # rotture, bootstrap, Kalman  (un paio di minuti)
```

Il seme è fisso (`20260808`), quindi i numeri escono identici a ogni esecuzione.

## Il controllo sintetico in tre righe

Non esiste un paese identico all'Italia da usare come confronto, ma un miscuglio
di paesi può assomigliarle molto più di qualunque singolo paese. Quindi si cercano
i pesi `w` che minimizzano

```
|| X_Italia − X_altri · w ||²      con    w_j ≥ 0    e    Σ w_j = 1
```

dove `X` sono i dati **prima** del trattamento. Il vincolo che i pesi siano positivi
e sommino a uno è quello che rende il metodo onesto: il paese finto deve essere una
media vera di paesi veri, senza pesi negativi che permetterebbero di far tornare
qualunque conto.

Poi si guarda cosa succede dopo. Il metodo è quello di Abadie e Gardeazabal, nato
per misurare quanto era costato il terrorismo ai Paesi Baschi.

**Risultati.** Pesi: Svizzera 0,54, Australia 0,17, Corea 0,14, Giappone 0,10,
Svezia 0,03, Islanda 0,02. Errore medio nei diciannove anni prima dell'euro: 0,43
punti sul Pil pro capite, 0,67 sulla produttività. Divario nel 2019: **−36,1 punti**
di Pil pro capite, **−25,3** di produttività per occupato.

**Placebo per paese.** Lo stesso esercizio con ogni donatore al posto dell'Italia.
Sulla produttività nessuno dei dodici ha un divario negativo quanto il nostro, da
cui il p-value per permutazione di 0,077.

**Placebo nel tempo.** Spostando il trattamento finto al 1990 il divario è +3,0, al
1995 è +0,1. Solo con la data vera esce −36,1.

## Le fonti

| file | cosa contiene | fonte |
|---|---|---|
| `dati/panel_sintetico.csv` | Pil reale pro capite e Pil per occupato, Italia e dodici paesi fuori dall'euro, 1960-2027 | AMECO *Spring 2026* |
| `dati/europa_lunga.csv` | quota salari, partite correnti, investimenti pubblici, Pil pro capite per paese | AMECO *Spring 2026* |
| `dati/rendimenti_10anni.csv` | rendimenti dei titoli decennali di Italia, Germania e Spagna, mensili 2009-2015 | Banca centrale europea, Data Portal |
| `dati/salari_reali_ocse.csv` | salario medio annuo, prezzi costanti a parità di potere d'acquisto | OCSE, *Average annual wages* |
| `dati/tassi_ufficiali.csv` | tassi ufficiali di sconto di Italia, Germania, Regno Unito e Stati Uniti, mensili dal 1964 | FMI *IFS* via FRED |
| `dati/cpi_italia.csv`, `dati/cpi_germania.csv` | prezzi al consumo mensili | OCSE via FRED |
| `dati/bot_italia.csv`, `dati/lira_dollaro.csv`, `dati/marco_dollaro.csv` | BOT e cambi mensili | FMI *IFS* via FRED |
| `dati/italia_annuale.csv` | debito, saldi, interessi, tasso implicito, spesa e entrate | Osservatorio Conti Pubblici Italiani, serie storiche 1861-2025 |

## Cosa non è qui dentro

I fatti storici non sono un dataset e non li rifai con uno script: la decisione del
Consiglio CEE 71/143 del 22 marzo 1971 sull'assistenza finanziaria a medio termine,
attivata una volta sola e per l'Italia nel 1974; lo swap in oro con la Bundesbank
dell'agosto 1974, 16.778.523 once pari a circa 522 tonnellate; il discorso di Draghi
del 26 luglio 2012; e G. Carli, *Cinquant'anni di vita italiana*, 1993, per la
dottrina del vincolo esterno. Quelli sono citati nel testo con nome e data.
