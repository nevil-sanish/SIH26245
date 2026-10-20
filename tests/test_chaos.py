"""Chaos tests (PROMPT §19, D5): 2 h uplink outage with zero loss; corrupt signature; reorder; duplicates."""
import os
import socket
import tempfile
import threading
import time

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/chaos.db"
os.environ["SAKSHI_ANALYZE_ON_INGEST"] = "0"

import uvicorn  # noqa: E402
from nacl.signing import SigningKey  # noqa: E402

from cloud.db import Centre, DataGap, Packet, SessionLocal, init_db  # noqa: E402
from cloud.ingest import ingest  # noqa: E402
from edge.outbox import Outbox  # noqa: E402
from edge.packet import Packetizer, public_key_b64  # noqa: E402

T0 = 1_792_400_000


def _centre(cid, key):
    init_db()
    with SessionLocal() as db:
        db.merge(Centre(id=cid, name=cid, state="-", district="-", lat=0, lon=0, public_key=public_key_b64(key)))
        db.commit()


def _packets(cid, key, n, cam="CAM1"):
    pz = Packetizer(cid, cam, key)
    return [pz.build(T0 + 60 * i, **{"in": i % 3, "out": 0, "occ": 10, "ev": "OK"}) for i in range(n)]


def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def test_two_hour_outage_no_data_loss(tmp_path):
    key = SigningKey.generate()
    _centre("CHAOS1", key)
    port = _free_port()
    ob = Outbox(str(tmp_path / "outbox.sqlite"), f"http://127.0.0.1:{port}")
    pz = Packetizer("CHAOS1", "CAM1", key)
    for i in range(120):                       # 120 one-minute packets = 2 h, uplink down the whole time
        p = pz.build(T0 + 60 * i, **{"in": 1, "out": 0, "occ": 12, "ev": "OK"})
        ob.put(p, pz.prev)
        assert ob.flush(timeout=0.2) == 0
    assert ob.pending() == 120
    from cloud.api import app
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    th = threading.Thread(target=server.run, daemon=True); th.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    try:
        assert ob.drain() == 120 and ob.pending() == 0
        assert ob.last_server_time is not None            # ack carried signed server time
    finally:
        server.should_exit = True; th.join(5)
    with SessionLocal() as db:
        rows = db.query(Packet).filter_by(centre_id="CHAOS1").order_by(Packet.seq).all()
        assert [r.seq for r in rows] == list(range(1, 121))
        assert all(r.sig_ok and r.chain_ok for r in rows)
        assert db.query(DataGap).filter_by(centre_id="CHAOS1", resolved=False).count() == 0


def test_corrupt_signature_rejected():
    key = SigningKey.generate()
    _centre("CHAOS2", key)
    pk = _packets("CHAOS2", key, 3)
    pk[1] = {**pk[1], "occ": 99}                           # tampered after signing
    with SessionLocal() as db:
        ack = ingest(db, pk)
    assert [r["seq"] for r in ack["rejected"]] == [2] and ack["rejected"][0]["reason"] == "bad signature"
    with SessionLocal() as db:
        assert db.query(DataGap).filter_by(centre_id="CHAOS2", reason="seq_gap").count() == 1   # hole is visible


def test_reorder_and_duplicates():
    key = SigningKey.generate()
    _centre("CHAOS3", key)
    pk = _packets("CHAOS3", key, 10)
    with SessionLocal() as db:
        a = ingest(db, pk[5:])                              # later half first (reordered delivery)
        b = ingest(db, pk[:5] + pk[2:4])                    # then the rest, plus two duplicates
    assert len(a["accepted"]) == 5 and len(b["accepted"]) == 5 and len(b["duplicate"]) == 2
    with SessionLocal() as db:
        rows = db.query(Packet).filter_by(centre_id="CHAOS3").order_by(Packet.seq).all()
        assert len(rows) == 10 and all(r.chain_ok for r in rows)
        assert db.query(DataGap).filter_by(centre_id="CHAOS3", resolved=False, reason="seq_gap").count() == 0


def test_unknown_device_rejected():
    init_db()
    with SessionLocal() as db:
        ack = ingest(db, _packets("NOPE", SigningKey.generate(), 1))
    assert ack["rejected"][0]["reason"] == "unknown device"


def test_sms_summary_fits_one_sms():
    from edge.outbox import sms_summary
    key = SigningKey.generate()
    pk = _packets("TC0421", key, 480) + [{**p, "cam": "CAM-ROOM", "flags": ["frozen"]} for p in _packets("TC0421", key, 480)]
    s = sms_summary(pk)
    assert s.startswith("SK|TC0421|") and len(s) <= 160
    segs = dict(x.split(":") for x in s.split("|")[3].split(";"))
    assert segs["M-ROOM"].endswith("/1") and segs["CAM1"].endswith("/0")   # frozen bit only on the room camera
