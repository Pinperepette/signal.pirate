#!/usr/bin/env python3
"""
Multi-agent edit lab — Redis Streams version.

Three agents (analyst / responder / auditor) emit edit operations
concurrently to three independent streams (one per format). Three
daemons (one per format) consume FIFO, apply ops to per-format
state stored in Redis Hashes, ack each message.

The streams are also the audit log: XRANGE replays the full edit
history across all three formats. State at any point in time is
recoverable by replaying ops from offset 0.

Single-file dispatch via `--mode`:

  init                       initialise per-format state in Redis
  daemon-{md,html,agd}       loop XREADGROUP → apply → HSET → XACK
  agent-{analyst,responder,auditor}
                             sleep with realistic timing, emit ops
  compare                    read final state + streams, print report
  drain                      delete the lab keys and groups

`run_lab.sh` orchestrates a full run.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, asdict
from typing import List, Tuple

import redis
from bs4 import BeautifulSoup

# ============================================================
#  Configuration
# ============================================================
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6391"))

DOC_ID = "incident-2026-05-09"
FORMATS = ["md", "html", "agd"]

OPS_STREAM = lambda fmt: f"agd-lab:{fmt}:ops"
STATE_KEY  = lambda fmt: f"agd-lab:{fmt}:state"
GROUP      = lambda fmt: f"daemon-{fmt}"
CONSUMER   = lambda fmt: f"daemon-{fmt}-1"

AGD_BIN = os.path.expanduser("~/.cargo/bin/agd")
HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(HERE, "output")


# ============================================================
#  Op + workload
# ============================================================
@dataclass
class Op:
    kind: str       # append_item | rename_section | set_attr
    target: str     # findings | actions | signed-off | root
    payload: dict
    agent: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"))

    @classmethod
    def from_json(cls, s: str) -> "Op":
        return cls(**json.loads(s))


# (delay_ms_from_run_start, op)
def workload_for(agent: str) -> List[Tuple[int, Op]]:
    if agent == "analyst":
        return [
            (   0, Op("append_item", "findings", {"text": "auth.log: 4127 failed SSH attempts from 185.220.101.0/24, 14:02-14:38"}, "analyst")),
            (  80, Op("append_item", "findings", {"text": "Targeted users: root, admin, deploy, ubuntu"}, "analyst")),
            ( 160, Op("append_item", "findings", {"text": "Source IPs match Tor exit nodes (TorDNSEL list)"}, "analyst")),
            ( 240, Op("rename_section", "findings", {"new_name": "Initial findings"}, "analyst")),
            ( 320, Op("set_attr", "meta", {"key": "severity", "value": "high"}, "analyst")),
        ]
    if agent == "responder":
        return [
            (  20, Op("append_item", "actions", {"text": "Block 185.220.101.0/24 at edge firewall"}, "responder")),
            ( 100, Op("append_item", "actions", {"text": "Disable password auth, enforce key-only on SSH"}, "responder")),
            ( 180, Op("append_item", "actions", {"text": "Rotate credentials for root and deploy"}, "responder")),
            ( 260, Op("append_item", "actions", {"text": "Add fail2ban rule: 5 attempts then 24h ban"}, "responder")),
        ]
    if agent == "auditor":
        return [
            ( 400, Op("append_item", "findings", {"text": "Same source attempted MySQL port 3306 at 15:11"}, "auditor")),
            ( 480, Op("append_item", "signed-off", {"text": "Reviewed by analyst, A. Amani"}, "auditor")),
            ( 560, Op("append_item", "signed-off", {"text": "Approved by SRE, pinperepette"}, "auditor")),
        ]
    raise SystemExit(f"unknown agent: {agent}")


# ============================================================
#  Initial documents
# ============================================================
INITIAL_MD = """# Incident 2026-05-09: SSH brute force

## Findings

## Mitigation actions

