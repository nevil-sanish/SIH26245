#!/bin/bash
# One-shot measured evaluation run on a GPU VM (Kaggle or Colab), from the repo root:
#   ONNX_DIR=<fine-tune output: rfdetr_nano_{head,coco}.onnx + head_metrics.json> RESULTS=<dir> bash scripts/gpu_runs.sh
# Runs in a Python 3.11 venv with the pinned edge requirements (VM system Pythons differ). Detection uses ONNX Runtime
# CUDA for turnaround (SAKSHI_GPU=1); edge CPU fps is benchmarked separately, without it. Result files are copied
# to $RESULTS with their repo paths (scripts/bundle_results.py FILES).
set -euo pipefail
: "${ONNX_DIR:?set ONNX_DIR to the fine-tune output folder}"
RESULTS=${RESULTS:-/tmp/sakshi_results}
git log --oneline -1

pip install -q uv==0.9.5
uv venv -q -p 3.11 /tmp/venv && source /tmp/venv/bin/activate
grep -v '^onnxruntime==' edge/requirements.txt > edge/req_gpu.txt     # same pins, GPU build of ONNX Runtime
uv pip install -q -r edge/req_gpu.txt onnxruntime-gpu==1.31.0 gdown==5.2.0
python -c "import onnxruntime as o, sys; print('python', sys.version.split()[0], 'ORT providers', o.get_available_providers())"

python data/download.py                                   # MEVA clips + annotations (ground truth), Commons lab clips
python models/download.py --onnx-from "$ONNX_DIR" --write-checksums
python -m pytest -q tests 2>&1 | tail -3
python -m redteam.runner prepare > /dev/null
ffprobe -v error -show_entries format=duration -of csv=p=0 data/work/clips/lab.mp4 | sed 's/^/lab clip seconds: /'
SAKSHI_GPU=1 python -m scripts.eval_head_onnx 2>&1 | grep -E "HEAD_ONNX|Error" || echo HEAD_ONNX_CHECK_FAILED

# CPU benchmark: 1 minute of the door clip on this VM's CPU (no GPU), honest edge fps.
python -m edge.run --camera edge/cameras/meva_G420_door.yaml --state /tmp/cpu_bench --max-minutes 1 --quiet \
  | tail -1 | tee data/work/cpu_benchmark.json

export SAKSHI_GPU=1
rm -rf data/edge_state
python -m eval.robustness --door-sweep 2>&1 | grep -vi warn | tail -8
python -m redteam.runner video 2>&1 | grep -E 'summary|exported|Error|Traceback' || true
python -m eval.robustness 2>&1 | grep -vi warn | tail -6
python -m eval.metrics --seeds 20
python -m eval.report
python -m scripts.demo_check 2>&1 | tail -15
python scripts/make_india_map.py
python scripts/bundle_results.py --copy "$RESULTS"
echo ALL_DONE
