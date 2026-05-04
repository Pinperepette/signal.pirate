"""Layer 2 — Costruzione del contesto (dominio cucina).

Tre tecniche, tre obiettivi:
  CAG  contesto pre-costruito: definizioni base + persona dell'agente
  RAG  retrieval semantico via VectorMemory (glossario tecniche)
  KG   knowledge graph delle ricette, interrogato via ARGREP

L'assembler decide cosa includere in base al "form" della query
(vedi agent.py). Output: una stringa di contesto pronta per il LLM.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from memory import Memory


class Form(str, Enum):
    KNOWLEDGE = "knowledge"     # domanda semplice → CAG
    OPERATIONAL = "operational" # task con tool deterministico
    ANALYTIC = "analytic"       # ricerca multi-hop → KG + multi-agent


# --------------------------------------------------------------------- #
# CAG — system prompt stabile
# --------------------------------------------------------------------- #


CAG_SYSTEM_PROMPT = """Sei un assistente di cucina italiana. Conosci la
cucina regionale, le tecniche classiche e gli abbinamenti. Rispondi in
italiano, in modo conciso e fattuale.

Definizioni base che sai gia':
- Soffritto: trito di cipolla, carota, sedano rosolato dolcemente.
- Mantecatura: legare a fuoco spento con grasso (burro, olio, formaggio).
- Cottura risottata: pasta o cereale cotto aggiungendo liquido a poco a poco.
- Stile romano: cucina basata su guanciale, pecorino, pepe.
- Stile napoletano: cucina basata su pomodoro san marzano, mozzarella, EVO.

Quando ti viene fornito CONTESTO RAG o note del KNOWLEDGE GRAPH,
citalo esplicitamente. Quando manca, dichiaralo. Non inventare ricette
non presenti nel contesto."""


# --------------------------------------------------------------------- #
# Assembled context
# --------------------------------------------------------------------- #


@dataclass
class AssembledContext:
    system: str
    user_blocks: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    layers_used: list[str] = field(default_factory=list)

    def render_user(self, query: str) -> str:
        parts = list(self.user_blocks)
        parts.append(f"DOMANDA: {query}")
        return "\n\n".join(parts)


class ContextAssembler:
    """Assembla il contesto in base al form."""

    def __init__(self, mem: Memory):
        self.mem = mem

    def build(self, query: str, form: Form) -> AssembledContext:
        ctx = AssembledContext(system=CAG_SYSTEM_PROMPT)
        ctx.layers_used.append("CAG")

        if form == Form.KNOWLEDGE:
            # solo CAG. La definizione e' nel system prompt.
            return ctx

        if form == Form.OPERATIONAL:
            # CAG + (eventuale RAG light). I tool faranno il resto.
            hits = self.mem.ltm.search(query, top_k=2)
            relevant = [(d, s) for d, s in hits if s > 0.10]
            if relevant:
                ctx.layers_used.append("RAG")
                rag = "CONTESTO RAG (glossario tecniche):\n"
                for doc, score in relevant:
                    rag += f"- [{doc.id}] (score {score:.2f}) {doc.text}\n"
                    ctx.sources.append(doc.id)
                ctx.user_blocks.append(rag)
            return ctx

        if form == Form.ANALYTIC:
            # Solo CAG qui: il KG verra' consultato dal researcher
            # nel multi-agent step. Niente RAG.
            return ctx

        return ctx


# --------------------------------------------------------------------- #
# helpers — entity extraction (qui dominio cucina)
# --------------------------------------------------------------------- #


_KNOWN_RECIPES = (
    "carbonara", "amatriciana", "cacio e pepe",
    "pizza margherita", "pasta e patate", "genovese",
)
# radice -> label canonica. La radice e' quello che matchiamo nella query
# E nel KG (ARGREP), cosi' singolare e plurale vengono presi entrambi:
# "napolet" cattura "napoletana" e "napoletane".
_STYLE_ROOTS: dict[str, str] = {
    "napolet": "napoletana",
    "roman":   "romana",
    "ligur":   "ligure",
    "sicilian": "siciliana",
}


def detect_recipe(query: str) -> str | None:
    q = query.lower()
    for r in _KNOWN_RECIPES:
        if r in q:
            # normalizza al titolo del KG (capitalizzato)
            return " ".join(w.capitalize() if w not in {"e"} else w for w in r.split())
    return None


def detect_style(query: str) -> tuple[str, str] | None:
    """Ritorna (label, root) dello stile rilevato, o None.

    Esempio: query "ricette napoletane" -> ("napoletana", "napolet").
    Il chiamante usa la radice come pattern ARGREP per filtrare il KG.
    """
    q = query.lower()
    for root, label in _STYLE_ROOTS.items():
        if root in q:
            return label, root
    return None


def detect_servings(query: str) -> int | None:
    m = re.search(r"per\s+(\d+)\s+persone", query.lower())
    return int(m.group(1)) if m else None
