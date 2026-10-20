"""Event builder: turns per-frame zone results into the per-minute numbers a Whisper packet carries.

entries/exits  second offsets within the minute (needed for H1 Hungarian matching in the cloud)
occupancy      a sample every 10 s = median of the last 3 frame counts; packet carries the
               minute's median plus the 6 raw samples
asset use      seconds with a person in the asset zone AND motion in the asset region
               (plus screen-on for monitors: mean brightness well above the registration frame)
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import cv2
import numpy as np


@dataclass
class MinuteBucket:
    t0: int
    entries: list[int] = field(default_factory=list)
    exits: list[int] = field(default_factory=list)
    occ: list[int] = field(default_factory=list)
    trainers: list[int] = field(default_factory=list)
    use: dict[str, float] = field(default_factory=dict)
    frames: int = 0
    t_first: float | None = None   # first / last frame time inside this minute (partial minutes at clip edges)
    t_last: float | None = None


class EventBuilder:
    def __init__(self, asset_ids, occ_every_s=10.0, motion_thr=6.0):
        self.asset_ids = list(asset_ids)
        self.occ_every_s, self.motion_thr = occ_every_s, motion_thr
        self._recent = deque(maxlen=3)
        self._next_occ = None
        self._prev_gray = None
        self.bucket: MinuteBucket | None = None

    def _roll(self, t: float) -> MinuteBucket | None:
        m = int(t // 60 * 60)
        done = None
        if self.bucket is None or m != self.bucket.t0:
            done, self.bucket = self.bucket, MinuteBucket(m, use={a: 0.0 for a in self.asset_ids})
        return done

    def update(self, t: float, dt: float, crossings: tuple[int, int], occ: tuple[int, int],
               frame_bgr: np.ndarray, asset_hits: dict[str, bool], asset_boxes: dict[str, list]) -> MinuteBucket | None:
        """Feed one processed frame. Returns the finished minute when the minute rolls over."""
        done = self._roll(t)
        b = self.bucket
        b.frames += 1
        b.t_first = t if b.t_first is None else b.t_first
        b.t_last = t
        off = int(t - b.t0)
        b.entries += [off] * crossings[0]
        b.exits += [off] * crossings[1]
        self._recent.append(occ)
        if self._next_occ is None or t >= self._next_occ:
            b.occ.append(int(np.median([o for o, _ in self._recent])))
            b.trainers.append(int(np.median([tr for _, tr in self._recent])))
            self._next_occ = t + self.occ_every_s
        if self.asset_ids:
            gray = cv2.cvtColor(cv2.resize(frame_bgr, (640, 360)), cv2.COLOR_BGR2GRAY)
            sx, sy = 640 / frame_bgr.shape[1], 360 / frame_bgr.shape[0]
            for a in self.asset_ids:
                if not asset_hits.get(a) or self._prev_gray is None:
                    continue
                x1, y1, x2, y2 = asset_boxes[a]
                r = (slice(int(y1 * sy), int(y2 * sy)), slice(int(x1 * sx), int(x2 * sx)))
                motion = float(np.abs(gray[r].astype(np.int16) - self._prev_gray[r]).mean())
                if motion > self.motion_thr:
                    b.use[a] += dt
            self._prev_gray = gray.astype(np.int16)
        return done

    def flush(self) -> MinuteBucket | None:
        done, self.bucket = self.bucket, None
        return done
