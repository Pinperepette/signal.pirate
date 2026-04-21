"""
PCAPStream — legge un PCAP reale con tshark e produce eventi strutturati.
Sostituisce StreamSimulator per il demo autonomo su dati veri.

Replay a velocità controllata per simulare arrivo live degli eventi.
attack_active si attiva quando rileva: webshell, C2, port scan, exploit upload.
"""

import json
import subprocess
import threading
import queue
import time
from pathlib import Path

TSHARK = "/Applications/Wireshark.app/Contents/MacOS/tshark"

# porte C2 note (Metasploit defaults + comuni)
C2_PORTS = {4444, 4445, 4446, 1234, 31337, 8080, 8888, 9999, 6666}

# path nei webshell tipici
WEBSHELL_PATTERNS = [
    ".php", "cmd=", "exec=", "system=", "shell=",
    "/uploads/", "/tmp/", "eval(", "base64_decode"
]

# WordPress plugin exploit paths
EXPLOIT_PATHS = [
    "wysija", "wp-admin/admin-post", "wp-content/uploads",
    "revslider", "gravityforms", "wp-file-manager"
]


def _parse_pcap(pcap_path: str) -> list[dict]:
    """Usa tshark per estrarre eventi HTTP e TCP strutturati."""
    cmd = [
        TSHARK, "-r", pcap_path,
        "-T", "json",
        "-e", "frame.time_relative",
        "-e", "ip.src",
        "-e", "ip.dst",
        "-e", "tcp.srcport",
        "-e", "tcp.dstport",
        "-e", "http.request.method",
        "-e", "http.request.uri",
        "-e", "http.request.full_uri",
        "-e", "http.response.code",
        "-e", "http.user_agent",
        "-e", "http.file_data",
        "-e", "tcp.len",
        "-e", "tcp.flags.syn",
        "-e", "tcp.flags.push",
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30
        )
        raw = json.loads(result.stdout)
    except Exception as e:
        print(f"tshark error: {e}")
        return []

    events = []
    for frame in raw:
        layers = frame.get("_source", {}).get("layers", {})

        def get(key):
            v = layers.get(key, [])
            if isinstance(v, list):
                return v[0] if v else None
            return v

        ts        = float(get("frame.time_relative") or 0)
        src       = get("ip.src")
        dst       = get("ip.dst")
        sport     = int(get("tcp.srcport") or 0)
        dport     = int(get("tcp.dstport") or 0)
        method    = get("http.request.method")
        uri       = get("http.request.uri")
        status    = get("http.response.code")
        ua        = get("http.user_agent")
        tcp_len   = int(get("tcp.len") or 0)
        is_syn    = get("tcp.flags.syn") == "1"
        is_push   = get("tcp.flags.push") == "1"

        if not src:
            continue

        event = {
            "ts":      round(ts, 3),
            "src":     src,
            "dst":     dst,
            "sport":   sport,
            "dport":   dport,
            "tcp_len": tcp_len,
        }

        if method:
            event["type"]   = "http_request"
            event["method"] = method
            event["uri"]    = uri or ""
            event["ua"]     = ua or ""
        elif status:
            event["type"]   = "http_response"
            event["status"] = int(status)
        elif is_syn and tcp_len == 0:
            event["type"]   = "tcp_syn"
        elif is_push and tcp_len > 0:
            event["type"]   = "tcp_data"
        else:
            continue  # skip pure ACKs

        events.append(event)

    return events


def _classify_event(ev: dict) -> tuple[str, str]:
    """Classifica un evento: (tipo_attacco, mitre_hint)"""
    uri  = ev.get("uri", "").lower()
    dport = ev.get("dport", 0)
    sport = ev.get("sport", 0)
    method = ev.get("method", "")
    status = ev.get("status", 0)

    # webshell upload
    if method == "POST" and any(p in uri for p in EXPLOIT_PATHS):
        return "exploit_upload", "T1190"

    # webshell execution
    if method == "GET" and "/uploads/" in uri and ".php" in uri:
        return "webshell_exec", "T1505.003"

    # C2 reverse shell
    if dport in C2_PORTS or sport in C2_PORTS:
        return "c2_connection", "T1071.001"

    # recon / scanning
    if method == "GET" and (status == 404 or any(p in uri for p in [".env", ".git", "phpinfo", "admin"])):
        return "recon", "T1595"

    return "normal", ""


