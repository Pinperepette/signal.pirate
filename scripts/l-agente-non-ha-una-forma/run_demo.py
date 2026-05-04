"""Demo: stesso agente, tre sentieri diversi nel diagramma.

Tre query in cucina italiana. Per ognuna stampiamo a video il PATH
effettivamente attraversato e i layer SALTATI, in modo che si veda a
occhio che il "diagramma completo" non e' la pipeline reale.

  Query 1 (knowledge)   INPUT → CAG → OUTPUT → GUARDRAIL
  Query 2 (operational) INPUT → CAG → TOOL → OUTPUT → GUARDRAIL → MEMORY
  Query 3 (analytic)    INPUT → KG → ORCHESTRATION → OUTPUT → GUARDRAIL

Uso:
    docker compose up -d
    export ANTHROPIC_API_KEY=...     (gia' nell'env in zsh)
    python run_demo.py
"""
from __future__ import annotations

import os
import sys
import time

import redis

from agent import Agent
from memory import Memory
from seed_corpus import seed as seed_rag
from seed_kg import seed as seed_kg


SESSION_ID = "demo-cucina"
QUERIES = [
    ("Cos'è il soffritto?", "knowledge"),
    ("Convertimi la ricetta della Carbonara per 6 persone", "operational"),
    ("Quali pattern hanno in comune le ricette napoletane tradizionali?", "analytic"),
]


def header(s: str) -> str:
    return "\n" + "═" * 76 + f"\n{s}\n" + "═" * 76


def main() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("[errore] ANTHROPIC_API_KEY non impostata", file=sys.stderr)
        return 1

    r = redis.Redis(host="127.0.0.1", port=6379)
    try:
        r.ping()
    except redis.ConnectionError:
        print("[errore] Redis non raggiungibile su 127.0.0.1:6379", file=sys.stderr)
        print("        avvia con: docker compose up -d", file=sys.stderr)
        return 1

    print(header("L'AGENTE NON HA UNA FORMA · DEMO"))
    print("Backbone : Redis 8.x (Array type mock per il KG)")
    print("Modelli  : claude-sonnet-4-6 (main), claude-haiku-4-5 (researcher)")
    print(f"Sessione : {SESSION_ID}")
    print("Dominio  : cucina italiana — tre sentieri nel diagramma")

    mem = Memory.build(r, SESSION_ID)

    # seed RAG (glossario tecniche) e KG (sei ricette)
    n_rag = seed_rag(mem.ltm)
    print(f"\n[seed RAG] {n_rag} voci di glossario nel vector store")
    n_kg = seed_kg(mem.kg)
    print(f"[seed KG ] {n_kg} ricette nel KG (Array Redis via ARGREP)")

    agent = Agent(mem)

    for i, (q, hint) in enumerate(QUERIES, start=1):
        print(header(f"QUERY {i} ({hint}): {q}"))
        t0 = time.time()
        trace = agent.ask(q)
        dt = time.time() - t0

        print("\n--- form trace ---")
        print(trace.render())
        print(f"  latenza      : {dt:.2f}s")

        print("\n--- risposta ---")
        print(trace.answer)
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
