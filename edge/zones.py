"""Camera YAML → supervision zones. One camera owns each zone (no multi-camera double counting).

YAML keys (see edge/cameras/*.yaml and PROMPT §8.1): camera_id, centre_id, role (door|room|workshop),
source, door_line, entry_direction, room_polygon, trainer_zone, assets[], timestamp_roi,
timestamp_format, detect{model, class_ids, threshold, tile}, sample_fps, integrity{...}.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import supervision as sv
import yaml


@dataclass
class CameraConfig:
    camera_id: str
    centre_id: str
    role: str
    source: str
    detect: dict
    door_line: list | None = None
    entry_direction: str = "in_is_left_to_right"
    room_polygon: list | None = None
    trainer_zone: list | None = None
    assets: list = field(default_factory=list)
    timestamp_roi: list | None = None
    timestamp_format: str = "%d-%m-%Y %H:%M:%S"
    sample_fps: float | None = None
    start_time: str | None = None        # file sources: wall-clock time of the first frame
    integrity: dict = field(default_factory=dict)

    @classmethod
    def load(cls, path: str) -> "CameraConfig":
        d = yaml.safe_load(open(path))
        return cls(**d)


class Zones:
    def __init__(self, cfg: CameraConfig):
        self.cfg = cfg
        self.line = None
        if cfg.door_line:
            (x1, y1), (x2, y2) = cfg.door_line
            # Bottom-centre anchor = feet: the point that actually crosses a doorway.
            self.line = sv.LineZone(start=sv.Point(x1, y1), end=sv.Point(x2, y2),
                                    triggering_anchors=[sv.Position.BOTTOM_CENTER])
        poly = lambda p: sv.PolygonZone(polygon=np.asarray(p, np.int32), triggering_anchors=[sv.Position.CENTER])
        self.room = poly(cfg.room_polygon) if cfg.room_polygon else None
        self.trainer = poly(cfg.trainer_zone) if cfg.trainer_zone else None
        self.assets = {a["asset_id"]: (poly(a["zone"]), a) for a in cfg.assets}
        # supervision counts "in" when crossing from the line's left to right (start→end view);
        # flip if this doorway's inside is the other side.
        self.flip = cfg.entry_direction == "in_is_right_to_left"

    def crossings(self, det: sv.Detections) -> tuple[int, int]:
        if self.line is None or det.tracker_id is None or len(det) == 0:
            return 0, 0
        cin, cout = self.line.trigger(det)
        i, o = int(cin.sum()), int(cout.sum())
        return (o, i) if self.flip else (i, o)

    def occupancy(self, det: sv.Detections) -> tuple[int, int]:
        """(people in room polygon excluding trainer zone, people in trainer zone)."""
        if len(det) == 0:
            return 0, 0
        in_room = self.room.trigger(det) if self.room else np.ones(len(det), bool)
        in_tr = self.trainer.trigger(det) if self.trainer else np.zeros(len(det), bool)
        return int((in_room & ~in_tr).sum()), int(in_tr.sum())
