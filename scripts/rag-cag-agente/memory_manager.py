"""
Memoria persistente su disco — due layer:
  semantic  : conoscenza stabile (CAG evolutivo) — cosa l'agente ha imparato
  episodic  : decisioni passate + outcome — come ha ragionato

Feature:
  - decay giornaliero (score scende nel tempo)
  - dedup embedding (non salva duplicati semantici)
  - filtro qualità (salva solo score >= soglia)
  - auto-prune sotto MIN_SCORE
"""

import json
import time
from pathlib import Path
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer

DECAY_RATE      = 0.05    # score *= (1 - DECAY_RATE) per giorno
MIN_SCORE       = 0.25    # elimina sotto questa soglia
DEDUP_THRESHOLD = 0.85    # cosine sim → considera duplicato
MAX_EPISODIC    = 100     # cap sugli episodi


class MemoryManager:

    def __init__(self, path: str = "output/memory.json",
                 encoder: Optional[SentenceTransformer] = None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.encoder = encoder
        self.data = self._load()

    # ── IO ────────────────────────────────────────────────────────────────────

    def _load(self) -> dict:
        if self.path.exists():
            with open(self.path, encoding="utf-8") as f:
                return json.load(f)
        return {"semantic": [], "episodic": []}

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    # ── Decay + prune ─────────────────────────────────────────────────────────

    def apply_decay(self):
        now = time.time()
        for layer in ("semantic", "episodic"):
            for item in self.data[layer]:
                if "ts" in item:
                    days = (now - item["ts"]) / 86400
                    item["score"] = item.get("score", 1.0) * ((1 - DECAY_RATE) ** days)
            self.data[layer] = [
                x for x in self.data[layer] if x.get("score", 1.0) >= MIN_SCORE
            ]
        self._save()

    # ── Semantic ──────────────────────────────────────────────────────────────

    def add_semantic(self, key: str, value: str, score: float = 1.0) -> bool:
        if score < MIN_SCORE:
            return False
        if self.encoder and self._is_duplicate(value, "semantic"):
            return False
        self.data["semantic"].append({
            "key": key,
            "value": value,
            "score": score,
            "ts": time.time(),
        })
        self._save()
        return True

    def _is_duplicate(self, text: str, layer: str) -> bool:
        existing = [x.get("value") or x.get("query", "") for x in self.data[layer]]
        existing = [e for e in existing if e]
        if not existing:
            return False
        embs = self.encoder.encode([text] + existing, show_progress_bar=False)
        q, rest = embs[0], embs[1:]
        norm_q = np.linalg.norm(q)
        norm_r = np.linalg.norm(rest, axis=1)
        sims = (rest @ q) / (norm_r * norm_q + 1e-8)
        return bool(np.max(sims) > DEDUP_THRESHOLD)

    def get_semantic_context(self) -> str:
        items = sorted(self.data["semantic"], key=lambda x: -x.get("score", 0))
        if not items:
            return ""
        lines = "\n".join(
            f"  [{x['score']:.2f}] {x['key']}: {x['value'][:200]}"
            for x in items[:12]
        )
        return f"## MEMORIA SEMANTICA APPRESA\n{lines}"

    # ── Episodic ──────────────────────────────────────────────────────────────

    def add_episodic(self, entry: dict) -> bool:
        score = entry.get("score", 0)
        if score < 5:
            return False   # non memorizzare risposte scadenti
        if self.encoder and self._is_duplicate(entry.get("query", ""), "episodic"):
            return False   # no duplicati semantici
        entry["ts"] = time.time()
        self.data["episodic"].append(entry)
        # cap + ordina per score decrescente
        if len(self.data["episodic"]) > MAX_EPISODIC:
            self.data["episodic"] = sorted(
                self.data["episodic"], key=lambda x: -x.get("score", 0)
            )[:MAX_EPISODIC]
        self._save()
        return True

    def get_episodic_summary(self, n: int = 5) -> str:
        if not self.data["episodic"]:
            return ""
        recent = sorted(self.data["episodic"], key=lambda x: -x.get("ts", 0))[:n]
        lines = []
        for e in recent:
            rag_tag = "RAG utile" if e.get("rag_useful") else "CAG sufficient"
            tools   = ", ".join(e.get("tools_used", [])) or "—"
            lines.append(
                f"  Q: {e.get('query','')[:70]}\n"
                f"    [{e.get('route','')} | {rag_tag} | score {e.get('score',0)}/10 | tool: {tools}]"
            )
        return "## MEMORIA EPISODICA\n" + "\n".join(lines)

    # ── Stats ──────────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        return {
            "semantic_items": len(self.data["semantic"]),
            "episodic_items": len(self.data["episodic"]),
            "avg_score_semantic": round(
                sum(x.get("score", 0) for x in self.data["semantic"])
                / max(len(self.data["semantic"]), 1), 2
            ),
            "avg_score_episodic": round(
                sum(x.get("score", 0) for x in self.data["episodic"])
                / max(len(self.data["episodic"]), 1), 2
            ),
        }
