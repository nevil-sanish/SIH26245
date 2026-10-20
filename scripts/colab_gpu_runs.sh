#!/bin/bash
# One-shot evaluation run on a Colab T4 VM (after models/finetune_heads_colab.ipynb has written /content/out).
# Inputs from Drive (MyDrive/sakshi_work): prepared clips + COCO ONNX. Output: /content/bundle.txt (+ Drive copy).
# Detection uses ONNX Runtime CUDA for turnaround (SAKSHI_GPU=1); edge CPU fps is benchmarked separately below.
set -euo pipefail
W=/content/drive/MyDrive/sakshi_work
cd /content && rm -rf sakshi && git clone -q --depth 1 https://github.com/nevil-sanish/SIH26245.git sakshi && cd sakshi
git log --oneline -1
grep -vE '^(torch|torchvision|onnxruntime)==' edge/requirements.txt > edge/req_gpu.txt   # keep Colab's CUDA torch
pip install -q -r edge/req_gpu.txt 2>&1 | tail -2
pip uninstall -y -q onnxruntime || true
pip install -q onnxruntime-gpu==1.31.0
python -c "import onnxruntime as o; print('ORT providers', o.get_available_providers())"

mkdir -p data/work/clips models
cp $W/clips/*.mp4 data/work/clips/
cp $W/rfdetr_nano_coco.onnx models/
python data/download.py                                   # MEVA annotations (ground truth) + raw clips
python models/download.py --onnx-from /content/out --write-checksums

python -m pytest -q tests 2>&1 | tail -3
pip install -q gdown==5.2.0
SAKSHI_GPU=1 python scripts/eval_head_onnx.py 2>&1 | grep -E "HEAD_ONNX|Error" || echo HEAD_ONNX_CHECK_FAILED

# CPU benchmark: 1 minute of the door clip on this VM's CPU (no GPU), honest edge fps.
python -m edge.run --camera edge/cameras/meva_G420_door.yaml --state /tmp/cpu_bench --max-minutes 1 --quiet \
  | tail -1 | tee data/work/cpu_benchmark.json

export SAKSHI_GPU=1
rm -rf data/edge_state
python -m redteam.runner video 2>&1 | grep -E 'summary|exported|Error|Traceback' || true
python -m eval.robustness 2>&1 | grep -vi warn | tail -6
python -m eval.metrics --seeds 20
python -m eval.report
python scripts/make_india_map.py
(cd dashboard && npm install --package-lock-only --no-audit --no-fund > /dev/null 2>&1 && echo lockfile ok)
python scripts/bundle_results.py > /content/bundle.txt
cp /content/bundle.txt $W/bundle.txt
grep -E '^(bundled|missing)|RESULTS_B64_BEGIN' /content/bundle.txt
echo ALL_DONE
