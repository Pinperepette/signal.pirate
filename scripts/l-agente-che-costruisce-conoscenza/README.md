# L'Agente Che Costruisce Conoscenza — Lab

Seguito di [L'Agente Che Non Inventa](../rag-cag-agente/).

Aggiunge un **Wiki layer** tra Memory e CAG:
`MEMORY → WIKI → CAG` con promozione/demozione automatica.

## Prerequisiti

```bash
pip install anthropic sentence-transformers rich numpy
export ANTHROPIC_API_KEY=sk-...
```

Corpus NVD + MITRE dal lab precedente (opzionale, migliora il RAG):
```bash
cd ../rag-cag-agente && python 00_fetch_nvd.py && python 00_fetch_mitre.py
```

## Demo

```bash
python run_demo.py
```

3 query reali via API, 3 comportamenti diversi:
1. CVE-2024-6387 → agente risponde, wiki crea note + link
2. CVE-2024-3094 → agente risponde, wiki collega al grafo esistente
3. Pattern OpenSSH → routing CAG_WIKI, bypassa RAG

Output: `output/wiki/` (apribile in Obsidian), `output/trace.json`.

## Struttura

```
wiki_manager.py        # vault Obsidian: note atomiche, backlink, search, grafo
knowledge_layer.py     # promozione memory→wiki→CAG, demozione CAG→wiki
meta_controller_v2.py  # routing con route CAG_WIKI
agent_wiki.py          # agente completo con wiki layer
run_demo.py            # 3 query reali via API
knowledge/core.json    # CAG base
```
