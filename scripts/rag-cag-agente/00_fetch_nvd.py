"""
Scarica CVE reali da NVD API v2.0.
Ultimi 120 giorni, CVSS >= 7.0 (HIGH + CRITICAL).
Salva ogni CVE come file .txt in corpus/nvd/.

NVD rate limit: 5 req/s senza API key — lo rispettiamo.
"""

import json
import time
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUT_DIR   = Path("corpus/nvd")
CVSS_MIN  = 7.0
DAYS_BACK = 120
PAGE_SIZE = 100   # max NVD

OUT_DIR.mkdir(parents=True, exist_ok=True)


def fetch_page(start_index: int, start_date: str, end_date: str) -> dict:
    params = urllib.parse.urlencode({
        "pubStartDate":  start_date,
        "pubEndDate":    end_date,
        "cvssV3Severity": "HIGH",   # prima HIGH
        "resultsPerPage": PAGE_SIZE,
        "startIndex":     start_index,
    })
    url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "security-lab/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def fetch_all(severity: str, start_date: str, end_date: str) -> list[dict]:
    params = urllib.parse.urlencode({
        "pubStartDate":   start_date,
        "pubEndDate":     end_date,
        "cvssV3Severity": severity,
        "resultsPerPage": PAGE_SIZE,
        "startIndex":     0,
    })
    url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "security-lab/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())

    total   = data["totalResults"]
    results = data.get("vulnerabilities", [])
    print(f"  {severity}: {total} totali, prima pagina {len(results)}")

    # pagine successive
    idx = PAGE_SIZE
    while idx < total and idx < 2000:  # cap 2000 per severità
        time.sleep(0.25)  # rispetta rate limit
        params = urllib.parse.urlencode({
            "pubStartDate":   start_date,
            "pubEndDate":     end_date,
            "cvssV3Severity": severity,
            "resultsPerPage": PAGE_SIZE,
            "startIndex":     idx,
        })
        url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "security-lab/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            page = json.loads(resp.read())
        results.extend(page.get("vulnerabilities", []))
        idx += PAGE_SIZE
        print(f"    → {len(results)}/{min(total, 2000)}")

    return results


def cve_to_text(vuln: dict) -> tuple[str, str]:
    cve = vuln["cve"]
    cve_id = cve["id"]

    desc = next(
        (d["value"] for d in cve.get("descriptions", []) if d["lang"] == "en"),
        "No description."
    )

    metrics = cve.get("metrics", {})
    cvss_score = severity = vector = None
    for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        if key in metrics and metrics[key]:
            m = metrics[key][0]
            d = m.get("cvssData", {})
            cvss_score = d.get("baseScore")
            severity   = d.get("baseSeverity") or m.get("baseSeverity")
            vector     = d.get("vectorString")
            break

    weaknesses = [
        d["value"]
        for w in cve.get("weaknesses", [])
        for d in w.get("description", [])
        if d.get("value", "").startswith("CWE")
    ]

    published  = cve.get("published", "")[:10]
    references = [r["url"] for r in cve.get("references", [])[:5]]
    configs    = cve.get("configurations", [])
    affected   = []
    for node in configs:
        for match in node.get("cpeMatch", []):
            uri = match.get("criteria", "")
            # estrai prodotto dall'URI cpe
            parts = uri.split(":")
            if len(parts) >= 5:
                affected.append(f"{parts[3]} {parts[4]}")
    affected = list(set(affected))[:10]

    lines = [
        f"CVE ID: {cve_id}",
        f"Pubblicata: {published}",
        f"CVSS Score: {cvss_score} ({severity})",
        f"CVSS Vector: {vector or 'N/A'}",
        f"CWE: {', '.join(weaknesses) or 'N/A'}",
        f"Prodotti affetti: {', '.join(affected) or 'N/A'}",
        "",
        "Descrizione:",
        desc,
    ]
    if references:
        lines += ["", "Riferimenti:"] + references

    return cve_id, "\n".join(lines)


def main():
    now   = datetime.now(timezone.utc)
    start = (now - timedelta(days=DAYS_BACK)).strftime("%Y-%m-%dT%H:%M:%S.000")
    end   = now.strftime("%Y-%m-%dT%H:%M:%S.000")

    print(f"Fetch CVE da NVD: {start[:10]} → {end[:10]}")
    print(f"CVSS minimo: {CVSS_MIN} | Directory: {OUT_DIR}")
    print()

    all_vulns = []
    for severity in ("CRITICAL", "HIGH"):
        print(f"Scarico {severity}...")
        try:
            vulns = fetch_all(severity, start, end)
            all_vulns.extend(vulns)
        except Exception as e:
            print(f"  Errore: {e}")
        time.sleep(0.5)

    # dedup per CVE ID
    seen = set()
    unique = []
    for v in all_vulns:
        cid = v["cve"]["id"]
        if cid not in seen:
            seen.add(cid)
            unique.append(v)

    print(f"\nTotale CVE uniche: {len(unique)}")
    print("Salvo su disco...")

    saved = 0
    skipped = 0
    for v in unique:
        # filtra su CVSS score effettivo
        metrics = v["cve"].get("metrics", {})
        score = None
        for key in ("cvssMetricV31", "cvssMetricV30"):
            if key in metrics and metrics[key]:
                score = metrics[key][0].get("cvssData", {}).get("baseScore")
                break
        if score and score < CVSS_MIN:
            skipped += 1
            continue

        cve_id, text = cve_to_text(v)
        fname = OUT_DIR / f"{cve_id}.txt"
        fname.write_text(text, encoding="utf-8")
        saved += 1

    print(f"\nSalvate: {saved} CVE")
    print(f"Saltate (score < {CVSS_MIN}): {skipped}")
    print(f"Directory: {OUT_DIR} ({sum(1 for _ in OUT_DIR.glob('*.txt'))} file)")


if __name__ == "__main__":
    main()
