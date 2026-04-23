"""
MetaController V2 — routing con Wiki layer:

  CAG_ONLY     → concettuale, risposta diretta
  CAG_WIKI     → concetto noto nel wiki, arricchisci con grafo
  CAG_STREAM   → analisi eventi real-time
  CAG_RAG      → retrieval dal corpus
  CAG_RAG_MCP  → retrieval + tool esterni
  FULL         → tutto

Novita' rispetto a V1: prima di andare al RAG, controlla se il wiki
ha gia' conoscenza strutturata. Se si', usa CAG_WIKI e bypassa il RAG.
"""

import re
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

import anthropic

MODEL_ROUTER = "claude-haiku-4-5-20251001"
CONFIDENCE_THRESHOLD = 0.75


class Route(Enum):
    CAG_ONLY    = "cag_only"
    CAG_WIKI    = "cag_wiki"
    CAG_STREAM  = "cag_stream"
    CAG_RAG     = "cag_rag"
    CAG_RAG_MCP = "cag_rag_mcp"
    FULL        = "full"


@dataclass
class RoutingDecision:
    route:      Route
    confidence: float
    method:     str
    reason:     str
    latency_ms: int = 0


PATTERN_MAP: list[tuple[re.Pattern, Route, float]] = [
    (re.compile(r"CVE-\d{4}-\d+",            re.I), Route.CAG_RAG_MCP, 1.0),
    (re.compile(r"\bexploit\b",               re.I), Route.CAG_RAG_MCP, 0.8),
    (re.compile(r"\bpoc\b|proof.of.concept",  re.I), Route.CAG_RAG_MCP, 0.8),
    (re.compile(r"remediati",                 re.I), Route.CAG_RAG_MCP, 0.6),
    (re.compile(r"patch\b",                   re.I), Route.CAG_RAG_MCP, 0.5),

    (re.compile(r"traffico.*(corrente|live|ora|adesso)", re.I), Route.CAG_STREAM, 1.0),
    (re.compile(r"analiz.*log",               re.I), Route.CAG_STREAM, 1.0),
    (re.compile(r"anomali",                   re.I), Route.CAG_STREAM, 0.9),
    (re.compile(r"attacco.*(in corso|live)",  re.I), Route.CAG_STREAM, 0.9),
    (re.compile(r"monitorin",                 re.I), Route.CAG_STREAM, 0.7),

    (re.compile(r"come si (implementa|costruisce|fa)", re.I), Route.CAG_RAG, 0.8),
    (re.compile(r"best practice",             re.I), Route.CAG_RAG, 0.7),
    (re.compile(r"architettura",              re.I), Route.CAG_RAG, 0.6),

    (re.compile(r"^cos['\s]+è\b",             re.I), Route.CAG_ONLY, 0.9),
    (re.compile(r"^cosa (è|sono|intendi)",    re.I), Route.CAG_ONLY, 0.9),
    (re.compile(r"^differenza (tra|fra)",     re.I), Route.CAG_ONLY, 0.8),
    (re.compile(r"^(definisci|definizione)",  re.I), Route.CAG_ONLY, 0.9),
    (re.compile(r"^spiega\b",                 re.I), Route.CAG_ONLY, 0.6),

    (re.compile(r"pattern.*(attacc|threat)",  re.I), Route.CAG_WIKI, 0.7),
    (re.compile(r"correlaz",                  re.I), Route.CAG_WIKI, 0.6),
    (re.compile(r"collega.*concett",          re.I), Route.CAG_WIKI, 0.8),
    (re.compile(r"storico.*(attacc|incident)",re.I), Route.CAG_WIKI, 0.7),
]


def _score_patterns(query: str) -> dict[Route, float]:
    scores: dict[Route, float] = {}
    for pattern, route, weight in PATTERN_MAP:
        if pattern.search(query):
            scores[route] = max(scores.get(route, 0.0), weight)
    return scores


class MetaControllerV2:

    def __init__(self, client: anthropic.Anthropic,
                 wiki_checker: Optional[Callable[[str], bool]] = None):
        self.client = client
        self.wiki_checker = wiki_checker
        self.history: list[RoutingDecision] = []

    def route(self, query: str, stream_attack_active: bool = False) -> RoutingDecision:
        t0 = time.time()

        if stream_attack_active:
            d = RoutingDecision(
                route=Route.FULL, confidence=1.0,
                method="deterministic",
                reason="stream: attacco attivo → FULL pipeline",
            )
            self.history.append(d)
            return d

        scores = _score_patterns(query)

        if self.wiki_checker and scores:
            best = max(scores, key=scores.__getitem__)
            if best in (Route.CAG_ONLY, Route.CAG_RAG) and self.wiki_checker(query):
                d = RoutingDecision(
                    route=Route.CAG_WIKI,
                    confidence=0.85,
                    method="deterministic+wiki",
                    reason="concetto trovato nel wiki → CAG_WIKI (bypass RAG)",
                    latency_ms=int((time.time() - t0) * 1000),
                )
                self.history.append(d)
                return d

        if scores:
            best = max(scores, key=scores.__getitem__)
            conf = min(scores[best] * 1.2, 1.0)

            if conf >= CONFIDENCE_THRESHOLD:
                d = RoutingDecision(
                    route=best, confidence=conf,
                    method="deterministic",
                    reason=f"pattern match ({conf:.0%})",
                    latency_ms=int((time.time() - t0) * 1000),
                )
                self.history.append(d)
                return d

            hint, hint_conf = best, conf
        else:
            hint, hint_conf = Route.CAG_RAG, 0.3

        d = self._llm_route(query, hint, hint_conf)
        d.latency_ms = int((time.time() - t0) * 1000)
        self.history.append(d)
        return d

    def _llm_route(self, query: str, hint: Route, hint_conf: float) -> RoutingDecision:
        desc = (
            "cag_only    → domanda concettuale semplice\n"
            "cag_wiki    → concetto noto nel wiki, arricchisci con grafo\n"
            "cag_stream  → analisi eventi real-time\n"
            "cag_rag     → retrieval documenti tecnici\n"
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
                    f"Suggerimento: {hint.value} (confidence {hint_conf:.0%})"
                )
            }]
        )
        text = resp.content[0].text.strip().lower()
        matched = next((r for r in Route if r.value in text), hint)
        return RoutingDecision(
            route=matched, confidence=0.85, method="llm",
            reason=f"LLM → {matched.value} (hint: {hint.value} @ {hint_conf:.0%})",
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
