"""Runs every engine for a centre and upserts explainable flags. Called after ingest, hourly, and by
`POST /v1/engines/run`. Re-running is idempotent: flags are keyed (centre, batch, date, type) and a
flag that a human already reviewed keeps its status.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from cloud.db import (AssetObservation, AssetRegistry, Batch, Centre, Checkin, DataGap, DoorEvent, Enrolment, Flag,
                      Inspection, IntegrityEvent, KeyframeHash, OccupancySample, Packet, Reconciliation,
                      SanctionedInventory, TimetableSlot, TrainerSchedule)
from cloud.engines import assets as asset_engine
from cloud.engines import registry, risk, shadow
from cloud.engines.reconcile import Params, Session as RSession, reconcile_session
from edge.evidence import TAMPER, batch_level

NEXT_STEP = {
    "unmatched_checkin": "Compare the check-in device log with the door timeline; ask the centre to explain unmatched check-ins.",
    "burst": "Check which device recorded the burst and whether trainees were physically present.",
    "ghost_session": "Prioritise an unannounced visit during this batch's timetable slot.",
    "inflation": "Verify enrolment vs physical attendance at the next visit.",
    "checkin_then_leave": "Review exit timeline; ask the centre about mid-session departures.",
    "trainee_hours_gap": "Withhold the unverified trainee-hours from payout until reviewed (officer decision).",
    "clock_drift": "Ask the centre for the DVR export and NVR clock settings; possible replayed footage.",
    "clock_non_monotonic": "Possible looped/replayed recording: request original DVR export.",
    "loop": "Same people-configuration seen on another day: request the original recording.",
    "cross_centre_duplicate": "Same frame submitted by another centre: escalate both centres for verification.",
    "frozen": "Camera frozen: ask the centre to restore the feed; data for this window is treated as a gap.",
    "covered": "Camera covered/defocused: ask the centre to fix the camera.",
    "moved": "Camera moved from its calibrated position: request re-calibration photo.",
    "ornamental_asset": "Inspect the asset during a practical session; check usage logs.",
    "asset_swapped": "Verify the asset's serial number against the sanctioned inventory.",
    "asset_missing": "Verify sanctioned equipment at the next visit.",
    "inspection_shadow": "Schedule an unannounced inspection outside the usual audit pattern.",
    "data_gap": "Data missing during scheduled sessions: confirm power/connectivity status with the centre.",
}


def _day_bounds(date: str) -> tuple[int, int]:
    d = datetime.fromisoformat(date)
    return int(d.timestamp()), int((d + timedelta(days=1)).timestamp())


def _confidence(sev: float, ev: str) -> str:
    if ev == "REDUCED":
        return "low" if sev < 0.5 else "medium"
    return "high" if sev >= 0.5 else "medium"


def upsert_flag(db: Session, centre_id, batch_id, date, ftype, severity, ev, explanation, links, label):
    f = db.scalars(select(Flag).where(Flag.centre_id == centre_id, Flag.batch_id == batch_id,
                                      Flag.date == date, Flag.type == ftype)).first()
    if f is None:
        f = Flag(centre_id=centre_id, batch_id=batch_id, date=date, type=ftype, status="open")
        db.add(f)
    f.severity = round(float(min(1.0, max(0.0, severity))), 3)
    f.evidence_level, f.explanation, f.links, f.label = ev, explanation, links, label
    f.confidence = _confidence(f.severity, ev)
    f.next_step = NEXT_STEP.get(ftype, "Review the evidence.")
    return f


def _label(rows) -> str:
    labels = {r.label for r in rows}
    return "simulated" if "simulated" in labels else "measured"


def reconcile_batch_day(db: Session, b: Batch, date: str, p: Params = Params()) -> dict | None:
    d0, d1 = _day_bounds(date)
    slots = db.scalars(select(TimetableSlot).where(TimetableSlot.batch_id == b.id, TimetableSlot.start >= d0,
                                                   TimetableSlot.start < d1)).all()
    if not slots:
        return None
    start, end = min(s.start for s in slots), max(s.end for s in slots)
    breaks = [(s.start, s.end) for s in slots if s.kind == "break"]
    pre = 3600  # trainees arrive and check in before the first slot
    checkins = db.scalars(select(Checkin.ts).where(Checkin.batch_id == b.id, Checkin.ts >= start - pre,
                                                   Checkin.ts < end)).all()
    door_rows = db.scalars(select(DoorEvent).where(DoorEvent.centre_id == b.centre_id, DoorEvent.cam == b.door_cam,
                                                   DoorEvent.ts >= start - pre, DoorEvent.ts < end)).all() if b.door_cam else []
    occ_rows = db.scalars(select(OccupancySample).where(
        OccupancySample.centre_id == b.centre_id, OccupancySample.cam == b.room_cam,
        OccupancySample.ts >= start, OccupancySample.ts < end).order_by(OccupancySample.ts)).all() if b.room_cam else []

    def cam_ok(cam):
        if not cam:
            return None
        pk = db.scalars(select(Packet.body).where(Packet.centre_id == b.centre_id, Packet.cam == cam,
                                                  Packet.t >= start - pre, Packet.t < end)).all()
        if not pk:
            return False
        bad = sum(1 for x in pk if x.get("ev") == "INSUFFICIENT")
        return bad / len(pk) < 0.2

    ev = batch_level(cam_ok(b.door_cam), cam_ok(b.room_cam))
    tr = db.scalars(select(TrainerSchedule.count).where(TrainerSchedule.batch_id == b.id,
                                                        TrainerSchedule.date == date)).first() or 1
    # Occupancy arrives at 10 s resolution; resample to one value per 60 s (median) for the engine.
    per_min = defaultdict(list)
    for r in occ_rows:
        per_min[r.ts // 60 * 60].append(r.occ)
    occ_t = sorted(per_min)
    occ = [sorted(per_min[t])[len(per_min[t]) // 2] for t in occ_t]
    s = RSession(start=start, end=end, checkins=list(checkins),
                 entries=[r.ts for r in door_rows if r.direction == "in"],
                 exits=[r.ts for r in door_rows if r.direction == "out"],
                 occ_t=occ_t, occ=occ, breaks=breaks, trainers=tr, evidence_level=ev)
    res = reconcile_session(s, p)
    label = _label(door_rows + occ_rows) if (door_rows or occ_rows) else "simulated"
    rec = db.get(Reconciliation, (b.id, date)) or Reconciliation(batch_id=b.id, date=date, centre_id=b.centre_id)
    rec.score, rec.status, rec.evidence_level = res["score"], res["status"], res["evidence_level"]
    rec.unverified_trainee_hours = res.get("unverified_trainee_hours")
    res["occupancy_curve"] = [[t, o] for t, o in zip(occ_t, occ)]
    res["entries"], res["exits"] = s.entries, s.exits
    res["timetable"] = [[x.start, x.end, x.kind] for x in slots]
    res["trainers"] = tr
    rec.result, rec.label = res, label
    db.merge(rec)
    links = {"reconciliation": f"/v1/batches/{b.id}/reconciliation?date={date}"}
    for k in res.get("flags", []):
        sig = res["signals"][k]
        upsert_flag(db, b.centre_id, b.id, date, k, sig["severity"] if k != "burst" else max(0.5, sig["severity"]),
                    res["evidence_level"], sig["detail"], links, label)
    if res["status"] == "INSUFFICIENT_EVIDENCE":
        upsert_flag(db, b.centre_id, b.id, date, "data_gap", 0.3, "INSUFFICIENT",
                    f"Evidence insufficient for this session (coverage {res['coverage']:.0%}). "
                    "Silence is not compliance: shown as a data gap.", links, label)
    return res


def integrity_flags(db: Session, c: Centre):
    evs = db.scalars(select(IntegrityEvent).where(IntegrityEvent.centre_id == c.id,
                                                  IntegrityEvent.kind.in_(TAMPER))).all()
    by = defaultdict(list)
    for e in evs:
        by[(datetime.fromtimestamp(e.ts).strftime("%Y-%m-%d"), e.kind)].append(e)
    for (date, kind), rows in by.items():
        mins = len(rows)
        if kind == "clock_drift":
            drifts = [r.value.get("clk") for r in rows if r.value and r.value.get("clk") is not None]
            worst = max(drifts, key=abs) if drifts else None
            txt = (f"DVR clock differs from signed device time by {worst / 3600:+.1f} h" if worst and abs(worst) > 3600
                   else f"DVR clock differs from signed device time by {worst:+.0f} s") if worst is not None else "DVR clock drift"
        elif kind == "loop":
            hit = next((r.value.get("loop") for r in rows if r.value and r.value.get("loop")), None) or {}
            txt = f"Keyframe matches this camera's view on {hit.get('other_day', 'another day')} (Hamming {hit.get('hamming', '?')}/64, people present)"
        else:
            txt = f"{kind.replace('_', ' ')} detected on {rows[0].cam} for {mins} packet-minute(s)"
        # The tamper itself is directly observed (FULL); it is the attendance decision that abstains.
        upsert_flag(db, c.id, None, date, kind, min(1.0, 0.4 + mins / 20), "FULL", txt,
                    {"evidence": f"/v1/centres/{c.id}/summary#integrity", "cam": rows[0].cam}, _label(rows))
    # cross-centre duplicate registry
    mine = db.scalars(select(KeyframeHash).where(KeyframeHash.centre_id == c.id)).all()
    others = db.scalars(select(KeyframeHash).where(KeyframeHash.centre_id != c.id)).all()
    hits = registry.cross_centre_duplicates([(h.centre_id, h.phash, h.ts) for h in mine],
                                            [(h.centre_id, h.phash, h.ts) for h in others])
    by_day = defaultdict(list)
    for h in hits:
        by_day[datetime.fromtimestamp(h["t"]).strftime("%Y-%m-%d")].append(h)
    for date, hs in by_day.items():
        o = hs[0]
        upsert_flag(db, c.id, None, date, "cross_centre_duplicate", min(1.0, 0.6 + len(hs) / 10), "FULL",
                    f"{len(hs)} keyframe(s) match centre {o['other_centre']} on "
                    f"{datetime.fromtimestamp(o['other_t']):%d %b} (Hamming {o['hamming']}/64)",
                    {"matches": hs[:10]}, "measured")


def asset_flags(db: Session, c: Centre):
    obs = db.scalars(select(AssetObservation).where(AssetObservation.centre_id == c.id)
                     .order_by(AssetObservation.date)).all()
    by = defaultdict(list)
    for o in obs:
        by[o.asset_id].append(o)
    for aid, rows in by.items():
        last = rows[-1].date
        orn = asset_engine.ornamental([(r.date, r.interaction_s, r.scheduled_practical_s) for r in rows[-30:]])
        if orn["flag"]:
            upsert_flag(db, c.id, None, last, "ornamental_asset", orn["oai"], "FULL",
                        f"{aid}: {orn['detail']}. Wording: no use observed — not a claim the asset is broken.",
                        {"asset": aid, "oai": orn["oai"]}, _label(rows))
        sw = asset_engine.swapped([(r.date, r.identity_score) for r in rows if r.identity_score is not None])
        if sw["flag"]:
            upsert_flag(db, c.id, None, last, "asset_swapped", 1 - sw["min_sim"], "FULL",
                        f"{aid}: {sw['detail']}", {"asset": aid}, _label(rows))


def inventory_flags(db: Session, c: Centre):
    for b in db.scalars(select(Batch).where(Batch.centre_id == c.id)):
        enrolled = db.scalars(select(Enrolment.count).where(Enrolment.batch_id == b.id)).first() or 0
        need = {}
        for s in db.scalars(select(SanctionedInventory).where(SanctionedInventory.qp_code == b.qp_code)):
            need[s.item] = s.qty * (enrolled if s.per == "trainee" else 1)
        have = defaultdict(int)
        for a in db.scalars(select(AssetRegistry).where(AssetRegistry.centre_id == c.id)):
            have[a.label] += 1
        gaps = asset_engine.inventory_gap(need, have) if have else []
        if gaps:
            worst = max(gaps, key=lambda g: g["missing"] / g["sanctioned"])
            upsert_flag(db, c.id, b.id, datetime.now().strftime("%Y-%m-%d"), "asset_missing",
                        worst["missing"] / worst["sanctioned"], "FULL",
                        "; ".join(f"{g['item']}: {g['observed']}/{g['sanctioned']}" for g in gaps[:3]),
                        {"gaps": gaps}, "simulated" if c.label == "simulated" else "measured")


def daily_series(db: Session, centre_id: str) -> tuple[list[str], list[float]]:
    rows = db.execute(select(Reconciliation.date, func.avg(Reconciliation.score))
                      .where(Reconciliation.centre_id == centre_id, Reconciliation.score.is_not(None))
                      .group_by(Reconciliation.date).order_by(Reconciliation.date)).all()
    return [r[0] for r in rows], [float(r[1]) for r in rows]


def shadow_flag(db: Session, c: Centre) -> dict | None:
    dates, ys = daily_series(db, c.id)
    insp = [i.date for i in db.scalars(select(Inspection).where(Inspection.centre_id == c.id))]
    idx = [dates.index(d) for d in insp if d in dates]
    if len(ys) < 20 or len(idx) < 2:
        return None
    r = shadow.shadow(ys, idx)
    if r["flag"]:
        upsert_flag(db, c.id, None, dates[-1], "inspection_shadow", min(1.0, r["lift"] / 30), "FULL", r["detail"],
                    {"p_value": r["p_value"], "change_points": [dates[i] for i in r["change_points"]],
                     "inspections": insp}, "simulated" if c.label == "simulated" else "measured")
    return r


def gap_flags(db: Session, c: Centre):
    for g in db.scalars(select(DataGap).where(DataGap.centre_id == c.id, DataGap.resolved.is_(False))):
        date = datetime.fromtimestamp(g.start).strftime("%Y-%m-%d")
        upsert_flag(db, c.id, None, date, "data_gap", 0.3, "INSUFFICIENT",
                    f"{g.reason.replace('_', ' ')} on {g.cam}: {datetime.fromtimestamp(g.start):%H:%M}–"
                    f"{datetime.fromtimestamp(g.end or g.start):%H:%M}. Not treated as compliant.",
                    {"gap_id": g.id}, "measured")


def run_centre(db: Session, centre_id: str, dates: list[str] | None = None) -> dict:
    c = db.get(Centre, centre_id)
    out = {"centre": centre_id, "sessions": 0}
    for b in db.scalars(select(Batch).where(Batch.centre_id == centre_id)):
        ds = dates or sorted({datetime.fromtimestamp(s).strftime("%Y-%m-%d") for s in
                              db.scalars(select(TimetableSlot.start).where(TimetableSlot.batch_id == b.id))})
        for d in ds:
            if reconcile_batch_day(db, b, d):
                out["sessions"] += 1
    integrity_flags(db, c)
    asset_flags(db, c)
    inventory_flags(db, c)
    gap_flags(db, c)
    out["shadow"] = shadow_flag(db, c)
    db.commit()
    return out


def centre_risk(db: Session, centre_id: str) -> dict:
    flags = db.scalars(select(Flag).where(Flag.centre_id == centre_id,
                                          Flag.status.in_(["open", "awaiting_centre", "confirmed"]))).all()
    r = risk.centre_risk([{"id": f.id, "type": f.type, "severity": f.severity, "evidence_level": f.evidence_level,
                           "explanation": f.explanation} for f in flags])
    since = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    hours = db.scalars(select(func.sum(Reconciliation.unverified_trainee_hours)).where(
        Reconciliation.centre_id == centre_id, Reconciliation.date >= since)).first() or 0.0
    r["unverified_trainee_hours"] = round(hours, 1)
    r["rupees_at_risk"] = risk.rupees_at_risk(hours)
    r["open_flags"] = len(flags)
    r["labels"] = sorted({f.label for f in flags})
    levels = [f.evidence_level for f in flags]
    r["evidence_level"] = ("INSUFFICIENT" if "INSUFFICIENT" in levels else "REDUCED" if "REDUCED" in levels
                           else "FULL") if levels else None
    return r
