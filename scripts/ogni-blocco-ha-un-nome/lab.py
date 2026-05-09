#!/usr/bin/env python3
"""
3-way comparison lab: same workload, three formats, three agents.

Same logical incident-response plan rendered as Markdown, HTML and AGD.
12 logical edit operations from 3 agents (analyst / responder / auditor).
For each format we measure how cleanly the workload lands.

No Redis required for v1: the architectural pattern (Redis Streams + agdd
demon) is described in the article; here we run the ops sequentially in
a single process and compare the *editing primitives* offered by each
format.

Run:
    pip install beautifulsoup4 lxml
    python3 lab.py

Output:
    output/final.md, output/final.html, output/final.agd
    output/report.md  ← copy/paste into the article
"""

import difflib
import json
import os
import re
import shutil
import subprocess
import tempfile
from bs4 import BeautifulSoup, NavigableString


def diff_noise(before, after):
    """Count +/- lines in the unified diff. Smaller = cleaner edit signal."""
    diff = list(difflib.unified_diff(
        before.splitlines(), after.splitlines(), n=0, lineterm=""
    ))
    return sum(
        1 for line in diff
        if (line.startswith("+") and not line.startswith("+++"))
        or (line.startswith("-") and not line.startswith("---"))
    )

AGD = os.path.expanduser("~/.cargo/bin/agd")
HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(HERE, "output")


# ============================================================
#  Logical edit operation
# ============================================================
class LogicalOp:
    __slots__ = ("kind", "target", "payload", "agent", "ts")

    def __init__(self, kind, target, payload, agent, ts):
        self.kind = kind          # "append_item" | "set_attr"
        self.target = target      # logical id: findings | actions | signed-off | root
        self.payload = payload
        self.agent = agent
        self.ts = ts

    def to_record(self):
        return json.dumps({
            "ts": self.ts,
            "agent": self.agent,
            "kind": self.kind,
            "target": self.target,
            "payload": self.payload,
        }, separators=(",", ":"))


# ============================================================
#  Initial documents (same logical content, three encodings)
# ============================================================
INITIAL_MD = """# Incident 2026-05-09: SSH brute force

## Findings

## Mitigation actions

## Sign-off
"""

INITIAL_HTML = """<!DOCTYPE html>
<html><body>
<h1 id="root">Incident 2026-05-09: SSH brute force</h1>
<section id="findings"><h2>Findings</h2><ul></ul></section>
<section id="actions"><h2>Mitigation actions</h2><ul></ul></section>
<section id="signed-off"><h2>Sign-off</h2><ul></ul></section>
</body></html>
"""

INITIAL_AGD = """@meta title="Incident 2026-05-09: SSH brute force"

@h1 SSH brute force [#root]

@h2 Findings [#findings-h]
@ul [#findings]

@h2 Mitigation actions [#actions-h]
@ul [#actions]

@h2 Sign-off [#signed-off-h]
@ul [#signed-off]
"""


# ============================================================
#  Adapter: Markdown — best-practice string editing via regex
# ============================================================
SECTION_NAME_BY_ID = {
    "findings":   "Findings",
    "actions":    "Mitigation actions",
    "signed-off": "Sign-off",
}


def apply_md(content, op):
    if op.kind == "append_item":
        # Markdown has no stable IDs — we look up by *current* section name,
        # so any prior `rename_section` invalidates this lookup.
        section_name = SECTION_NAME_BY_ID.get(op.target)
        if not section_name:
            return content, "target_not_found"
        pattern = rf"(## {re.escape(section_name)}\s*\n)((?:.*\n)*?)(##|\Z)"
        m = re.search(pattern, content)
        if not m:
            return content, "target_not_found"
        head, body, tail = m.group(1), m.group(2), m.group(3)
        new_body = body + f"- {op.payload['text']}\n"
        return content[:m.start()] + head + new_body + tail + content[m.end():], "applied"

    if op.kind == "rename_section":
        section_name = SECTION_NAME_BY_ID.get(op.target)
        if not section_name:
            return content, "target_not_found"
        pattern = rf"^## {re.escape(section_name)}\s*$"
        if not re.search(pattern, content, re.MULTILINE):
            return content, "target_not_found"
        new_content = re.sub(
            pattern, f"## {op.payload['new_name']}", content, count=1, flags=re.MULTILINE
        )
        # Update the local registry — but in a real distributed scenario other
        # agents won't see this update, which is precisely the failure mode
        # this op exposes. We deliberately do NOT update SECTION_NAME_BY_ID,
        # to simulate the inter-agent communication gap.
        return new_content, "applied"

    if op.kind == "set_attr":
        if op.target != "root":
            return content, "target_not_found"
        marker = f"<!-- {op.payload['key']}={op.payload['value']} -->"
        existing = re.search(rf"<!-- {re.escape(op.payload['key'])}=[^>]*-->", content)
        if existing:
            return content[:existing.start()] + marker + content[existing.end():], "applied"
        h1 = re.search(r"^# .+\n", content, re.MULTILINE)
        if not h1:
            return content, "target_not_found"
        return content[:h1.end()] + marker + "\n" + content[h1.end():], "applied"

    return content, "target_not_found"


