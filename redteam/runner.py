"""Red-team runner.

    python -m redteam.runner prepare            # build demo + red-team clips in data/work/clips (ffmpeg)
    python -m redteam.runner video [--uplink U] # run the edge pipeline on every video scenario → packets
    python -m redteam.runner sims --seeds 20    # event + series scenarios through the cloud engines

Timeline: MEVA footage from 2018-03-11 is re-stamped onto the demo day DEMO_DAY with a burned-in DVR clock
(documented in docs/DATASETS.md). Video scenarios run the *real* edge pipeline (label measured: real model
output on manipulated footage); event/series scenarios are labelled simulated.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

from redteam.generators import (SCENARIOS, Noise, burn_clock, event_session, freeze_and_cover, r7_asset_days,
                                r8_identity_days, r9_centre_days)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
CLIPS = ROOT / "data" / "work" / "clips"
DEMO_DAY = datetime(2026, 10, 19)
MEVA = RAW / "meva"

SOURCES = {
    "G420_busy": (MEVA / "2018-03-11.12-00-00.12-05-00.school.G420.r13.avi", DEMO_DAY.replace(hour=12)),
    "G420_exits": (MEVA / "2018-03-11.11-15-00.11-20-00.school.G420.r13.avi", DEMO_DAY.replace(hour=11, minute=15)),
    "G421_room": (MEVA / "2018-03-11.11-55-01.12-00-01.school.G421.r13.avi", DEMO_DAY.replace(hour=11, minute=55, second=1)),
    "lab": (RAW / "commons" / "mexico_computer_lab.ogv", DEMO_DAY.replace(hour=10)),
    "lab_india": (RAW / "commons" / "india_computer_lab.ogv", DEMO_DAY.replace(hour=10)),
}


def prepare():
    """Honest clips (clock = true time) + manipulated clips. Idempotent."""
    out = {}
    for name, (src, start) in SOURCES.items():
        dst = CLIPS / f"{name}.mp4"
        if not dst.exists():
            burn_clock(src, dst, start, scale="1280:720" if name.startswith("G42") else None)
        out[name] = str(dst)
    # R4 — yesterday's recording replayed today: the burned clock says yesterday.
    src, start = SOURCES["G420_busy"]
    r4 = CLIPS / "R4_G420_replay.mp4"
    if not r4.exists():
        burn_clock(src, r4, start - timedelta(days=1), scale="1280:720")
    out["R4"] = str(r4)
    # R6 — freeze then cover on the room clip.
    r6 = CLIPS / "R6_G421_freeze_cover.mp4"
    if not r6.exists():
        p = SCENARIOS["scenarios"]["R6"]["params"]
        freeze_and_cover(CLIPS / "G421_room.mp4", r6, tuple(p["freeze_s"]), tuple(p["cover_s"]))
    out["R6"] = str(r6)
    # Robustness variants (eval/robustness.py): 360p and heavy compression of the door clip.
    for tag, scale, crf in (("360p", "640:360", 28), ("720p_crf40", "1280:720", 40)):
        dst = CLIPS / f"G420_busy_{tag}.mp4"
        if not dst.exists():
            burn_clock(SOURCES["G420_busy"][0], dst, SOURCES["G420_busy"][1], scale=scale, crf=crf)
        out[f"G420_busy_{tag}"] = str(dst)
    # Low light: darker, lower contrast, sensor noise (evening classroom).
    dst = CLIPS / "G420_busy_lowlight.mp4"
    if not dst.exists():
        burn_clock(SOURCES["G420_busy"][0], dst, SOURCES["G420_busy"][1], scale="1280:720",
                   extra_vf="eq=brightness=-0.25:contrast=0.6:gamma=0.8,noise=alls=12:allf=t")
    out["G420_busy_lowlight"] = str(dst)
    return out


# Video scenarios: (centre, camera yaml, clip, start_time). Order matters for R4: day-before run fills the
# 7-day pHash index, then the replay with yesterday's clock runs "today".
VIDEO_RUNS = [
    ("TC0421", "meva_G420_door.yaml", "G420_busy", DEMO_DAY.replace(hour=12)),                       # honest
    ("TC0421", "meva_G421_room.yaml", "G421_room", DEMO_DAY.replace(hour=11, minute=55, second=1)),   # honest
    ("TC0777", "meva_G420_door.yaml", "G420_busy", DEMO_DAY.replace(hour=12) - timedelta(days=1)),   # R4 day −1
    ("TC0777", "meva_G420_door.yaml", "R4", DEMO_DAY.replace(hour=12)),                              # R4 replay
    ("TC0555", "meva_G421_room.yaml", "G421_room", DEMO_DAY.replace(hour=11, minute=55, second=1)),   # R5 same clip
    ("TC0612", "meva_G421_room.yaml", "R6", DEMO_DAY.replace(hour=11, minute=55, second=1)),          # R6
    ("TC0198", "lab_room.yaml", "lab", DEMO_DAY.replace(hour=10)),                                    # lab (assets)
]


def video(uplink: str | None, only: list[str] | None = None):
    from edge.run import run
    from edge.zones import CameraConfig
    clips = prepare()
    results = []
    for centre, cam_yaml, clip, start in VIDEO_RUNS:
        if only and centre not in only:
            continue
        cfg = CameraConfig.load(ROOT / "edge" / "cameras" / cam_yaml)
        cfg.centre_id, cfg.source, cfg.start_time = centre, clips[clip], start.isoformat()
        s = run(cfg, ROOT / "data" / "edge_state" / centre, uplink, tier="normal", quiet=True)
        results.append({"centre": centre, "camera": cfg.camera_id, "clip": clip, **s})
    log = ROOT / "data" / "work" / "edge_runs.json"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(json.dumps(results, indent=1))
    return results


def sims(seeds: int = 20, noise: Noise = Noise()) -> list[dict]:
    """Run every event/series scenario `seeds` times through the cloud engines. One row per run."""
    from cloud.engines import assets as A
    from cloud.engines import shadow
    from cloud.engines.reconcile import Params, reconcile_session
    params = Params(door_recall=noise.door_recall)
    rows = []
    for sid, sc in SCENARIOS["scenarios"].items():
        for seed in range(seeds):
            if sc["level"] == "event":
                s, gt = event_session(sid, seed, noise)
                r = reconcile_session(s, params)
                fired = r.get("flags", [])
            elif sid == "R7":
                fired = ["ornamental_asset"] if A.ornamental(r7_asset_days(seed, **{k: v for k, v in sc["params"].items() if k != "days"}, days=sc["params"]["days"]))["flag"] else []
                h = A.ornamental(r7_asset_days(seed, days=sc["params"]["days"], honest=True))["flag"]
                rows.append({"scenario": "R7-control", "seed": seed, "fired": ["ornamental_asset"] if h else [], "honest": True})
            elif sid == "R8":
                fired = ["asset_swapped"] if A.swapped(r8_identity_days(seed, sc["params"]["days"], sc["params"]["swap_day"]))["flag"] else []
                h = A.swapped(r8_identity_days(seed, sc["params"]["days"], honest=True))["flag"]
                rows.append({"scenario": "R8-control", "seed": seed, "fired": ["asset_swapped"] if h else [], "honest": True})
            elif sid == "R9":
                p = sc["params"]
                out = {}
                for honest in (False, True):
                    sess, insp = r9_centre_days(seed, noise, p["days"], p["inspections"], p["window"], honest=honest)
                    scores = [reconcile_session(x, params)["score"] for x in sess]
                    out[honest] = shadow.shadow(scores, insp, window=p["window"])
                fired = ["inspection_shadow"] if out[False]["flag"] else []
                rows.append({"scenario": "R9-control", "seed": seed, "honest": True,
                             "fired": ["inspection_shadow"] if out[True]["flag"] else [], "p_value": out[True]["p_value"]})
                rows.append({"scenario": sid, "seed": seed, "fired": fired, "honest": False,
                             "p_value": out[False]["p_value"], "expect": sc["expect"]})
                continue
            else:
                continue  # video scenarios run via `video`
            rows.append({"scenario": sid, "seed": seed, "fired": fired, "honest": sc["expect"] == "none",
                         "expect": sc["expect"]})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["prepare", "video", "sims"])
    ap.add_argument("--uplink", default=None)
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    if a.cmd == "prepare":
        print(json.dumps(prepare(), indent=1))
    elif a.cmd == "video":
        print(json.dumps(video(a.uplink, a.only), indent=1))
    else:
        rows = sims(a.seeds)
        print(json.dumps(rows[:5], indent=1), f"... {len(rows)} runs")


if __name__ == "__main__":
    main()
