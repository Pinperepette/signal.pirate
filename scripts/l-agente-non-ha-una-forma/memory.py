"""Layer 7 — Memoria su Redis 8.

Tre livelli su un solo backend:
  short term : Hash + TTL (sessione, cronologia)
  long term  : embedding vector store (per ora dict in-process; in
               produzione: Redis Vector Set con HNSW)
  knowledge  : RedisArray (mock del PR antirez #15162) per le note KG
  cache      : String + TTL per output deterministici

L'idea e' che TUTTO viva nello stesso processo Redis. Cambia la latenza
quando passi al PR nativo, ma il codice resta lo stesso.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
import redis

from redis_array import RedisArray


# --------------------------------------------------------------------- #
# Short term
# --------------------------------------------------------------------- #


class ShortTermMemory:
    """Cronologia conversazione di una sessione, con TTL."""

    def __init__(self, r: redis.Redis, session_id: str, ttl_s: int = 3600):
        self.r = r
        self.key = f"stm:{session_id}"
        self.ttl_s = ttl_s

    def append(self, role: str, content: str) -> None:
        entry = json.dumps({"role": role, "content": content, "ts": time.time()})
        pipe = self.r.pipeline()
        pipe.rpush(self.key, entry)
        pipe.expire(self.key, self.ttl_s)
        pipe.execute()

    def history(self, last_n: int = 20) -> list[dict[str, Any]]:
        raw = self.r.lrange(self.key, -last_n, -1)
        return [json.loads(x) for x in raw]


# --------------------------------------------------------------------- #
# Long term — vector
# --------------------------------------------------------------------- #


@dataclass
class Doc:
    id: str
    text: str
    meta: dict = field(default_factory=dict)


class VectorMemory:
    """Long term semantica con backend swappabile.

    Per la demo usiamo un encoder bag-of-words leggero (solo numpy +
    regex). Mostra che il layer RAG si attiva e ranka, ma evita
    sentence-transformers/torch (su Python 3.9 + Intel macOS i wheel
    di torch 2.x non sono disponibili).

    In produzione si sostituisce con sentence-transformers o, ancora
    meglio, con Redis Vector Set + HNSW. L'API resta identica.
    """

    def __init__(self, r: redis.Redis, namespace: str = "ltm"):
        self.r = r
        self.ns = namespace
        self._embeddings: dict[str, np.ndarray] = {}
        self._vocab: dict[str, int] = {}

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return [t for t in re.split(r"\W+", text.lower()) if len(t) >= 2]

    def _vectorize(self, text: str) -> np.ndarray:
        # bag-of-words su vocabolario incrementale
        toks = self._tokens(text)
        for t in toks:
            if t not in self._vocab:
                self._vocab[t] = len(self._vocab)
        vec = np.zeros(len(self._vocab), dtype=np.float32)
        for t in toks:
            vec[self._vocab[t]] += 1.0
        n = np.linalg.norm(vec)
        return vec / n if n > 0 else vec

    def _expand(self, vec: np.ndarray) -> np.ndarray:
        # padding al vocab corrente (cresce nel tempo)
        if len(vec) == len(self._vocab):
            return vec
        out = np.zeros(len(self._vocab), dtype=np.float32)
        out[: len(vec)] = vec
        return out

    def upsert(self, doc: Doc) -> None:
        emb = self._vectorize(doc.text)
        self._embeddings[doc.id] = emb
        self.r.hset(
            f"{self.ns}:meta",
            doc.id,
            json.dumps({"text": doc.text, "meta": doc.meta}),
        )

    def search(self, query: str, top_k: int = 3) -> list[tuple[Doc, float]]:
        if not self._embeddings:
            return []
        q = self._vectorize(query)
        scored = []
        for doc_id, emb in self._embeddings.items():
            emb_p = self._expand(emb)
            q_p = q if len(q) == len(emb_p) else self._expand(q)
            denom = (np.linalg.norm(q_p) * np.linalg.norm(emb_p)) or 1.0
            score = float(np.dot(q_p, emb_p) / denom)
            scored.append((doc_id, score))
        scored.sort(key=lambda x: -x[1])
        out = []
        for doc_id, score in scored[:top_k]:
            raw = self.r.hget(f"{self.ns}:meta", doc_id)
            if not raw:
                continue
            payload = json.loads(raw)
            out.append((Doc(id=doc_id, text=payload["text"], meta=payload.get("meta", {})), score))
        return out


# --------------------------------------------------------------------- #
# Knowledge layer — il pezzo nuovo, sopra il PR antirez
# --------------------------------------------------------------------- #


@dataclass
class KGNote:
    """Nota Markdown nel knowledge graph.

    Identica per struttura a quella dell'articolo precedente
    (frontmatter + content + Agent Notes), ma la storage layer e' un
    Array Redis sparso interrogato con ARGREP. Le note hanno indici
    deterministici (hash del titolo) cosi' upsert idempotente.
    """

    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    access_count: int = 0
    created_ts: float = field(default_factory=time.time)

    def render(self) -> str:
        """Forma testuale della nota: e' quello che ARGREP indicizza."""
        head = f"# {self.title}\n"
        meta = f"tags: {','.join(self.tags)} | access: {self.access_count}\n"
        return head + meta + "---\n" + self.content


