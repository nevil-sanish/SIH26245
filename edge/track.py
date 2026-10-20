"""ByteTrack (roboflow/trackers, Apache-2.0). IDs are session-scoped: a new tracker is created
for every session, so no person ID ever survives across sessions or days (PROMPT §1.3)."""
from __future__ import annotations

import supervision as sv
from trackers import ByteTrackTracker


class SessionTracker:
    def __init__(self, fps: float):
        self.fps = fps
        self.new_session()

    def new_session(self):
        self._t = ByteTrackTracker(frame_rate=self.fps, lost_track_buffer=int(self.fps * 2),
                                   track_activation_threshold=0.4, high_conf_det_threshold=0.5)

    def update(self, det: sv.Detections) -> sv.Detections:
        return self._t.update(det)