# ============================================================
#  Adapter: HTML — best-practice DOM via BeautifulSoup
# ============================================================
def apply_html(content, op):
    soup = BeautifulSoup(content, "html.parser")
    if op.kind == "append_item":
        section = soup.find(id=op.target)
        if not section:
            return content, "target_not_found"
        ul = section.find("ul")
        if ul is None:
            return content, "target_not_found"
        li = soup.new_tag("li")
        li.string = op.payload["text"]
        ul.append(li)
        return str(soup), "applied"

    if op.kind == "rename_section":
        section = soup.find(id=op.target)
        if not section:
            return content, "target_not_found"
        h2 = section.find("h2")
        if h2 is None:
            return content, "target_not_found"
        h2.string = op.payload["new_name"]
        return str(soup), "applied"

    if op.kind == "set_attr":
        target = soup.find(id=op.target)
        if target is None:
            return content, "target_not_found"
        target[f"data-{op.payload['key']}"] = op.payload["value"]
        return str(soup), "applied"

    return content, "target_not_found"


# ============================================================
#  Adapter: AGD — native edit operations via the agd CLI
# ============================================================
def _agd_call(args, stdin=None):
    return subprocess.run(
        args, input=stdin, text=True, check=True, capture_output=True
    ).stdout


def apply_agd(content, op):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".agd", delete=False) as f:
        f.write(content)
        tmp = f.name
    try:
        if op.kind == "append_item":
            ast = json.loads(_agd_call([AGD, "parse", "--json", tmp]))
            target_block = next(
                (b for b in ast["blocks"] if b.get("id") == op.target),
                None,
            )
            if not target_block or target_block["kind"] != "ul":
                return content, "target_not_found"
            existing_items = target_block["content"]["value"]
            new_items = existing_items + [
                [{"kind": "text", "text": op.payload["text"]}]
            ]
            new_block = {
                "kind": "ul",
                "attrs": target_block.get("attrs") or {},
                "id": op.target,
                "content": {"type": "items", "value": new_items},
            }
            edit_op = {"op": "replace", "id": op.target, "with": new_block}
            new_content = _agd_call([AGD, "edit", tmp, "--op", json.dumps(edit_op)])
            return new_content, "applied"

        if op.kind == "rename_section":
            # Rename means: replace the heading block keyed `<target>-h` with
            # the same kind/id but new inline content.
            heading_id = f"{op.target}-h"
            ast = json.loads(_agd_call([AGD, "parse", "--json", tmp]))
            heading_block = next(
                (b for b in ast["blocks"] if b.get("id") == heading_id),
                None,
            )
            if not heading_block:
                return content, "target_not_found"
            new_block = {
                "kind": heading_block["kind"],
                "attrs": heading_block.get("attrs") or {},
                "id": heading_id,
                "content": {
                    "type": "inline",
                    "value": [{"kind": "text", "text": op.payload["new_name"]}],
                },
            }
            edit_op = {"op": "replace", "id": heading_id, "with": new_block}
            new_content = _agd_call([AGD, "edit", tmp, "--op", json.dumps(edit_op)])
            return new_content, "applied"

        if op.kind == "set_attr":
            edit_op = {
                "op": "set_attr",
                "id": op.target,
                "key": op.payload["key"],
                "value": op.payload["value"],
            }
            try:
                new_content = _agd_call([AGD, "edit", tmp, "--op", json.dumps(edit_op)])
                return new_content, "applied"
            except subprocess.CalledProcessError:
                return content, "target_not_found"

        return content, "target_not_found"
    except subprocess.CalledProcessError:
        return content, "target_not_found"
    finally:
        os.unlink(tmp)


