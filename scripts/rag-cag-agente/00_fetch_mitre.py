"""
Scarica MITRE ATT&CK Enterprise (STIX bundle ufficiale).
Estrae tecniche, tattiche, mitigazioni, detection notes.
Salva ogni tecnica come file .txt in corpus/mitre/.

Fonte: https://github.com/mitre/cti (enterprise-attack)
"""

import json
import urllib.request
from pathlib import Path

MITRE_URL = (
    "https://raw.githubusercontent.com/mitre/cti/master/"
    "enterprise-attack/enterprise-attack.json"
)
OUT_DIR = Path("corpus/mitre")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def fetch_bundle() -> dict:
    print(f"Download MITRE ATT&CK Enterprise...")
    req = urllib.request.Request(
        MITRE_URL, headers={"User-Agent": "security-lab/1.0"}
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    print(f"Bundle scaricato: {len(data.get('objects', []))} oggetti STIX")
    return data


def extract_techniques(bundle: dict) -> list[dict]:
    objects = bundle.get("objects", [])

    # indice: id STIX → nome (per relazioni)
    id_to_name = {
        o["id"]: o.get("name", "")
        for o in objects
        if o.get("type") in ("attack-pattern", "course-of-action", "x-mitre-tactic")
    }

    # tattiche: external_id → nome
    tactic_map = {}
    for o in objects:
        if o.get("type") == "x-mitre-tactic":
            for ref in o.get("external_references", []):
                if ref.get("source_name") == "mitre-attack":
                    tactic_map[o["x_mitre_shortname"]] = o["name"]

    # relazioni mitigation → technique
    mitigations: dict[str, list[str]] = {}
    for o in objects:
        if o.get("type") == "relationship" and o.get("relationship_type") == "mitigates":
            tid = o["target_ref"]
            src_name = id_to_name.get(o["source_ref"], "")
            if src_name:
                mitigations.setdefault(tid, []).append(src_name)

    techniques = []
    for o in objects:
        if o.get("type") != "attack-pattern":
            continue
        if o.get("x_mitre_deprecated") or o.get("revoked"):
            continue

        # ATT&CK ID (es. T1059)
        attack_id = next(
            (ref["external_id"]
             for ref in o.get("external_references", [])
             if ref.get("source_name") == "mitre-attack"),
            None
        )
        if not attack_id:
            continue

        # solo tecniche (T1xxx), non sub-tecniche (T1059.001) per ora
        # cambia a True per includere anche le sub-tecniche
        is_subtechnique = o.get("x_mitre_is_subtechnique", False)

        name        = o.get("name", "")
        description = o.get("description", "").replace("\n\n", "\n").strip()
        # tronca descrizioni molto lunghe
        if len(description) > 3000:
            description = description[:3000] + "..."

        platforms   = o.get("x_mitre_platforms", [])
        permissions = o.get("x_mitre_permissions_required", [])
        detection   = o.get("x_mitre_detection", "").strip()
        if len(detection) > 1000:
            detection = detection[:1000] + "..."

        # kill chain phases → tattiche
        tactics = [
            tactic_map.get(phase["phase_name"], phase["phase_name"])
            for phase in o.get("kill_chain_phases", [])
            if phase.get("kill_chain_name") == "mitre-attack"
        ]

        mit = mitigations.get(o["id"], [])

        techniques.append({
            "id":          attack_id,
            "name":        name,
            "tactics":     tactics,
            "platforms":   platforms,
            "permissions": permissions,
            "description": description,
            "detection":   detection,
            "mitigations": mit,
            "is_sub":      is_subtechnique,
        })

    return techniques


def technique_to_text(t: dict) -> str:
    lines = [
        f"MITRE ATT&CK: {t['id']} — {t['name']}",
        f"Tattiche: {', '.join(t['tactics']) or 'N/A'}",
        f"Piattaforme: {', '.join(t['platforms']) or 'N/A'}",
        f"Permessi richiesti: {', '.join(t['permissions']) or 'N/A'}",
        "",
        "Descrizione:",
        t["description"],
    ]
    if t["detection"]:
        lines += ["", "Detection:", t["detection"]]
    if t["mitigations"]:
        lines += ["", "Mitigazioni:", *[f"  - {m}" for m in t["mitigations"][:8]]]
    return "\n".join(lines)


def main():
    bundle     = fetch_bundle()
    techniques = extract_techniques(bundle)

    parent_techs = [t for t in techniques if not t["is_sub"]]
    sub_techs    = [t for t in techniques if t["is_sub"]]
    print(f"\nTecniche estratte: {len(parent_techs)} parent + {len(sub_techs)} sub-tecniche")

    saved = 0
    for t in techniques:
        text  = technique_to_text(t)
        fname = OUT_DIR / f"{t['id']}.txt"
        fname.write_text(text, encoding="utf-8")
        saved += 1

    # stats per tattica
    from collections import Counter
    tactic_counts = Counter(
        tactic
        for t in parent_techs
        for tactic in t["tactics"]
    )
    print("\nDistribuzione per tattica:")
    for tactic, count in tactic_counts.most_common():
        print(f"  {tactic:35s} {count:3d} tecniche")

    print(f"\nSalvate: {saved} file in {OUT_DIR}")
    print(f"Totale file: {sum(1 for _ in OUT_DIR.glob('*.txt'))}")


if __name__ == "__main__":
    main()
