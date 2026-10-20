"""Tiered, signed, hash-chained packets (D5 low-bandwidth mode).

Whisper  every 60 s: counts, entry/exit second-offsets, occupancy, asset seconds, clock drift,
         integrity flags, evidence level, seq, prev hash, Ed25519 signature.        (~200–400 B)
Normal   Whisper + one 96×54 face-blurred JPEG per anomaly + keyframe pHash.
Audit    encrypted clips, uploaded only on a formal request (edge/privacy.py ring buffer).

Canonical JSON = sorted keys, no spaces, UTF-8. The signature covers every field except `sig`;
`prev` is the SHA-256 of the previous packet's canonical bytes (including its sig), so deleting,
reordering or editing any packet breaks the chain in the cloud.
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

from nacl.signing import SigningKey, VerifyKey

GENESIS = "0" * 16


def canonical(d: dict) -> bytes:
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def chain_hash(packet: dict) -> str:
    return hashlib.sha256(canonical(packet)).hexdigest()[:16]   # 64-bit prefix: enough for a chain, saves bytes


def load_or_create_key(path: str | Path) -> SigningKey:
    """One Ed25519 key per edge device. The public key is registered with the cloud at enrolment."""
    p = Path(path)
    if p.exists():
        return SigningKey(p.read_bytes())
    p.parent.mkdir(parents=True, exist_ok=True)
    k = SigningKey.generate()
    p.write_bytes(bytes(k))
    p.chmod(0o600)
    return k


def public_key_b64(k: SigningKey) -> str:
    return base64.b64encode(bytes(k.verify_key)).decode()


def sign(body: dict, key: SigningKey) -> dict:
    sig = key.sign(canonical(body)).signature
    return {**body, "sig": base64.b64encode(sig).decode()}


def verify(packet: dict, pub_b64: str) -> bool:
    body = {k: v for k, v in packet.items() if k != "sig"}
    try:
        VerifyKey(base64.b64decode(pub_b64)).verify(canonical(body), base64.b64decode(packet["sig"]))
        return True
    except Exception:  # noqa: BLE001 — any failure = invalid
        return False


class Packetizer:
    """Holds seq + prev-hash state for one camera; state is persisted by the outbox."""

    def __init__(self, centre: str, cam: str, key: SigningKey, seq: int = 0, prev: str = GENESIS):
        self.centre, self.cam, self.key, self.seq, self.prev = centre, cam, key, seq, prev

    def build(self, t: int, tier: str = "whisper", **fields) -> dict:
        self.seq += 1
        body = {"c": self.centre, "cam": self.cam, "t": int(t), "seq": self.seq, "tier": tier[0].upper(),
                "prev": self.prev, **{k: v for k, v in fields.items() if v is not None and v != [] and v != {}}}
        if tier == "whisper":
            body.pop("thumb", None)
        pkt = sign(body, self.key)
        self.prev = chain_hash(pkt)
        return pkt


if __name__ == "__main__":
    k = SigningKey.generate()
    pz = Packetizer("TC0421", "CAM2", k)
    a = pz.build(1729412400, **{"in": 3, "out": 1, "occ": 17, "ei": [4, 31, 50], "eo": [12], "ev": "FULL"})
    b = pz.build(1729412460, **{"in": 0, "out": 0, "occ": 17, "ev": "FULL"})
    pub = public_key_b64(k)
    assert verify(a, pub) and verify(b, pub)
    assert b["prev"] == chain_hash(a) and a["prev"] == GENESIS
    assert not verify({**a, "occ": 30}, pub)
    print("whisper packet bytes:", len(canonical(a)))
