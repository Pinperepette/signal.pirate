"""
CognitiveAgentV2 — pipeline completa con Wiki layer:

  META-CONTROLLER → CAG ↔ WIKI ↔ RAG → TOOLS → REFLECTION → MEMORY → WIKI update

Differenza dal V1: il wiki si inserisce tra CAG e RAG.
Se il concetto e' gia' nel wiki, il RAG viene bypassato.
Dopo ogni risposta con score >= 7, la conoscenza va nel wiki.
"""

import json
import re
import time
from pathlib import Path

import anthropic
import numpy as np
from sentence_transformers import SentenceTransformer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from meta_controller_v2 import MetaControllerV2, Route
from wiki_manager import WikiManager
from knowledge_layer import KnowledgeLayer

import sys
_parent = str(Path(__file__).parent.parent / "rag-cag-agente")
sys.path.insert(0, _parent)
from memory_manager import MemoryManager
from stream_simulator import StreamSimulator
from tools import TOOL_SCHEMAS, execute_tool

console = Console()

MODEL      = "claude-sonnet-4-6"
EMBED      = "paraphrase-multilingual-MiniLM-L12-v2"
RAG_THRESH = 0.28


class CognitiveAgentV2:

    def __init__(self,
                 knowledge_path: str = "knowledge/core.json",
                 corpus_path:    str = None,
                 memory_path:    str = "output/memory.json",
                 wiki_path:      str = "output/wiki"):

        self.client  = anthropic.Anthropic()
        self.encoder = SentenceTransformer(EMBED)

        self.wiki      = WikiManager(wiki_path, self.encoder)
        self.memory    = MemoryManager(memory_path, self.encoder)
        self.knowledge = KnowledgeLayer(self.wiki, knowledge_path)

        self.cag_base = self.knowledge.cag_data

        self.docs, self.embeddings = [], None
        if corpus_path and Path(corpus_path).exists():
            self.docs, self.embeddings = self._build_index(corpus_path)

        self.controller = MetaControllerV2(
            self.client,
            wiki_checker=self.knowledge.concept_in_wiki
        )

        self.stream = StreamSimulator()
        self.memory.apply_decay()
        self.stream.start()
        console.print("[dim]stream avviato[/dim]")

    # -- CAG ------------------------------------------------------------------

    def _build_cag_context(self) -> str:
        k = self.cag_base
        parts = []
        if "core_concepts" in k:
            lines = "\n".join(f"  - {key}: {val}"
                              for key, val in k["core_concepts"].items())
            parts.append(f"## CONOSCENZA CORE (CAG)\n{lines}")
        if "compressed_memory" in k:
            parts.append(f"## MEMORIA COMPRESSA\n{k['compressed_memory']}")
        learned = self.memory.get_semantic_context()
        if learned:
            parts.append(learned)
        episodic = self.memory.get_episodic_summary()
        if episodic:
            parts.append(episodic)
        return "\n\n".join(parts)

    # -- RAG ------------------------------------------------------------------

    def _build_index(self, corpus_path: str):
        docs = []
        for p in Path(corpus_path).rglob("*.txt"):
            text = p.read_text(encoding="utf-8")
            rel = p.relative_to(corpus_path)
            source = str(rel.parent / rel.stem) if rel.parent.name != "." else rel.stem
            chunks = [c.strip() for c in text.split("\n\n") if len(c.strip()) > 80]
            for chunk in chunks:
                docs.append({"source": source, "text": chunk})
        if not docs:
            return [], None
        console.print(f"[dim]RAG index: {len(docs)} chunk[/dim]")
        embs = self.encoder.encode(
            [d["text"] for d in docs], show_progress_bar=False, batch_size=64
        )
        return docs, embs

    def _retrieve(self, query: str, top_k: int = 6) -> list[dict]:
        if self.embeddings is None:
            return []
        q = self.encoder.encode([query])
        norms = np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(q) + 1e-8
        scores = (self.embeddings @ q.T).flatten() / norms
        idx = np.argsort(scores)[::-1][:top_k]
        return [
            {**self.docs[i], "score": float(scores[i])}
            for i in idx if scores[i] > RAG_THRESH
        ]

    # -- STREAM ---------------------------------------------------------------

    def _analyze_stream(self, events: list[dict]) -> str:
        if not events:
            return ""
        from collections import Counter
        types = Counter(e.get("type") for e in events)
        statuses = Counter(e.get("status") for e in events if "status" in e)
        lines = [
            f"## ANALISI STREAM ({len(events)} eventi)",
            f"Tipi: {dict(types)}",
            f"Status: {dict(statuses)}",
        ]
        return "\n".join(lines)

    # -- GENERATION -----------------------------------------------------------

    def _generate(self, query: str, cag_ctx: str, wiki_ctx: str,
                  rag_docs: list, stream_events: list, route: Route) -> tuple[str, list]:

        rag_block = "\n\n---\n\n".join(
            f"[fonte: {d['source']} | sim: {d['score']:.2f}]\n{d['text']}"
            for d in rag_docs
        ) if rag_docs else ""

        stream_block = self._analyze_stream(stream_events) if stream_events else ""

        system = f"""Sei un agente cognitivo specializzato in sicurezza informatica.

{cag_ctx}

{wiki_ctx}

Regole:
- Rispondi in italiano, tono tecnico e diretto
- Distingui CAG (pre-caricata), WIKI (strutturata), RAG (recuperata ora)
- Se usi conoscenza dal wiki, dillo esplicitamente
- Usa i tool quando servono dati reali
- Non inventare dati"""

        user_content = [{"type": "text", "text": f"Query: {query}"}]
        if rag_block:
            user_content.append({"type": "text", "text": f"\n\nDocumenti RAG:\n{rag_block}"})
        if stream_block:
            user_content.append({"type": "text", "text": f"\n\n{stream_block}"})

        messages = [{"role": "user", "content": user_content}]
        tools_used = []
        use_tools = route in (Route.CAG_RAG_MCP, Route.FULL)

        for _ in range(6):
            resp = self.client.messages.create(
                model=MODEL, max_tokens=1500, system=system,
                tools=TOOL_SCHEMAS if use_tools else [],
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
                        console.print(
                            f"[dim magenta]  tool: {block.name}("
                            f"{json.dumps(block.input)[:80]})[/dim magenta]"
                        )
                        result = execute_tool(block.name, block.input)
                        tools_used.append({
                            "tool": block.name, "input": block.input, "result": result,
                        })
                        results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result, ensure_ascii=False),
                        })
                messages.append({"role": "user", "content": results})
            else:
                text = "".join(b.text for b in resp.content if hasattr(b, "text"))
                return text, tools_used

        return "Errore: max round-trip raggiunto.", tools_used

    # -- REFLECTION -----------------------------------------------------------

    def _reflect(self, query: str, answer: str, rag_docs: list) -> dict:
        resp = self.client.messages.create(
            model=MODEL, max_tokens=300,
            system=(
                "Valuta la risposta. Rispondi SOLO con JSON valido:\n"
                '{"score": <0-10>, '
                '"rag_useful": <bool>, '
                '"would_fail_without_rag": <bool>, '
                '"lacune": ["..."], '
                '"punti_forti": ["..."]}'
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"Query: {query}\n\nRisposta:\n{answer}\n\n"
                    f"Documenti RAG usati: {len(rag_docs)}"
                )
            }]
        )
        try:
            m = re.search(r'\{.*?\}', resp.content[0].text, re.DOTALL)
            if m:
                return json.loads(m.group())
        except Exception:
            pass
        return {"score": 7, "rag_useful": bool(rag_docs),
                "would_fail_without_rag": False, "lacune": [], "punti_forti": []}

    # -- MAIN LOOP ------------------------------------------------------------

    def query(self, question: str) -> dict:
        t0 = time.time()
        console.print()
        console.print(Panel(
            f"[bold white]{question}[/bold white]",
            title="[bold cyan]QUERY[/bold cyan]", border_style="cyan"
        ))

        stream_events = self.stream.drain(max_events=20)
        decision = self.controller.route(question, self.stream.attack_active)

        _COLORS = {
            "cag_only": "white", "cag_wiki": "yellow",
            "cag_stream": "blue", "cag_rag": "green",
            "cag_rag_mcp": "magenta", "full": "red",
        }
        rc = _COLORS.get(decision.route.value, "white")
        console.print(
            f"[dim][ META ][/dim]  "
            f"route: [bold {rc}]{decision.route.value}[/bold {rc}]  "
            f"confidence: {decision.confidence:.0%}  "
            f"metodo: [italic]{decision.method}[/italic]  "
            f"→ {decision.reason}"
        )

        cag_ctx = self._build_cag_context()

        # WIKI layer
        wiki_ctx = ""
        if decision.route in (Route.CAG_WIKI, Route.FULL):
            wiki_ctx = self.knowledge.get_wiki_context(question)
            if wiki_ctx:
                n_notes = wiki_ctx.count("###")
                console.print(
                    f"[dim yellow][ WIKI ][/dim yellow]  "
                    f"{n_notes} note trovate nel grafo"
                )

        # RAG
        rag_docs = []
        if decision.route in (Route.CAG_RAG, Route.CAG_RAG_MCP, Route.FULL):
            rag_docs = self._retrieve(question)
            console.print(
                f"[dim green][ RAG ][/dim green]   "
                f"{len(rag_docs)} chunk"
            )

        # Stream
        active_stream: list[dict] = []
        if decision.route in (Route.CAG_STREAM, Route.FULL):
            active_stream = stream_events
            console.print(
                f"[dim blue][ STREAM ][/dim blue] {len(active_stream)} eventi"
            )

        # Generate
        console.print("[dim magenta][ GEN ][/dim magenta]   generazione...")
        answer, tools_used = self._generate(
            question, cag_ctx, wiki_ctx, rag_docs, active_stream, decision.route
        )

        # Reflection
        reflection = self._reflect(question, answer, rag_docs)
        score = reflection.get("score", 0)
        sc = "green" if score >= 7 else "yellow" if score >= 5 else "red"
        console.print(
            f"[dim][ REFLECT ][/dim] score: [bold {sc}]{score}/10[/bold {sc}]"
        )

        # Memory update
        self.memory.add_episodic({
            "query": question, "route": decision.route.value,
            "score": score,
            "rag_useful": reflection.get("rag_useful", False),
            "would_fail_without_rag": reflection.get("would_fail_without_rag", False),
            "tools_used": [t["tool"] for t in tools_used],
        })

        # WIKI update (il pezzo nuovo)
        wiki_notes = self.knowledge.maybe_promote_to_wiki(
            question, answer, reflection, rag_docs
        )
        if wiki_notes:
            titles = [n.title for n in wiki_notes]
            console.print(
                f"[dim yellow][ WIKI+ ][/dim yellow] "
                f"note create/aggiornate: {', '.join(titles)}"
            )

        # Check promozione wiki → CAG
        promoted = self.knowledge.maybe_promote_to_cag()
        if promoted:
            console.print(
                f"[dim cyan][ PROMO ][/dim cyan] wiki→CAG: {', '.join(promoted)}"
            )

        elapsed = time.time() - t0

        console.print(Panel(answer, title="[bold green]RISPOSTA[/bold green]",
                            border_style="green"))

        t = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
        t.add_column("k", style="dim", width=24)
        t.add_column("v")
        t.add_row("route", decision.route.value)
        t.add_row("wiki notes", str(len(wiki_notes)) if wiki_notes else "—")
        t.add_row("wiki totale", str(len(self.wiki.notes)))
        t.add_row("RAG chunk", str(len(rag_docs)) if rag_docs else "—")
        t.add_row("tool usati",
                  ", ".join(t_["tool"] for t_ in tools_used) or "—")
        t.add_row("score", f"{score}/10")
        t.add_row("tempo", f"{elapsed:.1f}s")
        console.print(t)

        return {
            "query": question, "answer": answer,
            "route": decision.route.value,
            "wiki_notes_created": [n.title for n in wiki_notes] if wiki_notes else [],
            "wiki_total": len(self.wiki.notes),
            "rag_sources": list(set(d["source"] for d in rag_docs)),
            "tools_used": tools_used,
            "reflection": reflection,
            "elapsed_s": round(elapsed, 2),
        }

    def shutdown(self):
        self.stream.stop()
