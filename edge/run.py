"""Edge main loop for one camera: ingest → detect → track → zones → events → integrity → packets → outbox.

    python -m edge.run --camera edge/cameras/TC0421-DOOR.yaml --uplink http://localhost:8000

State (device key, outbox, pHash index, asset registry) lives in --state (default data/edge_state/<centre>).
Prints one JSON line per packet; the last line is a run summary (frames, measured fps, bytes).
"""
from __future__ import annotations

import argparse
import base64
import json
import time
from pathlib import Path

import numpy as np

from edge import evidence, integrity
from edge.detect import Detector, ModuleUnavailable
from edge.events import EventBuilder
from edge.ingest import frames
from edge.outbox import Outbox
from edge.packet import Packetizer, canonical, load_or_create_key
from edge.privacy import FaceBlur, thumbnail
from edge.track import SessionTracker
from edge.zones import CameraConfig, Zones

ROOT = Path(__file__).resolve().parents[1]


def run(cfg: CameraConfig, state: Path, uplink: str | None, tier: str = "whisper", max_minutes: float | None = None,
        integrity_every=30, ocr_every=60, keyframe_every=300, asset_every=900, quiet=False):
    state.mkdir(parents=True, exist_ok=True)
    ip = integrity.IntegrityParams(**cfg.integrity)
    det_cfg = cfg.detect
    unavailable = []
    try:
        detector = Detector(str(ROOT / det_cfg["model"]), det_cfg.get("class_ids", [1]),
                            det_cfg.get("threshold", 0.4), det_cfg.get("tile"))
    except ModuleUnavailable as e:
        raise SystemExit(f"[{cfg.camera_id}] detection module unavailable: {e}")  # fail loudly
    fps = cfg.sample_fps or (5 if cfg.role == "door" else 1)
    tracker = SessionTracker(fps) if cfg.role == "door" else None
    zones = Zones(cfg)
    events = EventBuilder([a["asset_id"] for a in cfg.assets])
    asset_boxes = {a["asset_id"]: [*np.min(a["zone"], 0), *np.max(a["zone"], 0)] for a in cfg.assets}
    tamper = integrity.TamperState(ip)
    clock = integrity.ClockCheck(ip)
    reader = integrity.ClockReader(cfg.timestamp_roi, cfg.timestamp_format) if cfg.timestamp_roi else None
    if reader and not reader.available:
        unavailable.append("ocr")
    loops = integrity.LoopIndex(str(state / "phash.sqlite"), ip)
    blur = FaceBlur() if tier != "whisper" else None
    if blur and not blur.available:
        unavailable.append("faceblur")   # no blur → no thumbnails leave; packets degrade to whisper
    assets = None
    if cfg.assets:
        from edge.assets import AssetService
        assets = AssetService(str(state / f"{cfg.camera_id}_assets.json"))
        if not assets.available:
            unavailable.append("assets"); assets = None

    key = load_or_create_key(state / "device.key")
    outbox = Outbox(str(state / "outbox.sqlite"), uplink)
    seq, prev = outbox.load_chain(cfg.camera_id)
    pz = Packetizer(cfg.centre_id, cfg.camera_id, key, seq, prev)

    flags_min: set[str] = set()
    last = {"integ": -1e18, "ocr": -1e18, "key": -1e18, "asset": -1e18}
    clk_drift = sharp = phash_min = None
    ident: dict[str, float] = {}
    loop_hit = None
    thumb_frame = None
    n_frames, t_start_wall, first_t, prev_t = 0, time.time(), None, None
    sent_packets = []

    def emit(bucket):
        nonlocal flags_min, clk_drift, phash_min, ident, thumb_frame, loop_hit
        span = (bucket.t_last - bucket.t_first) if bucket.t_first is not None else 0
        expected = int(min(60, span + 1 / fps) * fps)   # only the part of the minute the source actually covered
        level = evidence.camera_level(flags_min, bucket.frames, expected, sharp, ip.lap_min)
        f = {"in": len(bucket.entries), "out": len(bucket.exits), "ei": bucket.entries, "eo": bucket.exits,
             "occ": int(np.median(bucket.occ)) if bucket.occ else None, "oc": bucket.occ,
             "tr": int(np.median(bucket.trainers)) if bucket.trainers and zones.trainer else None,
             "use": {k: round(v) for k, v in bucket.use.items()} or None,
             "clk": clk_drift, "ph": phash_min, "aid": ident or None,
             "ev": level, "flags": sorted(flags_min), "q": sharp, "na": unavailable or None,
             "loop": loop_hit}
        t_tier = "whisper"
        if tier == "normal" and flags_min and blur and blur.available and thumb_frame is not None:
            f["thumb"] = base64.b64encode(thumbnail(thumb_frame, blur)).decode()
            t_tier = "normal"
        pkt = pz.build(bucket.t0, tier=t_tier, **f)
        outbox.put(pkt, pz.prev)
        sent_packets.append(len(canonical(pkt)))
        if not quiet:
            print(json.dumps({k: v for k, v in pkt.items() if k not in ("sig", "thumb")}), flush=True)
        outbox.flush()
        flags_min, clk_drift, phash_min, ident, thumb_frame, loop_hit = set(), None, None, {}, None, None

    for frame, t in frames(cfg.source, fps, cfg.start_time):
        if first_t is None:
            first_t = t
        if max_minutes and t - first_t > max_minutes * 60:
            break
        dt = (t - prev_t) if prev_t else 1 / fps
        prev_t = t
        n_frames += 1
        det = detector(frame)
        crossings = (0, 0)
        if tracker:
            det = tracker.update(det)
            crossings = zones.crossings(det)
        occ = zones.occupancy(det)
        hits = {}
        for aid, (zone, _) in zones.assets.items():
            hits[aid] = bool(zone.trigger(det).any()) if len(det) else False

        if t - last["integ"] >= integrity_every:
            last["integ"] = t
            r = tamper.check(frame, t)
            sharp = r["sharpness"]
            for k in ("frozen", "covered", "moved"):
                if r[k]:
                    flags_min.add(k); thumb_frame = frame
        else:
            # frozen needs continuous evidence: keep feeding the diff cheaply
            r = tamper.check(frame, t, full=False)
            if r["frozen"]:
                flags_min.add("frozen")
        if reader and reader.available and t - last["ocr"] >= ocr_every:
            last["ocr"] = t
            c = clock.check(t, reader.read(frame))
            clk_drift = c["drift"]
            for k in ("clock_drift", "clock_non_monotonic"):
                if c[k]:
                    flags_min.add(k); thumb_frame = frame
        if occ[0] + occ[1] > 0 and t - last["key"] >= keyframe_every:
            last["key"] = t
            phash_min = integrity.phash(integrity.mask_roi(frame, cfg.timestamp_roi))
            hit = loops.check_and_add(cfg.camera_id, t, phash_min)
            if hit:
                flags_min.add("loop"); loop_hit = hit; thumb_frame = frame
        if assets and t - last["asset"] >= asset_every:
            last["asset"] = t
            for a in cfg.assets:
                if a["asset_id"] not in assets.registry:
                    assets.register(a["asset_id"], frame, a["zone"])
                ident[a["asset_id"]] = assets.identity(a["asset_id"], frame, a["zone"])

        done = events.update(t, dt, crossings, occ, frame, hits, asset_boxes)
        if done:
            emit(done)
    last_bucket = events.flush()
    if last_bucket and last_bucket.frames:
        emit(last_bucket)
    outbox.drain()
    wall = time.time() - t_start_wall
    summary = {"summary": cfg.camera_id, "frames": n_frames, "wall_s": round(wall, 1),
               "fps_measured": round(n_frames / wall, 2) if wall else None,
               "packets": len(sent_packets), "mean_packet_bytes": round(float(np.mean(sent_packets)), 1) if sent_packets else 0,
               "pending": outbox.pending(), "unavailable": unavailable}
    print(json.dumps(summary), flush=True)
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--camera", required=True)
    ap.add_argument("--uplink", default=None, help="http://host:8000 or mqtt://host:1883; omit = offline (store only)")
    ap.add_argument("--state", default=None)
    ap.add_argument("--tier", default="whisper", choices=["whisper", "normal"])
    ap.add_argument("--source", default=None, help="override camera source")
    ap.add_argument("--start-time", default=None, help="override wall-clock time of first frame (ISO)")
    ap.add_argument("--centre", default=None, help="override centre_id (red-team R5)")
    ap.add_argument("--max-minutes", type=float, default=None)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    cfg = CameraConfig.load(a.camera)
    cfg.source = a.source or cfg.source
    cfg.start_time = a.start_time or cfg.start_time
    cfg.centre_id = a.centre or cfg.centre_id
    state = Path(a.state) if a.state else ROOT / "data" / "edge_state" / cfg.centre_id
    run(cfg, state, a.uplink, a.tier, a.max_minutes, quiet=a.quiet)


if __name__ == "__main__":
    main()
