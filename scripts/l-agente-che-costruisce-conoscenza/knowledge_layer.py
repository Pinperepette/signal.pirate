"""
KnowledgeLayer — promozione e demozione tra i tre layer:

  MEMORY  →  WIKI  →  CAG
  (grezza)   (strutturata)   (operativa)

Regole:
  - Memory → Wiki:  se reflection score >= 7 e ci sono concetti estraibili
  - Wiki → CAG:     se una nota wiki ha >= 3 accessi (conoscenza stabile)
  - CAG → Wiki:     se un concetto CAG non viene usato da > 60 giorni
"""

import re
import json
import time
from pathlib import Path
from typing import Optional

from wiki_manager import WikiManager, WikiNote

PROMOTE_TO_WIKI_THRESHOLD = 7
PROMOTE_TO_CAG_THRESHOLD  = 3
DEMOTE_FROM_CAG_DAYS      = 60
MAX_CAG_ITEMS             = 20


class KnowledgeLayer:

    def __init__(self, wiki: WikiManager, cag_path: str = "knowledge/core.json"):
        self.wiki = wiki
        self.cag_path = Path(cag_path)
        self.cag_data = self._load_cag()
        self.promotions: list[dict] = []

    def _load_cag(self) -> dict:
        if self.cag_path.exists():
            with open(self.cag_path, encoding="utf-8") as f:
                return json.load(f)
        return {"core_concepts": {}}

    def _save_cag(self):
        self.cag_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cag_path, "w", encoding="utf-8") as f:
            json.dump(self.cag_data, f, indent=2, ensure_ascii=False)

    # -- MEMORY -> WIKI -------------------------------------------------------

    def maybe_promote_to_wiki(self, query: str, answer: str,
                               reflection: dict,
                               rag_docs: list = None) -> list[WikiNote]:
        score = reflection.get("score", 0)
        if score < PROMOTE_TO_WIKI_THRESHOLD:
            return []

        concepts = self._extract_concepts(query, answer)
        if not concepts:
            return []

        created_notes = []
        main = concepts[0]
        linked_names = concepts[1:]

        content = answer[:600]
        if linked_names:
            content += "\n\nConcetti collegati: " + " ".join(
                f"[[{c}]]" for c in linked_names
            )

        tags = self._extract_tags(query, answer)

        agent_notes = []
        if reflection.get("rag_useful"):
            agent_notes.append(f"RAG necessario (score: {score}/10)")
        if reflection.get("would_fail_without_rag"):
            agent_notes.append("Fallimento senza RAG: conoscenza CAG insufficiente")
        if rag_docs:
            sources = list(set(d.get("source", "") for d in rag_docs[:3]))
            agent_notes.append(f"Fonti: {', '.join(sources)}")

        note = self.wiki.create_note(
            title=main, content=content, tags=tags,
            links=linked_names, agent_notes=agent_notes,
        )
        created_notes.append(note)

        for concept in linked_names:
            if concept not in self.wiki.notes:
                n = self.wiki.create_note(
                    title=concept,
                    content=f"Concetto collegato a [[{main}]].",
                    tags=tags[:2], links=[main],
                )
                created_notes.append(n)

        self.promotions.append({
            "direction": "memory→wiki",
            "concept": main,
            "score": score,
            "linked": linked_names,
            "ts": time.time(),
        })

        return created_notes

    # -- WIKI -> CAG ----------------------------------------------------------

    def maybe_promote_to_cag(self) -> list[str]:
        promoted = []
        for title, note in self.wiki.notes.items():
            if note.access_count >= PROMOTE_TO_CAG_THRESHOLD:
                if title not in self.cag_data.get("core_concepts", {}):
                    if len(self.cag_data["core_concepts"]) < MAX_CAG_ITEMS:
                        exported = self.wiki.export_for_cag(title)
                        if exported:
                            value = exported["value"]
                            if exported["agent_notes"]:
                                value += f" [Agent: {'; '.join(exported['agent_notes'][:2])}]"
                            self.cag_data["core_concepts"][title] = value
                            self._save_cag()
                            promoted.append(title)
                            self.promotions.append({
                                "direction": "wiki→cag",
                                "concept": title,
                                "access_count": note.access_count,
                                "ts": time.time(),
                            })
        return promoted

    # -- CAG -> WIKI (demozione) ----------------------------------------------

    def maybe_demote_from_cag(self) -> list[str]:
        demoted = []
        now = time.time()
        to_remove = []

        for key in list(self.cag_data.get("core_concepts", {}).keys()):
            wiki_note = self.wiki.notes.get(key)
            if wiki_note:
                days = (now - wiki_note.updated) / 86400
                if days > DEMOTE_FROM_CAG_DAYS and wiki_note.access_count < 2:
                    to_remove.append(key)

        for key in to_remove:
            del self.cag_data["core_concepts"][key]
            demoted.append(key)
            self.promotions.append({
                "direction": "cag→wiki",
                "concept": key,
                "reason": "accesso insufficiente",
                "ts": time.time(),
            })

        if demoted:
            self._save_cag()

        return demoted

    # -- WIKI CONTEXT per query -----------------------------------------------

    def get_wiki_context(self, query: str) -> str:
        hits = self.wiki.search(query, top_k=3)
        if not hits:
            return ""

        parts = ["## WIKI KNOWLEDGE"]
        for note, score in hits:
            linked = self.wiki.get_linked_context(note.title, depth=1)
            linked_titles = [l.title for l in linked[:5]]

            parts.append(f"\n### {note.title} (relevance: {score:.2f})")
            parts.append(note.content[:400])

            if note.agent_notes:
                parts.append("Agent notes:")
                for an in note.agent_notes[:3]:
                    parts.append(f"  - {an}")

            if linked_titles:
                parts.append(f"Collegato a: {', '.join(linked_titles)}")

        return "\n".join(parts)

    def concept_in_wiki(self, query: str) -> bool:
        hits = self.wiki.search(query, top_k=1)
        return bool(hits and hits[0][1] > 0.5)

    # -- HELPERS --------------------------------------------------------------

    def _extract_concepts(self, query: str, answer: str) -> list[str]:
        text = f"{query} {answer}"
        concepts = []

        cves = re.findall(r'CVE-\d{4}-\d+', text)
        concepts.extend(cves)

        terms = [
            "OpenSSH", "Race Condition", "Buffer Overflow", "XSS",
            "SQL Injection", "RCE", "Privilege Escalation",
            "Lateral Movement", "Credential Stuffing", "Brute Force",
            "Meterpreter", "Metasploit", "Webshell", "C2",
            "Kerberoasting", "Pass-the-Hash", "Log4Shell",
            "Supply Chain", "Signal Handler", "ASLR",
            "WordPress", "MailPoet",
        ]
        for term in terms:
            if term.lower() in text.lower():
                concepts.append(term)

        mitre = re.findall(r'T\d{4}(?:\.\d{3})?', text)
        concepts.extend(mitre)

        return list(dict.fromkeys(concepts))[:6]

    def _extract_tags(self, query: str, answer: str) -> list[str]:
        text = f"{query} {answer}".lower()
        tag_map = {
            "cve": ["cve", "vulnerability", "vulnerabilit"],
            "critical": ["critical", "critico", "critica"],
            "network": ["network", "rete", "ssh", "tcp", "http"],
            "exploit": ["exploit", "poc", "proof of concept"],
            "malware": ["malware", "trojan", "backdoor", "webshell"],
            "auth": ["authentication", "autenticazione", "credential"],
            "rce": ["remote code execution", "rce", "esecuzione remota"],
        }
        tags = []
        for tag, keywords in tag_map.items():
            if any(kw in text for kw in keywords):
                tags.append(tag)
        return tags[:5]

    def promotion_stats(self) -> dict:
        from collections import Counter
        directions = Counter(p["direction"] for p in self.promotions)
        return {
            "total_promotions": len(self.promotions),
            "directions": dict(directions),
            "wiki_notes": len(self.wiki.notes),
            "cag_concepts": len(self.cag_data.get("core_concepts", {})),
        }
