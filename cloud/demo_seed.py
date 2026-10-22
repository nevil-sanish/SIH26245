"""Seed the demo story (PROMPT §22) into the cloud DB, then run every engine through the normal code path.

    python -m cloud.demo_seed [--fresh]

Programme data (centres, batches, timetable, check-ins, inspections) is MOCK (mock SIDH adapter).
History observations (door events, occupancy, asset use) are SIMULATED by the red-team generators, with
detector noise from the measured accuracy run when data/work/accuracy.json exists.
Demo-day packets for the MEVA / lab centres are MEASURED: real edge output from Colab (data/demo/packets.jsonl).

Stories:  TC0880 bulk check-in (H1) · TC0777 replayed feed (H2, measured) · TC0915 performing for audits (H3)
          TC0307 ornamental lathe (S1) · TC0421 honest, stays clean (measured) · + R2/R5/R6/R8 and honest fillers.
"""
from __future__ import annotations

import argparse
import json
import zlib
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import yaml

from cloud import analyze, sidh_mock
from cloud.db import (ROOT, AssetObservation, AssetRegistry, DoorEvent, OccupancySample, SessionLocal, init_db)
from cloud.ingest import ingest
from redteam.generators import Noise, event_session, r7_asset_days, r8_identity_days, r9_centre_days
from edge import IST
from redteam.runner import DEMO_DAY

DEMO = ROOT / "data" / "demo"
HISTORY_DAYS = 30
TRADE = {"it": ("SSC/Q2212", "Domestic Data Entry Operator"), "tailor": ("AMH/Q0301", "Sewing Machine Operator"),
         "workshop": ("ELE/Q3104", "Electrician / Welding workshop")}

# id, name, state, district, lat, lon, trade, story
CENTRES = [
    ("TC0421", "Shivaji Skill Centre", "Maharashtra", "Pune", 18.52, 73.86, "it", "honest_measured"),
    ("TC0777", "Ganga Vocational Institute", "Bihar", "Patna", 25.60, 85.14, "it", "replay_measured"),
    ("TC0555", "Aravalli Training Hub", "Rajasthan", "Jaipur", 26.91, 75.79, "it", "duplicate_measured"),
    ("TC0612", "Narmada Skills Academy", "Madhya Pradesh", "Bhopal", 23.26, 77.41, "it", "frozen_measured"),
    ("TC0198", "Awadh Computer Centre", "Uttar Pradesh", "Lucknow", 26.85, 80.95, "it", "lab_measured"),
    ("TC0880", "Jharkhand Kaushal Kendra", "Jharkhand", "Ranchi", 23.34, 85.31, "tailor", "bulk_checkin"),
    ("TC0915", "Brahmaputra Skill School", "Assam", "Guwahati", 26.14, 91.74, "tailor", "audit_performer"),
    ("TC0307", "Kongu Technical Institute", "Tamil Nadu", "Coimbatore", 11.02, 76.96, "workshop", "ornamental_lathe"),
    ("TC0333", "Kalinga Skills Centre", "Odisha", "Bhubaneswar", 20.30, 85.82, "tailor", "proxy"),
    ("TC0444", "Deccan Workshop Academy", "Telangana", "Hyderabad", 17.39, 78.49, "workshop", "asset_swap"),
    ("TC0101", "Marina Skill Centre", "Tamil Nadu", "Chennai", 13.08, 80.27, "it", "honest"),
    ("TC0102", "Hooghly Training Centre", "West Bengal", "Kolkata", 22.57, 88.36, "tailor", "honest"),
    ("TC0103", "Sabarmati Kaushal Kendra", "Gujarat", "Ahmedabad", 23.02, 72.57, "workshop", "honest"),
    ("TC0104", "Sukhna Skill Institute", "Chandigarh", "Chandigarh", 30.73, 76.78, "it", "honest"),
    ("TC0105", "Periyar Vocational Centre", "Kerala", "Kochi", 9.93, 76.27, "tailor", "honest"),
]
MEASURED = {"TC0421", "TC0777", "TC0555", "TC0612", "TC0198"}


def noise_from_accuracy() -> Noise:
    p = ROOT / "data" / "work" / "accuracy.json"
    if p.exists():
        n = json.loads(p.read_text()).get("noise_model", {})
        return Noise(**{k: n[k] for k in Noise.__dataclass_fields__ if k in n})
    return Noise()