## Sign-off
"""

INITIAL_HTML = """<!DOCTYPE html>
<html><body>
<div id="meta" data-doc-id="incident-2026-05-09"></div>
<h1 id="root">Incident 2026-05-09: SSH brute force</h1>
<section id="findings"><h2>Findings</h2><ul></ul></section>
<section id="actions"><h2>Mitigation actions</h2><ul></ul></section>
<section id="signed-off"><h2>Sign-off</h2><ul></ul></section>
</body></html>
"""

INITIAL_AGD = """@meta doc_id="incident-2026-05-09" [#meta]

@h1 SSH brute force [#root]

@h2 Findings [#findings-h]
@ul [#findings]

@h2 Mitigation actions [#actions-h]
@ul [#actions]

@h2 Sign-off [#signed-off-h]
@ul [#signed-off]
"""

INITIAL = {"md": INITIAL_MD, "html": INITIAL_HTML, "agd": INITIAL_AGD}


# ============================================================
#  Apply adapters (same as v1, repeated here so v2 stands alone)
# ============================================================
SECTION_NAME_BY_ID = {
    "findings":   "Findings",
    "actions":    "Mitigation actions",
    "signed-off": "Sign-off",
}


def apply_md(content: str, op: Op):
    if op.kind == "append_item":
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
        new_content = re.sub(pattern, f"## {op.payload['new_name']}", content, count=1, flags=re.MULTILINE)
        return new_content, "applied"

    if op.kind == "set_attr":
        # Markdown has no attribute syntax. We use a HTML comment placed
        # right after the H1, regardless of `op.target` (the only logical
        # target in this workload is "meta"). For repeated keys we replace
        # the existing comment.
        marker = f"<!-- {op.payload['key']}={op.payload['value']} -->"
        existing = re.search(rf"<!-- {re.escape(op.payload['key'])}=[^>]*-->", content)
        if existing:
            return content[:existing.start()] + marker + content[existing.end():], "applied"
        h1 = re.search(r"^# .+\n", content, re.MULTILINE)
        if not h1:
            return content, "target_not_found"
        return content[:h1.end()] + marker + "\n" + content[h1.end():], "applied"

    return content, "target_not_found"


def apply_html(content: str, op: Op):
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


def _agd_call(args, stdin=None):
    return subprocess.run(args, input=stdin, text=True, check=True, capture_output=True).stdout


def apply_agd(content: str, op: Op):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".agd", delete=False) as f:
        f.write(content)
        tmp = f.name
    try:
        if op.kind == "append_item":
            ast = json.loads(_agd_call([AGD_BIN, "parse", "--json", tmp]))
            target_block = next((b for b in ast["blocks"] if b.get("id") == op.target), None)
            if not target_block or target_block["kind"] != "ul":
                return content, "target_not_found"
            existing = target_block["content"]["value"]
            new_items = existing + [[{"kind": "text", "text": op.payload["text"]}]]
            new_block = {
                "kind": "ul",
                "attrs": target_block.get("attrs") or {},
                "id": op.target,
                "content": {"type": "items", "value": new_items},
            }
            edit_op = {"op": "replace", "id": op.target, "with": new_block}
            return _agd_call([AGD_BIN, "edit", tmp, "--op", json.dumps(edit_op)]), "applied"

        if op.kind == "rename_section":
            heading_id = f"{op.target}-h"
            ast = json.loads(_agd_call([AGD_BIN, "parse", "--json", tmp]))
            heading = next((b for b in ast["blocks"] if b.get("id") == heading_id), None)
            if not heading:
                return content, "target_not_found"
            new_block = {
                "kind": heading["kind"],
                "attrs": heading.get("attrs") or {},
                "id": heading_id,
                "content": {"type": "inline", "value": [{"kind": "text", "text": op.payload["new_name"]}]},
            }
            edit_op = {"op": "replace", "id": heading_id, "with": new_block}
            return _agd_call([AGD_BIN, "edit", tmp, "--op", json.dumps(edit_op)]), "applied"

        if op.kind == "set_attr":
            edit_op = {"op": "set_attr", "id": op.target, "key": op.payload["key"], "value": op.payload["value"]}
            try:
                return _agd_call([AGD_BIN, "edit", tmp, "--op", json.dumps(edit_op)]), "applied"
            except subprocess.CalledProcessError:
                return content, "target_not_found"

        return content, "target_not_found"
    except subprocess.CalledProcessError:
        return content, "target_not_found"
    finally:
        os.unlink(tmp)


APPLY = {"md": apply_md, "html": apply_html, "agd": apply_agd}


# ============================================================
#  Modes
# ============================================================
def r() -> redis.Redis:
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def mode_init():
    """Reset all lab keys, write initial state."""
    cli = r()
    keys = []
    for fmt in FORMATS:
        keys.append(STATE_KEY(fmt))
        keys.append(OPS_STREAM(fmt))
    if keys:
        cli.delete(*keys)
    for fmt in FORMATS:
        cli.hset(STATE_KEY(fmt), mapping={"content": INITIAL[fmt], "last_status": "init"})
        try:
            cli.xgroup_create(OPS_STREAM(fmt), GROUP(fmt), id="0", mkstream=True)
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise
    print("[init] state and groups ready", flush=True)


def mode_daemon(fmt: str):
    cli = r()
    apply_fn = APPLY[fmt]
    stream = OPS_STREAM(fmt)
    group = GROUP(fmt)
    consumer = CONSUMER(fmt)
    log = open(os.path.join(OUTPUT, f"daemon-{fmt}.log"), "w")
    deadline = time.time() + 8.0  # max wall time before giving up
    while time.time() < deadline:
        msgs = cli.xreadgroup(group, consumer, {stream: ">"}, count=10, block=400)
        if not msgs:
            continue
        deadline = time.time() + 2.0  # extend each time we see traffic
        for _stream, entries in msgs:
            for msg_id, data in entries:
                op = Op.from_json(data["data"])
                content = cli.hget(STATE_KEY(fmt), "content")
                t0 = time.perf_counter()
                new_content, status = apply_fn(content, op)
                dt_ms = (time.perf_counter() - t0) * 1000
                cli.hset(STATE_KEY(fmt), mapping={"content": new_content, "last_status": status})
                cli.xack(stream, group, msg_id)
                log.write(f"{msg_id}\t{op.agent}\t{op.kind}\t{op.target}\t{status}\t{dt_ms:.2f}ms\n")
                log.flush()
    log.close()
    print(f"[daemon-{fmt}] done", flush=True)


def mode_agent(name: str):
    cli = r()
    items = workload_for(name)
    t_start = time.time()
    for delay_ms, op in items:
        target_t = t_start + (delay_ms / 1000.0)
        sleep_for = target_t - time.time()
        if sleep_for > 0:
            time.sleep(sleep_for)
        record = op.to_json()
        for fmt in FORMATS:
            cli.xadd(OPS_STREAM(fmt), {"data": record})
    print(f"[{name}] emitted {len(items)} ops to {len(FORMATS)} streams", flush=True)


def mode_drain():
    cli = r()
    keys = []
    for fmt in FORMATS:
        keys.append(STATE_KEY(fmt))
        keys.append(OPS_STREAM(fmt))
    if keys:
        cli.delete(*keys)
    print("[drain] cleared", flush=True)


def mode_compare():
    cli = r()
    summary = {}
    for fmt in FORMATS:
        content = cli.hget(STATE_KEY(fmt), "content") or ""
        # Save final state
        suffix = "md" if fmt == "md" else ("html" if fmt == "html" else "agd")
        with open(os.path.join(OUTPUT, f"final.{suffix}"), "w") as f:
            f.write(content)

        # Replay stream + count statuses by reading the daemon log
        log_path = os.path.join(OUTPUT, f"daemon-{fmt}.log")
        applied = not_found = errored = 0
        total_dt = 0.0
        n_dt = 0
        if os.path.exists(log_path):
            with open(log_path) as lf:
                for line in lf:
                    parts = line.rstrip("\n").split("\t")
                    if len(parts) < 6:
                        continue
                    status = parts[4]
                    dt_str = parts[5]
                    if status == "applied": applied += 1
                    elif status == "target_not_found": not_found += 1
                    else: errored += 1
                    # Daemons emit either "1.23ms" (Python) or "7us" (Rust agdd)
                    try:
                        if dt_str.endswith("us"):
                            total_dt += float(dt_str[:-2]) / 1000.0
                        elif dt_str.endswith("ms"):
                            total_dt += float(dt_str[:-2])
                        else:
                            total_dt += float(dt_str)
                        n_dt += 1
                    except ValueError:
                        pass

        # Stream length (audit trail size)
        stream_len = cli.xlen(OPS_STREAM(fmt))

        # Replay reconstruction: read full stream, replay onto initial state, compare
        entries = cli.xrange(OPS_STREAM(fmt), "-", "+")
        replay_state = INITIAL[fmt]
        replay_applied = 0
        for _id, data in entries:
            op = Op.from_json(data["data"])
            replay_state, status = APPLY[fmt](replay_state, op)
            if status == "applied":
                replay_applied += 1
        replay_matches_live = (replay_state == content)

        summary[fmt] = {
            "applied": applied,
            "not_found": not_found,
            "errored": errored,
            "final_size": len(content),
            "stream_len": stream_len,
            "replay_applied": replay_applied,
            "replay_matches_live": replay_matches_live,
            "avg_apply_ms": (total_dt / n_dt) if n_dt else 0.0,
        }

    # Build report
    lines = []
    lines.append("# Lab v2 — Redis Streams, three agents, three formats\n")
    lines.append("12 logical edit operations emitted concurrently by 3 agents to 3 independent Redis Streams. One daemon per format consumes FIFO via XREADGROUP, applies, persists state in a Hash, ACKs.\n")
    lines.append("Replay test: re-apply the full stream from offset 0 to a fresh initial state. The replayed state must equal the live state for the audit trail to be authoritative.\n")
    lines.append("| metric                          | markdown | html | agd |")
    lines.append("|---------------------------------|---------:|-----:|----:|")
    def fmt_latency(ms: float) -> str:
        if ms >= 1.0:
            return f"{ms:.2f} ms"
        if ms >= 0.001:
            return f"{ms*1000:.1f} us"
        return f"{ms*1_000_000:.0f} ns"

    rows = [
        ("ops applied",                    lambda s: f"{s['applied']}/12"),
        ("ops not_found",                  lambda s: str(s['not_found'])),
        ("ops errored",                    lambda s: str(s['errored'])),
        ("stream length (audit trail)",    lambda s: str(s['stream_len'])),
        ("replay reconstructs live state", lambda s: "yes" if s['replay_matches_live'] else "no"),
        ("replay applied count",           lambda s: f"{s['replay_applied']}/12"),
        ("final size (bytes)",             lambda s: str(s['final_size'])),
        ("avg apply latency",              lambda s: fmt_latency(s['avg_apply_ms'])),
    ]
    for label, fn in rows:
        lines.append(f"| {label:32} | {fn(summary['md']):>8} | {fn(summary['html']):>4} | {fn(summary['agd']):>3} |")

    report = "\n".join(lines) + "\n"
    with open(os.path.join(OUTPUT, "report.md"), "w") as f:
        f.write(report)
    print(report)


# ============================================================
#  Dispatch
# ============================================================
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", required=True, choices=[
        "init", "daemon-md", "daemon-html", "daemon-agd",
        "agent-analyst", "agent-responder", "agent-auditor",
        "compare", "drain",
    ])
    args = p.parse_args()
    os.makedirs(OUTPUT, exist_ok=True)

    if args.mode == "init":
        mode_init()
    elif args.mode.startswith("daemon-"):
        mode_daemon(args.mode.split("-", 1)[1])
    elif args.mode.startswith("agent-"):
        mode_agent(args.mode.split("-", 1)[1])
    elif args.mode == "compare":
        mode_compare()
    elif args.mode == "drain":
        mode_drain()


if __name__ == "__main__":
    main()
