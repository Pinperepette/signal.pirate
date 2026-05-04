"""Layer 1 + 3 + 5 — Input / Orchestrazione / Output.

Il punto di questo modulo: stesso agente, tre sentieri diversi nel
diagramma. La struttura `PathTrace` traccia in modo esplicito quali
layer sono stati ATTIVATI e quali SALTATI per quella query.

Routing deterministico (zero LLM bruciato sulla classificazione):
  KNOWLEDGE   → "cos'e'", "spiega", "definizione", "che cos"
  OPERATIONAL → presenza di una ricetta nota + numero di persone, oppure
                richiesta di lista della spesa / conversione
  ANALYTIC    → "pattern", "cosa hanno in comune", presenza di uno stile
                regionale (napoletana/romana/...) + KG popolato
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from anthropic import Anthropic

from context import (
    ContextAssembler,
    Form,
    detect_recipe,
    detect_servings,
    detect_style,
)
from guardrails import filter_pii, reflect, validate
from memory import KGNote, Memory
from multi_agent import analyst_step, researcher_step
from tools import convert_servings, get_recipe


MODEL_MAIN = "claude-sonnet-4-6"
MODEL_RESEARCH = "claude-haiku-4-5-20251001"


# --------------------------------------------------------------------- #
# Path trace
# --------------------------------------------------------------------- #


# elenco completo dei layer del diagramma (ordine canonico)
ALL_LAYERS = [
    "INPUT",
    "CAG",
    "RAG",
    "KG",
    "ORCHESTRATION",
    "TOOL",
    "OUTPUT",
    "GUARDRAIL",
    "MEMORY(write)",
]


@dataclass
class PathTrace:
    """Verita' su cosa e' stato attraversato, per quella query."""

    form: Form
    path: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    tools_called: list[str] = field(default_factory=list)
    reflection_score: int = 0
    reflection_reason: str = ""
    answer: str = ""

    @property
    def skipped(self) -> list[str]:
        return [layer for layer in ALL_LAYERS if layer not in self.path]

    def render(self) -> str:
        path_str = " → ".join(self.path)
        skipped = ", ".join(self.skipped) or "-"
        return (
            f"  form         : {self.form.value}\n"
            f"  PATH         : {path_str}\n"
            f"  SKIPPED      : {skipped}\n"
            f"  sources      : {', '.join(self.sources) or '-'}\n"
            f"  tools called : {', '.join(self.tools_called) or '-'}\n"
            f"  reflection   : {self.reflection_score}/10 ({self.reflection_reason})"
        )


# --------------------------------------------------------------------- #
# Router
# --------------------------------------------------------------------- #


_KNOWLEDGE_HINTS = ("cos'e'", "cosa e'", "cosa è", "definizione", "spiega", "che cos")
_OP_HINTS = ("converti", "convertimi", "scala", "porzioni", "lista della spesa")
_AN_HINTS = ("pattern", "cosa hanno in comune", "comune", "comuni", "tendenza", "stile", "tradizioni")


def decide_form(query: str, mem: Memory) -> Form:
    q = query.lower()

    if any(k in q for k in _KNOWLEDGE_HINTS):
        return Form.KNOWLEDGE

    # ANALYTIC: chiede di pattern / si menziona uno stile regionale e
    # il KG ha qualcosa di analizzabile (almeno 2 ricette)
    if any(k in q for k in _AN_HINTS) or detect_style(query) is not None:
        if mem.kg.size() >= 2:
            return Form.ANALYTIC

    # OPERATIONAL: richiede una conversione / lista, oppure ricetta + persone
    if any(k in q for k in _OP_HINTS):
        return Form.OPERATIONAL
    if detect_recipe(query) and detect_servings(query):
        return Form.OPERATIONAL

    # default: knowledge form (CAG-only). Risposta basata sul system prompt.
    return Form.KNOWLEDGE


# --------------------------------------------------------------------- #
# Agent
# --------------------------------------------------------------------- #


class Agent:
    """Orchestratore minimo con tre sentieri.

    Path effettivamente esercitati:
      KNOWLEDGE   INPUT → CAG → OUTPUT → GUARDRAIL
      OPERATIONAL INPUT → CAG → (RAG) → TOOL → OUTPUT → GUARDRAIL → MEMORY
      ANALYTIC    INPUT → KG → ORCHESTRATION(researcher+analyst) → OUTPUT → GUARDRAIL
    """

    def __init__(self, mem: Memory):
        self.mem = mem
        self.assembler = ContextAssembler(mem)
        self.client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

    # ------------------------------------------------------------------ #
    # entry point
    # ------------------------------------------------------------------ #

    def ask(self, query: str) -> PathTrace:
        form = decide_form(query, self.mem)
        if form == Form.KNOWLEDGE:
            return self._path_knowledge(query)
        if form == Form.OPERATIONAL:
            return self._path_operational(query)
        return self._path_analytic(query)

    # ------------------------------------------------------------------ #
    # path 1: KNOWLEDGE — domanda semplice
    #   INPUT → CAG → OUTPUT → GUARDRAIL
    # ------------------------------------------------------------------ #

    def _path_knowledge(self, query: str) -> PathTrace:
        trace = PathTrace(form=Form.KNOWLEDGE)
        trace.path.append("INPUT")

        ctx = self.assembler.build(query, Form.KNOWLEDGE)
        trace.path.append("CAG")

        answer = self._llm_call(ctx.system, ctx.render_user(query), max_tokens=300)
        trace.path.append("OUTPUT")

        # guardrail leggero
        ok, reason = validate(answer)
        if not ok:
            answer = f"[validation failed: {reason}] " + answer
        answer = filter_pii(answer)
        ref = reflect(query, answer, ctx.sources)
        trace.path.append("GUARDRAIL")
        trace.reflection_score = ref.score
        trace.reflection_reason = ref.reason
        trace.answer = answer
        return trace

    # ------------------------------------------------------------------ #
    # path 2: OPERATIONAL — task con tool deterministico
    #   INPUT → CAG → (RAG opzionale) → TOOL → OUTPUT → GUARDRAIL → MEMORY
    # ------------------------------------------------------------------ #

    def _path_operational(self, query: str) -> PathTrace:
        trace = PathTrace(form=Form.OPERATIONAL)
        trace.path.append("INPUT")

        ctx = self.assembler.build(query, Form.OPERATIONAL)
        trace.path.append("CAG")
        if "RAG" in ctx.layers_used:
            trace.path.append("RAG")
            trace.sources.extend(ctx.sources)

        # Tool deterministico: convertire una ricetta per N persone.
        recipe = detect_recipe(query)
        servings = detect_servings(query) or 4
        tool_block = ""
        if recipe:
            res = convert_servings(self.mem.kg, recipe, servings)
            trace.tools_called.append(f"convert_servings({recipe},{servings})")
            if res.ok:
                # ISTRUZIONE esplicita per il LLM: non rifare il calcolo.
                # Sonnet a volte ignora le note dentro al tool block, qui
                # la mettiamo fuori al livello del prompt utente.
                tool_block = (
                    "\n\nIMPORTANTE: il blocco TOOL qui sotto contiene la "
                    "ricetta GIA' SCALATA per il numero di persone richiesto. "
                    "Riformatta i contenuti in markdown chiaro per l'utente "
                    "(tabella ingredienti + procedimento), ma NON rieseguire "
                    "moltiplicazioni: usa i numeri esattamente come sono.\n\n"
                    f"TOOL[{res.source}]:\n{res.payload}\n"
                )
                trace.sources.append(res.source)
                trace.path.append("TOOL")
            else:
                tool_block = f"\n\nTOOL warning: {res.payload}\n"

        if tool_block:
            ctx.user_blocks.append(tool_block)

        answer = self._llm_call(ctx.system, ctx.render_user(query), max_tokens=400)
        trace.path.append("OUTPUT")

        ok, reason = validate(answer)
        if not ok:
            answer = f"[validation failed: {reason}] " + answer
        answer = filter_pii(answer)
        ref = reflect(query, answer, ctx.sources)
        trace.path.append("GUARDRAIL")
        trace.reflection_score = ref.score
        trace.reflection_reason = ref.reason

        # memoria (sessione)
        self.mem.stm.append("user", query)
        self.mem.stm.append("assistant", answer)
        trace.path.append("MEMORY(write)")

        trace.answer = answer
        return trace

    # ------------------------------------------------------------------ #
    # path 3: ANALYTIC — ricerca multi-hop con multi-agent
    #   INPUT → KG(ARGREP) → ORCHESTRATION(researcher+analyst) → OUTPUT → GUARDRAIL
    # ------------------------------------------------------------------ #

    def _path_analytic(self, query: str) -> PathTrace:
        trace = PathTrace(form=Form.ANALYTIC)
        trace.path.append("INPUT")

        # filtro ARGREP a partire dallo stile rilevato. La radice (es.
        # "napolet") cattura sia singolare che plurale (napoletana,
        # napoletane), e' il modo piu' robusto per filtrare il KG.
        detected = detect_style(query)
        if detected is not None:
            label, root = detected
            regex_filter = rf"stile:\s*\w*{root}\w*"
        else:
            regex_filter = r"stile:\s*\w+"  # default: qualsiasi stile
            label = None
        trace.tools_called.append(f"ARGREP('{regex_filter}')")
        trace.path.append("KG")

        # Multi-agent: researcher → analyst
        facts, titles = researcher_step(self.mem.kg, regex_filter, MODEL_RESEARCH)
        trace.sources.extend(f"kg:{t}" for t in titles)
        synthesis = analyst_step(query, facts, titles, MODEL_MAIN)
        trace.path.append("ORCHESTRATION")
        trace.path.append("OUTPUT")

        answer = synthesis
        ok, reason = validate(answer)
        if not ok:
            answer = f"[validation failed: {reason}] " + answer
        answer = filter_pii(answer)
        ref = reflect(query, answer, trace.sources)
        trace.path.append("GUARDRAIL")
        trace.reflection_score = ref.score
        trace.reflection_reason = ref.reason
        trace.answer = answer
        return trace

    # ------------------------------------------------------------------ #
    # private
    # ------------------------------------------------------------------ #

    def _llm_call(self, system: str, user_prompt: str, max_tokens: int = 400) -> str:
        msg = self.client.messages.create(
            model=MODEL_MAIN,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_prompt}],
            timeout=None,
        )
        for block in msg.content:
            if getattr(block, "type", None) == "text":
                return block.text
        return ""
