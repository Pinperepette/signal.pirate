# Vi ho chiesto una serie e mi avete costruito un dataset

Il lab dell'articolo [mi-avete-costruito-un-dataset.html](../../articoli/mi-avete-costruito-un-dataset.html).

Due conversazioni su X, ricontate da zero il 12 agosto 2026:

* serie TV: [post originale](https://x.com/Pinperepette/status/2086859435490656571), 323 risposte raccolte su 373 dichiarate
* libri: [post originale](https://x.com/Pinperepette/status/2087117060631375995), 114 risposte

## Com'e' fatto

```
serie/
  raw/merged.json     le risposte grezze, deduplicate per id
  dati.py             SERIE (titolo, anno, paese, genere) + RECS [(persona, chiave)]
  stile.py            palette e helper condivisi dei grafici
  g1_videoteca.py     tutti i 210 titoli in nove scaffali
  g2_annate.py        i consigli sull'anno di prima messa in onda
  g3_classifica.py    la classifica, con i nomi di chi ha votato
  g4_grafo.py         il grafo circolare delle coppie consigliate insieme
  g5_confronto.py     serie vs libri: rarefazione di Hurlbert e coda lunga
  g6_diversita.py     numeri di Hill (q=0,1,2), Gini, somiglianza fra persone
  g7_persone.py       somiglianza di Jaccard fra le persone
  analisi_diversita.py  banco di prova: stampa numeri, nessun grafico
libri/
  raw/merged.json
  dati.py             BOOKS + RECS + AUTORI_SOLI + DI_PARTENZA
  stile.py
  g1_mappa.py         i 195 titoli in nove scaffali tematici
  g2_timeline.py      sette secoli, dall'anno di prima edizione originale
  g3_classifica.py
```

## Come si rifa'

```sh
pip install matplotlib numpy
cd serie && python3 g1_videoteca.py g2_annate.py g3_classifica.py   # uno per volta
python3 g5_confronto.py                                             # legge anche ../libri/dati.py
```

Nessun font particolare e' obbligatorio: se Impact e Menlo non ci sono, matplotlib
ripiega sui default e i grafici restano leggibili.

## Le due regole che contano

1. **Un voto per persona per titolo.** Se qualcuno ripete lo stesso titolo in tre
   commenti resta un voto. Se qualcuno ne elenca venticinque, quei venticinque
   valgono uno a testa.
2. **Il dataset e' curato a mano.** Nessun parsing automatico: i refusi
   (`Breaking Bed`, `Batlestar`, `Le Boureau`), le conferme senza titolo
   ("vero, quella e' bellissima") e le stroncature dentro un elenco di consigli
   non li distingue un regex. Se una riga di `RECS` vi sembra sbagliata, si vede
   e si corregge.

## Misure usate, e due che ho scartato

Il confronto serie/libri gira su tre strumenti, tutti a parita' di campione
(223 menzioni per entrambi, 500 sorteggi, seed 20260812):

* **rarefazione di Hurlbert** (`g5`): titoli diversi attesi dopo k menzioni
* **numeri di Hill** (`g6`): quanti titoli equiprobabili darebbero la stessa
  diversita'. q=0 e' il conteggio crudo, q=1 e' exp(entropia) cioe' la
  perplexity, q=2 e' l'inverso dell'indice di Herfindahl. Sono la stessa
  formula con un parametro diverso, non tre strumenti diversi.
* **Jaccard fra persone** (`g7`): titoli in comune diviso titoli totali, su ogni
  coppia di partecipanti. Attenzione alla trappola: J dipende dalla lunghezza
  delle liste, e sulle serie il 61% delle liste ha un titolo solo. Delle 77
  coppie con J = 1 (liste identiche), **76 sono coppie da un titolo solo, lo
  stesso**: non e' affinita', e' una lista corta, e gonfia il risultato dalla
  parte comoda. Il conto va rifatto tenendo solo chi ha nominato >= 2 titoli:
  il divario passa da 2x a 4x invece di sgonfiarsi (10.6% contro 2.4%, e a
  soglia 3 il 19.7% contro il 4.8%).
* **assortativita' di Newman** (`g4`) sul grafo titolo-titolo rispetto al
  genere, con test di permutazione su 3000 rimescolamenti delle etichette:
  r = +0.29, null -0.08 ± 0.09, p = 0.001. Sostituisce il "44 corde su 100",
  che dipendeva da come erano stati disegnati i settori del cerchio.

Due analisi girano in `analisi_diversita.py` ma **non finiscono nell'articolo**:

* **fit di una legge di potenza (Zipf)** con l'MLE di Clauset-Shalizi-Newman:
  alpha = 2.04 per le serie e 3.72 per i libri, KS 0.079 e 0.010. Non lo uso
  perche' sui libri il massimo e' 5 voti: stimare un esponente su interi da 1 a
  5 non e' informativo, e i due alpha non sono confrontabili in modo onesto.
* **informazione mutua genere/titolo**: e' degenere. Il titolo determina il
  genere, quindi H(genere | titolo) = 0 e I(titolo; genere) = H(genere) sempre,
  per costruzione. Riformulata come I(persona; genere) ha senso, ma con ~2
  titoli a testa il valore plug-in e' quasi tutto bias: osservato 1.28 nat
  contro un null di 1.09 ± 0.02. L'eccesso c'e', ma e' il 15% del totale.

## Limiti dichiarati

* la paginazione dell'API si ferma a 200 risposte per query: le 323 sono l'unione
  di quattro interrogazioni con ordinamenti e finestre diverse, e restano fuori
  circa 50 risposte che non e' stato possibile recuperare
* i generi sono un'etichetta mia e in piu' di un punto sono arbitrari
* l'anno e' la prima messa in onda della serie originale, non del reboot; 5 titoli
  su 210 (e 6 libri su 195) non hanno un anno accertato e restano fuori dalle
  viste temporali
* l'assortativita' e' calcolata su 23 nodi e 36 archi: il test di permutazione
  dice che non e' rumore, ma l'intervallo attorno a +0.29 e' largo
* il campione non e' rappresentativo di niente: sono le persone che seguono
  [@Pinperepette](https://x.com/Pinperepette) e avevano voglia di rispondere quella sera
