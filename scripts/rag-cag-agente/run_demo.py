"""
Demo — 3 query, 3 route distinti:

  1. CAG-only      → "Cos'è il credential stuffing?"
                     fast path, zero tool, risposta da knowledge base

  2. CAG + Stream  → "Analizza il traffico corrente"
                     stream trigger attivo, routing cambia dinamicamente

  3. CAG + RAG + MCP → "CVE-2024-6387: analisi e remediation"
                        retrieval corpus + tool NVD reale
"""

import json
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

from agent import CognitiveAgent
from rich.console import Console
from rich.rule import Rule

console = Console()

QUERIES = [
    "Cos'è il credential stuffing e come si distingue da un brute force classico?",
    "Analizza il traffico di rete corrente: ci sono segnali di attacco in corso?",
    "CVE-2024-6387: analisi della vulnerabilità, impatto reale e piano di remediation.",
]


def main():
    console.print()
    console.print(Rule(
        "[bold cyan]COGNITIVE AGENT  ·  RAG + CAG + PLAN + REFLECT[/bold cyan]"
    ))
    console.print()

    agent = CognitiveAgent(
        knowledge_path="knowledge/core.json",
        corpus_path="corpus/",
        memory_path="output/memory.json",
    )

    # warm-up stream: aspetta che si popoli con eventi normali
    console.print("[dim]stream warm-up (2s)...[/dim]")
    time.sleep(2)

    results = []

    # ── Query 1: CAG-only (fast path) ─────────────────────────────────────────
    console.print(Rule("[dim]query 1/3 — atteso: CAG-only[/dim]"))
    results.append(agent.query(QUERIES[0]))
    time.sleep(0.5)

    # ── Query 2: CAG + Stream (trigger attacco prima della query) ─────────────
    console.print(Rule("[dim]query 2/3 — atteso: CAG+STREAM (attacco attivo)[/dim]"))
    console.print("[dim red]→ trigger attacco stream...[/dim red]")
    agent.stream.trigger_attack()
    time.sleep(0.8)   # lascia al thread di generare eventi attacco
    results.append(agent.query(QUERIES[1]))
    agent.stream.reset_attack()
    time.sleep(0.5)

    # ── Query 3: CAG + RAG + MCP ──────────────────────────────────────────────
    console.print(Rule("[dim]query 3/3 — atteso: CAG+RAG+MCP (CVE lookup reale)[/dim]"))
    results.append(agent.query(QUERIES[2]))

    agent.shutdown()

    # ── Salva trace ───────────────────────────────────────────────────────────
    out = Path("output/trace.json")
    out.parent.mkdir(exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # ── Riepilogo finale ──────────────────────────────────────────────────────
    console.print()
    console.print(Rule("[bold green]RIEPILOGO[/bold green]"))
    console.print()
    for i, r in enumerate(results, 1):
        score  = r["reflection"].get("score", "?")
        color  = "green" if isinstance(score, int) and score >= 7 else "red"
        tools  = ", ".join(t["tool"] for t in r["tools_used"]) or "—"
        stream = f"stream:{r['stream_events']}" if r["stream_events"] else "no-stream"
        console.print(
            f"  {i}. [{color}]{score}/10[/{color}]  "
            f"[dim]{r['route']}[/dim]  "
            f"{r['elapsed_s']}s  "
            f"tool:{tools}  {stream}\n"
            f"     {r['query'][:70]}..."
        )

    console.print()
    console.print(f"[dim]trace completa → {out}[/dim]")
    console.print(f"[dim]memoria persistente → output/memory.json[/dim]")


if __name__ == "__main__":
    main()
