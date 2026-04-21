"""
Demo autonomo — nessuna query umana.

L'agente monitora il PCAP reale (AngstromCTF 2016, Metasploitable),
rileva l'attack chain autonomamente e produce un incident report completo.

Attack chain nel PCAP:
  1. POST /wp-admin/admin-post.php (MailPoet plugin exploit, file upload)
  2. GET  /wp-content/uploads/wysija/themes/.../shell.php (webshell deployed)
  3. TCP  192.168.1.7 → 192.168.1.13:4444 (Metasploit reverse shell C2)

L'agente non viene mai interrogato direttamente —
decide da solo quando alertare e cosa includere nel report.
"""

import json
import os
import time
import warnings
from pathlib import Path

os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore")

import anthropic
import numpy as np
from sentence_transformers import SentenceTransformer
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich import box

from pcap_stream import PCAPStream
from meta_controller import MetaController, Route, RoutingDecision
from memory_manager import MemoryManager
from tools import TOOL_SCHEMAS, execute_tool

console = Console()
MODEL  = "claude-sonnet-4-6"
EMBED  = "paraphrase-multilingual-MiniLM-L12-v2"
TSHARK_PATH = "/Applications/Wireshark.app/Contents/MacOS/tshark"
PCAP   = "pcaps/metasploitable.pcap"


def load_cag(path: str = "knowledge/core.json") -> str:
    with open(path, encoding="utf-8") as f:
        k = json.load(f)
    parts = []
    if "core_concepts" in k:
        lines = "\n".join(f"  • {key}: {val}" for key, val in k["core_concepts"].items())
        parts.append(f"## CONOSCENZA CORE (CAG)\n{lines}")
    if "compressed_memory" in k:
        parts.append(f"## MEMORIA COMPRESSA\n{k['compressed_memory']}")
    return "\n\n".join(parts)


def build_rag_index(corpus_path: str = "corpus/", encoder=None):
    from pathlib import Path
    docs = []
    for p in Path(corpus_path).rglob("*.txt"):
        text = p.read_text(encoding="utf-8")
        rel  = p.relative_to(corpus_path)
        src  = str(rel.parent / rel.stem) if rel.parent.name != "." else rel.stem
        for chunk in [c.strip() for c in text.split("\n\n") if len(c.strip()) > 80]:
            docs.append({"source": src, "text": chunk})
    if not docs:
        return [], None
    embs = encoder.encode([d["text"] for d in docs], show_progress_bar=False, batch_size=64)
    return docs, embs


def retrieve(query: str, docs, embeddings, encoder, top_k: int = 8) -> list[dict]:
    if embeddings is None:
        return []
    q = encoder.encode([query])
    norms = np.linalg.norm(embeddings, axis=1) * np.linalg.norm(q) + 1e-8
    scores = (embeddings @ q.T).flatten() / norms
    idx = np.argsort(scores)[::-1][:top_k]
    return [
        {**docs[i], "score": float(scores[i])}
        for i in idx if scores[i] > 0.28
    ]


def generate_incident_report(
    client, cag_ctx: str, rag_docs: list,
    stream_summary: dict, pcap_events: list
) -> tuple[str, list]:
    """Genera il report di incidente usando tutti e 4 i layer."""
    import re

    rag_block = "\n\n---\n\n".join(
        f"[{d['source']} | sim {d['score']:.2f}]\n{d['text']}"
        for d in rag_docs
    ) if rag_docs else ""

    # formatta gli eventi attacco per il report
    attack_events = [e for e in pcap_events if e.get("attack_type") != "normal"]
    events_block  = json.dumps(attack_events, indent=2, ensure_ascii=False)

    system = f"""Sei un analista SOC senior. Hai appena ricevuto un alert: attacco rilevato su un host interno.

{cag_ctx}

Hai tool per interrogare CVE reali (NVD) e cercare informazioni su exploit e infrastrutture esposte.
Investigali come faresti in un vero incidente — raccogliendo prove prima di concludere.

Il report finale deve essere usabile da un SOC analyst: severity reale, IOC concreti, azioni immediate."""

    content = [
        {"type": "text", "text": (
            f"PCAP analizzato: {PCAP}\n\n"
            f"STREAM SUMMARY:\n{json.dumps(stream_summary, indent=2)}\n\n"
            f"EVENTI ATTACCO RILEVATI ({len(attack_events)}):\n{events_block}"
        )}
    ]
    if rag_block:
        content.append({"type": "text", "text": f"\n\nDocumenti RAG pertinenti:\n{rag_block}"})

    messages   = [{"role": "user", "content": content}]
    tools_used = []

    for _ in range(8):
        resp = client.messages.create(
            model=MODEL, max_tokens=4000,
            system=system,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )

        if resp.stop_reason == "end_turn":
            text = "".join(b.text for b in resp.content if hasattr(b, "text"))
            return text, tools_used

        if resp.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": resp.content})
            results = []
            for block in resp.content:
                if block.type == "tool_use":
                    console.print(f"[dim magenta]  ⚙ {block.name}({json.dumps(block.input)[:80]})[/dim magenta]")
                    result = execute_tool(block.name, block.input)
                    tools_used.append({"tool": block.name, "input": block.input, "result": result})
                    console.print(f"[dim]    → {str(result)[:140]}[/dim]")
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    })
            messages.append({"role": "user", "content": results})
        else:
            text = "".join(b.text for b in resp.content if hasattr(b, "text"))
            return text, tools_used

    return "Errore: max round-trip.", []


