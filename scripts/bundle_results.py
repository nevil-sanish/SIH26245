"""Collect a GPU run's result files.
    python scripts/bundle_results.py --copy DIR   copy them to DIR with their repo paths (Kaggle: kernel output)
    python scripts/bundle_results.py              print one base64 tar.gz between markers (Colab, no downloads):
                                                  (locally) base64 -d | tar xz
"""
import base64
import shutil
import sys
import io
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = ["docs/ACCURACY_REPORT.md", "models/checksums.txt", "models/head_metrics.json", "data/work/accuracy.json",
         "data/work/robustness.json", "data/work/door_sweep.json", "data/work/head_onnx_check.json", "data/work/cpu_benchmark.json", "data/work/edge_runs.json", "data/demo/packets.jsonl", "data/demo/device_keys.json",
         "dashboard/package-lock.json", "edge/cameras/meva_G420_door.yaml", "dashboard/public/india.json"]

if "--copy" in sys.argv:
    dst = Path(sys.argv[sys.argv.index("--copy") + 1])
    for f in FILES:
        if (ROOT / f).exists():
            (dst / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / f, dst / f)
        print("copied" if (ROOT / f).exists() else "missing", f)
    sys.exit()

buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode="w:gz", compresslevel=9) as t:
    for f in FILES:
        if (ROOT / f).exists():
            t.add(ROOT / f, arcname=f)
            print("bundled", f, (ROOT / f).stat().st_size, "B")
        else:
            print("missing", f)
b = base64.b64encode(buf.getvalue()).decode()
print(f"RESULTS_B64_BEGIN {len(b)}")
for i in range(0, len(b), 100):
    print(b[i:i + 100])
print("RESULTS_B64_END")
