"""Layer 3 (variante multi-agent) — Researcher + Analyst.

Si attiva solo per la query "analisi". Due ruoli, due chiamate LLM
distinte con system prompt diversi:

  Researcher  Legge il KG via ARGREP, estrae fatti strutturati
              (tecniche, ingredienti, tempi). Niente ragionamento.
  Analyst     Riceve i fatti del researcher e produce la sintesi:
              quali pattern emergono, perche', cosa hanno in comune.

E' multi-agent vero, non un finto fan-out: due chiamate Claude
sequenziali con responsabilita' diverse, come nel CASO 3 dell'immagine
("ricercatore + analista + redattore"). Per la demo bastano due dei
tre ruoli.
"""
from __future__ import annotations

import os
import re

from anthropic import Anthropic


_RESEARCHER_SYSTEM = """Sei il RICERCATORE di un team multi-agent.
Il tuo compito e' estrarre FATTI da appunti di ricette, niente
ragionamento. Output: una lista di fatti puntuali (tecniche,
ingredienti chiave, tempi, note tradizionali). Nessuna conclusione.
Massimo 12 punti."""

_ANALYST_SYSTEM = """Sei l'ANALISTA di un team multi-agent. Ricevi i
fatti raccolti dal ricercatore e individui i PATTERN COMUNI.
Risposta concisa: 4-6 punti, ognuno con il pattern e una frase di
spiegazione. Niente bullshit, niente bullet decorativi."""


def _client() -> Anthropic:
    return Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


def researcher_step(kg, regex_filter: str, model: str) -> tuple[str, list[str]]:
    """Estrae fatti dalle ricette che matchano il filtro ARGREP.

    Ritorna (corpus_di_fatti, lista_di_titoli_consultati).
    """
    matches = kg.grep(regex_filter)
    if not matches:
        return "Nessuna ricetta trovata per il filtro.", []

    titles: list[str] = []
    blocks: list[str] = []
    for _, raw in matches:
        # estrai titolo dalla prima riga (# Titolo)
        m = re.match(r"^# (.+)$", raw, re.MULTILINE)
        title = m.group(1).strip() if m else "?"
        titles.append(title)
        blocks.append(f"=== {title} ===\n{raw}")

    user_prompt = (
        "Estrai fatti strutturati (tecniche, ingredienti, tempi, note) "
        "dalle ricette qui sotto. Non sintetizzare ancora.\n\n"
        + "\n\n".join(blocks)
    )

    msg = _client().messages.create(
        model=model,
        max_tokens=500,
        system=_RESEARCHER_SYSTEM,
        messages=[{"role": "user", "content": user_prompt}],
        timeout=None,
    )
    facts = ""
    for block in msg.content:
        if getattr(block, "type", None) == "text":
            facts = block.text
            break
    return facts, titles


def analyst_step(query: str, facts: str, titles: list[str], model: str) -> str:
    """Sintesi dei pattern comuni a partire dai fatti del researcher."""
    user_prompt = (
        f"DOMANDA UTENTE: {query}\n\n"
        f"RICETTE CONSULTATE: {', '.join(titles)}\n\n"
        f"FATTI RACCOLTI DAL RICERCATORE:\n{facts}\n\n"
        "Identifica i pattern comuni. Massimo 6 punti."
    )
    msg = _client().messages.create(
        model=model,
        max_tokens=400,
        system=_ANALYST_SYSTEM,
        messages=[{"role": "user", "content": user_prompt}],
        timeout=None,
    )
    for block in msg.content:
        if getattr(block, "type", None) == "text":
            return block.text
    return ""
