"""Store-and-forward uplink. Packets go into SQLite first, then leave in order; nothing is lost when
the link (or power) drops. Transports: HTTPS batch (default) or MQTT QoS 1.

Every cloud ack carries a server-signed time `{"server_time", "sig"}`; the edge keeps the last one
to detect device-clock skew (used by the OCR clock check in edge/integrity.py).
"""
from __future__ import annotations

import base64
import json
import sqlite3
import time

import requests
from nacl.signing import VerifyKey

from edge.packet import GENESIS, canonical


class Outbox:
    def __init__(self, path: str, uplink: str | None, server_pub_b64: str | None = None, batch: int = 200):
        self.db = sqlite3.connect(path)
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS outbox (cam TEXT, seq INTEGER, body TEXT, sent INTEGER DEFAULT 0,
                                               PRIMARY KEY (cam, seq));
            CREATE TABLE IF NOT EXISTS state (k TEXT PRIMARY KEY, v TEXT);""")
        self.uplink, self.batch = uplink, batch
        self.server_pub = server_pub_b64
        self.bytes_sent = 0
        self.last_server_time: float | None = None
        self._mqtt = None

    # --- chain state survives restarts so seq/prev never repeat --------------------------------
    def load_chain(self, cam: str) -> tuple[int, str]:
        r = self.db.execute("SELECT v FROM state WHERE k=?", (f"chain:{cam}",)).fetchone()
        return tuple(json.loads(r[0])) if r else (0, GENESIS)

    def put(self, pkt: dict, prev_after: str):
        self.db.execute("INSERT OR REPLACE INTO outbox (cam, seq, body) VALUES (?,?,?)",
                        (pkt["cam"], pkt["seq"], canonical(pkt).decode()))
        self.db.execute("INSERT OR REPLACE INTO state VALUES (?,?)",
                        (f"chain:{pkt['cam']}", json.dumps([pkt["seq"], prev_after])))
        self.db.commit()

    def pending(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM outbox WHERE sent=0").fetchone()[0]

    # --- delivery ---------------------------------------------------------------------------------
    def flush(self, timeout: float = 10) -> int:
        """Send pending packets oldest-first. Returns number acked; 0 on any network failure."""
        if not self.uplink:
            return 0
        rows = self.db.execute("SELECT cam, seq, body FROM outbox WHERE sent=0 ORDER BY rowid LIMIT ?",
                               (self.batch,)).fetchall()
        if not rows:
            return 0
        payload = "[" + ",".join(r[2] for r in rows) + "]"
        try:
            if self.uplink.startswith("mqtt://"):
                ack = self._send_mqtt(payload)
            else:
                resp = requests.post(f"{self.uplink.rstrip('/')}/v1/ingest/packets", data=payload,
                                     headers={"Content-Type": "application/json"}, timeout=timeout)
                resp.raise_for_status()
                ack = resp.json()
        except Exception:  # noqa: BLE001 — offline: keep everything, retry later
            return 0
        self.bytes_sent += len(payload)
        self._take_server_time(ack)
        acked = {(a["cam"], a["seq"]) for a in ack.get("accepted", [])} | \
                {(a["cam"], a["seq"]) for a in ack.get("duplicate", [])}
        self.db.executemany("UPDATE outbox SET sent=1 WHERE cam=? AND seq=?", list(acked))
        self.db.commit()
        return len(acked)

    def drain(self, max_rounds: int = 1000) -> int:
        n = 0
        for _ in range(max_rounds):
            k = self.flush()
            if not k:
                break
            n += k
        return n

    def _take_server_time(self, ack: dict):
        st = ack.get("server_time")
        if not st:
            return
        if self.server_pub:
            try:
                VerifyKey(base64.b64decode(self.server_pub)).verify(
                    str(st["t"]).encode(), base64.b64decode(st["sig"]))
            except Exception:  # noqa: BLE001
                return  # unsigned / forged time is ignored
        self.last_server_time = float(st["t"])
        self.clock_skew = time.time() - self.last_server_time

    def _send_mqtt(self, payload: str) -> dict:
        """Publish one batch QoS 1 and wait for the cloud's ack on sakshi/ack/<client>."""
        import paho.mqtt.client as mqtt
        from urllib.parse import urlparse
        u = urlparse(self.uplink)
        if self._mqtt is None:
            self._ack = None
            c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"edge-{id(self)}")
            c.on_message = lambda _c, _u, m: setattr(self, "_ack", json.loads(m.payload))
            c.connect(u.hostname, u.port or 1883)
            c.subscribe(f"sakshi/ack/edge-{id(self)}", qos=1)
            c.loop_start()
            self._mqtt = c
        self._ack = None
        self._mqtt.publish("sakshi/packets", json.dumps({"reply": f"sakshi/ack/edge-{id(self)}",
                                                         "packets": json.loads(payload)}), qos=1).wait_for_publish(10)
        for _ in range(100):
            if self._ack is not None:
                return self._ack
            time.sleep(0.1)
        raise TimeoutError("no MQTT ack")


SMS_AFTER_S = 6 * 3600


def sms_summary(packets: list[dict]) -> str:
    """One ≤160-char daily heads-up for when the link has been down > 6 h (PROMPT §11). Never evidence:
    the signed packets still follow. Format: SK|centre|date|cam:peakOcc/entries/flagBits;…|lastSeq"""
    if not packets:
        return ""
    bits = {"frozen": 1, "covered": 2, "moved": 4, "clock_drift": 8, "clock_non_monotonic": 16, "loop": 32}
    by = {}
    for p in packets:
        b = by.setdefault(p["cam"], [0, 0, 0])
        b[0] = max(b[0], p.get("occ") or 0)
        b[1] += p.get("in", 0)
        for f in p.get("flags", []):
            b[2] |= bits.get(f, 0)
    from datetime import datetime
    from edge import IST
    day = datetime.fromtimestamp(packets[-1]["t"], IST).strftime("%y%m%d")
    body = ";".join(f"{c[-6:]}:{o}/{i}/{f}" for c, (o, i, f) in sorted(by.items()))
    return f"SK|{packets[-1]['c']}|{day}|{body}|{max(p['seq'] for p in packets)}"[:160]