# ============================================================
#  Workload — 12 ops, 3 agents, 1 deliberate attribute conflict
# ============================================================
WORKLOAD = [
    LogicalOp("append_item", "findings", {"text": "auth.log: 4127 failed SSH attempts from 185.220.101.0/24, 14:02-14:38"}, "analyst", ts=1),
    LogicalOp("append_item", "findings", {"text": "Targeted users: root, admin, deploy, ubuntu"}, "analyst", ts=2),
    LogicalOp("append_item", "findings", {"text": "Source IPs match Tor exit nodes (TorDNSEL list)"}, "analyst", ts=3),

    # The analyst refactors: "Findings" → "Initial findings". Every format
    # must keep the logical ID `findings` resolvable AFTER this rename.
    # Markdown has no stable id mechanism, so subsequent ops by name break.
    LogicalOp("rename_section", "findings", {"new_name": "Initial findings"}, "analyst", ts=4),

    LogicalOp("set_attr",    "root",     {"key": "severity", "value": "high"}, "analyst", ts=5),

    LogicalOp("append_item", "actions",  {"text": "Block 185.220.101.0/24 at edge firewall"}, "responder", ts=6),
    LogicalOp("append_item", "actions",  {"text": "Disable password auth, enforce key-only on SSH"}, "responder", ts=7),
    LogicalOp("append_item", "actions",  {"text": "Rotate credentials for root and deploy"}, "responder", ts=8),
    LogicalOp("append_item", "actions",  {"text": "Add fail2ban rule: 5 attempts then 24h ban"}, "responder", ts=9),

    # Auditor adds a late finding to the *logical* findings section. In MD
    # the section was renamed at ts=4 → regex-by-name fails. In HTML and
    # AGD the id `findings` is still resolvable.
    LogicalOp("append_item", "findings", {"text": "Same source attempted MySQL port 3306 at 15:11"}, "auditor", ts=10),
    LogicalOp("append_item", "signed-off", {"text": "Reviewed by analyst, A. Amani"}, "auditor", ts=11),
    LogicalOp("append_item", "signed-off", {"text": "Approved by SRE, pinperepette"}, "auditor", ts=12),
]


# ============================================================
#  Integrity & quality checks
# ============================================================
def integrity_md(content):
    missing = []
    for op in WORKLOAD:
        if op.kind == "append_item":
            if op.payload["text"] not in content:
                missing.append(op.payload["text"][:50])
    return (not missing), missing


def integrity_html(content):
    soup = BeautifulSoup(content, "html.parser")
    missing = []
    for op in WORKLOAD:
        if op.kind == "append_item":
            section = soup.find(id=op.target)
            if not section:
                missing.append(f"section {op.target} missing")
                continue
            items = [li.get_text() for li in section.find_all("li")]
            if op.payload["text"] not in items:
                missing.append(op.payload["text"][:50])
    return (not missing), missing


def integrity_agd(content):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".agd", delete=False) as f:
        f.write(content); tmp = f.name
    try:
        ast = json.loads(_agd_call([AGD, "parse", "--json", tmp]))
        missing = []
        for op in WORKLOAD:
            if op.kind == "append_item":
                block = next(
                    (b for b in ast["blocks"] if b.get("id") == op.target),
                    None,
                )
                if not block:
                    missing.append(f"block #{op.target} missing")
                    continue
                items_lines = block["content"]["value"]
                texts = [
                    n.get("text", "")
                    for line in items_lines
                    for n in line
                ]
                if op.payload["text"] not in texts:
                    missing.append(op.payload["text"][:50])
        return (not missing), missing
    finally:
        os.unlink(tmp)


def canonical_md(content):
    """No real canonical form — return as-is."""
    return content


def canonical_html(content):
    """BeautifulSoup re-serialization is the closest thing to canonical."""
    return str(BeautifulSoup(content, "html.parser"))


def canonical_agd(content):
    return _agd_call([AGD, "format", "-"], stdin=content)


def canonical_idempotent(canon_fn, content):
    once = canon_fn(content)
    twice = canon_fn(once)
    return once == twice


