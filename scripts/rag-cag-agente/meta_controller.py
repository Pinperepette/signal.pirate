"""
Meta-controller — routing ibrido:
  fast path  : pattern matching + confidence score
  slow path  : LLM (Haiku, economico) solo se ambiguo o borderline
"""

import re
import time
from dataclasses import dataclass
from enum import Enum
import anthropic

MODEL_ROUTER = "claude-haiku-4-5-20251001"   # cheap + fast per routing
CONFIDENCE_THRESHOLD = 0.75                   # sopra → deterministico, sotto → LLM


class Route(Enum):
    CAG_ONLY    = "cag_only"
    CAG_STREAM  = "cag_stream"
    CAG_RAG     = "cag_rag"
    CAG_RAG_MCP = "cag_rag_mcp"
    FULL        = "full"          # CAG + RAG + Stream + MCP


@dataclass
class RoutingDecision:
    route:      Route
    confidence: float
    method:     str    # "deterministic" | "llm"
    reason:     str
    latency_ms: int = 0


# pattern → (route, peso per match)
PATTERN_MAP: list[tuple[re.Pattern, Route, float]] = [
    # MCP / CVE lookup
    (re.compile(r"CVE-\d{4}-\d+",            re.I), Route.CAG_RAG_MCP, 1.0),
    (re.compile(r"\bexploit\b",               re.I), Route.CAG_RAG_MCP, 0.8),
    (re.compile(r"\bpoc\b|proof.of.concept",  re.I), Route.CAG_RAG_MCP, 0.8),
    (re.compile(r"remediati",                 re.I), Route.CAG_RAG_MCP, 0.6),
    (re.compile(r"patch\b",                   re.I), Route.CAG_RAG_MCP, 0.5),

    # Stream / live
    (re.compile(r"traffico.*(corrente|live|ora|adesso)", re.I), Route.CAG_STREAM, 1.0),
    (re.compile(r"analiz.*log",               re.I), Route.CAG_STREAM, 1.0),
    (re.compile(r"anomali",                   re.I), Route.CAG_STREAM, 0.9),
    (re.compile(r"attacco.*(in corso|live)",  re.I), Route.CAG_STREAM, 0.9),
    (re.compile(r"monitorin",                 re.I), Route.CAG_STREAM, 0.7),
    (re.compile(r"segnali.*(attacco|intrusione)", re.I), Route.CAG_STREAM, 0.8),

    # RAG (retrieval tecnico, no tool)
    (re.compile(r"come si (implementa|costruisce|fa)", re.I), Route.CAG_RAG, 0.8),
    (re.compile(r"best practice",             re.I), Route.CAG_RAG, 0.7),
    (re.compile(r"architettura",              re.I), Route.CAG_RAG, 0.6),
    (re.compile(r"tecnica.*avanzat",          re.I), Route.CAG_RAG, 0.6),

    # CAG-only (definitorio, concettuale)
    (re.compile(r"^cos['\s]+è\b",             re.I), Route.CAG_ONLY, 0.9),
    (re.compile(r"^cosa (è|sono|intendi)",    re.I), Route.CAG_ONLY, 0.9),
    (re.compile(r"^differenza (tra|fra)",     re.I), Route.CAG_ONLY, 0.8),
    (re.compile(r"^(definisci|definizione)",  re.I), Route.CAG_ONLY, 0.9),
    (re.compile(r"^spiega\b",                 re.I), Route.CAG_ONLY, 0.6),
    (re.compile(r"^come funziona\b",          re.I), Route.CAG_ONLY, 0.7),
]


def _score_patterns(query: str) -> dict[Route, float]:
    scores: dict[Route, float] = {}
    for pattern, route, weight in PATTERN_MAP:
        if pattern.search(query):
            scores[route] = max(scores.get(route, 0.0), weight)
    return scores


class MetaController:

    def __init__(self, client: anthropic.Anthropic):
        self.client = client
        self.history: list[RoutingDecision] = []

    def route(self, query: str, stream_attack_active: bool = False) -> RoutingDecision:
        t0 = time.time()

        # stream override: attacco attivo → full pipeline sempre
        if stream_attack_active:
            d = RoutingDecision(
                route=Route.FULL,
                confidence=1.0,
                method="deterministic",
                reason="stream: attacco attivo rilevato → upgrade a FULL pipeline",
                latency_ms=0,
            )
            self.history.append(d)
            return d

        scores = _score_patterns(query)

        if scores:
            best = max(scores, key=scores.__getitem__)
            conf = min(scores[best] * 1.2, 1.0)   # scale leggero

            if conf >= CONFIDENCE_THRESHOLD:
                d = RoutingDecision(
                    route=best,
                    confidence=conf,
                    method="deterministic",
                    reason=f"pattern match ({conf:.0%})",
                    latency_ms=int((time.time() - t0) * 1000),
                )
                self.history.append(d)
                return d

            # borderline: hint all'LLM
            hint = best
            hint_conf = conf
        else:
            hint = Route.CAG_RAG
            hint_conf = 0.3

        # LLM fallback
        d = self._llm_route(query, hint, hint_conf)
        d.latency_ms = int((time.time() - t0) * 1000)
        self.history.append(d)
        return d

    def _llm_route(self, query: str, hint: Route, hint_conf: float) -> RoutingDecision:
        desc = (
            "cag_only    → domanda concettuale/definitoria (nessun lookup)\n"
            "cag_stream  → richiede analisi eventi real-time o traffico live\n"
            "cag_rag     → retrieval documenti tecnici, no tool esterni\n"
            "cag_rag_mcp → CVE lookup / ricerca web / esecuzione codice\n"
            "full        → tutto: knowledge + stream + retrieval + tool"
        )
        resp = self.client.messages.create(
            model=MODEL_ROUTER,
            max_tokens=20,
            system=f"Scegli il route. Rispondi SOLO con il nome esatto.\n\n{desc}",
            messages=[{
                "role": "user",
                "content": (
                    f"Query: {query}\n"
                    f"Suggerimento deterministico: {hint.value} (confidence {hint_conf:.0%})"
                )
            }]
        )
        text = resp.content[0].text.strip().lower()
        matched = next((r for r in Route if r.value in text), hint)

        return RoutingDecision(
            route=matched,
            confidence=0.85,
            method="llm",
            reason=f"LLM → {matched.value} (hint era {hint.value} @ {hint_conf:.0%})",
        )

    def routing_stats(self) -> dict:
        if not self.history:
            return {}
        by_route: dict[str, int] = {}
        by_method: dict[str, int] = {}
        for d in self.history:
            by_route[d.route.value] = by_route.get(d.route.value, 0) + 1
            by_method[d.method] = by_method.get(d.method, 0) + 1
        return {"by_route": by_route, "by_method": by_method, "total": len(self.history)}
