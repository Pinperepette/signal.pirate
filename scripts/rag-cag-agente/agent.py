"""
CognitiveAgent — pipeline completa:
  Meta-controller → CAG → [RAG / Stream] → Planner → MCP → Reflection → Memory update
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

from meta_controller import MetaController, Route
from stream_simulator import StreamSimulator
from memory_manager import MemoryManager
from tools import TOOL_SCHEMAS, execute_tool

console = Console()

MODEL      = "claude-sonnet-4-6"
EMBED      = "paraphrase-multilingual-MiniLM-L12-v2"
RAG_THRESH = 0.28


class CognitiveAgent:

    def __init__(self,
                 knowledge_path: str = "knowledge/core.json",
                 corpus_path:    str = "corpus/",
                 memory_path:    str = "output/memory.json"):

        self.client     = anthropic.Anthropic()
        self.encoder    = SentenceTransformer(EMBED)
        self.cag_base   = self._load_cag(knowledge_path)
        self.docs, self.embeddings = self._build_index(corpus_path)
        self.memory     = MemoryManager(memory_path, self.encoder)
        self.controller = MetaController(self.client)
        self.stream     = StreamSimulator()

        self.memory.apply_decay()
        self.stream.start()
        console.print("[dim]stream avviato[/dim]")

    # ── CAG ───────────────────────────────────────────────────────────────────

    def _load_cag(self, path: str) -> dict:
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _build_cag_context(self) -> str:
        k = self.cag_base
        parts = []

        if "core_concepts" in k:
            lines = "\n".join(f"  • {key}: {val}"
                              for key, val in k["core_concepts"].items())
            parts.append(f"## CONOSCENZA CORE (CAG statica)\n{lines}")

        if "compressed_memory" in k:
            parts.append(f"## MEMORIA COMPRESSA\n{k['compressed_memory']}")

        learned = self.memory.get_semantic_context()
        if learned:
            parts.append(learned)

        episodic = self.memory.get_episodic_summary()
        if episodic:
            parts.append(episodic)

        return "\n\n".join(parts)

    # ── RAG ───────────────────────────────────────────────────────────────────

    def _build_index(self, corpus_path: str):
        docs = []
        for p in Path(corpus_path).rglob("*.txt"):  # subdirectory incluse
            text = p.read_text(encoding="utf-8")
            # chunk con source = subdir/stem per distinguere nvd vs mitre vs custom
            rel = p.relative_to(corpus_path)
            source = str(rel.parent / rel.stem) if rel.parent.name != "." else rel.stem
            chunks = [c.strip() for c in text.split("\n\n") if len(c.strip()) > 80]
            for chunk in chunks:
                docs.append({"source": source, "text": chunk})

        if not docs:
            return [], None

        console.print(f"[dim]RAG index: {len(docs)} chunk | "
                      f"{len(set(d['source'] for d in docs))} doc[/dim]")
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

    # ── STREAM ANALYSIS ───────────────────────────────────────────────────────

    def _analyze_stream_events(self, events: list[dict]) -> str:
        """Pre-processa gli eventi stream: estrae pattern, conteggi, IP anomali.
        Restituisce un report strutturato invece di raw JSON."""
        if not events:
            return ""

        from collections import Counter

        types     = Counter(e.get("type") for e in events)
        endpoints = Counter(e.get("endpoint") for e in events if "endpoint" in e)
        statuses  = Counter(e.get("status") for e in events if "status" in e)
        all_ips   = [e.get("ip") for e in events if "ip" in e]
        ip_counts = Counter(all_ips)
        top_ips   = ip_counts.most_common(5)
        user_agents = Counter(e.get("user_agent") for e in events if "user_agent" in e)

        # rate max
        rates = [e.get("rate", 0) for e in events if "rate" in e]
        max_rate = max(rates) if rates else 0

        # sequenze 401 → 200 (credential stuffing signal)
        auth_events = [e for e in events if e.get("type") == "auth_attempt"]
        successes_after_failures = sum(
            1 for e in auth_events
            if e.get("status") == 200 and e.get("prev_failures", 0) >= 5
        )

        # IP rotation events
        rotation_events = [e for e in events if e.get("type") == "ip_rotation"]
        max_unique_ips = max(
            (len(e.get("ips_last_60s", [])) for e in rotation_events), default=0
        )

        # pattern classification
        patterns = []
        if statuses.get(401, 0) >= 3:
            patterns.append(f"Flood autenticazione: {statuses[401]} errori 401")
        if successes_after_failures:
            patterns.append(
                f"⚠ CREDENTIAL STUFFING: {successes_after_failures} login riusciti dopo fallimenti multipli"
            )
        if max_rate > 100:
            patterns.append(f"⚠ RATE ANOMALO: picco {max_rate} req/s (soglia: 100)")
        if max_unique_ips > 15:
            patterns.append(f"⚠ IP ROTATION: {max_unique_ips} IP distinti in 60s")
        malicious_uas = [
            ua for ua in user_agents
            if ua and any(x in str(ua) for x in ["requests", "curl", "Go-http", "masscan", "Nuclei"])
        ]
        if malicious_uas:
            patterns.append(f"⚠ USER-AGENT SOSPETTI: {', '.join(malicious_uas[:3])}")
        if not patterns:
            patterns.append("Traffico nella norma — nessun pattern anomalo rilevato")

        severity = "CRITICA" if successes_after_failures else \
                   "ALTA" if max_rate > 100 or max_unique_ips > 15 else \
                   "MEDIA" if statuses.get(401, 0) >= 3 else "BASSA"

        lines = [
            f"## ANALISI STREAM ({len(events)} eventi)",
            f"Tipi evento: {dict(types)}",
            f"Endpoint: {dict(endpoints)}",
            f"Status codes: {dict(statuses)}",
            f"Top IP per frequenza: {top_ips}",
            f"User-agent: {dict(user_agents)}",
            f"Rate massimo osservato: {max_rate} req/s",
            f"Login riusciti dopo fallimenti (credstuff signal): {successes_after_failures}",
            f"IP rotation — max IP distinti/60s: {max_unique_ips}",
            "",
            "PATTERN RILEVATI:",
            *[f"  • {p}" for p in patterns],
            "",
            f"SEVERITÀ STIMATA: {severity}",
        ]
        return "\n".join(lines)

    # ── PLANNING ──────────────────────────────────────────────────────────────

    def _plan(self, query: str, preview: str) -> list[str]:
        resp = self.client.messages.create(
            model=MODEL, max_tokens=400,
            system=(
                "Pianifica il ragionamento. "
                "Elenca 4-5 passi per rispondere alla query in modo completo. "
                "Rispondi SOLO con array JSON di stringhe."
            ),
            messages=[{
                "role": "user",
                "content": f"Query: {query}\n\nContesto (preview):\n{preview[:600]}"
            }]
        )
        try:
            m = re.search(r'\[.*?\]', resp.content[0].text, re.DOTALL)
            if m:
                return json.loads(m.group())
        except Exception:
            pass
        return ["Analizza query", "Usa CAG+RAG", "Applica piano", "Verifica coerenza"]

    # ── GENERATION + TOOL LOOP ────────────────────────────────────────────────

    def _generate(self, query: str, cag_ctx: str, rag_docs: list,
                  stream_events: list, plan: list[str], route: Route) -> tuple[str, list]:

        rag_block = "\n\n---\n\n".join(
            f"[fonte: {d['source']} | sim: {d['score']:.2f}]\n{d['text']}"
            for d in rag_docs
        ) if rag_docs else ""

        stream_block = self._analyze_stream_events(stream_events) if stream_events else ""

        plan_block = "\n".join(f"{i+1}. {s}" for i, s in enumerate(plan))

        system = f"""Sei un agente cognitivo specializzato in sicurezza informatica.

