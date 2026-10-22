"""Head-count MAE of the *deployed* ONNX head model (edge.detect.Detector) on SCUT-HEAD Part A (classroom CCTV).
The fine-tune reports PyTorch metrics; this checks the exported artifact the edge actually runs.

For each tiling option the score threshold is chosen on the Part A images of the fine-tune's *valid* split
(same seeded A+B trainval shuffle as models/finetune_heads_kaggle.py, so no training image is used), and MAE is
reported on Part A *test* at that threshold. The deployed (tile, threshold) is the one with the lowest valid MAE.
Also records the per-image relative count error spread (room-level count bias, used by the H1 occupancy test).
Writes data/work/head_onnx_check.json.   python -m scripts.eval_head_onnx [--max 500] [--tiles 0 640 480]
"""
import argparse
import json
import random
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import cv2
import numpy as np

from edge.detect import Detector

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "scut"
PARTS = {"PartA": "1yaOF9os5wPVNNG4GVzNyULLVe74vdrBE", "PartB": "1LZ_KlTPStDEcqycfqUkDkqQ-aNMMC3cl"}  # SCUT-HEAD README (research use only)
THRS = [round(t, 3) for t in np.arange(0.25, 0.5001, 0.025)]


def fetch(part):
    d = RAW / part
    if not any(d.rglob("JPEGImages")):
        d.mkdir(parents=True, exist_ok=True)
        subprocess.run(["gdown", "-q", "--fuzzy", f"https://drive.google.com/open?id={PARTS[part]}", "-O", str(d / "a.archive")], check=True)
        import patoolib
        patoolib.extract_archive(str(d / "a.archive"), outdir=str(d), verbosity=-1)
    return next(d.rglob("JPEGImages")).parent


def ids(root, split):
    return (root / "ImageSets" / "Main" / f"{split}.txt").read_text().split()


def counts(det, root, stems):
    gt, pred = [], {t: [] for t in THRS}
    for stem in stems:
        gt.append(len(ET.parse(root / "Annotations" / f"{stem}.xml").getroot().findall("object")))
        d = det(cv2.imread(str(root / "JPEGImages" / f"{stem}.jpg")))
        for t in THRS:
            pred[t].append(int((d.confidence >= t).sum()))
    return np.array(gt), {t: np.array(p) for t, p in pred.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=500)
    ap.add_argument("--tiles", type=int, nargs="*", default=[0, 640, 480])
    a = ap.parse_args()
    A, B = fetch("PartA"), fetch("PartB")
    tv = [("A", s) for s in ids(A, "trainval")] + [("B", s) for s in ids(B, "trainval")]
    random.Random(0).shuffle(tv)
    val = [s for p, s in tv[: len(tv) // 10] if p == "A"]
    test = ids(A, "test")[: a.max]
    res = {"images": len(test), "valid_images": len(val), "label": "measured", "by_tile": {},
           "note": "exported ONNX via edge.detect (class column 0); threshold chosen on SCUT-HEAD Part A valid, MAE on Part A test"}
    for tile in a.tiles:
        det = Detector(str(ROOT / "models" / "rfdetr_nano_head.onnx"), [0], threshold=min(THRS), tile=tile or None)
        gv, pv = counts(det, A, val)
        gt, pt = counts(det, A, test)
        mae_v = {t: float(np.abs(pv[t] - gv).mean()) for t in THRS}
        thr = min(mae_v, key=mae_v.get)
        err = pt[thr] - gt
        res["provider"] = det.provider
        res["mean_heads"] = round(float(gt.mean()), 2)
        res["by_tile"][str(tile)] = {
            "threshold": thr, "valid_mae": round(mae_v[thr], 3), "test_mae": round(float(np.abs(err).mean()), 3),
            "test_bias": round(float(err.mean()), 3),
            "rel_err_sd": round(float(np.std(err / np.maximum(gt, 1))), 4),   # per-image (≈ per-room) count bias spread
            "valid_mae_by_threshold": {t: round(v, 3) for t, v in mae_v.items()},
            "test_mae_by_threshold": {t: round(float(np.abs(pt[t] - gt).mean()), 3) for t in THRS}}
        print("TILE", tile, json.dumps(res["by_tile"][str(tile)]), flush=True)
    best = min(res["by_tile"], key=lambda k: res["by_tile"][k]["valid_mae"])
    res["deployed"] = {"tile": int(best), **{k: res["by_tile"][best][k] for k in ("threshold", "valid_mae", "test_mae", "test_bias", "rel_err_sd")}}
    out = ROOT / "data" / "work" / "head_onnx_check.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1))
    y = ROOT / "edge" / "cameras" / "lab_room.yaml"   # the head-detector camera keeps the valid-chosen setting
    tile = f", tile: {best}" if int(best) else ""
    y.write_text("\n".join(f"detect: {{model: models/rfdetr_nano_head.onnx, class_ids: [0], threshold: {res['deployed']['threshold']}{tile}}}"
                           "   # head = logit column 0; threshold/tile chosen on SCUT-HEAD Part A valid (scripts/eval_head_onnx.py)"
                           if l.startswith("detect:") else l for l in y.read_text().splitlines()) + "\n")
    print("HEAD_ONNX", json.dumps(res["deployed"]))


if __name__ == "__main__":
    main()
