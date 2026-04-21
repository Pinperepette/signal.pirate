# rag-cag-agente

Lab per l'articolo [L'Agente Che Non Inventa](../../articoli/l-agente-che-non-inventa.html).

Agente AI a 7 layer: Meta-controller → CAG → RAG → Stream → Tool → Reflection → Memory.
Corpus reale: 2401 CVE da NVD API + 691 tecniche MITRE ATT&CK.
Demo autonomo: analisi PCAP senza query umane.

## Prerequisiti

- Python 3.10+
- tshark: `brew install wireshark` (o scarica Wireshark da wireshark.org)
- ANTHROPIC_API_KEY
- NVD API key (gratuita su nvd.nist.gov/developers/request-an-api-key)

## Setup

```bash
cd scripts/rag-cag-agente
python -m venv .venv && source .venv/bin/activate
pip install anthropic sentence-transformers numpy rich
```

## Costruisci il corpus

```bash
# CVE reali da NVD (ultimi 120 giorni, CVSS >= 7)
python 00_fetch_nvd.py

# MITRE ATT&CK Enterprise (bundle ufficiale GitHub)
python 00_fetch_mitre.py
```

## Demo 1 — 3 query, 3 route diversi

```bash
TOKENIZERS_PARALLELISM=false python run_demo.py
```

Mostra il meta-controller in azione: CAG-only, Full+Stream, CAG+RAG+MCP.

## Demo 2 — PCAP autonomo

```bash
TOKENIZERS_PARALLELISM=false python run_incident.py
```

L'agente monitora il replay del PCAP, rileva l'attack chain (MailPoet exploit → webshell → Meterpreter C2), e produce un incident report completo senza query umane.

## File principali

| File | Cosa fa |
|------|---------|
| `meta_controller.py` | Routing deterministico + fallback LLM |
| `agent.py` | Pipeline completa: CAG → RAG → stream → generate → reflect → memory |
| `tools.py` | query_cve (NVD reale), search_web, run_code |
| `memory_manager.py` | Memoria persistente con decay |
| `pcap_stream.py` | Parser PCAP con tshark, classificazione eventi |
| `run_demo.py` | 3 query demo |
| `run_incident.py` | Demo autonomo su PCAP |
| `00_fetch_nvd.py` | Scarica corpus CVE da NVD |
| `00_fetch_mitre.py` | Scarica corpus MITRE ATT&CK |
| `knowledge/core.json` | CAG: conoscenza stabile pre-caricata |
| `pcaps/metasploitable.pcap` | PCAP AngstromCTF 2016 |
