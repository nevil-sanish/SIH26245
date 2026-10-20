"""Frame sources: RTSP (live), DVR file pull (periodic folder of exports), MP4/AVI (demo).

Yields (frame_bgr, capture_t): capture_t is wall-clock seconds. For RTSP it is time.time(); for files
it is `start_time` + video offset, so recorded footage replays on its own timeline (this is how the
red-team "replayed footage" scenario presents to the pipeline).
"""
from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import cv2

VIDEO_EXT = {".mp4", ".avi", ".mkv", ".mov", ".ogv", ".webm"}


def _files(source: str) -> list[Path]:
    p = Path(urlparse(source).path if source.startswith("file://") else source)
    return sorted(f for f in p.iterdir() if f.suffix.lower() in VIDEO_EXT) if p.is_dir() else [p]


def frames(source: str, sample_fps: float, start_time: str | None = None, max_backoff: float = 60):
    if source.startswith(("rtsp://", "http://", "https://")):
        yield from _live(source, sample_fps, max_backoff)
        return
    t0 = datetime.fromisoformat(start_time).timestamp() if start_time else time.time()
    for f in _files(source):
        cap = cv2.VideoCapture(str(f))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        step = max(1, round(fps / sample_fps))
        i = 0
        while True:
            ok = cap.grab()
            if not ok:
                break
            if i % step == 0:
                ok, frame = cap.retrieve()
                if ok:
                    yield frame, t0 + i / fps
            i += 1
        t0 += i / fps     # next DVR export continues the timeline
        cap.release()


def _live(url: str, sample_fps: float, max_backoff: float):
    backoff = 1.0
    while True:
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            time.sleep(backoff); backoff = min(max_backoff, backoff * 2)
            continue
        backoff, last = 1.0, 0.0
        while True:
            ok, frame = cap.read()
            if not ok:
                break                      # stream dropped → reconnect with backoff
            now = time.time()
            if now - last >= 1 / sample_fps:
                last = now
                yield frame, now
        cap.release()
