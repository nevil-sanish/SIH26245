"""Sanity-check an exported RF-DETR ONNX before long runs: I/O names + shapes, and which class columns fire on a
real frame.  python scripts/check_onnx.py models/rfdetr_nano_coco.onnx data/work/clips/G420_busy.mp4 [t_s]"""
import sys

import cv2
import numpy as np
import onnxruntime as ort

from edge.detect import MEAN, STD

model, video = sys.argv[1], sys.argv[2]
t = float(sys.argv[3]) if len(sys.argv) > 3 else 100
s = ort.InferenceSession(model, providers=["CPUExecutionProvider"])
print("inputs ", [(i.name, i.shape, i.type) for i in s.get_inputs()])
print("outputs", [(o.name, o.shape) for o in s.get_outputs()])
meta = s.get_modelmeta().custom_metadata_map
print("metadata", {k: v[:200] for k, v in meta.items()})
cap = cv2.VideoCapture(video); cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000); ok, f = cap.read()
_, _, h, w = s.get_inputs()[0].shape
x = ((cv2.resize(cv2.cvtColor(f, cv2.COLOR_BGR2RGB), (w, h)).astype(np.float32) / 255 - MEAN) / STD).transpose(2, 0, 1)[None]
outs = s.run(None, {s.get_inputs()[0].name: x})
logits = next(o for o in outs if o.shape[-1] != 4)[0]
p = 1 / (1 + np.exp(-logits))
top = np.argsort(-p.max(0))[:5]
print("top class columns by max prob:", [(int(c), round(float(p[:, c].max()), 3)) for c in top])
print("queries > 0.4 per top column:", {int(c): int((p[:, c] > 0.4).sum()) for c in top})
