"""
WikiManager — vault Obsidian-compatibile per conoscenza strutturata.

Note atomiche in Markdown con:
  - Frontmatter YAML (tipo, tag, timestamp)
  - Backlink [[nota]] per grafo navigabile
  - Sezione Agent Notes (scritta dall'agente, non dall'umano)
  - Full-text search + tag search + graph traversal
"""

import re
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer

LINK_RE = re.compile(r'\[\[([^\]]+)\]\]')


class WikiNote:

    def __init__(self, title: str, content: str, tags: list[str] = None,
                 links: list[str] = None, agent_notes: list[str] = None,
                 note_type: str = "concept", created: float = 0,
                 updated: float = 0, access_count: int = 0):
        self.title = title
        self.content = content
        self.tags = tags or []
        self.links = links or []
        self.agent_notes = agent_notes or []
        self.note_type = note_type
        self.created = created or time.time()
        self.updated = updated or time.time()
        self.access_count = access_count

    def to_markdown(self) -> str:
        dt_c = datetime.fromtimestamp(self.created).strftime("%Y-%m-%d %H:%M")
        dt_u = datetime.fromtimestamp(self.updated).strftime("%Y-%m-%d %H:%M")

        lines = [
            "---",
            f"title: {self.title}",
            f"type: {self.note_type}",
            f"tags: [{', '.join(self.tags)}]",
            f"created: {dt_c}",
            f"updated: {dt_u}",
            f"access_count: {self.access_count}",
            "---",
            "",
            self.content,
        ]

        if self.agent_notes:
            lines.extend(["", "## Agent Notes"])
            for note in self.agent_notes:
                lines.append(f"- {note}")

        if self.tags:
            lines.extend(["", " ".join(f"#{t}" for t in self.tags)])

        return "\n".join(lines)

    @classmethod
    def from_markdown(cls, path: Path) -> "WikiNote":
        text = path.read_text(encoding="utf-8")

        fm_match = re.match(r'^---\n(.*?)\n---\n', text, re.DOTALL)
        meta = {}
        body = text
        if fm_match:
            for line in fm_match.group(1).split("\n"):
                if ": " in line:
                    k, v = line.split(": ", 1)
                    meta[k.strip()] = v.strip()
            body = text[fm_match.end():]

        links = LINK_RE.findall(body)
        tags_raw = meta.get("tags", "[]")
        tags = [t.strip() for t in tags_raw.strip("[]").split(",") if t.strip()]

        agent_notes = []
        if "## Agent Notes" in body:
            section = body.split("## Agent Notes")[1]
            agent_notes = [
                line.lstrip("- ").strip()
                for line in section.split("\n")
                if line.strip().startswith("- ")
            ]

        content = body.split("## Agent Notes")[0].strip() if "## Agent Notes" in body else body.strip()

        return cls(
            title=meta.get("title", path.stem),
            content=content,
            tags=tags,
            links=links,
            agent_notes=agent_notes,
            note_type=meta.get("type", "concept"),
            created=time.time(),
            updated=time.time(),
            access_count=int(meta.get("access_count", 0)),
        )


