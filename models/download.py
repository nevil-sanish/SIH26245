"""Fetch model weights into models/ and verify checksums. No weights are committed to git.

    python models/download.py [--onnx-from DIR]

ONNX detectors come from the Colab fine-tune (models/finetune_heads_colab.ipynb) — pass the folder it
wrote (e.g. /content/drive/MyDrive/sakshi_models). HF models (DINOv2-small, OWLv2) are snapshot-downloaded
to models/hf/ so the edge runs fully offline afterwards. A file whose SHA-256 differs from checksums.txt
is refused (fail loudly).
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ONNX = ["rfdetr_nano_coco.onnx", "rfdetr_nano_head.onnx"]
EXTRA = ["head_metrics.json"]
HF = {"facebook/dinov2-small": "Apache-2.0", "google/owlv2-base-patch16-ensemble": "Apache-2.0"}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while b := f.read(1 << 20):
            h.update(b)
    return h.hexdigest()


def known() -> dict[str, str]:
    f = HERE / "checksums.txt"
    if not f.exists():
        return {}
    return {name: digest for digest, name in (l.split() for l in f.read_text().splitlines() if l.strip())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--onnx-from", type=Path)
    ap.add_argument("--write-checksums", action="store_true", help="record current files (after a new fine-tune)")
    a = ap.parse_args()
    if a.onnx_from:
        for n in ONNX + EXTRA:
            if (a.onnx_from / n).exists():
                shutil.copy(a.onnx_from / n, HERE / n)
    sums = known()
    for n in ONNX:
        p = HERE / n
        if not p.exists():
            print(f"MISSING {n} — run the Colab fine-tune, then --onnx-from <its output folder>")
            continue
        d = sha256(p)
        if n in sums and sums[n] != d and not a.write_checksums:
            raise SystemExit(f"CHECKSUM MISMATCH {n}: {d} != {sums[n]}")
        sums[n] = d
        print("ok", n, d[:12])
    if a.write_checksums:
        (HERE / "checksums.txt").write_text("".join(f"{d}  {n}\n" for n, d in sorted(sums.items())))
    from huggingface_hub import snapshot_download
    for repo, lic in HF.items():
        snapshot_download(repo, local_dir=HERE / "hf" / repo, allow_patterns=["*.json", "*.safetensors", "*.txt"])
        print("ok", repo, lic)


if __name__ == "__main__":
    main()
