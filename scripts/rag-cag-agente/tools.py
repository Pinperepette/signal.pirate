"""
MCP-style tool definitions (prototype: Python function calling).

  query_cve   → NVD API reale
  search_web  → mock con latenza artificiale (simula Shodan/GreyNoise/Exploit-DB)
  run_code    → subprocess isolato con blocklist
"""

import json
import re
import subprocess
import time
import random
import urllib.request
import urllib.error
from typing import Any

# ── Schema Anthropic tool_use ─────────────────────────────────────────────────

TOOL_SCHEMAS = [
    {
        "name": "query_cve",
        "description": (
            "Recupera i dettagli di una CVE dalla NVD (National Vulnerability Database). "
            "Ritorna descrizione, CVSS score, severity, CWE, data pubblicazione. "
            "Usare solo con CVE-ID specifici nel formato CVE-YYYY-NNNNN."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cve_id": {
                    "type": "string",
                    "description": "CVE ID, es: CVE-2024-6387"
                }
            },
            "required": ["cve_id"]
        }
    },
    {
        "name": "search_web",
        "description": (
            "Simula una ricerca su fonti security specializzate (Shodan, GreyNoise, Exploit-DB, NVD). "
            "Include latenza artificiale per simulare comportamento reale."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query":  {"type": "string"},
                "source": {
                    "type": "string",
                    "enum": ["nvd", "shodan", "greynoise", "exploit-db"],
                    "description": "Fonte da interrogare"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "run_code",
        "description": (
            "Esegue un frammento Python in un subprocess isolato (timeout 5s). "
            "Permette: math, json, re, hashlib, base64, collections, statistics. "
            "Blocca: os, sys, subprocess, open, exec, eval. "
            "Solo per analisi dati, mai per costruire exploit."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "code":    {"type": "string"},
                "timeout": {"type": "integer", "default": 5}
            },
            "required": ["code"]
        }
    }
]

# ── Implementazioni ───────────────────────────────────────────────────────────

def query_cve(cve_id: str) -> dict:
    cve_id = cve_id.strip().upper()
    if not re.match(r"^CVE-\d{4}-\d{1,7}$", cve_id):
        return {"error": f"formato CVE non valido: {cve_id}"}

    url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_id}"
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "security-research-lab/1.0"}
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read())

        vulns = data.get("vulnerabilities", [])
        if not vulns:
            return {"error": f"{cve_id} non trovata nel NVD"}

        cve = vulns[0]["cve"]
        desc = next(
            (d["value"] for d in cve.get("descriptions", []) if d["lang"] == "en"),
            "no description available"
        )

        metrics = cve.get("metrics", {})
        cvss_score = severity = vector = None
        for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            if key in metrics and metrics[key]:
                m = metrics[key][0]
                cvss_data = m.get("cvssData", {})
                cvss_score = cvss_data.get("baseScore")
                severity   = cvss_data.get("baseSeverity") or m.get("baseSeverity")
                vector     = cvss_data.get("vectorString")
                break

        weaknesses = [
            d["value"]
            for w in cve.get("weaknesses", [])
            for d in w.get("description", [])
            if d.get("value", "").startswith("CWE")
        ]

        references = [r["url"] for r in cve.get("references", [])[:3]]

        return {
            "cve_id":      cve_id,
            "description": desc,
            "cvss_score":  cvss_score,
            "severity":    severity,
            "cvss_vector": vector,
            "weaknesses":  weaknesses,
            "published":   cve.get("published", "")[:10],
            "references":  references,
            "source":      "NVD (reale)",
        }

    except urllib.error.URLError as e:
        return {"error": f"NVD non raggiungibile: {e}"}
    except Exception as e:
        return {"error": str(e)}


_MOCK_TEMPLATES = {
    "shodan": (
        "[Shodan] '{q}': {n} host esposti. "
        "Top banner: OpenSSH 8.2p1. "
        "AS più frequenti: AS15169 Google, AS8075 Microsoft, AS16509 Amazon. "
        "Geo: US 34%, DE 12%, CN 11%."
    ),
    "greynoise": (
        "[GreyNoise] '{q}': {n} IP attivi nelle ultime 24h. "
        "Classificati: {m} malicious, {b} benign. "
        "Top tags: #ssh-scanner, #log4j-scanner, #credential-stuffing. "
        "Trend: +18% rispetto alla settimana scorsa."
    ),
    "exploit-db": (
        "[Exploit-DB] '{q}': {e} exploit pubblici trovati. "
        "Più recente: 2024-11-22, tipo RCE, verified. "
        "Linguaggi: Python 2, Ruby 1. "
        "Piattaforme: Linux/x86_64, Windows x64."
    ),
    "nvd": (
        "[NVD search] '{q}': {e} CVE correlate. "
        "Score medio: 7.8. Più severe: CVSS 9.8 (RCE), 8.6 (auth bypass). "
        "Trend: +23% CVE critiche rispetto all'anno precedente."
    ),
}

def search_web(query: str, source: str = "nvd") -> dict:
    delay = random.uniform(0.4, 1.4)
    time.sleep(delay)

    tmpl = _MOCK_TEMPLATES.get(source, "[mock] nessun risultato per '{q}'")
    result = tmpl.format(
        q=query,
        n=random.randint(200, 5000),
        m=random.randint(50, 300),
        b=random.randint(100, 800),
        e=random.randint(2, 12),
    )
    return {
        "source":     source,
        "query":      query,
        "latency_ms": int(delay * 1000),
        "result":     result,
    }


_BLOCKLIST = [
    "import os", "import sys", "import subprocess",
    "__import__", "open(", "exec(", "eval(",
    "shutil", "socket", "pathlib", "glob",
]

def run_code(code: str, timeout: int = 5) -> dict:
    for blocked in _BLOCKLIST:
        if blocked in code:
            return {"error": f"bloccato: '{blocked}' non permesso in sandbox"}

    wrapper = (
        "import math, json, re, hashlib, base64, "
        "collections, itertools, statistics\n"
        + code
    )
    try:
        result = subprocess.run(
            ["python3", "-c", wrapper],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "stdout":     result.stdout.strip(),
            "stderr":     result.stderr.strip() if result.returncode != 0 else "",
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"timeout ({timeout}s)"}
    except Exception as e:
        return {"error": str(e)}


# ── Dispatcher ────────────────────────────────────────────────────────────────

def execute_tool(name: str, inputs: dict) -> Any:
    handlers = {
        "query_cve":  lambda i: query_cve(i["cve_id"]),
        "search_web": lambda i: search_web(i["query"], i.get("source", "nvd")),
        "run_code":   lambda i: run_code(i["code"], i.get("timeout", 5)),
    }
    handler = handlers.get(name)
    if not handler:
        return {"error": f"tool '{name}' non trovato"}
    return handler(inputs)