class WikiManager:

    def __init__(self, vault_path: str = "wiki",
                 encoder: Optional[SentenceTransformer] = None):
        self.vault = Path(vault_path)
        self.vault.mkdir(parents=True, exist_ok=True)
        self.encoder = encoder
        self.notes: dict[str, WikiNote] = {}
        self._embeddings: dict[str, np.ndarray] = {}
        self._load_vault()

    def _load_vault(self):
        for md in self.vault.glob("*.md"):
            try:
                note = WikiNote.from_markdown(md)
                self.notes[note.title] = note
                if self.encoder:
                    self._embeddings[note.title] = self.encoder.encode(
                        [f"{note.title} {note.content[:500]}"],
                        show_progress_bar=False
                    )[0]
            except Exception:
                pass

    def _slug(self, title: str) -> str:
        return re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '-').lower()

    # -- CRUD -----------------------------------------------------------------

    def create_note(self, title: str, content: str,
                    tags: list[str] = None, links: list[str] = None,
                    note_type: str = "concept",
                    agent_notes: list[str] = None) -> WikiNote:
        if title in self.notes:
            return self.update_note(title, agent_notes=agent_notes or [],
                                    append_content=content)

        implicit_links = LINK_RE.findall(content)
        all_links = list(set((links or []) + implicit_links))

        note = WikiNote(
            title=title, content=content, tags=tags or [],
            links=all_links, agent_notes=agent_notes or [],
            note_type=note_type,
        )
        self.notes[title] = note
        self._write(note)

        if self.encoder:
            self._embeddings[title] = self.encoder.encode(
                [f"{title} {content[:500]}"], show_progress_bar=False
            )[0]

        return note

    def update_note(self, title: str, agent_notes: list[str] = None,
                    append_content: str = None) -> Optional[WikiNote]:
        if title not in self.notes:
            return None

        note = self.notes[title]
        if agent_notes:
            note.agent_notes.extend(agent_notes)
        if append_content:
            note.content += f"\n\n{append_content}"
            new_links = LINK_RE.findall(append_content)
            note.links = list(set(note.links + new_links))
        note.updated = time.time()
        self._write(note)

        if self.encoder:
            self._embeddings[title] = self.encoder.encode(
                [f"{title} {note.content[:500]}"], show_progress_bar=False
            )[0]

        return note

    def get_note(self, title: str) -> Optional[WikiNote]:
        note = self.notes.get(title)
        if note:
            note.access_count += 1
        return note

    def _write(self, note: WikiNote):
        path = self.vault / f"{self._slug(note.title)}.md"
        path.write_text(note.to_markdown(), encoding="utf-8")

    # -- SEARCH ---------------------------------------------------------------

    def search(self, query: str, top_k: int = 5) -> list[tuple[WikiNote, float]]:
        if not self.notes:
            return []

        results = []

        if self.encoder and self._embeddings:
            q_emb = self.encoder.encode([query], show_progress_bar=False)[0]
            for title, emb in self._embeddings.items():
                sim = float(np.dot(q_emb, emb) / (
                    np.linalg.norm(q_emb) * np.linalg.norm(emb) + 1e-8
                ))
                if sim > 0.3:
                    results.append((self.notes[title], sim))

        query_lower = query.lower()
        for note in self.notes.values():
            if any(t in query_lower for t in note.tags):
                if not any(r[0].title == note.title for r in results):
                    results.append((note, 0.5))

        results.sort(key=lambda x: -x[1])
        return results[:top_k]

    def search_by_tag(self, tag: str) -> list[WikiNote]:
        return [n for n in self.notes.values() if tag in n.tags]

    # -- GRAPH ----------------------------------------------------------------

    def get_backlinks(self, title: str) -> list[str]:
        return [
            n.title for n in self.notes.values()
            if title in n.links and n.title != title
        ]

    def get_linked_context(self, title: str, depth: int = 1) -> list[WikiNote]:
        if title not in self.notes:
            return []

        visited = {title}
        frontier = [title]
        result = []

        for _ in range(depth):
            next_frontier = []
            for t in frontier:
                note = self.notes.get(t)
                if not note:
                    continue
                for link in note.links:
                    if link not in visited and link in self.notes:
                        visited.add(link)
                        next_frontier.append(link)
                        result.append(self.notes[link])
                for backlink in self.get_backlinks(t):
                    if backlink not in visited:
                        visited.add(backlink)
                        next_frontier.append(backlink)
                        result.append(self.notes[backlink])
            frontier = next_frontier

        return result

    def get_graph(self) -> dict:
        nodes = []
        edges = []
        for title, note in self.notes.items():
            nodes.append({
                "id": title,
                "type": note.note_type,
                "tags": note.tags,
                "access_count": note.access_count,
            })
            for link in note.links:
                if link in self.notes:
                    edges.append({"from": title, "to": link})
        return {"nodes": nodes, "edges": edges}

    # -- EXPORT ---------------------------------------------------------------

    def export_for_cag(self, title: str) -> Optional[dict]:
        note = self.notes.get(title)
        if not note:
            return None
        linked = self.get_linked_context(title, depth=1)
        return {
            "key": title,
            "value": note.content[:400],
            "agent_notes": note.agent_notes,
            "linked": [l.title for l in linked],
            "tags": note.tags,
        }

    def stats(self) -> dict:
        graph = self.get_graph()
        most_linked = None
        if self.notes:
            most_linked = max(
                self.notes.values(),
                key=lambda n: len(n.links) + len(self.get_backlinks(n.title)),
            ).title
        return {
            "total_notes": len(self.notes),
            "total_links": len(graph["edges"]),
            "total_tags": len(set(t for n in self.notes.values() for t in n.tags)),
            "avg_links": round(len(graph["edges"]) / max(len(self.notes), 1), 1),
            "most_linked": most_linked,
        }
