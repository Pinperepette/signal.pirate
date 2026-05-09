# Lab — Tre formati, stessa workload

Tre agenti (analyst, responder, auditor) modificano lo stesso piano di
risposta a un incidente di security. Il piano e' renderizzato in tre
formati: **Markdown**, **HTML**, **AGD**. Ogni agente emette le proprie
edit operation come record JSON. Il lab le applica al formato corrispondente
con la best-practice di editing per quel formato:

| Formato  | Strategia di editing                                |
|----------|-----------------------------------------------------|
| Markdown | regex string-replace via section heading            |
| HTML     | DOM manipulation via BeautifulSoup + `id` selector  |
| AGD      | native edit operations via la CLI `agd edit`        |

## Cosa misuriamo

- `applied`: quante delle 12 ops hanno trovato il loro target ed sono state applicate
- `not_found`: ops dove l'editor non e' riuscito a localizzare il target
- `integrity`: dopo tutte le ops, ogni item del workload e' presente nel doc finale?
- `final size`: dimensione del documento finale
- `canonical idempotent`: applicare il formatter due volte produce lo stesso byte-output?
- `avg bytes/op`: byte aggiunti al file per ogni op (proxy di "sparsita' dell'edit")
- `avg/max diff noise`: numero medio/massimo di righe `+`/`-` nel diff unified per ogni op
  (proxy di "leggibilita' del diff in PR")

## Il punto del workload

L'op `ts=4` rinomina la sezione "Findings" in "Initial findings". Markdown
non ha un meccanismo di stable ID, quindi il regex per "## Findings" non
trova piu' la sezione. La successiva op `ts=10` (auditor che aggiunge un
finding tardivo) fallisce silenziosamente in MD, mentre HTML e AGD la
applicano correttamente perche' indirizzano per `id="findings"` o `[#findings]`.

E' il pattern reale di un workflow multi-agente: gli agenti non condividono
lo stato ricodificato del documento, condividono solo gli ID logici.
Markdown li trasforma in nomi-stringa, e i nomi cambiano.

## Setup

```sh
pip install beautifulsoup4 lxml
# AGD CLI
cargo install --path /Users/pinperepette/Porgetti/MDF2/agd
# (oppure clone https://github.com/Pinperepette/agd e cargo install --path .)
```

## Run

```sh
python3 lab.py
```

L'output va in `output/`:

- `final.md`, `final.html`, `final.agd` — i documenti finali
- `<format>.audit.jsonl` — il log delle ops emesse (audit trail)
- `report.md` — la tabella di confronto, copy-paste-friendly

## Output atteso

```
| metric                     | markdown | html | agd |
|----------------------------|---------:|-----:|----:|
| ops applied (out of 12)    |    11/12 | 12/12 | 12/12 |
| ops not_found              |        1 |    0 |   0 |
| integrity (all items present) |     FAIL | PASS | PASS |
| final file size (bytes)    |      527 |  839 | 707 |
| canonical idempotent       |      yes |  yes | yes |
| avg bytes added per op     |       36 |   45 |  40 |
| avg diff noise             |      1.1 |  2.1 | 1.4 |
| max diff noise             |        3 |    3 |   4 |
```

Markdown e' il piu' compatto e ha i diff piu' puliti, ma rompe l'integrity
sul rename (workflow non-locale). HTML applica tutto ma e' il piu' grande
(+19% vs AGD) e i diff sono piu' rumorosi (2.1 vs 1.4 righe/op). AGD e' il
compromesso: stable ID come HTML, diff line-oriented come Markdown,
canonical form byte-stable.

## Cosa NON c'e' in questo lab (e dove andrebbe)

Il lab e' single-process, sequenziale. La storia architetturale completa
includerebbe **Redis Streams** come canale di ops + un demone (`agdd`) che
applica in ordine FIFO, con `XREADGROUP` per audit trail nativo e ricostruzione
dello stato a un istante T:

```
agents → XADD agd:doc:{id}:ops → agdd → HSET agd:doc:{id}:state
                                  ↓
                                  PUBLISH agd:doc:{id}:changes
```

Quella versione del lab e' v2, con `docker-compose.yml` per Redis 8 e tre
script Python che girano in parallelo. Per il punto del post, la versione
sequenziale e' sufficiente: dimostra le primitive di editing, non la
sincronizzazione distribuita.