{cag_ctx}

Piano di ragionamento:
{plan_block}

Regole:
- Rispondi in italiano, tono tecnico e diretto
- Distingui esplicitamente CAG (conoscenza pre-caricata) da RAG (recuperato ora)
- Cita le fonti RAG: [fonte: nome_documento]
- Se analizzi eventi stream, identifica pattern specifici e valutane la severità
- Usa i tool quando servono dati reali (CVE, lookup esterno)
- Non inventare dati: se manca qualcosa, dillo"""

        user_content = [{"type": "text", "text": f"Query: {query}"}]
        if rag_block:
            user_content.append({"type": "text", "text": f"\n\nDocumenti RAG:\n{rag_block}"})
        if stream_block:
            user_content.append({
                "type": "text",
                "text": (
                    f"\n\nANALISI STREAM PRE-PROCESSATA ({len(stream_events)} eventi raw):\n"
                    f"{stream_block}\n\n"
                    "ISTRUZIONE OBBLIGATORIA: analizza i pattern sopra in modo concreto e specifico. "
                    "Cita numeri esatti. Dai un verdetto chiaro sulla presenza/assenza di attacco. "
                    "Non descrivere cosa farai: fallo direttamente."
                )
            })

        messages = [{"role": "user", "content": user_content}]
        tools_used = []
        use_tools = route in (Route.CAG_RAG_MCP, Route.FULL)

        for _ in range(6):  # max round-trip
            resp = self.client.messages.create(
                model=MODEL,
                max_tokens=1500,
                system=system,
                tools=TOOL_SCHEMAS if use_tools else [],
                messages=messages,
            )

            if resp.stop_reason == "end_turn":
                text = "".join(
                    b.text for b in resp.content if hasattr(b, "text")
                )
                return text, tools_used

            if resp.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": resp.content})
                results = []
                for block in resp.content:
                    if block.type == "tool_use":
                        console.print(
                            f"[dim magenta]  ⚙ {block.name}("
                            f"{json.dumps(block.input)[:80]})[/dim magenta]"
                        )
                        result = execute_tool(block.name, block.input)
                        tools_used.append({
                            "tool":   block.name,
                            "input":  block.input,
                            "result": result,
                        })
                        console.print(f"[dim]    → {str(result)[:140]}[/dim]")
                        results.append({
                            "type":        "tool_result",
                            "tool_use_id": block.id,
                            "content":     json.dumps(result, ensure_ascii=False),
                        })
                messages.append({"role": "user", "content": results})
            else:
                text = "".join(b.text for b in resp.content if hasattr(b, "text"))
                return text, tools_used

        return "Errore: max round-trip raggiunto.", tools_used

    # ── REFLECTION ────────────────────────────────────────────────────────────

    def _reflect(self, query: str, answer: str, rag_docs: list) -> dict:
        resp = self.client.messages.create(
            model=MODEL, max_tokens=300,
            system=(
                "Valuta la risposta con rigore. Rispondi SOLO con JSON valido:\n"
                '{"score": <0-10>, '
                '"rag_useful": <bool>, '
                '"would_fail_without_rag": <bool>, '
                '"lacune": ["..."], '
                '"punti_forti": ["..."], '
                '"retry": <bool se score < 7>}'
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"Query: {query}\n\n"
                    f"Risposta:\n{answer}\n\n"
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
        return {
            "score": 7, "rag_useful": bool(rag_docs),
            "would_fail_without_rag": False, "lacune": [], "punti_forti": [], "retry": False
        }

    # ── MAIN LOOP ─────────────────────────────────────────────────────────────

    def query(self, question: str) -> dict:
        t0 = time.time()
        console.print()
        console.print(Panel(
            f"[bold white]{question}[/bold white]",
            title="[bold cyan]QUERY[/bold cyan]",
            border_style="cyan"
        ))

        # 1. Stream drain + routing
        stream_events = self.stream.drain(max_events=20)
        decision = self.controller.route(question, self.stream.attack_active)

        _ROUTE_COLORS = {
            "cag_only": "white", "cag_stream": "blue",
            "cag_rag": "yellow", "cag_rag_mcp": "magenta", "full": "red"
        }
        rc = _ROUTE_COLORS.get(decision.route.value, "white")
        console.print(
            f"[dim][ META ][/dim]  "
            f"route: [bold {rc}]{decision.route.value}[/bold {rc}]  "
            f"confidence: {decision.confidence:.0%}  "
            f"metodo: [italic]{decision.method}[/italic]  "
            f"→ {decision.reason}"
        )

        # 2. CAG
        cag_ctx = self._build_cag_context()

        # 3. RAG
        rag_docs = []
        if decision.route in (Route.CAG_RAG, Route.CAG_RAG_MCP, Route.FULL):
            rag_docs = self._retrieve(question)
            srcs = set(d["source"] for d in rag_docs)
            console.print(
                f"[dim green][ RAG ][/dim green]   "
                f"{len(rag_docs)} chunk | {', '.join(srcs) or '—'}"
            )

        # 4. Stream
        active_stream: list[dict] = []
        if decision.route in (Route.CAG_STREAM, Route.FULL):
            active_stream = stream_events
            console.print(
                f"[dim blue][ STREAM ][/dim blue] "
                f"{len(active_stream)} eventi ingeriti"
            )
            if self.stream.attack_active:
                console.print("[bold red]  ⚠ attacco attivo rilevato dallo stream[/bold red]")
            # pre-processa e stampa summary
            summary = self._analyze_stream_events(active_stream)
            for line in summary.split("\n")[:6]:
                console.print(f"[dim blue]  {line}[/dim blue]")

        # 5. Plan
        preview = (
            " ".join(d["text"] for d in rag_docs[:2])
            + " ".join(json.dumps(e) for e in active_stream[:3])
        )
        plan = self._plan(question, preview)
        console.print(f"[dim yellow][ PLAN ][/dim yellow]  {len(plan)} passi")
        for i, s in enumerate(plan):
            console.print(f"          {i+1}. {s}")

        # 6. Generate
        console.print("[dim magenta][ GEN ][/dim magenta]   generazione...")
        answer, tools_used = self._generate(
            question, cag_ctx, rag_docs, active_stream, plan, decision.route
        )

        # 7. Reflection
        reflection = self._reflect(question, answer, rag_docs)
        score = reflection.get("score", 0)
        sc = "green" if score >= 7 else "yellow" if score >= 5 else "red"
        console.print(
            f"[dim][ REFLECT ][/dim] "
            f"score: [bold {sc}]{score}/10[/bold {sc}]  "
            f"RAG utile: {reflection.get('rag_useful','?')}  "
            f"senza RAG → errore: {reflection.get('would_fail_without_rag','?')}"
        )

        # 8. Memory update
        saved = self.memory.add_episodic({
            "query":                 question,
            "route":                 decision.route.value,
            "score":                 score,
            "rag_useful":            reflection.get("rag_useful", False),
            "would_fail_without_rag": reflection.get("would_fail_without_rag", False),
            "tools_used":            [t["tool"] for t in tools_used],
        })
        if saved and reflection.get("rag_useful") and score >= 7:
            for doc in rag_docs[:2]:
                self.memory.add_semantic(
                    key=doc["source"],
                    value=doc["text"][:300],
                    score=score / 10
                )
        console.print(
            f"[dim][ MEM ][/dim]    "
            f"episodio {'salvato' if saved else 'scartato (score basso/duplicato)'}  "
            f"| stats: {self.memory.stats()}"
        )

        elapsed = time.time() - t0

        # ── output panel ──────────────────────────────────────────────────────
        console.print(Panel(
            answer,
            title="[bold green]RISPOSTA[/bold green]",
            border_style="green"
        ))

        t = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
        t.add_column("k", style="dim", width=24)
        t.add_column("v")
        t.add_row("route",            decision.route.value)
        t.add_row("routing method",   decision.method)
        t.add_row("fonti RAG",        ", ".join(set(d["source"] for d in rag_docs)) or "—")
        t.add_row("tool usati",       ", ".join(t_["tool"] for t_ in tools_used) or "—")
        t.add_row("stream eventi",    str(len(active_stream)))
        t.add_row("score",            f"{score}/10")
        t.add_row("RAG utile",        str(reflection.get("rag_useful", "?")))
        t.add_row("senza RAG → errore", str(reflection.get("would_fail_without_rag", "?")))
        t.add_row("tempo totale",     f"{elapsed:.1f}s")
        if reflection.get("lacune"):
            t.add_row("[red]lacune[/red]", " · ".join(reflection["lacune"]))
        if reflection.get("punti_forti"):
            t.add_row("punti forti", " · ".join(reflection["punti_forti"]))
        console.print(t)

        return {
            "query":          question,
            "answer":         answer,
            "route":          decision.route.value,
            "routing_method": decision.method,
            "plan":           plan,
            "rag_sources":    list(set(d["source"] for d in rag_docs)),
            "tools_used":     tools_used,
            "stream_events":  len(active_stream),
            "reflection":     reflection,
            "elapsed_s":      round(elapsed, 2),
        }

    def shutdown(self):
        self.stream.stop()
