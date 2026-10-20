"""Packet ingest: verify signature + hash chain + sequence, then expand into observation rows.

Robust to the chaos tests in PROMPT §19:
  duplicate   same (centre, cam, seq) and same sig → acked as duplicate, stored once
  reorder     chain is checked against whichever neighbour (seq−1 / seq+1) is already stored
  gap         seq jump → data_gap row (closed automatically when the missing packets arrive)
  forged      bad signature → rejected, logged as an integrity event, never used for analytics
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
from pathlib import Path

from nacl.signing import SigningKey
from sqlalchemy import select
from sqlalchemy.orm import Session

from cloud.db import (AssetObservation, Camera, Centre, DataGap, DoorEvent, IntegrityEvent, KeyframeHash,
                      OccupancySample, Packet, ROOT)
from edge.packet import canonical, chain_hash, verify

SERVER_KEY_PATH = Path(ROOT / "data" / "server.key")
OCC_STEP_S = 10


def server_key() -> SigningKey:
    if SERVER_KEY_PATH.exists():
        return SigningKey(SERVER_KEY_PATH.read_bytes())
    SERVER_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    k = SigningKey.generate()
    SERVER_KEY_PATH.write_bytes(bytes(k))
    return k


def signed_time() -> dict:
    t = int(datetime.now(timezone.utc).timestamp())
    sig = server_key().sign(str(t).encode()).signature
    return {"t": t, "sig": base64.b64encode(sig).decode()}


def ingest(db: Session, packets: list[dict], label: str = "measured") -> dict:
    accepted, duplicate, rejected = [], [], []
    keys = {}
    for p in sorted(packets, key=lambda p: (p.get("c", ""), p.get("cam", ""), p.get("seq", 0))):
        ref = {"cam": p.get("cam"), "seq": p.get("seq")}
        c = p.get("c")
        if c not in keys:
            centre = db.get(Centre, c)
            keys[c] = centre.public_key if centre else None
        if not keys[c]:
            rejected.append({**ref, "reason": "unknown device"}); continue
        old = db.get(Packet, (c, p["cam"], p["seq"]))
        if old:
            (duplicate if old.sig == p.get("sig") else rejected).append(
                ref if old.sig == p.get("sig") else {**ref, "reason": "seq reuse with different content"})
            continue
        if not verify(p, keys[c]):
            db.add(IntegrityEvent(centre_id=c, cam=p["cam"], ts=int(p.get("t", 0)), kind="bad_signature",
                                  value={"seq": p["seq"]}, label=label))
            rejected.append({**ref, "reason": "bad signature"}); continue
        h = chain_hash(p)
        prev = db.get(Packet, (c, p["cam"], p["seq"] - 1))
        nxt = db.get(Packet, (c, p["cam"], p["seq"] + 1))
        chain_ok = None
        if prev is not None:
            chain_ok = prev.hash == p["prev"]
        elif p["seq"] == 1:
            chain_ok = p["prev"] == "0" * 16
        if nxt is not None:
            nxt.chain_ok = nxt.prev_hash == h
            if not nxt.chain_ok:
                _chain_break(db, c, p["cam"], nxt.t)
        if chain_ok is False:
            _chain_break(db, c, p["cam"], p["t"])
        db.add(Packet(centre_id=c, cam=p["cam"], seq=p["seq"], t=p["t"], prev_hash=p["prev"], hash=h,
                      sig=p["sig"], sig_ok=True, chain_ok=chain_ok, bytes=len(canonical(p)),
                      tier=p.get("tier", "W"), body=p, label=label))
        _gaps(db, c, p, prev)
        _expand(db, p, label)
        db.flush()
        accepted.append(ref)
    db.commit()
    return {"accepted": accepted, "duplicate": duplicate, "rejected": rejected, "server_time": signed_time()}


def _chain_break(db, c, cam, t):
    db.add(DataGap(centre_id=c, cam=cam, start=t, end=t, reason="chain_break"))


def _gaps(db: Session, c: str, p: dict, prev: Packet | None):
    """Open a gap if the previous seq is missing; close any gap this packet fills."""
    seq = p["seq"]
    if prev is None and seq > 1:
        last = db.scalars(select(Packet).where(Packet.centre_id == c, Packet.cam == p["cam"], Packet.seq < seq)
                          .order_by(Packet.seq.desc()).limit(1)).first()
        if last is not None:
            db.add(DataGap(centre_id=c, cam=p["cam"], start=last.t + 60, end=p["t"], reason="seq_gap"))
    for g in db.scalars(select(DataGap).where(DataGap.centre_id == c, DataGap.cam == p["cam"],
                                              DataGap.reason == "seq_gap", DataGap.resolved.is_(False))):
        # A gap is resolved once every seq between its edges is present.
        lo = db.scalars(select(Packet.seq).where(Packet.centre_id == c, Packet.cam == p["cam"], Packet.t < g.start)
                        .order_by(Packet.seq.desc()).limit(1)).first()
        hi = db.scalars(select(Packet.seq).where(Packet.centre_id == c, Packet.cam == p["cam"], Packet.t >= g.end)
                        .order_by(Packet.seq).limit(1)).first()
        if lo is not None and hi is not None:
            n = len(db.scalars(select(Packet.seq).where(Packet.centre_id == c, Packet.cam == p["cam"],
                                                        Packet.seq > lo, Packet.seq < hi)).all())
            if n + (1 if lo < seq < hi else 0) >= hi - lo - 1:
                g.resolved = True


def _expand(db: Session, p: dict, label: str):
    c, cam, t = p["c"], p["cam"], int(p["t"])
    cam_row = db.get(Camera, f"{c}:{cam}")
    if cam_row is None:
        cam_row = Camera(id=f"{c}:{cam}", centre_id=c, cam=cam, role="door" if p.get("in") or p.get("out") else "room")
        db.add(cam_row)
    cam_row.last_seen = datetime.now(timezone.utc)
    cam_row.last_t = max(cam_row.last_t or 0, t)
    cam_row.unavailable = p.get("na")
    for off in p.get("ei", []):
        db.add(DoorEvent(centre_id=c, cam=cam, ts=t + off, direction="in", label=label))
    for off in p.get("eo", []):
        db.add(DoorEvent(centre_id=c, cam=cam, ts=t + off, direction="out", label=label))
    samples = p.get("oc") or ([p["occ"]] if p.get("occ") is not None else [])
    step = 60 // max(len(samples), 1)
    for i, v in enumerate(samples):
        db.merge(OccupancySample(centre_id=c, cam=cam, ts=t + i * step, occ=v, trainers=p.get("tr"), label=label))
    for f in p.get("flags", []):
        db.add(IntegrityEvent(centre_id=c, cam=cam, ts=t, kind=f, label=label,
                              value={"clk": p.get("clk"), "q": p.get("q"), "loop": p.get("loop")}))
    if p.get("clk") is not None:
        db.add(IntegrityEvent(centre_id=c, cam=cam, ts=t, kind="clock_reading", value={"drift": p["clk"]}, label=label))
    if p.get("ph"):
        db.add(KeyframeHash(centre_id=c, cam=cam, ts=t, phash=p["ph"]))
    # Asset use seconds and identity scores → one observation row per asset per day (scheduled practical
    # time is filled from the timetable by cloud/analyze.py).
    date = datetime.fromtimestamp(t).strftime("%Y-%m-%d")
    for aid in set(p.get("use") or {}) | set(p.get("aid") or {}):
        o = db.scalars(select(AssetObservation).where(AssetObservation.centre_id == c, AssetObservation.asset_id == aid,
                                                      AssetObservation.date == date)).first()
        if o is None:
            o = AssetObservation(centre_id=c, asset_id=aid, date=date, interaction_s=0, scheduled_practical_s=0, label=label)
            db.add(o)
        o.interaction_s = (o.interaction_s or 0) + (p.get("use") or {}).get(aid, 0)
        if (p.get("aid") or {}).get(aid) is not None:
            o.identity_score = p["aid"][aid]
