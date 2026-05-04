"""Layer 6 — Valutazione e controllo.

Volutamente leggero. Tre cose:
  validate    coerenza/lunghezza/loop
  reflect     score 0-10 euristico contro la query e le fonti
  filter_pii  rimuovi pattern sensibili (per uniformita': qui non scatta mai)
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Reflection:
    score: int  # 0-10
    reason: str
    pass_threshold: bool


def validate(answer: str) -> tuple[bool, str]:
    if not answer or not answer.strip():
        return False, "risposta vuota"
    if len(answer.strip()) < 20:
        return False, "risposta troppo corta"
    words = answer.split()
    if len(words) > 30:
        if len(set(words)) / len(words) < 0.3:
            return False, "ratio uniqueness basso (probabile loop)"
    return True, "ok"


_PII = [
    (re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "[ip]"),
    (re.compile(r"\b[\w._%+-]+@[\w.-]+\.[A-Za-z]{2,}\b"), "[email]"),
]


def filter_pii(text: str) -> str:
    out = text
    for rx, repl in _PII:
        out = rx.sub(repl, out)
    return out


def reflect(query: str, answer: str, sources: list[str]) -> Reflection:
    """Score euristico semplice. In produzione: critic agent dedicato."""
    score = 5
    reasons: list[str] = []

    if sources and any(s.split(":")[-1].lower() in answer.lower() for s in sources):
        score += 2
        reasons.append("cita fonti")

    if re.search(r"\bnon\s+lo\s+so\b|\bnon\s+posso\b", answer.lower()) and sources:
        score -= 2
        reasons.append("rifiuta nonostante contesto")

    # bonus brevita': risposta concisa premiata
    n_words = len(answer.split())
    if 30 <= n_words <= 250:
        score += 1
        reasons.append("lunghezza adeguata")
    elif n_words > 500:
        score -= 1
        reasons.append("troppo lunga")

    score = max(0, min(10, score))
    return Reflection(
        score=score,
        reason="; ".join(reasons) or "baseline",
        pass_threshold=score >= 6,
    )
