"""RF-DETR (Apache-2.0) ONNX wrapper on ONNX Runtime CPU → `sv.Detections`.

Two models (both produced by models/finetune_heads_colab.ipynb, fetched by models/download.py):
  rfdetr_nano_coco.onnx  person (COCO class 1)        door cameras, workshops
  rfdetr_nano_head.onnx  head (fine-tuned SCUT-HEAD)  seated classrooms / labs
Optional SAHI-style tiling (supervision.InferenceSlicer) for small back-row heads on room cameras.

Fail loudly (PROMPT §5.3): a missing model raises ModuleUnavailable; the caller reports
"module unavailable" and never silently substitutes another model.
"""
from __future__ import annotations

import os
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort
import supervision as sv

MEAN = np.array([0.485, 0.456, 0.406], np.float32)
STD = np.array([0.229, 0.224, 0.225], np.float32)


class ModuleUnavailable(RuntimeError):
    pass


class Detector:
    def __init__(self, model_path: str, class_ids: list[int], threshold: float = 0.4,
                 tile: int | None = None, threads: int | None = None):
        if not Path(model_path).exists():
            raise ModuleUnavailable(f"model missing: {model_path} — run `make setup`")
        so = ort.SessionOptions()
        so.intra_op_num_threads = threads or os.cpu_count() or 1   # more threads than cores only adds contention
        self.sess = ort.InferenceSession(model_path, so, providers=["CPUExecutionProvider"])
        inp = self.sess.get_inputs()[0]
        self.input_name = inp.name
        self.h, self.w = int(inp.shape[2]), int(inp.shape[3])
        self.class_ids = np.asarray(class_ids)
        self.threshold = threshold
        self.slicer = sv.InferenceSlicer(callback=self._infer, slice_wh=tile, overlap_wh=tile // 5) if tile else None

    def _infer(self, bgr: np.ndarray) -> sv.Detections:
        H, W = bgr.shape[:2]
        x = cv2.resize(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), (self.w, self.h)).astype(np.float32) / 255
        x = ((x - MEAN) / STD).transpose(2, 0, 1)[None]
        outs = self.sess.run(None, {self.input_name: x})
        boxes = next(o for o in outs if o.shape[-1] == 4)[0]          # (Q, 4) cx, cy, w, h normalised
        logits = next(o for o in outs if o.shape[-1] != 4)[0]         # (Q, C)
        probs = 1 / (1 + np.exp(-logits[:, self.class_ids]))
        conf = probs.max(1)
        keep = conf >= self.threshold
        cx, cy, bw, bh = boxes[keep].T
        xyxy = np.stack([(cx - bw / 2) * W, (cy - bh / 2) * H, (cx + bw / 2) * W, (cy + bh / 2) * H], 1)
        return sv.Detections(xyxy=xyxy.astype(np.float32), confidence=conf[keep].astype(np.float32),
                             class_id=self.class_ids[probs[keep].argmax(1)] if keep.any() else np.zeros(0, int))

    def __call__(self, bgr: np.ndarray) -> sv.Detections:
        d = self.slicer(bgr) if self.slicer else self._infer(bgr)
        return d.with_nms(threshold=0.6)