# ============================================================
#  Run
# ============================================================
def run_format(name, init, apply_fn, integ_fn, canon_fn, outfile):
    content = init
    applied = not_found = errored = 0
    bytes_per_op = []
    diff_noise_per_op = []
    audit_log = []

    for op in WORKLOAD:
        before = content
        record = op.to_record()
        audit_log.append(record)
        new_content, status = apply_fn(content, op)
        delta = len(new_content) - len(before)
        noise = diff_noise(before, new_content)
        if status == "applied":
            applied += 1
        elif status == "target_not_found":
            not_found += 1
        else:
            errored += 1
        bytes_per_op.append((status, delta, len(record)))
        diff_noise_per_op.append(noise)
        content = new_content

    ok, missing = integ_fn(content)

    canon_ok = canonical_idempotent(canon_fn, content)
    canon_size = len(canon_fn(content))

    with open(os.path.join(OUTPUT, outfile), "w") as f:
        f.write(content)
    with open(os.path.join(OUTPUT, f"{name}.audit.jsonl"), "w") as f:
        f.write("\n".join(audit_log) + "\n")

    return {
        "name": name,
        "applied": applied,
        "not_found": not_found,
        "errored": errored,
        "final_size": len(content),
        "canonical_size": canon_size,
        "canonical_idempotent": canon_ok,
        "integrity": ok,
        "missing": missing,
        "avg_bytes_per_op": sum(d for (_, d, _) in bytes_per_op) // max(1, len(bytes_per_op)),
        "avg_audit_record_size": sum(r for (_, _, r) in bytes_per_op) // max(1, len(bytes_per_op)),
        "avg_diff_noise_lines": round(sum(diff_noise_per_op) / max(1, len(diff_noise_per_op)), 1),
        "max_diff_noise_lines": max(diff_noise_per_op) if diff_noise_per_op else 0,
    }


def main():
    if not os.path.isfile(AGD):
        raise SystemExit(f"agd binary not found at {AGD} — install with `cargo install --path /Users/pinperepette/Porgetti/MDF2/agd`")
    os.makedirs(OUTPUT, exist_ok=True)

    formats = [
        ("markdown", INITIAL_MD,   apply_md,   integrity_md,   canonical_md,   "final.md"),
        ("html",     INITIAL_HTML, apply_html, integrity_html, canonical_html, "final.html"),
        ("agd",      INITIAL_AGD,  apply_agd,  integrity_agd,  canonical_agd,  "final.agd"),
    ]

    results = []
    for spec in formats:
        print(f"\n=== {spec[0].upper()} ===", flush=True)
        r = run_format(*spec)
        results.append(r)
        print(f"  applied:                {r['applied']}/{len(WORKLOAD)}")
        print(f"  not_found:              {r['not_found']}")
        print(f"  errored:                {r['errored']}")
        print(f"  integrity:              {'PASS' if r['integrity'] else 'FAIL — ' + str(r['missing'])}")
        print(f"  final size:             {r['final_size']} B")
        print(f"  canonical size:         {r['canonical_size']} B")
        print(f"  canonical idempotent:   {r['canonical_idempotent']}")
        print(f"  avg bytes/op (file):    {r['avg_bytes_per_op']}")
        print(f"  avg audit record size:  {r['avg_audit_record_size']} B")
        print(f"  avg diff noise:         {r['avg_diff_noise_lines']} lines/op")
        print(f"  max diff noise:         {r['max_diff_noise_lines']} lines (worst op)")

    # Build the report.md table
    lines = []
    lines.append("# Lab — three formats, same workload\n")
    lines.append("12 logical edit operations across 3 agents (analyst / responder / auditor) on a shared incident-response plan rendered three ways.\n")
    lines.append("| metric                     | markdown | html | agd |")
    lines.append("|----------------------------|---------:|-----:|----:|")
    rows = [
        ("ops applied (out of 12)",       lambda r: f"{r['applied']}/12"),
        ("ops not_found",                 lambda r: str(r['not_found'])),
        ("ops errored",                   lambda r: str(r['errored'])),
        ("integrity (all items present)", lambda r: "PASS" if r['integrity'] else "FAIL"),
        ("final file size (bytes)",       lambda r: f"{r['final_size']}"),
        ("canonical idempotent",          lambda r: "yes" if r['canonical_idempotent'] else "no"),
        ("avg bytes added per op",        lambda r: f"{r['avg_bytes_per_op']}"),
        ("avg diff noise (+/- lines/op)", lambda r: f"{r['avg_diff_noise_lines']}"),
        ("max diff noise (worst op)",     lambda r: f"{r['max_diff_noise_lines']}"),
    ]
    by_name = {r['name']: r for r in results}
    for label, fn in rows:
        lines.append(
            f"| {label:26} | {fn(by_name['markdown']):>8} | {fn(by_name['html']):>4} | {fn(by_name['agd']):>3} |"
        )

    report = "\n".join(lines) + "\n"
    with open(os.path.join(OUTPUT, "report.md"), "w") as f:
        f.write(report)

    print("\n\n" + report)
    print(f"\n→ output written to {OUTPUT}/")


if __name__ == "__main__":
    main()
