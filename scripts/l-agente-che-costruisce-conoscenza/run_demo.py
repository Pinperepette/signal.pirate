"""
Demo — costruzione conoscenza nel tempo (query reali via API):

  Query 1: CVE-2024-6387  → agente risponde, wiki crea note + link
  Query 2: CVE-2024-3094  → agente risponde, wiki collega al grafo
  Query 3: pattern OpenSSH → routing CAG_WIKI, bypassa RAG

Richiede: ANTHROPIC_API_KEY, sentence-transformers, rich
"""

import json
import time
import shutil
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule
from rich import box

from agent_wiki import CognitiveAgentV2

console = Console()

QUERIES = [
    "CVE-2024-6387: analisi della vulnerabilita', impatto reale e piano di remediation.",
    "CVE-2024-3094: analisi backdoor xz-utils e impatto su OpenSSH.",
    "Pattern di attacco ricorrenti su OpenSSH: cosa sappiamo dalle analisi precedenti?",
]


def show_wiki_state(agent, title: str = "STATO WIKI"):
    wiki = agent.wiki
    console.print()
    console.print(Rule(f"[bold yellow]{title}[/bold yellow]"))

    stats = wiki.stats()
    t = Table(box=box.ROUNDED, show_header=True, title="Wiki Stats")
    t.add_column("Metrica", style="dim")
    t.add_column("Valore", style="bold")
    t.add_row("Note totali", str(stats["total_notes"]))
    t.add_row("Link totali", str(stats["total_links"]))
    t.add_row("Tag unici", str(stats["total_tags"]))
    t.add_row("Link medi/nota", str(stats["avg_links"]))
    if stats["most_linked"]:
        t.add_row("Piu' collegata", stats["most_linked"])
    console.print(t)

    graph = wiki.get_graph()
    if graph["nodes"]:
        console.print()
        console.print("[bold]Grafo:[/bold]")
        for node in graph["nodes"]:
            tags = " ".join(f"[dim]#{tg}[/dim]" for tg in node["tags"])
            console.print(f"  [cyan]{node['id']}[/cyan] ({node['type']}) {tags}")
        for edge in graph["edges"]:
            console.print(f"    [dim]{edge['from']}[/dim] → [green]{edge['to']}[/green]")


def show_note_detail(agent, title: str):
    note = agent.wiki.get_note(title)
    if not note:
        return
    console.print(Panel(
        note.to_markdown(),
        title=f"[bold cyan]{title}[/bold cyan]",
        border_style="cyan", width=80,
    ))


