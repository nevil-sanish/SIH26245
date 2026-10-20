"""End-to-end §22 demo check: fresh SQLite DB → demo_seed → API walk (login, risk queue, centre, batch, flag,
review, centre response, scoping). Exits non-zero on the first broken expectation.

    python -m scripts.demo_check
"""
import os
import sys
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/demo.db"

from fastapi.testclient import TestClient  # noqa: E402

from cloud import demo_seed  # noqa: E402
from cloud.api import app  # noqa: E402

PW = "sakshi-demo-2026"   # demo accounts from data/demo/users.yaml
HIGH, CLEAN = {"TC0880", "TC0777", "TC0915", "TC0307"}, "TC0421"


def main():
    sys.argv = ["demo_seed", "--fresh"]
    demo_seed.main()
    c = TestClient(app)
    tok = lambda u: {"Authorization": "Bearer " + c.post("/v1/auth/login", json={"username": u, "password": PW}).json()["token"]}
    state, op = tok("state"), tok("tc0421")

    q = c.get("/v1/risk-queue", headers=state).json()
    print("risk queue:", [(r["id"], r["risk"], [x["type"] for x in r["reasons"]][:3]) for r in q])
    top = {r["id"] for r in q[:len(HIGH)]}
    clean = next(r for r in q if r["id"] == CLEAN)
    assert top == HIGH, f"top of queue {top} != {HIGH}"
    assert clean["risk"] < min(r["risk"] for r in q if r["id"] in HIGH), "honest TC0421 ranked with fraud centres"

    s = c.get(f"/v1/centres/{q[0]['id']}/summary", headers=state)
    assert s.status_code == 200, s.text
    b = s.json()["batches"][0]
    r = c.get(f"/v1/batches/{b['batch_id']}/reconciliation", headers=state, params={"date": b["date"]})
    assert r.status_code == 200, r.text

    flags = c.get("/v1/flags", headers=state, params={"centre": q[0]["id"]}).json()
    assert flags, "no flags on the top centre"
    f = flags[0]
    detail = c.get(f"/v1/flags/{f['id']}", headers=state).json()
    print("flag:", detail.get("type"), detail.get("label"), "evidence keys:", sorted(detail)[:12])
    r = c.post(f"/v1/flags/{f['id']}/review", headers=state, json={"action": "request_response", "note": "demo check"})
    assert r.status_code == 200, r.text
    case = r.json()["case_id"]
    assert c.get(f"/v1/centres/{q[0]['id']}/summary", headers=op).status_code == 403, "operator saw another centre"
    assert c.get("/v1/risk-queue", headers=op).status_code == 403, "operator saw the risk queue"
    for path in ("/v1/inspector/today", "/v1/health/fleet", "/v1/privacy", "/v1/accuracy", "/v1/audit-log"):
        assert c.get(path, headers=tok("admin")).status_code == 200, path
    print("case", case, "→ response requested; scoping + pages OK")
    print("DEMO_CHECK_OK")


if __name__ == "__main__":
    main()
