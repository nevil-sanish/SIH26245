"""Integration: edge packets → ingest → engines → API → review workflow, with role scoping (PROMPT §19)."""
import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/api.db"
os.environ["SAKSHI_ANALYZE_ON_INGEST"] = "0"

import numpy as np  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from nacl.signing import SigningKey  # noqa: E402

from cloud import analyze, sidh_mock  # noqa: E402
from cloud.api import app  # noqa: E402
from cloud.db import SessionLocal, init_db  # noqa: E402
from edge.packet import Packetizer, public_key_b64  # noqa: E402

T0 = 1_792_400_400 // 60 * 60     # a minute boundary
PW = "test-only-pw"


def setup_module():
    init_db(drop=True)
    key = SigningKey.generate()
    seed = {"centres": [dict(id="TCX", name="Test centre", state="S", district="D", lat=20, lon=80, label="mock",
                             public_key=public_key_b64(key))],
            "batches": [dict(id="TCX-B1", centre_id="TCX", job_role="r", qp_code="SSC/Q2212", room="R1",
                             door_cam="CAM-DOOR", room_cam="CAM-ROOM", label="mock")],
            "timetable": [dict(batch_id="TCX-B1", room="R1", start=T0, end=T0 + 3600, kind="theory")],
            "enrolments": [dict(batch_id="TCX-B1", count=25)],
            # bulk check-in: 25 check-ins in 40 s, nobody walks in, room empty
            "checkins": [dict(batch_id="TCX-B1", ts=int(T0 + 60 + i * 1.6), label="mock") for i in range(25)],
            "users": [dict(username="officer", role="state_monitor", password=PW),
                      dict(username="op", role="centre_operator", centre_id="TCX", password=PW),
                      dict(username="other", role="centre_operator", centre_id="TCY", password=PW)]}
    with SessionLocal() as db:
        sidh_mock.load(db, seed)
    door, room = Packetizer("TCX", "CAM-DOOR", key), Packetizer("TCX", "CAM-ROOM", key)
    pk = []
    for m in range(-5, 60):
        pk.append(door.build(T0 + 60 * m, **{"in": 0, "out": 0, "ev": "OK"}))
        pk.append(room.build(T0 + 60 * m, **{"occ": 1, "oc": [1] * 6, "ev": "OK"}))
    c = TestClient(app)
    r = c.post("/v1/ingest/packets", json=pk)
    assert len(r.json()["accepted"]) == len(pk)
    with SessionLocal() as db:
        analyze.run_centre(db, "TCX")


def tok(c, u):
    return {"Authorization": "Bearer " + c.post("/v1/auth/login", json={"username": u, "password": PW}).json()["token"]}


def test_end_to_end_flag_review_and_scoping():
    with TestClient(app) as c:
        off, op, other = tok(c, "officer"), tok(c, "op"), tok(c, "other")
        q = c.get("/v1/risk-queue", headers=off).json()
        assert q[0]["id"] == "TCX" and q[0]["risk"] > 50 and q[0]["evidence_level"] == "FULL"
        types = {r["type"] for r in q[0]["reasons"]}
        assert types & {"unmatched_checkin", "burst", "ghost_session"}
        rec = c.get("/v1/batches/TCX-B1/reconciliation", params={"date": analyze.datetime.fromtimestamp(T0).strftime("%Y-%m-%d")}, headers=off).json()
        assert rec["status"] == "DISCREPANCY" and len(rec["unmatched"]) == 25 and rec["source_data"]["label"] == "mock"
        fid = q[0]["reasons"][0]["flag_id"]
        ev = c.get(f"/v1/flags/{fid}", headers=off).json()
        assert ev["packets"]["signature_ok"] == ev["packets"]["count"] > 0
        assert c.post(f"/v1/flags/{fid}/review", json={"action": "request_response", "note": "explain"}, headers=off).json()["status"] == "awaiting_centre"
        # centre operators: own centre only, cannot confirm, can respond
        assert c.get("/v1/risk-queue", headers=op).status_code == 403
        assert c.get("/v1/centres/TCX/summary", headers=other).status_code == 403
        assert c.post(f"/v1/flags/{fid}/review", json={"action": "confirm"}, headers=op).status_code == 403
        case_id = c.get(f"/v1/flags/{fid}", headers=op).json()["case"]["id"]
        assert c.post(f"/v1/cases/{case_id}/response", json={"note": "device fault"}, headers=op).json()["status"] == "open"
        log = c.get("/v1/audit-log", headers=off).json()
        assert any(a["action"] == "centre_response" for a in log) and any(a["target"] == f"flag:{fid}" for a in log)
        assert c.get("/v1/risk-queue").status_code == 401
