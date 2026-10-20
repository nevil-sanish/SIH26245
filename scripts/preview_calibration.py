"""Draw each camera YAML's door line, room/trainer polygons, asset zones and timestamp box on a frame of its source,
so calibration can be checked by eye before an edge run.  python scripts/preview_calibration.py [t_seconds] → data/work/calib_*.jpg
"""
import sys
from pathlib import Path

import cv2
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
t = float(sys.argv[1]) if len(sys.argv) > 1 else 65.0
for y in sorted((ROOT / "edge" / "cameras").glob("*.yaml")):
    cfg = yaml.safe_load(open(y))
    cap = cv2.VideoCapture(str(ROOT / cfg["source"]))
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, f = cap.read()
    if not ok:
        print("no frame", y.name); continue
    if cfg.get("door_line"):
        (a, b) = cfg["door_line"]
        cv2.line(f, tuple(a), tuple(b), (0, 94, 213), 3)
        cv2.putText(f, "1", tuple(a), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 94, 213), 2)
        cv2.putText(f, "2", tuple(b), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 94, 213), 2)
    for k, col in (("room_polygon", (178, 114, 0)), ("trainer_zone", (0, 159, 230))):
        if cfg.get(k):
            cv2.polylines(f, [np.array(cfg[k], np.int32)], True, col, 2)
    for a in cfg.get("assets", []):
        cv2.polylines(f, [np.array(a["zone"], np.int32)], True, (115, 158, 0), 2)
        cv2.putText(f, a["asset_id"], tuple(a["zone"][0]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (115, 158, 0), 1)
    if cfg.get("timestamp_roi"):
        x, w_, = cfg["timestamp_roi"][0], cfg["timestamp_roi"][2]
        yy, h = cfg["timestamp_roi"][1], cfg["timestamp_roi"][3]
        cv2.rectangle(f, (x, yy), (x + w_, yy + h), (167, 121, 204), 2)
    out = ROOT / "data" / "work" / f"calib_{y.stem}.jpg"
    cv2.imwrite(str(out), f)
    print("wrote", out, f.shape)
