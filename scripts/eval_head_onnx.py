"""Head-count MAE of the *deployed* ONNX head model (edge.detect.Detector) on SCUT-HEAD Part A test (classroom CCTV).
The Colab fine-tune reports PyTorch metrics; this checks the exported artifact the edge actually runs.
Writes data/work/head_onnx_check.json.   python -m scripts.eval_head_onnx [--max 500]
"""
import argparse
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import cv2
import numpy as np

from edge.detect import Detector

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "scut"
PART_A = "1yaOF9os5wPVNNG4GVzNyULLVe74vdrBE"   # Google Drive id from the SCUT-HEAD release README (research use only)


def fetch():
    if not any(RAW.rglob("JPEGImages")):
        RAW.mkdir(parents=True, exist_ok=True)
        subprocess.run(["gdown", "-q", "--fuzzy", f"https://drive.google.com/open?id={PART_A}", "-O", str(RAW / "a.zip")], check=True)
        subprocess.run(["unzip", "-q", "-o", str(RAW / "a.zip"), "-d", str(RAW)], check=True)
    return next(RAW.rglob("JPEGImages")).parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=500)
    a = ap.parse_args()
    root = fetch()
    ids = (root / "ImageSets" / "Main" / "test.txt").read_text().split()[: a.max]
    det = Detector(str(ROOT / "models" / "rfdetr_nano_head.onnx"), [0], threshold=0.2)
    thrs = [0.2, 0.25, 0.3, 0.35, 0.4, 0.5]
    gt, pred = [], {t: [] for t in thrs}
    for stem in ids:
        gt.append(len(ET.parse(root / "Annotations" / f"{stem}.xml").getroot().findall("object")))
        d = det(cv2.imread(str(root / "JPEGImages" / f"{stem}.jpg")))
        for t in thrs:
            pred[t].append(int((d.confidence >= t).sum()))
    gt = np.array(gt)
    res = {"images": len(gt), "mean_heads": round(float(gt.mean()), 2), "provider": det.provider,
           "mae_by_threshold": {t: round(float(np.abs(np.array(p) - gt).mean()), 3) for t, p in pred.items()},
           "bias_by_threshold": {t: round(float((np.array(p) - gt).mean()), 3) for t, p in pred.items()},
           "label": "measured", "note": "exported ONNX via edge.detect (class column 0), SCUT-HEAD Part A test"}
    out = ROOT / "data" / "work" / "head_onnx_check.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1))
    print("HEAD_ONNX", json.dumps(res))


if __name__ == "__main__":
    main()
