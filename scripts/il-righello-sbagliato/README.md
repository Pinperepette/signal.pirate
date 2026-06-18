# Stabilità del ranking — benchmark *Propaganda Resistance* (EKI)

Codice e dati per riprodurre l'analisi quantitativa dell'articolo
**[Il Righello Sbagliato](https://pinperepette.github.io/signal.pirate/articoli/il-righello-sbagliato.html)**
(Signal Pirate). Tutti i numeri citati nell'articolo — densità del vicinato,
perturbazione del rango, simulazione Monte Carlo, Kendall τ — sono prodotti da
questo codice e verificabili byte-per-byte sul dato congelato.

## File

| File | Cosa |
|------|------|
| `stabilita_ranking.ipynb` | **Notebook di verifica**, eseguibile dall'alto in basso, con output e 4 figure incorporati. È l'artefatto da aprire per prima cosa. |
| `stabilita_ranking.py` | Stesso calcolo in forma di script (`python3 stabilita_ranking.py`). |
| `results.json` | **Dato congelato** del benchmark (vedi *Provenienza*). |
| `requirements.txt` | Ambiente con versioni fissate. |
| `_build_notebook.py` | Generatore del notebook (per trasparenza su come è costruito). |

## Provenienza del dato (pinned)

- **Fonte:** repository ufficiale del benchmark, [`keeleinstituut/leaderboard-data-ui`](https://github.com/keeleinstituut/leaderboard-data-ui), file `results.json`
- **Commit:** `1d1d8d3c260d7b40cf833cdd05deb41b495be64f` (2026-06-15)
- **SHA-256:** `db30576fbb28e99535319900a171686cfb0b0b5a40dec9feb76a574131a6f020`
- **URL verificabile (stesso commit):**
  <https://raw.githubusercontent.com/keeleinstituut/leaderboard-data-ui/1d1d8d3c260d7b40cf833cdd05deb41b495be64f/results.json>

Il file qui incluso è **congelato** a quel commit perché la leaderboard è *live* e
può cambiare. Per controllarlo:

```bash
shasum -a 256 results.json
# atteso: db30576fbb28e99535319900a171686cfb0b0b5a40dec9feb76a574131a6f020
```

Il notebook esegue questo stesso `assert` come prima cella: se il dato non
corrisponde, l'esecuzione si ferma.

## Come riprodurre

```bash
pip install -r requirements.txt

# opzione A — script (stampa i numeri, salva le figure in ../../immagini/...)
python3 stabilita_ranking.py

# opzione B — notebook (riesegue e reincorpora output e figure)
jupyter nbconvert --to notebook --execute --inplace stabilita_ranking.ipynb
```

Il seme del generatore casuale è fissato (`np.random.default_rng(20260618)`):
le 100.000 simulazioni Monte Carlo danno gli **stessi** risultati a ogni
esecuzione.

## Risultati attesi (riferimento)

```
entro +/-1 / 2 / 3 / 5 pt da Mistral : 3 / 6 / 14 / 18 modelli
distacco medio per posizione         : 0.80 pt (globale) | 0.36 pt (zona 40-50)
perturbazione del solo Mistral       : +1 pt -> 46o | -1 pt -> 49o
SEM del punteggio (pavimento)        : ~0.58 pt

Monte Carlo (100.000 simulazioni):
  sigma=0.5 | IC95% rango [45, 50] | P(rango!=47)=0.68 | Kendall tau 0.97
  sigma=1.0 | IC95% rango [42, 50] | P(rango!=47)=0.80 | Kendall tau 0.95
  sigma=2.0 | IC95% rango [37, 52] | P(rango!=47)=0.90 | Kendall tau 0.90
  scambio col vicino di casella (sigma=1): P ~ 0.40-0.45
```

## Caveat di onestà

Le intensità di rumore (σ ∈ {0.5, 1, 2} punti) sono **assunzioni**, non quantità
misurate: lo studio originale non pubblica le annotazioni umane grezze (il repo
`propa-bench` restituisce 404), quindi il σ reale non è stimabile dall'esterno.
I risultati sul rango sono perciò **condizionati a σ** e vanno letti come analisi
di sensibilità, non come stima puntuale. Il pavimento teorico dell'errore
(SEM ≈ 0,58 punti) indica che σ ≥ 0,5 è plausibile, e già a σ = 0,5 il rango di
Mistral non è stabile (IC 95% [45, 50]). Il Kendall τ alto (≈ 0,90–0,97) mostra
inoltre che a essere rumore è la risoluzione *fine* nel centro affollato della
classifica, non l'ordine globale.
