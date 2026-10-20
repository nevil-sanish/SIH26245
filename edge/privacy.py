"""Privacy on the edge. Any image that leaves the device is face-blurred here first.

* Face blur: CenterFace detector shipped with `deface` (MIT). Detection only: no embeddings,
  no identities. Faces are blurred with an enlarged elliptical mask.
* Thumbnails: 96×54 JPEG with EXIF stripped (OpenCV writes none).
* Encrypted ring buffer: raw clips kept 7–30 days for a formal audit request only, encrypted with
  the state nodal officer's public key (libsodium sealed box), so the centre cannot read or edit
  them and the cloud never receives them unless an audit is requested.
"""
from __future__ import annotations

import time
from pathlib import Path

import cv2
import numpy as np
from nacl.public import PublicKey, SealedBox


class FaceBlur:
    def __init__(self, threshold: float = 0.2):
        self.threshold = threshold
        self.error = None
        try:
            from deface.centerface import CenterFace
            self._cf = CenterFace(in_shape=None, backend="onnxrt")
        except Exception as e:  # noqa: BLE001 — fail loudly: no blur = no images leave
            self._cf, self.error = None, f"face blur unavailable: {e!r}"

    @property
    def available(self) -> bool:
        return self._cf is not None

    def faces(self, frame_bgr: np.ndarray) -> np.ndarray:
        dets, _ = self._cf(frame_bgr, threshold=self.threshold)
        return dets[:, :4] if len(dets) else np.zeros((0, 4))

    def blur(self, frame_bgr: np.ndarray, extra_boxes: np.ndarray | None = None) -> np.ndarray:
        """Blur detected faces, plus the top 30 % of any person box we were given (belt and braces:
        far-away faces are often too small for the face detector)."""
        if not self.available:
            raise RuntimeError(self.error)
        out = frame_bgr.copy()
        boxes = list(self.faces(frame_bgr))
        if extra_boxes is not None:
            for x1, y1, x2, y2 in extra_boxes:
                boxes.append((x1, y1, x2, y1 + 0.3 * (y2 - y1)))
        h, w = out.shape[:2]
        for x1, y1, x2, y2 in boxes:
            cx, cy, rx, ry = (x1 + x2) / 2, (y1 + y2) / 2, (x2 - x1) * 0.65, (y2 - y1) * 0.65
            xa, ya, xb, yb = (int(max(0, cx - rx)), int(max(0, cy - ry)), int(min(w, cx + rx)), int(min(h, cy + ry)))
            if xb <= xa or yb <= ya:
                continue
            roi = out[ya:yb, xa:xb]
            k = max(3, (max(xb - xa, yb - ya) // 3) | 1)
            blurred = cv2.GaussianBlur(roi, (k, k), 0)
            mask = np.zeros(roi.shape[:2], np.uint8)
            cv2.ellipse(mask, ((xb - xa) // 2, (yb - ya) // 2), ((xb - xa) // 2, (yb - ya) // 2), 0, 0, 360, 255, -1)
            roi[mask > 0] = blurred[mask > 0]
        return out


def thumbnail(frame_bgr: np.ndarray, blur: FaceBlur, person_boxes=None, size=(96, 54), quality=60) -> bytes:
    """Blur at full resolution, then downscale. Returns JPEG bytes (no EXIF)."""
    safe = blur.blur(frame_bgr, person_boxes)
    ok, buf = cv2.imencode(".jpg", cv2.resize(safe, size, interpolation=cv2.INTER_AREA),
                           [cv2.IMWRITE_JPEG_QUALITY, quality])
    return buf.tobytes()


class ClipRing:
    """Encrypted, time-limited local clip store (audit tier). Files older than `days` are deleted."""

    def __init__(self, folder: str, officer_pub_b64: str | None, days: int = 30):
        self.dir = Path(folder); self.dir.mkdir(parents=True, exist_ok=True)
        self.days = days
        import base64
        self.box = SealedBox(PublicKey(base64.b64decode(officer_pub_b64))) if officer_pub_b64 else None

    def store(self, name: str, data: bytes) -> Path | None:
        if self.box is None:
            return None  # no officer key configured = no clip retention at all (most private default)
        p = self.dir / f"{int(time.time())}_{name}.sealed"
        p.write_bytes(self.box.encrypt(data))
        return p

    def expire(self):
        cutoff = time.time() - self.days * 86400
        for p in self.dir.glob("*.sealed"):
            if p.stat().st_mtime < cutoff:
                p.unlink()
