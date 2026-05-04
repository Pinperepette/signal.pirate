"""Mock del nuovo tipo Array di Redis (PR #15162 di antirez).

Riproduce le semantiche di ARSET/ARGREP/ARINSERT/ARSCAN su primitive
disponibili in Redis 8.x (Sorted Set + Hash). Quando il PR atterra in
master, sostituisci questa classe con i comandi nativi: l'API resta
identica.

Riferimento: https://antirez.com/news/164
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

import redis


@dataclass
class GrepHit:
    index: int
    value: str


class RedisArray:
    """Sparse array con regex server-side.

    Lo storage usa due chiavi per array:
    - "{key}:idx"  Sorted Set degli indici popolati (score = index)
    - "{key}:val"  Hash {str(index): value}

    Nel PR di antirez la rappresentazione interna e' una super-directory
    di directory sliced dense con slice di 4096 elementi. Qui simuliamo
    solo la semantica esterna: indici giganti senza allocazione, regex
    sui valori popolati, scan in tempo proporzionale alla popolazione.
    """

    def __init__(self, r: redis.Redis):
        self.r = r

    def _idx_key(self, key: str) -> str:
        return f"arr:{key}:idx"

    def _val_key(self, key: str) -> str:
        return f"arr:{key}:val"

    def arset(self, key: str, index: int, value: str) -> None:
        """ARSET key idx value — set su indice arbitrario, sparse."""
        pipe = self.r.pipeline()
        pipe.zadd(self._idx_key(key), {str(index): index})
        pipe.hset(self._val_key(key), str(index), value)
        pipe.execute()

    def arget(self, key: str, index: int) -> str | None:
        """ARGET key idx — get singolo, None se l'indice non e' popolato."""
        v = self.r.hget(self._val_key(key), str(index))
        if v is None:
            return None
        return v.decode() if isinstance(v, bytes) else v

    def arinsert(self, key: str, value: str) -> int:
        """ARINSERT key value — append all'indice successivo all'ultimo."""
        last = self.r.zrange(self._idx_key(key), -1, -1, withscores=True)
        next_idx = int(last[0][1]) + 1 if last else 0
        self.arset(key, next_idx, value)
        return next_idx

    def argrep(
        self,
        key: str,
        pattern: str,
        mode: str = "RE",
        limit: int | None = None,
    ) -> list[GrepHit]:
        """ARGREP key pattern [MODE EXACT|MATCH|GLOB|RE] — match server-side.

        Modes:
          EXACT  uguaglianza esatta
          MATCH  substring case-sensitive
          GLOB   wildcard * ?
          RE     regex (default, come la libreria TRE del PR)
        """
        # Iteriamo sugli indici popolati nell'ordine di inserimento.
        # In nativo questo sarebbe O(elementi popolati), non O(range).
        idx_raw = self.r.zrange(self._idx_key(key), 0, -1, withscores=True)
        idx_list = [(int(s), m.decode() if isinstance(m, bytes) else m) for m, s in idx_raw]
        if not idx_list:
            return []

        members = [str(idx) for idx, _ in idx_list]
        vals_raw = self.r.hmget(self._val_key(key), members)
        vals = [v.decode() if isinstance(v, bytes) else v for v in vals_raw]

        out: list[GrepHit] = []
        matcher = self._build_matcher(pattern, mode)
        for (idx, _), v in zip(idx_list, vals):
            if v is None:
                continue
            if matcher(v):
                out.append(GrepHit(index=idx, value=v))
                if limit is not None and len(out) >= limit:
                    break
        return out

    def arscan(self, key: str) -> Iterable[GrepHit]:
        """ARSCAN key — iter sugli elementi popolati (no pattern)."""
        for idx, member in self.r.zscan_iter(self._idx_key(key)):
            i = int(member) if isinstance(member, (int, float)) else int(idx)
            v = self.arget(key, i)
            if v is not None:
                yield GrepHit(index=i, value=v)

    def arlen(self, key: str) -> int:
        """ARLEN key — numero di elementi popolati."""
        return int(self.r.zcard(self._idx_key(key)) or 0)

    @staticmethod
    def _build_matcher(pattern: str, mode: str):
        mode = mode.upper()
        if mode == "EXACT":
            return lambda v: v == pattern
        if mode == "MATCH":
            return lambda v: pattern in v
        if mode == "GLOB":
            rx = re.compile(
                "^"
                + re.escape(pattern)
                .replace(r"\*", ".*")
                .replace(r"\?", ".")
                + "$"
            )
            return lambda v: bool(rx.search(v))
        # RE default
        rx = re.compile(pattern)
        return lambda v: bool(rx.search(v))
