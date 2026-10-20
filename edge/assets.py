"""Asset service (runs every 10–30 min, not per frame).

discovery     OWLv2 zero-shot detection from the sanctioned-inventory text list (Apache-2.0)
registration  one DINOv2-small embedding per sanctioned asset crop, stored on the edge
identity      daily crop vs registration embedding → cosine similarity (S2 asset_swapped in the cloud)
screen-on     for monitors: mean brightness / variance inside the box vs the registration crop

Weights are loaded from models/hf/ (fetched by `make setup`); missing weights = module unavailable.
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

HF_DIR = Path(__file__).resolve().parents[1] / "models" / "hf"
OWL = "google/owlv2-base-patch16-ensemble"
DINO = "facebook/dinov2-small"


class AssetService:
    def __init__(self, registry_path: str):
        self.registry_path = Path(registry_path)
        self.registry = json.loads(self.registry_path.read_text()) if self.registry_path.exists() else {}
        self.error = None
        try:
            import torch
            from transformers import AutoImageProcessor, AutoModel, Owlv2ForObjectDetection, Owlv2Processor
            self.torch = torch
            self.dproc = AutoImageProcessor.from_pretrained(HF_DIR / DINO, local_files_only=True)
            self.dino = AutoModel.from_pretrained(HF_DIR / DINO, local_files_only=True).eval()
            self._owl_cls = (Owlv2Processor, Owlv2ForObjectDetection)
            self._owl = None  # lazy: only discovery needs it (~600 MB)
        except Exception as e:  # noqa: BLE001
            self.dino, self.error = None, f"asset module unavailable: {e!r}"

    @property
    def available(self) -> bool:
        return self.dino is not None

    def embed(self, crop_bgr: np.ndarray) -> np.ndarray:
        rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
        with self.torch.no_grad():
            out = self.dino(**self.dproc(images=rgb, return_tensors="pt"))
        v = out.pooler_output[0].numpy()
        return v / np.linalg.norm(v)

    def discover(self, frame_bgr: np.ndarray, labels: list[str], threshold: float = 0.25) -> list[dict]:
        if self._owl is None:
            P, M = self._owl_cls
            self._owlp = P.from_pretrained(HF_DIR / OWL, local_files_only=True)
            self._owl = M.from_pretrained(HF_DIR / OWL, local_files_only=True).eval()
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        inputs = self._owlp(text=[[f"a photo of a {l}" for l in labels]], images=rgb, return_tensors="pt")
        with self.torch.no_grad():
            out = self._owl(**inputs)
        h, w = rgb.shape[:2]
        s = max(h, w)  # OWLv2 pads to a square
        res = self._owlp.post_process_object_detection(out, threshold=threshold,
                                                       target_sizes=self.torch.tensor([[s, s]]))[0]
        return [{"label": labels[int(l)], "score": round(float(sc), 3), "box": [round(float(v)) for v in b]}
                for b, sc, l in zip(res["boxes"], res["scores"], res["labels"])]

    @staticmethod
    def crop(frame_bgr, zone) -> np.ndarray:
        pts = np.asarray(zone)
        x1, y1 = pts.min(0); x2, y2 = pts.max(0)
        return frame_bgr[int(y1):int(y2), int(x1):int(x2)]

    def register(self, asset_id: str, frame_bgr: np.ndarray, zone):
        c = self.crop(frame_bgr, zone)
        self.registry[asset_id] = {"emb": self.embed(c).round(5).tolist(),
                                   "brightness": float(cv2.cvtColor(c, cv2.COLOR_BGR2GRAY).mean())}
        self.registry_path.write_text(json.dumps(self.registry))

    def identity(self, asset_id: str, frame_bgr: np.ndarray, zone) -> float | None:
        if asset_id not in self.registry:
            return None
        v = self.embed(self.crop(frame_bgr, zone))
        return round(float(np.dot(v, np.asarray(self.registry[asset_id]["emb"]))), 3)


def screen_on(crop_bgr: np.ndarray, off_brightness: float, margin: float = 25) -> bool:
    """A lit monitor is clearly brighter and more textured than its switched-off registration crop."""
    g = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    return float(g.mean()) > off_brightness + margin and float(g.std()) > 20