def add_session(seed, cid, bid, s, kind="theory", practical_split=False):
    """Write one simulated session's programme + observation rows (programme = mock, observations = simulated)."""
    slots = [{"batch_id": bid, "room": "R1", "start": int(s.start), "end": int(s.end), "kind": kind}]
    if practical_split:
        mid = int(s.start + (s.end - s.start) / 2)
        slots = [{"batch_id": bid, "room": "R1", "start": int(s.start), "end": mid, "kind": "theory"},
                 {"batch_id": bid, "room": "R1", "start": mid, "end": int(s.end), "kind": "practical"}]
    for b0, b1 in s.breaks:
        slots.append({"batch_id": bid, "room": "R1", "start": int(b0), "end": int(b1), "kind": "break"})
    seed["timetable"] += slots
    seed["checkins"] += [{"batch_id": bid, "ts": int(t), "label": "mock"} for t in s.checkins]
    obs = [DoorEvent(centre_id=cid, cam="CAM-DOOR", ts=int(t), direction="in", label="simulated") for t in s.entries]
    obs += [DoorEvent(centre_id=cid, cam="CAM-DOOR", ts=int(t), direction="out", label="simulated") for t in s.exits]
    obs += [OccupancySample(centre_id=cid, cam="CAM-ROOM", ts=int(t), occ=int(o), trainers=None, label="simulated")
            for t, o in zip(s.occ_t, s.occ)]
    return obs


def build(noise: Noise):
    users = yaml.safe_load(open(DEMO / "users.yaml"))["users"]
    seed = {"centres": [], "batches": [], "timetable": [], "enrolments": [], "trainers": [], "checkins": [],
            "inspections": [], "users": users}
    obs, assets, asset_obs = [], [], []
    rng = np.random.default_rng(7)
    for cid, name, state, dist, lat, lon, trade, story in CENTRES:
        seed["centres"].append(dict(id=cid, name=name, state=state, district=dist, lat=lat, lon=lon, label="mock", story=story))
        qp, role = TRADE[trade]
        bid = f"{cid}-B1"
        seed["batches"].append(dict(id=bid, centre_id=cid, job_role=role, qp_code=qp, room="R1",
                                    door_cam="CAM-DOOR", room_cam="CAM-LAB" if cid == "TC0198" else "CAM-ROOM", label="mock"))
        seed["enrolments"].append(dict(batch_id=bid, count=20 if cid in MEASURED else 30))
        # history: HISTORY_DAYS days of sessions ending the day before the demo day
        if story == "audit_performer":
            sessions, insp = r9_centre_days(91, noise, days=75)
            base = DEMO_DAY - timedelta(days=75)
            for i, s in enumerate(sessions):
                shift = (base + timedelta(days=i)) - datetime.fromtimestamp(s.start, IST).replace(hour=0, minute=0, second=0, microsecond=0)
                s = _shift(s, shift.total_seconds())
                obs += add_session(seed, cid, bid, s)
            seed["inspections"] += [dict(centre_id=cid, date=(base + timedelta(days=i)).strftime("%Y-%m-%d"),
                                         outcome="satisfactory", label="mock") for i in insp]
        else:
            for d in range(HISTORY_DAYS, 0, -1):
                day = DEMO_DAY - timedelta(days=d)
                if day.weekday() == 6:
                    continue  # no training on Sundays
                sid = {"bulk_checkin": "R1" if d <= 6 else "N1", "proxy": "R2"}.get(story, "N2" if d % 3 == 0 else "N1")
                s, _ = event_session(sid, zlib.crc32(f'{cid}:{d}'.encode()) % 10_000, noise, day)
                obs += add_session(seed, cid, bid, s, practical_split=trade == "workshop")
            for k in rng.choice(np.arange(5, HISTORY_DAYS), size=2, replace=False):
                seed["inspections"].append(dict(centre_id=cid, date=(DEMO_DAY - timedelta(days=int(k))).strftime("%Y-%m-%d"),
                                                outcome="satisfactory", label="mock"))
        seed["trainers"] += [dict(batch_id=bid, date=(DEMO_DAY - timedelta(days=d)).strftime("%Y-%m-%d"), count=1)
                             for d in range(0, 76)]
        # workshop assets: full sanctioned inventory registered; story centres get usage / identity series
        if trade == "workshop":
            for item, n in (("lathe machine", 1), ("welding machine", 2 if story != "asset_swap" else 1), ("workbench", 30)):
                for k in range(n):
                    aid = f"{item.split()[0].upper()}-{k + 1:02d}"
                    assets.append(AssetRegistry(asset_id=f"{cid}-{aid}", centre_id=cid, label=item, zone=None,
                                                embedding_ref="edge", source="registration crop (simulated)"))
            use = r7_asset_days(3, days=14) if story == "ornamental_lathe" else r7_asset_days(5, days=14, honest=True)
            ids = r8_identity_days(4, 10, 6) if story == "asset_swap" else r8_identity_days(6, 10, honest=True)
            for i, (_, used, sched) in enumerate(use):
                date = (DEMO_DAY - timedelta(days=14 - i)).strftime("%Y-%m-%d")
                sim = ids[i - 4][1] if i >= 4 else None
                asset_obs.append(AssetObservation(centre_id=cid, asset_id=f"{cid}-LATHE-01", date=date, present=True,
                                                  interaction_s=used, scheduled_practical_s=sched, identity_score=sim,
                                                  label="simulated"))
    # demo-day session for the measured centres: 12:00–12:05 (the MEVA slot), mock check-ins
    # The claim matches what the room camera measured (peak occupancy in the packets): an honest centre's check-ins.
    t0 = int(DEMO_DAY.replace(hour=12).timestamp())
    peak = defaultdict(int)
    if (DEMO / "packets.jsonl").exists():
        for p in map(json.loads, filter(str.strip, open(DEMO / "packets.jsonl"))):
            if p.get("cam") != "CAM-DOOR" and p.get("occ") is not None:
                peak[p["c"]] = max(peak[p["c"]], p["occ"])
    for cid in MEASURED:
        bid = f"{cid}-B1"
        kind = "practical" if cid == "TC0198" else "theory"
        seed["timetable"].append(dict(batch_id=bid, room="R1", start=t0, end=t0 + 300, kind=kind))
        n = peak[cid] - 1 if peak[cid] else 20   # the room peak includes the 1 scheduled trainer (seed["trainers"])
        ck = np.sort(np.random.default_rng(zlib.crc32(cid.encode())).uniform(t0 - 240, t0 + 240, n))
        seed["checkins"] += [{"batch_id": bid, "ts": int(t), "label": "mock"} for t in ck]
    return seed, obs, assets, asset_obs


