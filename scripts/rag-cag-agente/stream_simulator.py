"""
Security event stream — thread separato, push su queue.
Genera eventi HTTP realistici con pattern attack progressivi.
attack_active cambia il routing del meta-controller.
"""

import threading
import queue
import time
import random
from datetime import datetime, timezone

IPS_LEGIT = [f"192.168.1.{i}" for i in range(1, 30)]
IPS_ATTACKER = [
    f"{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}"
    for _ in range(60)
]
UA_LEGIT = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
]
UA_MALICIOUS = [
    "python-requests/2.31.0",
    "curl/8.1.2",
    "Go-http-client/1.1",
    "Nuclei - Open-source project (https://nuclei.projectdiscovery.io)",
    "masscan/1.3",
]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rand_ip(malicious: bool = False) -> str:
    pool = IPS_ATTACKER if malicious else IPS_LEGIT
    return random.choice(pool)


class StreamSimulator:

    def __init__(self):
        self.queue: queue.Queue = queue.Queue(maxsize=200)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.attack_active: bool = False
        self._phase: str = "normal"   # normal | buildup | attack
        self._phase_counter: int = 0

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def trigger_attack(self):
        """Forza un pattern di attacco — usato dal demo per query 2."""
        self._phase = "attack"
        self.attack_active = True

    def reset_attack(self):
        self._phase = "normal"
        self.attack_active = False
        self._phase_counter = 0

    # ── generatori eventi ─────────────────────────────────────────────────────

    def _normal_event(self) -> dict:
        return {
            "type": "http_log",
            "ts": _now(),
            "ip": _rand_ip(malicious=False),
            "endpoint": random.choice(["/api/data", "/api/user", "/dashboard", "/"]),
            "status": random.choices([200, 304, 404], weights=[80, 10, 10])[0],
            "rate": random.randint(1, 8),
            "user_agent": random.choice(UA_LEGIT),
        }

    def _buildup_event(self) -> dict:
        scenario = random.choices(
            ["normal", "probe", "slow_auth"],
            weights=[50, 30, 20]
        )[0]

        if scenario == "probe":
            return {
                "type": "http_log",
                "ts": _now(),
                "ip": _rand_ip(malicious=True),
                "endpoint": random.choice(["/login", "/admin", "/.env", "/wp-login.php"]),
                "status": random.choices([401, 403, 404], weights=[60, 25, 15])[0],
                "rate": random.randint(10, 40),
                "user_agent": random.choice(UA_MALICIOUS),
            }
        if scenario == "slow_auth":
            return {
                "type": "auth_attempt",
                "ts": _now(),
                "ip": _rand_ip(malicious=True),
                "endpoint": "/login",
                "status": 401,
                "prev_failures": random.randint(2, 8),
                "user_agent": random.choice(UA_MALICIOUS),
            }
        return self._normal_event()

    def _attack_events(self) -> list[dict]:
        events = []
        attack_ip_pool = random.sample(IPS_ATTACKER, min(20, len(IPS_ATTACKER)))

        # spike /login
        events.append({
            "type": "http_log",
            "ts": _now(),
            "ip": random.choice(attack_ip_pool),
            "endpoint": "/login",
            "status": 429,
            "rate": random.randint(120, 500),
            "user_agent": random.choice(UA_MALICIOUS),
        })

        # credential stuffing: sequenza 401 → 200
        events.append({
            "type": "auth_attempt",
            "ts": _now(),
            "ip": random.choice(attack_ip_pool),
            "endpoint": "/login",
            "status": random.choices([401, 200], weights=[80, 20])[0],
            "prev_failures": random.randint(10, 80),
            "user_agent": random.choice(UA_MALICIOUS),
        })

        # IP rotation
        events.append({
            "type": "ip_rotation",
            "ts": _now(),
            "ips_last_60s": random.sample(IPS_ATTACKER, min(25, len(IPS_ATTACKER))),
            "endpoint": "/login",
            "unique_asn": random.randint(18, 45),
        })

        # user-agent anomaly
        events.append({
            "type": "user_agent_anomaly",
            "ts": _now(),
            "ip": random.choice(attack_ip_pool),
            "user_agent": random.choice(UA_MALICIOUS),
            "endpoint": "/api/admin",
            "status": random.choice([401, 403]),
        })

        return events

    # ── thread loop ───────────────────────────────────────────────────────────

    def _run(self):
        while not self._stop.is_set():
            self._phase_counter += 1

            # progressione automatica: normal → buildup → attack
            if self._phase == "normal" and self._phase_counter > 30:
                self._phase = "buildup"
            elif self._phase == "buildup" and self._phase_counter > 60:
                self._phase = "attack"
                self.attack_active = True

            if self._phase == "attack":
                for ev in self._attack_events():
                    try:
                        self.queue.put_nowait(ev)
                    except queue.Full:
                        pass
                time.sleep(random.uniform(0.05, 0.2))
            elif self._phase == "buildup":
                ev = self._buildup_event()
                try:
                    self.queue.put_nowait(ev)
                except queue.Full:
                    pass
                time.sleep(random.uniform(0.2, 0.5))
            else:
                ev = self._normal_event()
                try:
                    self.queue.put_nowait(ev)
                except queue.Full:
                    pass
                time.sleep(random.uniform(0.3, 0.8))

    def drain(self, max_events: int = 20) -> list[dict]:
        events = []
        while not self.queue.empty() and len(events) < max_events:
            try:
                events.append(self.queue.get_nowait())
            except queue.Empty:
                break
        return events
