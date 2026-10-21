"""Robustness curves (PROMPT §14): door P/R and per-frame count MAE on the labelled MEVA G420 clip at
1080p / 720p / 360p, heavy compression (CRF 40) and synthetic low light. Writes data/work/robustness.json.

    python -m eval.robustness                # robustness curves
    python -m eval.robustness --door-sweep   # door P/R vs crossing hysteresis (door_min_frames)
"""
from __future__ import annotations

import json
from pathlib import Path

from edge.run import run
from edge.zones import CameraConfig
from eval.metrics import count_eval, door_eval
from redteam.runner import CLIPS, SOURCES

ROOT = Path(__file__).resolve().parents[1]
# (tag, clip file, scale factor of door-line coordinates relative to the 720p calibration)
VARIANTS = [("1080p", "G420_busy_1080p.mp4", 1.5), ("720p", "G420_busy.mp4", 1.0), ("360p", "G420_busy_360p.mp4", 0.5),
            ("720p_crf40", "G420_busy_720p_crf40.mp4", 1.0), ("720p_lowlight", "G420_busy_lowlight.mp4", 1.0)]


def door_sweep(values=(1, 2, 3, 5)):
    """Door P/R vs door_min_frames (crossing hysteresis) on both annotated MEVA door clips: G420_busy (43 entries)
    and G420_exits (42 exits). Writes data/work/door_sweep.json; the camera YAML keeps the best F1 on exits+entries."""
    out = []
    for n in values:
        for clip in ("G420_busy", "G420_exits"):
            cfg = CameraConfig.load(ROOT / "edge" / "cameras" / "meva_G420_door.yaml")
            centre = f"SWEEP-{clip}-{n}"
            cfg.centre_id, cfg.source, cfg.door_min_frames = centre, str(CLIPS / f"{clip}.mp4"), n
            cfg.start_time = SOURCES[clip][1].isoformat()
            state = ROOT / "data" / "edge_state" / centre
            for f in ("outbox.sqlite", "phash.sqlite"):
                (state / f).unlink(missing_ok=True)
            run(cfg, state, None, quiet=True)
            d = door_eval(centre=centre, cam=cfg.camera_id, clip=clip)
            out.append({"door_min_frames": n, "clip": clip, "in": d["in"], "out": d["out"], "label": "measured"})
            print(json.dumps(out[-1]))
    # Choose on the exits clip only (tuning clip); the busy clip's entries stay a held-out check. F1 over both directions.
    f1 = lambda x: 0.0 if not x["precision"] or not x["recall"] else 2 * x["precision"] * x["recall"] / (x["precision"] + x["recall"])
    tune = [v for v in out if v["clip"] == "G420_exits"]
    best = max(tune, key=lambda v: (f1(v["in"]) + f1(v["out"]), -v["door_min_frames"]))["door_min_frames"]
    (ROOT / "data" / "work" / "door_sweep.json").write_text(json.dumps(out, indent=1))
    y = ROOT / "edge" / "cameras" / "meva_G420_door.yaml"
    lines = [l for l in y.read_text().splitlines() if not l.startswith("door_min_frames:")]
    i = next(k for k, l in enumerate(lines) if l.startswith("entry_direction:")) + 1
    lines.insert(i, f"door_min_frames: {best}          # chosen by `python -m eval.robustness --door-sweep` (exits clip F1)")
    y.write_text("\n".join(lines) + "\n")
    print("door_min_frames chosen:", best)


def main():
    base = CameraConfig.load(ROOT / "edge" / "cameras" / "meva_G420_door.yaml")
    out = []
    for tag, clip, k in VARIANTS:
        cfg = CameraConfig.load(ROOT / "edge" / "cameras" / "meva_G420_door.yaml")
        centre = f"ROB-{tag}"
        cfg.centre_id, cfg.source = centre, str(CLIPS / clip)
        cfg.door_line = [[round(x * k), round(y * k)] for x, y in base.door_line]
        cfg.timestamp_roi = [round(v * k) for v in base.timestamp_roi]
        state = ROOT / "data" / "edge_state" / centre
        for f in ("outbox.sqlite", "phash.sqlite"):
            (state / f).unlink(missing_ok=True)   # fresh run each time
        s = run(cfg, state, None, quiet=True)
        d = door_eval(centre=centre, cam=cfg.camera_id)
        c = count_eval(video=CLIPS / clip)
        out.append({"variant": tag, "fps_measured": s["fps_measured"], "door_in": d["in"], "door_out": d["out"],
                    "door_any": d["any_direction"], "count": c, "label": "measured"})
        print(json.dumps(out[-1]))
    p = ROOT / "data" / "work" / "robustness.json"
    p.write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    import sys
    door_sweep() if "--door-sweep" in sys.argv else main()