class PCAPStream:

    def __init__(self, pcap_path: str, replay_speed: float = 20.0):
        self.pcap_path    = pcap_path
        self.replay_speed = replay_speed   # replay N× più veloce del reale
        self.queue: queue.Queue = queue.Queue(maxsize=500)
        self._stop        = threading.Event()
        self._thread: threading.Thread | None = None
        self.attack_active: bool = False
        self.detected_attacks: list[dict] = []
        self._events: list[dict] = []

    def load(self):
        """Carica e pre-processa il PCAP. Chiamare prima di start()."""
        print(f"  parsing PCAP: {self.pcap_path}")
        raw = _parse_pcap(self.pcap_path)

        for ev in raw:
            attack_type, mitre = _classify_event(ev)
            ev["attack_type"] = attack_type
            ev["mitre_hint"]  = mitre
            self._events.append(ev)

        attacks = [e for e in self._events if e["attack_type"] != "normal"]
        print(f"  {len(self._events)} eventi totali | {len(attacks)} eventi attacco")
        return self

    def start(self):
        self._thread = threading.Thread(target=self._replay, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _replay(self):
        """Riproduce gli eventi del PCAP rispettando i timestamp (accelerati)."""
        if not self._events:
            return

        t0_real = time.time()
        t0_pcap = self._events[0]["ts"]

        for ev in self._events:
            if self._stop.is_set():
                break

            # aspetta il momento giusto (timestamp relativo / speed)
            elapsed_pcap = ev["ts"] - t0_pcap
            elapsed_real = time.time() - t0_real
            wait = (elapsed_pcap / self.replay_speed) - elapsed_real
            if wait > 0:
                time.sleep(wait)

            # aggiorna attack_active
            if ev["attack_type"] in ("exploit_upload", "webshell_exec", "c2_connection"):
                self.attack_active = True
                self.detected_attacks.append({
                    "ts":          ev["ts"],
                    "attack_type": ev["attack_type"],
                    "mitre_hint":  ev["mitre_hint"],
                    "src":         ev.get("src"),
                    "dst":         ev.get("dst"),
                    "uri":         ev.get("uri", ""),
                    "dport":       ev.get("dport", 0),
                })

            try:
                self.queue.put_nowait(ev)
            except queue.Full:
                pass

    def drain(self, max_events: int = 50) -> list[dict]:
        events = []
        while not self.queue.empty() and len(events) < max_events:
            try:
                events.append(self.queue.get_nowait())
            except queue.Empty:
                break
        return events

    def summary(self) -> dict:
        """Riassunto degli attacchi rilevati dal PCAP.
        Usa _events (pre-classificati) + detected_attacks (dal replay)."""
        from collections import Counter

        # usa detected_attacks se disponibili, altrimenti fall-back su _events
        attack_src = self.detected_attacks if self.detected_attacks else [
            e for e in self._events if e.get("attack_type") != "normal"
        ]

        types  = Counter(a["attack_type"] for a in attack_src)
        mitres = list(dict.fromkeys(
            a["mitre_hint"] for a in attack_src if a.get("mitre_hint")
        ))
        srcs   = list(dict.fromkeys(
            a["src"] for a in attack_src if a.get("src")
        ))
        c2     = list(dict.fromkeys(
            str(a.get("dport", ""))
            for a in attack_src
            if a.get("attack_type") == "c2_connection" and a.get("dport")
        ))
        return {
            "total_events":  len(self._events),
            "attack_events": len(attack_src),
            "attack_types":  dict(types),
            "mitre_hints":   mitres,
            "attacker_ips":  srcs,
            "c2_ports":      c2,
        }