class KnowledgeMemory:
    """Wrapper sopra RedisArray per gestire note KG come un grafo.

    Ogni nota e' un singolo elemento dell'array. ARGREP fa il lavoro di
    retrieval (regex sul rendered text). I link [[...]] dentro il
    contenuto formano il grafo: quando cerchi un nodo, ARGREP trova
    anche tutte le note che lo linkano.
    """

    KEY = "notes"

    def __init__(self, ra: RedisArray):
        self.ra = ra

    @staticmethod
    def _slot(title: str) -> int:
        # indice sparso e deterministico cross-process: usiamo md5 (primi
        # 8 byte) cosi' lo stesso titolo cade sempre nello stesso slot.
        # Python's builtin hash() e' randomizzato e qui non va bene.
        digest = hashlib.md5(title.encode("utf-8")).digest()[:8]
        return int.from_bytes(digest, "big") % (10**12)

    def upsert(self, note: KGNote) -> int:
        idx = self._slot(note.title)
        self.ra.arset(self.KEY, idx, note.render())
        return idx

    def get(self, title: str) -> str | None:
        return self.ra.arget(self.KEY, self._slot(title))

    def grep(self, pattern: str, mode: str = "RE") -> list[tuple[int, str]]:
        hits = self.ra.argrep(self.KEY, pattern, mode=mode)
        return [(h.index, h.value) for h in hits]

    def find_by_link(self, title: str) -> list[str]:
        """Note che linkano [[title]]: il backbone del grafo."""
        # re.escape sul titolo perche' nomi come "Cacio e Pepe" o titoli
        # con punteggiatura potrebbero contenere caratteri speciali regex
        pat = r"\[\[" + re.escape(title) + r"\]\]"
        return [v for _, v in self.grep(pat)]

    def size(self) -> int:
        return self.ra.arlen(self.KEY)


# --------------------------------------------------------------------- #
# Cache — semantic-light
# --------------------------------------------------------------------- #


class ResponseCache:
    """Cache key-value sulle risposte deterministiche (TTL breve).

    LangCache fa la stessa cosa con similarity semantica; qui ci
    accontentiamo di una match exact sulla query normalizzata.
    """

    def __init__(self, r: redis.Redis, ttl_s: int = 600):
        self.r = r
        self.ttl_s = ttl_s

    @staticmethod
    def _key(query: str) -> str:
        # md5 deterministico cross-process (Python's hash() e' randomizzato)
        digest = hashlib.md5(query.strip().lower().encode("utf-8")).hexdigest()
        return f"cache:{digest[:16]}"

    def get(self, query: str) -> str | None:
        v = self.r.get(self._key(query))
        if v is None:
            return None
        return v.decode() if isinstance(v, bytes) else v

    def set(self, query: str, response: str) -> None:
        self.r.setex(self._key(query), self.ttl_s, response)


# --------------------------------------------------------------------- #
# Bundle
# --------------------------------------------------------------------- #


@dataclass
class Memory:
    """Layer 7 completo: tutti i sotto-layer su un solo Redis."""

    stm: ShortTermMemory
    ltm: VectorMemory
    kg: KnowledgeMemory
    cache: ResponseCache

    @classmethod
    def build(cls, r: redis.Redis, session_id: str) -> "Memory":
        ra = RedisArray(r)
        return cls(
            stm=ShortTermMemory(r, session_id),
            ltm=VectorMemory(r),
            kg=KnowledgeMemory(ra),
            cache=ResponseCache(r),
        )
