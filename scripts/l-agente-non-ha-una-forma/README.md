# L'Agente Non Ha Una Forma — Lab

Un assistente di **cucina italiana** costruito su Redis 8 come backbone unico. Tre query, tre **sentieri diversi nel diagramma** dei sette layer agentici. Il punto del lab: dimostrare empiricamente che le frecce del diagramma sono possibilita', non obbligo.

Companion code dell'articolo [L'Agente Non Ha Una Forma](https://pinperepette.github.io/signal.pirate/articoli/l-agente-non-ha-una-forma.html).

## La tesi (in codice)

Il diagramma dell'architettura agentica sembra una pipeline fissa. Non lo e'. Quasi nessuna richiesta attraversa tutti i layer.

| Query | Sentiero | Layer skipped |
|-------|----------|---------------|
| `Cos'e' il soffritto?` | Input → CAG → Output → Guardrail | RAG, KG, Orchestration, Tool, Memory(write) |
| `Convertimi la Carbonara per 6 persone` | Input → CAG → Tool → Output → Guardrail → Memory | RAG, KG, Orchestration |
| `Pattern delle ricette napoletane?` | Input → KG → Orchestration → Output → Guardrail | CAG, RAG, Tool, Memory(write) |

Il demo stampa `PATH` e `SKIPPED` per ogni query: vedi a video quali nodi sono attraversati e quali no.

## I sette layer su un solo backbone

```
Layer 1  INPUT          → query, normalizzazione, classificazione
Layer 2  CONTESTO       → CAG (definizioni base) + RAG (glossario tecniche) + KG (ricette)
Layer 3  ORCHESTRAZIONE → routing deterministico → eventuale multi-agent
Layer 4  TOOL           → get_recipe, convert_servings, shopping_list
Layer 5  OUTPUT         → testo finale per l'utente
Layer 6  GUARDRAIL      → validazione, reflection score, filtri
Layer 7  MEMORIA        → STM (Hash+TTL), LTM (vector BoW), KG (Array Redis)
```

## La novita': Redis Array Type (PR di antirez)

Il modulo `redis_array.py` riproduce le semantiche del nuovo tipo Array proposto da antirez nella [PR #15162](https://github.com/redis/redis/pull/15162) (post: [antirez.com/news/164](https://antirez.com/news/164)).

I tre comandi chiave:

- **ARSET key idx value** — set sparso, niente allocazioni gigantesche
- **ARGREP key pattern** — regex server-side (libreria TRE in nativo)
- **ARINSERT key value** — append con tracking dell'indice ultimo

Il lab usa una classe Python che implementa la stessa API sopra primitive Redis disponibili oggi (Sorted Set + Hash). **Quando il PR atterra in master, sostituisci la classe con i comandi nativi senza toccare il resto del codice.**

### La cornice di antirez (X, 3 maggio 2026)

> "Una cosa da capire sul nuovo tipo Array di Redis e sul supporto di ARGREP e' che puoi memorizzare, nelle chiavi di Redis, diversi documenti markdown (abilita') che vengono utilizzati e aggiornati collettivamente da una **moltitudine di agenti remoti**. Gli agenti possono scoprire documenti tramite KEYS o ARGREP-pando un indice, e poi possono `ARGREP skill.md - + RE foo|bar|zap` e cosi' via."

Nel lab le ricette sono esattamente questo: documenti markdown nel KG, interrogabili via regex. La query 3 fa un `ARGREP "stile:\s*napoletana"` per trovare le tre ricette napoletane fra le sei disponibili.

## Setup

```bash
# 1) Redis 8 via docker
docker compose up -d

# 2) Python deps (Python 3.9+ va bene: niente torch necessario)
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3) API key Anthropic (la mia e' gia' nel .zshrc)
export ANTHROPIC_API_KEY=sk-ant-...

# 4) Run demo
python run_demo.py
```

Output atteso: tre query in sequenza. Per ognuna stampa il `PATH` effettivamente attraversato, i layer `SKIPPED`, le `sources` consultate, i `tools called`, e la risposta dell'agente.

## File

| File | Layer | Cosa fa |
|------|-------|---------|
| `redis_array.py` | infra | Mock dell'Array type di antirez (ARSET/ARGREP/ARINSERT/ARSCAN) |
| `memory.py` | 7 | Short term, long term (vector BoW), KG (Array), cache |
| `context.py` | 2 | Assembly CAG/RAG/KG + entity detection per cucina |
| `tools.py` | 4 | `get_recipe`, `convert_servings`, `shopping_list` |
| `multi_agent.py` | 3 | Researcher (Haiku) + Analyst (Sonnet) per la query analitica |
| `guardrails.py` | 6 | Validazione, reflection, filter PII |
| `agent.py` | 1+3+5 | Routing + orchestrazione + path tracing esplicito |
| `seed_corpus.py` | seed | Glossario di tecniche per il RAG (5 voci) |
| `seed_kg.py` | seed | Sei ricette per il KG (3 romane, 3 napoletane) |
| `run_demo.py` | demo | Tre query con form trace visibile |

## Modelli usati

- **Sonnet 4.6** (`claude-sonnet-4-6`): tutte le chiamate principali e l'analyst del multi-agent
- **Haiku 4.5** (`claude-haiku-4-5-20251001`): il researcher del multi-agent (estrazione fatti, low-cost)

## Limiti dichiarati

- Il PR #15162 non e' merged: le latenze di `ARGREP` mockato saranno peggiori del nativo.
- Il routing deterministico funziona per il dominio cucina; cambiando dominio (legale, medico, finanza...) le euristiche vanno riadattate.
- `VectorMemory` usa bag-of-words via numpy invece di sentence-transformers, per evitare dipendenze pesanti su Python 3.9 / Intel macOS. Per uso serio si swappa con un encoder vero o (meglio) con Redis Vector Set + HNSW nativo.
- "Memoria" non e' "apprendimento": i pesi del LLM non cambiano, l'agente ricorda nel senso letterale.

## Riferimenti

- [antirez.com/news/164](https://antirez.com/news/164) — il post che annuncia l'Array type
- [PR #15162](https://github.com/redis/redis/pull/15162) — il pull request
- [redis.io/blog/long-term-memory-architectures-ai-agents](https://redis.io/blog/long-term-memory-architectures-ai-agents/) — l'architettura di memoria
- [github.com/redis/agent-memory-server](https://github.com/redis/agent-memory-server) — il memory server di Redis
