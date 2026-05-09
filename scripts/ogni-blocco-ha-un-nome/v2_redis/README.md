# Lab v2 — Redis Streams, multi-agente reale

Versione del lab dove i tre agenti girano come **processi separati**, emettono
ops a **Redis Streams**, e tre **demoni** (uno per formato) consumano FIFO con
`XREADGROUP`, applicano l'op alla loro versione del documento (Hash key),
fanno `XACK`. Lo stream e' l'audit trail nativo; il replay da `XRANGE 0 +`
ricostruisce lo stato.

Differenza chiave rispetto a `../lab.py` (v1 sequenziale):

- v1: un singolo processo applica le 12 ops in ordine totale artificialmente
- v2: tre processi indipendenti, race condition vera, ordine determinato dal
  broker (Redis), audit trail persistente in stream

## Architettura

```
                      ┌──────────────────────┐
  agent-analyst   ──▶ │                      │
  agent-responder ──▶ │  Redis Streams (3×)  │ ──▶ daemon-md   ──▶ HSET md:state
  agent-auditor   ──▶ │  agd-lab:{md,html,   │ ──▶ daemon-html ──▶ HSET html:state
                      │   agd}:ops           │ ──▶ daemon-agd  ──▶ HSET agd:state
                      └──────────────────────┘
                                                 ↑
                                                 XACK + retention = audit nativo
```

Stessa workload di v1: 12 ops, l'analyst rinomina la sezione `findings` a t=240ms,
l'auditor la appendizza a t=400ms (logical id `findings`, non per nome).

## Cosa misura in piu' rispetto a v1

- **stream length** = lunghezza dell'audit log persistito (deve essere 12)
- **replay reconstructs live state** = `XRANGE 0 + → re-apply su stato iniziale`
  produce lo stesso byte-output dello stato live? Se si', lo stream e'
  authoritative. Se no, il demone ha modificato lo stato in modo non
  deducibile dalle ops.
- **avg apply latency** = costo wallclock per applicare un'op nel demone

## Setup

```sh
# Redis client + parser
pip install redis beautifulsoup4 lxml
# AGD CLI
cargo install --path /Users/pinperepette/Porgetti/MDF2/agd
# Docker
docker --version  # qualunque > 20
```

## Run

```sh
./run_lab.sh
```

Lo script:
1. `docker-compose up -d` (Redis 8 su 127.0.0.1:6391)
2. Inizializza HSET con doc iniziali e crea i consumer group
3. Lancia 3 daemon in background, redirige stdout su `output/daemon-*.stdout`
4. Lancia 3 agent in parallelo
5. Aspetta che gli agent finiscano di emettere
6. Aspetta che i demoni drenino le code (timeout interno 2s di idle)
7. Lancia `--mode compare` che genera `output/report.md`
8. Tear down container

## Output atteso (mediana di 5 run consecutive)

```
| metric                          | markdown | html  | agd |
|---------------------------------|---------:|------:|----:|
| ops applied                      |    11/12 | 12/12 | 12/12 |
| ops not_found                    |        1 |     0 |    0 |
| stream length (audit trail)      |       12 |    12 |   12 |
| replay reconstructs live state   |      yes |   yes |  yes |
| final size (bytes)               |      527 |   895 |  697 |
| avg apply latency                |   118 us | 1.21 ms | 2.3 us |
| throughput (op/sec)              |   ~8.500 |  ~830 | ~430.000 |
```

## Lettura

- **MD perde una op** anche con la concorrenza vera. Stessa causa di v1: il
  rename ha cambiato il nome della sezione, il regex per "## Findings" non
  trova piu' il target. Lo stream registra l'op rifiutata in modo onesto
  (lo `status` nel `daemon-md.log` e' `target_not_found`).
- **HTML applica tutto** — gli `id` resistono al rename.
- **AGD applica tutto** — gli `[#id]` resistono al rename.
- **Replay funziona ovunque**: lo stream e' authoritative. Da `XRANGE 0 +`
  ricostruisco lo stato live, byte-per-byte.
- **Latenza AGD: 2,3 us/op** — il demone `agdd` e' scritto in Rust, parsea
  il documento una sola volta all'avvio, costruisce un `DocumentIndex`
  in memoria, applica ogni op come mutazione strutturale tipata via la
  library API. Niente subprocess, niente fork+exec, niente re-parse.
  Sorgente in `src/bin/agdd.rs` del repo agd (~150 righe). Build con
  `cargo install --path /Users/pinperepette/Porgetti/MDF2/agd`.

  Una versione precedente del lab usava subprocess CLI Python→Rust e
  misurava ~16 ms/op (artefatto del fork+exec ad ogni op). Il fix vero
  era scrivere `agdd` in Rust, non ottimizzare Python.

## File generati

```
output/
├── daemon-md.log         tab-separated: msg_id, agent, kind, target, status, dt_ms
├── daemon-html.log
├── daemon-agd.log
├── daemon-{md,html,agd}.stdout
├── agent-{analyst,responder,auditor}.stdout
├── final.md              stato finale di markdown
├── final.html
├── final.agd
└── report.md             tabella riassuntiva
```

## Variazione: rieseguire

Lo stream e' effimero (Redis senza persistenza). Ad ogni run lo stato viene
azzerato dall'`init`. Per rieseguire piu' volte:

```sh
./run_lab.sh && ./run_lab.sh && ./run_lab.sh
```

L'esito su 3 run: AGD e HTML sempre 12/12, MD sempre 11/12 (deterministico,
perche' il rename arriva sempre prima del late-finding via timing fissato).

## Da notare

- Una versione del lab dove gli agenti emettono **direttamente la nuova
  versione del blocco** (Replace-by-blob) invece di un'op semantica
  esibirebbe il **lost-update problem** classico: due agent appendono allo
  stesso list quasi simultaneamente, vince l'ultimo. Quel pattern e' fuori
  scope qui — il punto e' che gli agent dovrebbero emettere ops semantiche
  (kind/target/payload), non blob, e questa e' una scelta di disciplina che
  il formato puo' incoraggiare ma non imporre.
- Il prossimo passo, fuori scope per la v2 di questo lab, e' integrare il
  nuovo Array type di Redis (PR antirez 15162) per memorizzare lo stato come
  array di blocchi indipendentemente indirizzabili lato server. Quello
  cambierebbe la semantica del demone: non piu' "leggi-modifica-scrivi tutto
  il doc" ma "modifica il singolo blocco lato Redis".
