"""H2 (edge half) — feed-integrity checks, all cheap enough to run every 30 s on a CPU.

frozen     mean |frame − prev| below the sensor-noise floor for > T seconds
covered    very low Laplacian variance (defocus / lens covered) or near-uniform histogram
moved      ORB keypoint match ratio vs the calibration reference frame
clock      OCR of the DVR burned-in timestamp vs device time (NTP + last signed server time)
loop       pHash of people-present keyframes vs a 7-day local index (cross-day replay)

Thresholds are per-camera overridable in the camera YAML under `integrity:`.
"""
from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime

import cv2
import imagehash
import numpy as np
from PIL import Image

from edge import IST


@dataclass
class IntegrityParams:
    noise_floor: float = 0.05       # mean abs diff (0–255) below which two frames are "identical": a live feed's
                                    # ticking DVR clock alone exceeds this; a stuck encoder repeats frames exactly
    frozen_s: float = 20            # identical for longer than this = frozen
    lap_min: float = 22.0           # Laplacian variance below this = defocused / covered
    uniform_max: float = 0.9        # share of pixels in the top-3 histogram bins above this = covered (plain walls ≈ 0.5–0.7)
    orb_min_ratio: float = 0.25     # good ORB matches / reference keypoints below this = moved
    clock_drift_s: float = 120
    clock_rate_tol: float = 0.2     # OCR clock must advance 1 ± 0.2 s per real second
    loop_hamming: int = 6
    loop_days: int = 7


def sharpness(gray: np.ndarray) -> float:
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def uniformity(gray: np.ndarray) -> float:
    hist = cv2.calcHist([gray], [0], None, [32], [0, 256]).ravel()
    return float(np.sort(hist)[-3:].sum() / max(hist.sum(), 1))


@dataclass
class TamperState:
    p: IntegrityParams = field(default_factory=IntegrityParams)
    ref_gray: np.ndarray | None = None
    _prev: np.ndarray | None = None
    _still_since: float | None = None
    _orb: cv2.ORB = field(default_factory=lambda: cv2.ORB_create(500))
    _ref_kp: tuple | None = None

    def set_reference(self, gray: np.ndarray):
        self.ref_gray = gray
        kp, des = self._orb.detectAndCompute(gray, None)
        self._ref_kp = (kp, des)

    def check(self, frame_bgr: np.ndarray, t: float, full: bool = True) -> dict:
        """Return {'frozen','covered','moved'} booleans plus raw measurements for this frame.
        full=False only updates the frozen timer (cheap, every frame); full=True also runs covered + ORB moved."""
        gray = cv2.cvtColor(cv2.resize(frame_bgr, (320, 180)), cv2.COLOR_BGR2GRAY)
        out = {"sharpness": round(sharpness(gray), 1), "uniformity": round(uniformity(gray), 3)}
        if self._prev is not None:
            diff = float(np.abs(gray.astype(np.int16) - self._prev).mean())
            out["diff"] = round(diff, 3)
            if diff < self.p.noise_floor:
                self._still_since = self._still_since or t
            else:
                self._still_since = None
        self._prev = gray.astype(np.int16)
        out["frozen"] = bool(self._still_since is not None and t - self._still_since > self.p.frozen_s)
        if not full:
            return out
        out["covered"] = out["sharpness"] < self.p.lap_min or out["uniformity"] > self.p.uniform_max
        out["moved"] = False
        if self._ref_kp is None:
            self.set_reference(gray)
        elif self._ref_kp[1] is not None and len(self._ref_kp[0]) >= 20 and not out["covered"]:
            kp, des = self._orb.detectAndCompute(gray, None)
            good = 0
            if des is not None:
                pairs = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(self._ref_kp[1], des, k=2)
                good = sum(1 for m in pairs if len(m) == 2 and m[0].distance < 0.75 * m[1].distance)
            out["orb_ratio"] = round(good / len(self._ref_kp[0]), 3)
            out["moved"] = out["orb_ratio"] < self.p.orb_min_ratio
        return out