def main():
    console.print(Rule("[bold cyan]INCIDENT MONITOR — PCAP REALE · AUTONOMOUS MODE[/bold cyan]"))
    console.print(f"[dim]PCAP: {PCAP} (AngstromCTF 2016 — Metasploitable)[/dim]")

    # ── init ──────────────────────────────────────────────────────────────────
    client  = anthropic.Anthropic()
    encoder = SentenceTransformer(EMBED)
    memory  = MemoryManager("output/memory.json", encoder)
    memory.apply_decay()

    console.print("[dim]building RAG index...[/dim]", end=" ")
    docs, embeddings = build_rag_index("corpus/", encoder)
    console.print(f"[dim]{len(docs)} chunk — ok[/dim]")

    cag_ctx = load_cag()

    # ── PCAP stream ───────────────────────────────────────────────────────────
    stream = PCAPStream(PCAP, replay_speed=50.0)
    stream.load()
    stream.start()

    # ── watch loop: aspetta che l'attacco emerga ──────────────────────────────
    console.print(Rule("[bold yellow]MONITORING[/bold yellow]"))
    all_events = []
    t_start    = time.time()
    alerted    = False

    while not alerted:
        time.sleep(0.2)
        batch = stream.drain(max_events=50)
        all_events.extend(batch)

        attack_evs = [e for e in all_events if e.get("attack_type") != "normal"]

        if batch:
            types = set(e.get("attack_type") for e in batch if e.get("attack_type") != "normal")
            for t in types:
                ev = next(e for e in batch if e.get("attack_type") == t)
                loc = ev.get("uri") or f":{ev.get('dport', '')}"
                console.print(
                    f"[dim]{ev['ts']:6.3f}s[/dim]  "
                    f"[bold red]{t}[/bold red]  "
                    f"[dim]{ev.get('src')} → {ev.get('dst')}  {loc}[/dim]"
                )

        # triggera quando vediamo c2_connection (attack chain completa)
        c2_seen = any(e["attack_type"] == "c2_connection" for e in all_events)
        if c2_seen:
            elapsed = time.time() - t_start
            console.print(Panel(
                f"[bold red]ATTACK CHAIN COMPLETA RILEVATA[/bold red]  "
                f"elapsed:{elapsed:.2f}s  events:{len(all_events)}  attacks:{len(attack_evs)}",
                border_style="red", padding=(0, 1)
            ))
            alerted = True

        # safety: se il PCAP è finito
        if time.time() - t_start > 30:
            console.print("[dim]PCAP esaurito[/dim]")
            break

    stream.stop()
    summary = stream.summary()

    # ── show summary ──────────────────────────────────────────────────────────
    t = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    t.add_column("Campo")
    t.add_column("Valore")
    t.add_row("PCAP events totali",  str(summary["total_events"]))
    t.add_row("Attack events",       str(summary["attack_events"]))
    t.add_row("Attack types",        str(summary["attack_types"]))
    t.add_row("MITRE hints",         ", ".join(summary["mitre_hints"]))
    t.add_row("Attacker IPs",        ", ".join(summary["attacker_ips"]))
    t.add_row("C2 ports",            ", ".join(summary["c2_ports"]) or "—")
    console.print(t)

    # ── RAG: cerca contesto MITRE + CVE correlate ─────────────────────────────
    console.print(Rule("[bold yellow]RAG + MCP[/bold yellow]"))

    rag_query = (
        f"WordPress plugin file upload exploit webshell reverse shell Meterpreter "
        f"MITRE {' '.join(summary['mitre_hints'])} "
        f"MailPoet wysija CVE arbitrary file upload"
    )
    rag_docs = retrieve(rag_query, docs, embeddings, encoder)
    srcs = set(d["source"] for d in rag_docs)
    console.print(f"[dim green]RAG:[/dim green] {len(rag_docs)} chunk | {', '.join(srcs)}")

    # ── genera incident report ────────────────────────────────────────────────
    console.print(Rule("[bold yellow]INCIDENT REPORT[/bold yellow]"))
    console.print("[dim]generazione...[/dim]")

    t0     = time.time()
    report, tools_used = generate_incident_report(
        client, cag_ctx, rag_docs, summary, all_events
    )
    elapsed = time.time() - t0

    # ── output ────────────────────────────────────────────────────────────────
    console.print(Panel(report, title="[bold red]INCIDENT REPORT[/bold red]", border_style="red"))

    t2 = Table(box=box.SIMPLE, show_header=False, padding=(0,1))
    t2.add_column("k", style="dim", width=22)
    t2.add_column("v")
    t2.add_row("PCAP sorgente",  PCAP)
    t2.add_row("Tool usati",     ", ".join(x["tool"] for x in tools_used) or "—")
    t2.add_row("RAG fonti",      ", ".join(srcs))
    t2.add_row("Tempo report",   f"{elapsed:.1f}s")
    t2.add_row("Memory stats",   str(memory.stats()))
    console.print(t2)

    # ── salva ─────────────────────────────────────────────────────────────────
    out = Path("output/incident_report.json")
    out.parent.mkdir(exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({
            "pcap":        PCAP,
            "summary":     summary,
            "rag_sources": list(srcs),
            "tools_used":  tools_used,
            "report":      report,
            "elapsed_s":   round(elapsed, 2),
        }, f, indent=2, ensure_ascii=False)

    console.print(f"[dim]report salvato → {out}[/dim]")
    console.print(Rule("[bold green]FINE[/bold green]"))


if __name__ == "__main__":
    main()