def main():
    console.print()
    console.print(Rule(
        "[bold cyan]L'AGENTE CHE COSTRUISCE CONOSCENZA  ·  WIKI LAYER DEMO[/bold cyan]"
    ))
    console.print()

    out = Path("output")
    wiki_path = out / "wiki"
    if wiki_path.exists():
        shutil.rmtree(wiki_path)

    parent_lab = Path(__file__).parent.parent / "rag-cag-agente"
    corpus_path = parent_lab / "corpus"

    agent = CognitiveAgentV2(
        knowledge_path="knowledge/core.json",
        corpus_path=str(corpus_path) if corpus_path.exists() else None,
        memory_path=str(out / "memory.json"),
        wiki_path=str(wiki_path),
    )

    time.sleep(2)
    results = []

    # ── Query 1: CVE-2024-6387 ────────────────────────────────────────────────
    console.print(Rule("[bold red]QUERY 1/3 — CVE-2024-6387[/bold red]"))
    r = agent.query(QUERIES[0])
    results.append(r)
    show_wiki_state(agent, "WIKI DOPO QUERY 1")
    if r["wiki_notes_created"]:
        show_note_detail(agent, r["wiki_notes_created"][0])
    time.sleep(1)

    # ── Query 2: CVE-2024-3094 ────────────────────────────────────────────────
    console.print(Rule("[bold red]QUERY 2/3 — CVE-2024-3094 (xz backdoor)[/bold red]"))
    r = agent.query(QUERIES[1])
    results.append(r)

    for _ in range(3):
        agent.wiki.get_note("OpenSSH")

    show_wiki_state(agent, "WIKI DOPO QUERY 2")
    if r["wiki_notes_created"]:
        show_note_detail(agent, r["wiki_notes_created"][0])
    if "OpenSSH" in agent.wiki.notes:
        show_note_detail(agent, "OpenSSH")
    time.sleep(1)

    # ── Query 3: pattern OpenSSH → atteso CAG_WIKI ────────────────────────────
    agent.stream.reset_attack()
    agent.stream.drain(max_events=50)
    console.print(Rule("[bold red]QUERY 3/3 — PATTERN OpenSSH (atteso: CAG_WIKI)[/bold red]"))
    r = agent.query(QUERIES[2])
    results.append(r)

    # confronto
    console.print()
    console.print(Panel(
        "Memory episodica:\n"
        f"  Q: {QUERIES[0][:50]}... [score {results[0]['reflection'].get('score','?')}/10]\n"
        f"  Q: {QUERIES[1][:50]}... [score {results[1]['reflection'].get('score','?')}/10]\n\n"
        "→ Due entry separate. Nessun collegamento.\n"
        "  Per correlare serve RAG da zero.",
        title="[bold red]SENZA WIKI[/bold red]",
        border_style="red",
    ))

    linked = agent.wiki.get_linked_context("OpenSSH", depth=1)
    linked_titles = [l.title for l in linked]
    openssh_note = agent.wiki.notes.get("OpenSSH")
    console.print(Panel(
        f"Wiki search: 'pattern attacco OpenSSH'\n"
        f"Hit: OpenSSH (accessi: {openssh_note.access_count if openssh_note else 0})\n\n"
        f"Grafo da OpenSSH (depth=1):\n"
        + "\n".join(f"  → {t}" for t in linked_titles) + "\n\n"
        f"→ Contesto strutturato, zero RAG.\n"
        f"  Route: {r['route']}",
        title="[bold green]CON WIKI[/bold green]",
        border_style="green",
    ))

    promoted = agent.knowledge.maybe_promote_to_cag()
    if promoted:
        console.print(f"[bold cyan]Promossi a CAG: {', '.join(promoted)}[/bold cyan]")

    show_wiki_state(agent, "WIKI FINALE")

    agent.shutdown()

    # ── Riepilogo ─────────────────────────────────────────────────────────────
    console.print()
    console.print(Rule("[bold green]RIEPILOGO[/bold green]"))
    for i, r in enumerate(results, 1):
        score = r["reflection"].get("score", "?")
        color = "green" if isinstance(score, int) and score >= 7 else "red"
        console.print(
            f"  {i}. [{color}]{score}/10[/{color}]  "
            f"[dim]{r['route']}[/dim]  {r['elapsed_s']}s  "
            f"wiki:{r['wiki_total']}  "
            f"notes:{','.join(r['wiki_notes_created']) or '—'}\n"
            f"     {r['query'][:70]}..."
        )

    kstats = agent.knowledge.promotion_stats()
    t = Table(box=box.ROUNDED, show_header=True, title="Knowledge Layer Stats")
    t.add_column("Metrica", style="dim")
    t.add_column("Valore", style="bold")
    t.add_row("Promozioni totali", str(kstats["total_promotions"]))
    for direction, count in kstats["directions"].items():
        t.add_row(f"  {direction}", str(count))
    t.add_row("Note wiki", str(kstats["wiki_notes"]))
    t.add_row("Concetti CAG", str(kstats["cag_concepts"]))
    console.print(t)

    trace = {
        "results": results,
        "wiki_stats": agent.wiki.stats(),
        "knowledge_stats": kstats,
        "graph": agent.wiki.get_graph(),
    }
    trace_path = out / "trace.json"
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(trace, f, indent=2, ensure_ascii=False, default=str)

    console.print()
    console.print(f"[dim]trace → {trace_path}[/dim]")
    console.print(f"[dim]wiki vault → {wiki_path}/[/dim]")


if __name__ == "__main__":
    main()
