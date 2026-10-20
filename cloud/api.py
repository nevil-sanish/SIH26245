"""SAKSHI cloud API (PROMPT §10). Run: uvicorn cloud.api:app --port 8000

Auth: JWT (HS256) with roles admin | state_monitor | district_officer | inspector | centre_operator.
Centre operators only ever see their own centre. Packet ingest is authenticated by the edge device's
Ed25519 signature instead of a JWT (devices have no user session).
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import threading
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import func, select

from cloud import analyze, cases
from cloud.db import (ROOT, AuditLog, Batch, Camera, Case, CaseAction, Centre, DataGap, Flag, IntegrityEvent,
                      Packet, Reconciliation, SessionLocal, User, init_db)
from cloud.ingest import ingest, server_key
from cloud.sidh_mock import check_password, export_batch

SECRET = os.environ.get("SAKSHI_JWT_SECRET", "dev-only-change-me")
DEV = os.environ.get("SAKSHI_DEV", "1") == "1"
THUMB_RETENTION_DAYS = 90
OFFICERS = ("admin", "state_monitor", "district_officer", "inspector")


def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def user(request: Request) -> dict:
    h = request.headers.get("authorization", "")
    if not h.lower().startswith("bearer "):
        raise HTTPException(401, "login required")
    try:
        return jwt.decode(h[7:], SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "invalid token")


def officer(u: dict = Depends(user)) -> dict:
    if u["role"] not in OFFICERS:
        raise HTTPException(403, "officers only")
    return u


def get_or_404(db, model, key, what: str):
    row = db.get(model, key)
    if row is None:
        raise HTTPException(404, f"unknown {what}")
    return row


def can_see(u: dict, centre_id: str):
    if u["role"] == "centre_operator" and u.get("centre_id") != centre_id:
        raise HTTPException(403, "centre operators see only their own centre")


def audit(db, u, action, target):
    db.add(AuditLog(user=u["sub"], role=u["role"], action=action, target=target)); db.commit()


# --- background: MQTT bridge + hourly partial reconciliation + retention purge -------------------
_dirty: set[str] = set()


def _mqtt_bridge(url: str):
    import paho.mqtt.client as mqtt
    from urllib.parse import urlparse
    u = urlparse(url)

    def on_msg(client, _u, m):
        msg = json.loads(m.payload)
        with SessionLocal() as db:
            ack = ingest(db, msg["packets"])
        _dirty.update(p["c"] for p in msg["packets"])
        client.publish(msg["reply"], json.dumps(ack), qos=1)

    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="sakshi-cloud")
    c.on_message = on_msg
    c.on_connect = lambda cl, *_: cl.subscribe("sakshi/packets", qos=1)
    while True:
        try:
            c.connect(u.hostname, u.port or 1883); c.loop_forever()
        except OSError:
            time.sleep(5)


def purge_and_analyze():
    with SessionLocal() as db:
        cutoff = int((datetime.now(timezone.utc) - timedelta(days=THUMB_RETENTION_DAYS)).timestamp())
        for p in db.scalars(select(Packet).where(Packet.t < cutoff, Packet.tier == "N")):
            p.body = {k: v for k, v in p.body.items() if k != "thumb"}
            p.tier = "W"
        db.commit()
        for c in list(_dirty):
            _dirty.discard(c)
            analyze.run_centre(db, c)


async def _hourly():
    while True:
        await asyncio.sleep(3600)
        await asyncio.to_thread(purge_and_analyze)


@asynccontextmanager
async def lifespan(_app):
    init_db()
    server_key()
    if os.environ.get("MQTT_URL"):
        threading.Thread(target=_mqtt_bridge, args=(os.environ["MQTT_URL"],), daemon=True).start()
    task = asyncio.create_task(_hourly())
    yield
    task.cancel()


app = FastAPI(title="SAKSHI", version="0.1", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(","),
                   allow_methods=["*"], allow_headers=["*"])


# --- auth / devices ----------------------------------------------------------------------------
class Login(BaseModel):
    username: str
    password: str


@app.post("/v1/auth/login")
def login(body: Login, db=Depends(db_session)):
    u = db.get(User, body.username)
    if not u or not check_password(body.password, u.password_hash):
        raise HTTPException(401, "bad credentials")
    claims = {"sub": u.username, "role": u.role, "centre_id": u.centre_id, "state": u.state,
              "exp": datetime.now(timezone.utc) + timedelta(hours=12)}
    db.add(AuditLog(user=u.username, role=u.role, action="login", target="-")); db.commit()
    return {"token": jwt.encode(claims, SECRET, algorithm="HS256"), "role": u.role, "centre_id": u.centre_id}


class Device(BaseModel):
    centre_id: str
    public_key: str


@app.post("/v1/devices")
def enrol_device(body: Device, u=Depends(user), db=Depends(db_session)):
    if u["role"] != "admin":
        raise HTTPException(403, "admin only")
    c = get_or_404(db, Centre, body.centre_id, "centre")
    c.public_key = body.public_key
    audit(db, u, "enrol_device", f"centre:{body.centre_id}")
    return {"ok": True, "server_public_key": base64.b64encode(bytes(server_key().verify_key)).decode()}


# --- ingest ------------------------------------------------------------------------------------
@app.post("/v1/ingest/packets")
async def ingest_packets(request: Request, bg: BackgroundTasks, db=Depends(db_session)):
    packets = await request.json()
    if isinstance(packets, dict):
        packets = [packets]
    ack = ingest(db, packets)
    centres = {p["c"] for p in packets if "c" in p}
    _dirty.update(centres)
    if os.environ.get("SAKSHI_ANALYZE_ON_INGEST", "1") == "1":
        bg.add_task(lambda: [analyze.run_centre(SessionLocal(), c) for c in centres])
    return ack


@app.post("/v1/engines/run")
def run_engines(centre: str | None = None, u=Depends(officer), db=Depends(db_session)):
    ids = [centre] if centre else [c.id for c in db.scalars(select(Centre))]
    return [analyze.run_centre(db, c) for c in ids]


# --- centres / risk ----------------------------------------------------------------------------
def _centre_row(db, c: Centre) -> dict:
    r = analyze.centre_risk(db, c.id)
    last_insp = db.execute(select(func.max(analyze.Inspection.date)).where(analyze.Inspection.centre_id == c.id)).scalar()
    gaps = db.scalar(select(func.count()).select_from(DataGap).where(DataGap.centre_id == c.id,
                                                                     DataGap.resolved.is_(False)))
    return {"id": c.id, "name": c.name, "state": c.state, "district": c.district, "lat": c.lat, "lon": c.lon,
            "label": c.label, "risk": r["risk"], "reasons": r["reasons"], "evidence_level": r["evidence_level"],
            "rupees_at_risk": r["rupees_at_risk"], "unverified_trainee_hours": r["unverified_trainee_hours"],
            "open_flags": r["open_flags"], "flag_labels": r["labels"], "last_inspection": last_insp, "data_gaps": gaps}


def _visible_centres(db, u):
    q = select(Centre)
    if u["role"] == "centre_operator":
        q = q.where(Centre.id == u["centre_id"])
    elif u["role"] in ("state_monitor", "district_officer") and u.get("state"):
        q = q.where(Centre.state == u["state"])
    return db.scalars(q).all()


@app.get("/v1/centres")
def list_centres(state: str | None = None, risk_min: float = 0, u=Depends(user), db=Depends(db_session)):
    rows = [_centre_row(db, c) for c in _visible_centres(db, u) if not state or c.state == state]
    return [r for r in rows if r["risk"] >= risk_min]


@app.get("/v1/risk-queue")
def risk_queue(u=Depends(officer), db=Depends(db_session)):
    rows = sorted((_centre_row(db, c) for c in _visible_centres(db, u)), key=lambda r: -r["risk"])
    audit(db, u, "view", "risk-queue")
    return rows


@app.get("/v1/centres/{cid}/summary")
def centre_summary(cid: str, u=Depends(user), db=Depends(db_session)):
    can_see(u, cid)
    c = get_or_404(db, Centre, cid, "centre")
    dates, ys = analyze.daily_series(db, cid)
    recs = db.scalars(select(Reconciliation).where(Reconciliation.centre_id == cid)
                      .order_by(Reconciliation.date.desc())).all()
    obs = db.scalars(select(analyze.AssetObservation).where(analyze.AssetObservation.centre_id == cid)
                     .order_by(analyze.AssetObservation.date)).all()
    per_asset = defaultdict(list)
    for o in obs:
        per_asset[o.asset_id].append(o)
    from cloud.engines.assets import ornamental
    assets = [{"asset_id": a, **ornamental([(r.date, r.interaction_s, r.scheduled_practical_s) for r in rows[-30:]]),
               "identity": [[r.date, r.identity_score] for r in rows if r.identity_score is not None],
               "label": rows[-1].label} for a, rows in per_asset.items()]
    inventory = []
    for b in db.scalars(select(Batch).where(Batch.centre_id == cid)):
        enr = (db.get(analyze.Enrolment, b.id) or analyze.Enrolment(count=0)).count
        have = defaultdict(int)
        for a in db.scalars(select(analyze.AssetRegistry).where(analyze.AssetRegistry.centre_id == cid)):
            have[a.label] += 1
        for s in db.scalars(select(analyze.SanctionedInventory).where(analyze.SanctionedInventory.qp_code == b.qp_code)):
            inventory.append({"batch": b.id, "item": s.item, "sanctioned": s.qty * (enr if s.per == "trainee" else 1),
                              "observed": have.get(s.item, 0), "source_note": s.source_note, "label": "mock"})
    integ = db.scalars(select(IntegrityEvent).where(IntegrityEvent.centre_id == cid)
                       .order_by(IntegrityEvent.ts)).all()
    flags = db.scalars(select(Flag).where(Flag.centre_id == cid).order_by(Flag.date.desc())).all()
    audit(db, u, "view", f"centre:{cid}")
    return {"centre": {"id": c.id, "name": c.name, "state": c.state, "district": c.district, "label": c.label},
            "risk": analyze.centre_risk(db, cid),
            "score_trend": [{"date": d, "score": round(y, 1)} for d, y in zip(dates, ys)],
            "inspections": [i.date for i in db.scalars(select(analyze.Inspection).where(analyze.Inspection.centre_id == cid))],
            "batches": [{"batch_id": r.batch_id, "date": r.date, "score": r.score, "status": r.status,
                         "evidence_level": r.evidence_level, "unverified_trainee_hours": r.unverified_trainee_hours,
                         "label": r.label} for r in recs[:60]],
            "assets": assets, "inventory": inventory,
            "integrity": [{"ts": e.ts, "cam": e.cam, "kind": e.kind, "value": e.value, "label": e.label}
                          for e in integ if e.kind != "clock_reading"][-200:],
            "clock": [{"ts": e.ts, "drift": e.value["drift"]} for e in integ if e.kind == "clock_reading"][-500:],
            "flags": [_flag_row(f) for f in flags]}


def _flag_row(f: Flag) -> dict:
    return {"id": f.id, "centre_id": f.centre_id, "batch_id": f.batch_id, "date": f.date, "type": f.type,
            "severity": f.severity, "confidence": f.confidence, "evidence_level": f.evidence_level,
            "explanation": f.explanation, "next_step": f.next_step, "status": f.status, "label": f.label,
            "links": f.links}


@app.get("/v1/batches/{bid}/reconciliation")
def batch_reconciliation(bid: str, date: str, u=Depends(user), db=Depends(db_session)):
    b = get_or_404(db, Batch, bid, "batch")
    can_see(u, b.centre_id)
    r = db.get(Reconciliation, (bid, date))
    if r is None:
        raise HTTPException(404, "no reconciliation for that date")
    d0, d1 = analyze._day_bounds(date)
    audit(db, u, "view", f"reconciliation:{bid}:{date}")
    return {"batch_id": bid, "date": date, "label": r.label, "source_data": export_batch(db, bid, d0 - 3600, d1),
            **r.result}


@app.get("/v1/flags")
def list_flags(centre: str | None = None, status: str | None = None, u=Depends(user), db=Depends(db_session)):
    q = select(Flag)
    if u["role"] == "centre_operator":
        q = q.where(Flag.centre_id == u["centre_id"])
    elif centre:
        q = q.where(Flag.centre_id == centre)
    if status:
        q = q.where(Flag.status == status)
    return [_flag_row(f) for f in db.scalars(q.order_by(Flag.date.desc())).all()]


@app.get("/v1/flags/{fid}")
def flag_evidence(fid: int, u=Depends(user), db=Depends(db_session)):
    f = get_or_404(db, Flag, fid, "flag")
    can_see(u, f.centre_id)
    d0, d1 = analyze._day_bounds(f.date)
    pk = db.scalars(select(Packet).where(Packet.centre_id == f.centre_id, Packet.t >= d0, Packet.t < d1)
                    .order_by(Packet.cam, Packet.seq)).all()
    thumbs = [{"t": p.t, "cam": p.cam, "jpeg_b64": p.body["thumb"], "flags": p.body.get("flags")}
              for p in pk if p.body.get("thumb")][:12]
    case = db.query(Case).filter_by(flag_id=f.id).first()
    actions = db.query(CaseAction).filter_by(case_id=case.id).order_by(CaseAction.ts).all() if case else []
    audit(db, u, "view", f"flag:{fid}")
    return {**_flag_row(f),
            "packets": {"count": len(pk), "signature_ok": sum(p.sig_ok for p in pk),
                        "chain_ok": sum(1 for p in pk if p.chain_ok), "chain_unknown": sum(1 for p in pk if p.chain_ok is None),
                        "chain_broken": sum(1 for p in pk if p.chain_ok is False),
                        "sample": [{"cam": p.cam, "seq": p.seq, "t": p.t, "hash": p.hash, "prev": p.prev_hash,
                                    "sig": p.sig[:16] + "…", "bytes": p.bytes} for p in pk[:5]]},
            "thumbnails": thumbs,
            "clock": [{"ts": p.t, "drift": p.body.get("clk")} for p in pk if p.body.get("clk") is not None],
            "case": {"id": case.id, "status": case.status, "assigned_to": case.assigned_to,
                     "actions": [{"actor": a.actor, "role": a.role, "action": a.action, "note": a.note,
                                  "ts": a.ts.isoformat()} for a in actions]} if case else None}


class Review(BaseModel):
    action: str                    # confirm | false_alarm | request_response | assign | site_check | close
    note: str | None = None
    assignee: str | None = None


@app.post("/v1/flags/{fid}/review")
def review_flag(fid: int, body: Review, u=Depends(user), db=Depends(db_session)):
    f = get_or_404(db, Flag, fid, "flag")
    try:
        c = cases.act(db, f, u, body.action, body.note, body.assignee)
    except cases.Forbidden as e:
        raise HTTPException(403, str(e))
    return {"case_id": c.id, "status": c.status}


class Response(BaseModel):
    note: str
    action: str = "centre_response"   # centre_response | appeal


@app.post("/v1/cases/{cid}/response")
def case_response(cid: int, body: Response, u=Depends(user), db=Depends(db_session)):
    c = get_or_404(db, Case, cid, "case")
    try:
        c = cases.act(db, db.get(Flag, c.flag_id), u, body.action, body.note)
    except cases.Forbidden as e:
        raise HTTPException(403, str(e))
    return {"case_id": c.id, "status": c.status}


# --- inspector ---------------------------------------------------------------------------------
@app.get("/v1/inspector/today")
def inspector_today(n: int = 5, u=Depends(officer), db=Depends(db_session)):
    visits = []
    for r in sorted((_centre_row(db, c) for c in _visible_centres(db, u)), key=lambda r: -r["risk"])[:n]:
        fl = db.scalars(select(Flag).where(Flag.centre_id == r["id"], Flag.status.in_(["open", "awaiting_centre"]))).all()
        visits.append({**r, "checklist": [{"flag_id": f.id, "type": f.type, "check": f.next_step,
                                           "what": f.explanation} for f in fl]})
    return visits


# --- fleet health / calibration ----------------------------------------------------------------
@app.get("/v1/health/fleet")
def fleet_health(u=Depends(officer), db=Depends(db_session)):
    now_t = time.time()
    cams = []
    for cam in db.scalars(select(Camera)):
        recent = db.scalars(select(Packet.body).where(Packet.centre_id == cam.centre_id, Packet.cam == cam.cam)
                            .order_by(Packet.seq.desc()).limit(60)).all()
        cams.append({"id": cam.id, "centre_id": cam.centre_id, "cam": cam.cam, "role": cam.role,
                     "last_packet_t": cam.last_t, "online": bool(cam.last_seen and now_t - cam.last_seen.timestamp() < 300),
                     "unavailable_modules": cam.unavailable or [], "packets": len(recent),
                     "evidence": {lvl: sum(1 for b in recent if b.get("ev") == lvl) for lvl in ("OK", "INSUFFICIENT")},
                     "mean_bytes": round(db.scalar(select(func.avg(Packet.bytes)).where(
                         Packet.centre_id == cam.centre_id, Packet.cam == cam.cam)) or 0, 1)})
    gaps = db.scalars(select(DataGap).where(DataGap.resolved.is_(False))).all()
    models = {m: (ROOT / "models" / m).exists() for m in ("rfdetr_nano_coco.onnx", "rfdetr_nano_head.onnx")}
    run_log = ROOT / "data" / "work" / "edge_runs.json"
    return {"cameras": cams, "models": models,
            "edge_runs": json.loads(run_log.read_text()) if run_log.exists() else [],
            "data_gaps": [{"id": g.id, "centre_id": g.centre_id, "cam": g.cam, "start": g.start, "end": g.end,
                           "reason": g.reason} for g in gaps]}


@app.get("/v1/cameras/{camera_id}/config")
def get_config(camera_id: str, u=Depends(user), db=Depends(db_session)):
    cam = get_or_404(db, Camera, camera_id, "camera")
    can_see(u, cam.centre_id)
    return cam.config or {}


@app.put("/v1/cameras/{camera_id}/config")
async def put_config(camera_id: str, request: Request, u=Depends(user), db=Depends(db_session)):
    cam = get_or_404(db, Camera, camera_id, "camera")
    if u["role"] not in ("admin", "centre_operator"):
        raise HTTPException(403, "admin or the centre's operator only")
    can_see(u, cam.centre_id)
    cam.config = await request.json()
    audit(db, u, "calibrate", f"camera:{camera_id}")
    return {"ok": True}


# --- privacy / audit / accuracy / red-team -----------------------------------------------------
@app.get("/v1/privacy")
def privacy(u=Depends(user), db=Depends(db_session)):
    return {"stored": [
        {"data": "Whisper packets (counts, event offsets, occupancy, flags)", "where": "cloud", "retention": "scheme duration (aggregate, no images)", "label": "measured"},
        {"data": "Face-blurred 96×54 thumbnails (anomalies only)", "where": "cloud", "retention": f"{THUMB_RETENTION_DAYS} days, then purged hourly", "label": "measured"},
        {"data": "Encrypted raw clips (sealed to the state nodal officer)", "where": "edge only", "retention": "7–30 days, released only on a formal audit request", "label": "measured"},
        {"data": "Check-in timestamps (no names)", "where": "cloud", "retention": "scheme duration", "label": "mock"},
        {"data": "Asset embeddings (equipment only, never people)", "where": "edge only", "retention": "until asset de-registered", "label": "measured"}],
        "never": ["face recognition", "face or person embeddings", "cross-day person tracking", "behaviour / engagement scoring",
                  "automatic penalties", "raw video upload"],
        "thumbnails_held": db.scalar(select(func.count()).select_from(Packet).where(Packet.tier == "N"))}


@app.get("/v1/audit-log")
def audit_log(limit: int = 200, u=Depends(user), db=Depends(db_session)):
    if u["role"] not in ("admin", "state_monitor"):
        raise HTTPException(403, "admin / state monitor only")
    return [{"ts": a.ts.isoformat(), "user": a.user, "role": a.role, "action": a.action, "target": a.target}
            for a in db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(limit))]


@app.get("/v1/accuracy")
def accuracy(u=Depends(user)):
    p = ROOT / "data" / "work" / "accuracy.json"
    if not p.exists():
        raise HTTPException(404, "no accuracy run yet — `make eval`")
    return json.loads(p.read_text())


@app.post("/v1/redteam/run")
def redteam_run(seeds: int = Query(10, le=50), u=Depends(officer)):
    if not DEV:
        raise HTTPException(403, "dev only")
    from eval.metrics import run_all
    return run_all(seeds=seeds)