def _shift(s, dt):
    s.start += dt; s.end += dt
    s.checkins = [t + dt for t in s.checkins]; s.entries = [t + dt for t in s.entries]; s.exits = [t + dt for t in s.exits]
    s.occ_t = [t + dt for t in s.occ_t]; s.breaks = [(a + dt, b + dt) for a, b in s.breaks]
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fresh", action="store_true", help="drop and recreate all tables first")
    ap.add_argument("--if-empty", action="store_true", help="seed only when no centres exist (container start)")
    a = ap.parse_args()
    init_db(drop=a.fresh)
    if a.if_empty:
        with SessionLocal() as db:
            if db.query(analyze.Centre).first() is not None:
                print("demo data already present"); return
    noise = noise_from_accuracy()
    seed, obs, assets, asset_obs = build(noise)
    with SessionLocal() as db:
        sidh_mock.load_inventory(db)
        sidh_mock.load(db, seed)
        db.add_all(obs + assets + asset_obs)
        db.commit()
        keys = json.loads((DEMO / "device_keys.json").read_text()) if (DEMO / "device_keys.json").exists() else {}
        for cid, pub in keys.items():
            c = db.get(analyze.Centre, cid)
            if c:
                c.public_key = pub
        db.commit()
        n = 0
        if (DEMO / "packets.jsonl").exists():
            pk = [json.loads(l) for l in open(DEMO / "packets.jsonl") if l.strip()]
            for i in range(0, len(pk), 500):
                n += len(ingest(db, pk[i:i + 500])["accepted"])
        print(f"measured packets ingested: {n}")
        for cid, *_ in CENTRES:
            r = analyze.run_centre(db, cid)
            print(cid, r["sessions"], "sessions", "shadow p=" + str(r["shadow"]["p_value"]) if r.get("shadow") else "")
        for cid, *_ in CENTRES:
            rk = analyze.centre_risk(db, cid)
            print(f"{cid} risk {rk['risk']:5.1f} flags {rk['open_flags']:3d} {[x['type'] for x in rk['reasons']]}")


if __name__ == "__main__":
    main()
