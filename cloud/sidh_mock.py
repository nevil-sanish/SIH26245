"""MOCK Skill India Digital Hub (SIDH) adapter — label: mock. Never implies real government data.

The real SIDH export format is not public; this adapter defines the shape SAKSHI expects
(batches, timetable, enrolment counts, trainer schedule, anonymous check-in timestamps) so a real
adapter only has to produce the same dict. `load()` writes a seed dict into the DB; `export_batch()`
returns the plausible SIDH-shaped view used by the dashboard's "source data" panel.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import yaml
from sqlalchemy import delete
from sqlalchemy.orm import Session

from cloud.db import (ROOT, Batch, Centre, Checkin, Enrolment, Inspection, SanctionedInventory, TimetableSlot,
                      TrainerSchedule, User)

INVENTORY = ROOT / "data" / "sanctioned_inventory" / "mock_qp_inventory.yaml"


def hash_password(pw: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    h = hashlib.scrypt(pw.encode(), salt=salt, n=2 ** 14, r=8, p=1)
    return f"{salt.hex()}${h.hex()}"


def check_password(pw: str, stored: str) -> bool:
    salt, _ = stored.split("$")
    return hash_password(pw, bytes.fromhex(salt)) == stored


def load_inventory(db: Session, path: Path = INVENTORY):
    d = yaml.safe_load(open(path))
    db.execute(delete(SanctionedInventory))
    for t in d["trades"]:
        for it in t["items"]:
            db.add(SanctionedInventory(qp_code=t["qp_code"], job_role=t["job_role"], item=it["item"], qty=it["qty"],
                                       per=it["per"], source_note=t["source_note"]))


def load(db: Session, seed: dict):
    """seed keys: centres, batches, timetable, enrolments, trainers, checkins, inspections, users."""
    for c in seed.get("centres", []):
        db.merge(Centre(**c))
    for b in seed.get("batches", []):
        db.merge(Batch(**b))
    db.flush()
    for s in seed.get("timetable", []):
        db.add(TimetableSlot(**s))
    for e in seed.get("enrolments", []):
        db.merge(Enrolment(**e))
    for t in seed.get("trainers", []):
        db.add(TrainerSchedule(**t))
    for c in seed.get("checkins", []):
        db.add(Checkin(**c))
    for i in seed.get("inspections", []):
        db.add(Inspection(**i))
    for u in seed.get("users", []):
        db.merge(User(username=u["username"], role=u["role"], centre_id=u.get("centre_id"), state=u.get("state"),
                      password_hash=hash_password(u["password"])))
    db.commit()


def export_batch(db: Session, batch_id: str, d0: int, d1: int) -> dict:
    b = db.get(Batch, batch_id)
    slots = db.query(TimetableSlot).filter(TimetableSlot.batch_id == batch_id, TimetableSlot.start >= d0,
                                           TimetableSlot.start < d1).all()
    return {"label": "mock", "source": "SIDH (mock adapter)", "batch_id": b.id, "centre_id": b.centre_id,
            "job_role": b.job_role, "qp_code": b.qp_code,
            "enrolled": (db.get(Enrolment, batch_id) or Enrolment(count=0)).count,
            "timetable": [{"start": s.start, "end": s.end, "type": s.kind, "room": s.room} for s in slots],
            "checkins": [c.ts for c in db.query(Checkin).filter(Checkin.batch_id == batch_id, Checkin.ts >= d0,
                                                                Checkin.ts < d1).order_by(Checkin.ts)]}
