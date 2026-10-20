"""D4 accuracy assessment. `python -m eval.metrics` → data/work/accuracy.json (then eval/report.py → docs).

measured   door P/R and per-frame count MAE of the real edge pipeline on the labelled MEVA G420 clip;
           video red-team scenarios (R4 replay, R5 two centres, R6 frozen/covered) through edge + cloud
simulated  event/series scenarios R1–R3, R7–R9, N1–N3 (+ controls for R7–R9) through the cloud engines,
           with detector noise set from the *measured* door recall/precision and count MAE
bandwidth  bytes per packet / per hour per camera per tier, from the real outbox
Head-count MAE on SCUT-HEAD (classroom CCTV stills) is measured in Colab: models/head_metrics.json.
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
import yaml
from scipy.optimize import linear_sum_assignment

from redteam.generators import SCENARIOS, Noise
from redteam.runner import DEMO_DAY, SOURCES, VIDEO_RUNS

ROOT = Path(__file__).resolve().parents[1]
ANN = ROOT / "data" / "raw" / "meva" / "annotations" / "annotation" / "DIVA-phase-2" / "MEVA" / "kitware"
OUT = ROOT / "data" / "work" / "accuracy.json"
FRAUD_FLAGS = {"unmatched_checkin", "burst", "ghost_session", "inflation", "checkin_then_leave", "trainee_hours_gap",
               "clock_drift", "clock_non_monotonic", "loop", "cross_centre_duplicate", "frozen", "covered", "moved",
               "ornamental_asset", "asset_swapped", "inspection_shadow"}


# --------------------------------------------------------------------------- MEVA ground truth
def meva_gt(stem: str, fps: float = 30.0):
    """Door events (end frame of each *_through_structure activity) and per-frame person boxes."""
    day, hour = stem[:10], stem.split(".")[1][:2]
    base = ANN / day / hour / stem
    acts = yaml.load(open(f"{base}.activities.yml"), Loader=yaml.CSafeLoader)
    events = []
    for a in acts:
        if "act" not in a:
            continue
        kind = next(iter(a["act"]["act2"]))
        if kind.endswith("scene_through_structure"):
            f0, f1 = a["act"]["timespan"][0]["tsr0"]
            events.append(("in" if "enters" in kind else "out", f1 / fps))
    per_frame = defaultdict(int)
    pat = re.compile(r"ts0: (\d+),")
    for line in open(f"{base}.geom.yml"):
        m = pat.search(line)
        if m:
            per_frame[int(m.group(1))] += 1
    return events, per_frame


def match_pr(gt: list[float], det: list[float], tol: float) -> dict:
    gt, det = np.asarray(gt, float), np.asarray(det, float)
    if gt.size == 0 or det.size == 0:
        return {"tp": 0, "fp": int(det.size), "fn": int(gt.size), "precision": None if det.size == 0 else 0.0,
                "recall": None if gt.size == 0 else 0.0}
    cost = np.abs(gt[:, None] - det[None, :])
    cost[cost > tol] = 1e9
    r, c = linear_sum_assignment(cost)
    tp = int((cost[r, c] < 1e9).sum())
    return {"tp": tp, "fp": int(det.size - tp), "fn": int(gt.size - tp),
            "precision": round(tp / det.size, 3), "recall": round(tp / gt.size, 3)}


def outbox_packets(centre: str, cam: str) -> list[dict]:
    p = ROOT / "data" / "edge_state" / centre / "outbox.sqlite"
    if not p.exists():
        return []
    rows = sqlite3.connect(p).execute("SELECT body FROM outbox WHERE cam=? ORDER BY seq", (cam,)).fetchall()
    return [json.loads(r[0]) for r in rows]


def door_eval(centre="TC0421", cam="CAM-DOOR", clip="G420_busy", tol=4.0, start=None) -> dict:
    stem = Path(SOURCES[clip][0]).name.removesuffix(".r13.avi")
    start = start or SOURCES[clip][1]
    t0 = start.timestamp()
    events, _ = meva_gt(stem)
    pk = [p for p in outbox_packets(centre, cam) if t0 - 60 <= p["t"] <= t0 + 400]
    det = {"in": [p["t"] + o - t0 for p in pk for o in p.get("ei", [])],
           "out": [p["t"] + o - t0 for p in pk for o in p.get("eo", [])]}
    res = {}
    for d in ("in", "out"):
        res[d] = match_pr([t for k, t in events if k == d], det[d], tol)
        res[d]["gt"] = sum(1 for k, _ in events if k == d)
    both = match_pr([t for _, t in events], det["in"] + det["out"], tol)  # direction-agnostic
    res["any_direction"] = both
    res["tolerance_s"] = tol
    res["label"] = "measured"
    return res


def count_eval(clip="G420_busy", model="models/rfdetr_nano_coco.onnx", every_s=2.0, video=None) -> dict:
    """Per-frame person count vs MEVA annotated boxes on a 5-min clip. Caveat: MEVA annotates the people
    involved in activities; on the door camera that is effectively everyone in view."""
    import cv2
    from edge.detect import Detector
    stem = Path(SOURCES[clip][0]).name.removesuffix(".r13.avi")
    _, per_frame = meva_gt(stem)
    det = Detector(str(ROOT / model), [1], 0.4)
    cap = cv2.VideoCapture(str(video or ROOT / "data" / "work" / "clips" / f"{clip}.mp4"))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    err, n, i, step = [], 0, 0, int(fps * every_s)
    pred, truth = [], []
    while True:
        ok = cap.grab()
        if not ok:
            break
        if i % step == 0:
            _, f = cap.retrieve()
            gt_frame = int(round(i / fps * 30))
            p = len(det(f))
            pred.append(p); truth.append(per_frame.get(gt_frame, 0))
        i += 1
    pred, truth = np.array(pred), np.array(truth)
    return {"frames": int(len(pred)), "mae": round(float(np.abs(pred - truth).mean()), 3),
            "mean_true": round(float(truth.mean()), 2), "bias": round(float((pred - truth).mean()), 3),
            "label": "measured"}


# --------------------------------------------------------------------------- confusion matrices
def confusion(rows: list[dict]) -> dict:
    """Per scenario: fraud rows → TP (an expected flag fired) / FN; honest rows → TN / FP (any fraud flag)."""
    out = {}
    by = defaultdict(list)
    for r in rows:
        by[r["scenario"]].append(r)
    for sid, rs in sorted(by.items()):
        if rs[0]["honest"]:
            fp = sum(1 for r in rs if set(r["fired"]) & FRAUD_FLAGS)
            out[sid] = {"kind": "honest", "n": len(rs), "TN": len(rs) - fp, "FP": fp,
                        "fp_rate": round(fp / len(rs), 3),
                        "false_flags": sorted({f for r in rs for f in r["fired"]})}
        else:
            exp = set(rs[0]["expect"])
            tp = sum(1 for r in rs if set(r["fired"]) & exp)
            out[sid] = {"kind": "fraud", "n": len(rs), "TP": tp, "FN": len(rs) - tp,
                        "fn_rate": round(1 - tp / len(rs), 3), "expected": sorted(exp),
                        "fired": sorted({f for r in rs for f in r["fired"]})}
        out[sid]["name"] = SCENARIOS["scenarios"].get(sid.split("-")[0], {}).get("name", sid)
        out[sid]["label"] = rs[0].get("label", "simulated")
    return out


def video_scenarios() -> list[dict]:
    """Ingest every edge outbox into a throw-away in-process cloud and read back the flags per centre."""
    import os
    import tempfile
    os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/eval.db"
    import importlib
    import cloud.db as dbm
    importlib.reload(dbm)
    from cloud import analyze, ingest as ing
    importlib.reload(ing); importlib.reload(analyze)
    from edge.packet import load_or_create_key, public_key_b64
    dbm.init_db()
    db = dbm.SessionLocal()
    centres = sorted({c for c, *_ in VIDEO_RUNS})
    for c in centres:
        key = load_or_create_key(ROOT / "data" / "edge_state" / c / "device.key")
        db.merge(dbm.Centre(id=c, name=c, state="-", district="-", lat=0, lon=0, public_key=public_key_b64(key)))
    db.commit()
    for c in centres:
        p = ROOT / "data" / "edge_state" / c / "outbox.sqlite"
        pk = [json.loads(r[0]) for r in sqlite3.connect(p).execute("SELECT body FROM outbox")]
        ing.ingest(db, pk)
    for c in centres:
        analyze.integrity_flags(db, db.get(dbm.Centre, c))
    db.commit()
    fired = defaultdict(set)
    for f in db.query(dbm.Flag).all():
        fired[f.centre_id].add(f.type)
    plan = {"TC0421": ("N-video", True, None), "TC0777": ("R4", False, ["clock_drift", "loop"]),
            "TC0555": ("R5", False, ["cross_centre_duplicate"]), "TC0612": ("R6", False, ["frozen", "covered"]),
            "TC0198": ("N-video-lab", True, None)}
    rows = []
    for c, (sid, honest, exp) in plan.items():
        if c in centres:
            rows.append({"scenario": sid, "seed": 0, "honest": honest, "expect": exp, "fired": sorted(fired[c]),
                         "label": "measured"})
    return rows


def bandwidth() -> dict:
    out = {}
    for centre, *_ in VIDEO_RUNS:
        p = ROOT / "data" / "edge_state" / centre / "outbox.sqlite"
        if not p.exists():
            continue
        for cam, body in sqlite3.connect(p).execute("SELECT cam, body FROM outbox"):
            b = json.loads(body)
            out.setdefault(cam, {"W": [], "N": []})[b.get("tier", "W")].append(len(body))
    res = {}
    for cam, t in out.items():
        allb = t["W"] + t["N"]
        res[cam] = {"packets": len(allb), "whisper_mean_B": round(float(np.mean(t["W"])), 1) if t["W"] else None,
                    "normal_mean_B": round(float(np.mean(t["N"])), 1) if t["N"] else None,
                    "whisper_KB_per_hour": round(float(np.mean(t["W"])) * 60 / 1024, 2) if t["W"] else None,
                    "observed_KB_per_hour": round(float(np.mean(allb)) * 60 / 1024, 2), "label": "measured"}
    return res


def measured_noise(door: dict | None, count: dict | None) -> Noise:
    n = Noise()
    if door and door["any_direction"]["recall"] is not None:
        n.door_recall = max(0.05, door["any_direction"]["recall"])
        n.door_precision = max(0.05, door["any_direction"]["precision"] or 0.05)
    if count:
        n.count_mae = count["mae"]
    return n


def run_all(seeds: int = 20, video: bool = True) -> dict:
    from redteam.runner import sims
    res = {"generated": datetime.now().isoformat(timespec="seconds"), "seeds": seeds, "demo_day": DEMO_DAY.date().isoformat()}
    door = count = None
    if (ROOT / "models" / "rfdetr_nano_coco.onnx").exists() and outbox_packets("TC0421", "CAM-DOOR"):
        door = door_eval()
        count = count_eval()
        res["door"], res["count_door_clip"] = door, count
    noise = measured_noise(door, count)
    res["noise_model"] = {**noise.__dict__, "source": "measured" if door else "placeholder (no edge run yet)"}
    rows = sims(seeds, noise)
    if video and (ROOT / "data" / "edge_state").exists():
        rows += video_scenarios()
    res["confusion"] = confusion(rows)
    fraud = [v for v in res["confusion"].values() if v["kind"] == "fraud"]
    honest = [v for v in res["confusion"].values() if v["kind"] == "honest"]
    res["overall"] = {"fraud_fn_rate": round(sum(v["FN"] for v in fraud) / max(1, sum(v["n"] for v in fraud)), 3),
                      "honest_fp_rate": round(sum(v["FP"] for v in honest) / max(1, sum(v["n"] for v in honest)), 3)}
    res["bandwidth"] = bandwidth()
    hm = ROOT / "models" / "head_metrics.json"
    res["head_model"] = json.loads(hm.read_text()) if hm.exists() else None
    rb = ROOT / "data" / "work" / "robustness.json"
    res["robustness"] = json.loads(rb.read_text()) if rb.exists() else None
    runs = ROOT / "data" / "work" / "edge_runs.json"
    res["edge_runs"] = json.loads(runs.read_text()) if runs.exists() else None
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1, default=str))
    return res


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--no-video", action="store_true")
    a = ap.parse_args()
    r = run_all(a.seeds, not a.no_video)
    print(json.dumps({k: r[k] for k in ("overall", "noise_model")}, indent=1))