# ---------------------------------------------------------------------------------- clock
class ClockReader:
    """Reads the DVR's burned-in timestamp from a calibrated ROI with PaddleOCR.

    Fails loudly: if PaddleOCR is missing, `available` is False and the module reports
    'module unavailable' instead of silently passing.
    """

    def __init__(self, roi, fmt: str):
        self.roi, self.fmt = roi, fmt
        self.error = None
        try:
            from paddleocr import TextRecognition  # recognition-only model: the ROI is already a text line
            self._ocr = TextRecognition(model_name="en_PP-OCRv5_mobile_rec")
        except Exception as e:  # noqa: BLE001 — any import/model failure = module unavailable
            self._ocr, self.error = None, f"PaddleOCR unavailable: {e!r}"

    @property
    def available(self) -> bool:
        return self._ocr is not None

    def read(self, frame_bgr: np.ndarray) -> float | None:
        if not self._ocr:
            return None
        x, y, w, h = self.roi
        crop = frame_bgr[y:y + h, x:x + w]
        crop = cv2.resize(crop, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        res = self._ocr.predict(crop)
        text = res[0]["rec_text"] if res else ""
        return parse_clock(text, self.fmt)


def parse_clock(text: str, fmt: str) -> float | None:
    """Parse OCR text into unix time, tolerating common OCR confusions (O→0, l→1, spacing)."""
    t = text.strip().translate(str.maketrans({"O": "0", "o": "0", "l": "1", "I": "1", "S": "5", "B": "8"}))
    digits = "".join(ch for ch in t if ch.isdigit())
    # Rebuild from digits using the format's field order, so missing separators don't matter.
    probe = datetime(2000, 1, 2, 3, 4, 5).strftime(fmt)
    if len("".join(c for c in probe if c.isdigit())) != len(digits):
        return None
    it = iter(digits)
    rebuilt = "".join(next(it) if c.isdigit() else c for c in probe)
    try:
        return datetime.strptime(rebuilt, fmt).replace(tzinfo=IST).timestamp()   # DVRs show centre-local time
    except ValueError:
        return None


@dataclass
class ClockCheck:
    p: IntegrityParams = field(default_factory=IntegrityParams)
    _last: tuple[float, float] | None = None   # (device_t, ocr_t)

    def check(self, device_t: float, ocr_t: float | None) -> dict:
        if ocr_t is None:
            return {"drift": None, "clock_drift": False, "clock_non_monotonic": False, "ocr_ok": False}
        drift = ocr_t - device_t
        non_mono = False
        if self._last:
            dt_dev, dt_ocr = device_t - self._last[0], ocr_t - self._last[1]
            if dt_dev > 5:
                rate = dt_ocr / dt_dev
                non_mono = dt_ocr <= 0 or abs(rate - 1) > self.p.clock_rate_tol
        self._last = (device_t, ocr_t)
        return {"drift": round(drift, 1), "clock_drift": abs(drift) > self.p.clock_drift_s,
                "clock_non_monotonic": non_mono, "ocr_ok": True}


# ---------------------------------------------------------------------------------- loop
def phash(frame_bgr: np.ndarray) -> str:
    """64-bit perceptual hash of a keyframe (timestamp overlay region should be masked by caller)."""
    img = Image.fromarray(cv2.cvtColor(cv2.resize(frame_bgr, (256, 144)), cv2.COLOR_BGR2RGB))
    return str(imagehash.phash(img))


class LoopIndex:
    """7-day local pHash index. Only people-present keyframes are indexed: an empty room
    legitimately looks identical every day."""

    def __init__(self, path: str, p: IntegrityParams = IntegrityParams()):
        self.p = p
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS keyframes (cam TEXT, t REAL, day TEXT, ph TEXT)")

    def check_and_add(self, cam: str, t: float, ph: str) -> dict | None:
        day = datetime.fromtimestamp(t, IST).strftime("%Y-%m-%d")
        self.db.execute("DELETE FROM keyframes WHERE t < ?", (t - self.p.loop_days * 86400,))
        rows = self.db.execute("SELECT t, day, ph FROM keyframes WHERE cam=? AND day != ?", (cam, day)).fetchall()
        h = int(ph, 16)
        hit = None
        for ot, oday, oph in rows:
            d = bin(h ^ int(oph, 16)).count("1")
            if d <= self.p.loop_hamming and (hit is None or d < hit["hamming"]):
                hit = {"other_t": ot, "other_day": oday, "hamming": d}
        self.db.execute("INSERT INTO keyframes VALUES (?,?,?,?)", (cam, t, day, ph))
        self.db.commit()
        return hit


def mask_roi(frame_bgr: np.ndarray, roi) -> np.ndarray:
    """Black out the timestamp ROI so the burned-in clock doesn't change the pHash."""
    if not roi:
        return frame_bgr
    f = frame_bgr.copy()
    x, y, w, h = roi
    f[y:y + h, x:x + w] = 0
    return f


if __name__ == "__main__":
    assert parse_clock("07-03-2018 11:00:05", "%d-%m-%Y %H:%M:%S") == datetime(2018, 3, 7, 11, 0, 5, tzinfo=IST).timestamp()
    assert parse_clock("O7-03-2018 11:00:O5", "%d-%m-%Y %H:%M:%S") is not None
    c = ClockCheck()
    assert not c.check(1000, 1000)["clock_non_monotonic"]
    r = c.check(1060, 1000)   # clock stuck for 60 s
    assert r["clock_non_monotonic"]
    assert ClockCheck().check(time.time(), time.time() - 86400)["clock_drift"]
    print("integrity self-check ok")
