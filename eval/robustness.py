"""Robustness curves (PROMPT §14): door P/R and per-frame count MAE on the labelled MEVA G420 clip at
1080p / 720p / 360p, heavy compression (CRF 40) and synthetic low light. Writes data/work/robustness.json.

    python -m eval.robustness
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
    main()
