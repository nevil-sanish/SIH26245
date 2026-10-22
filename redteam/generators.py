"""Red-team generators (S6). Three levels, all labelled `simulated`:

event   one batch-session: check-in log + door events + occupancy, with detector noise from the
        measured door recall/precision and count MAE (so simulated detections err like the real model)
series  multi-day series for R7 (asset use), R8 (identity similarity), R9 (daily sessions around audits)
video   manipulations of real MEVA clips with ffmpeg: DVR timestamp burn-in, replay with an old
        timestamp (R4), freeze and lens-cover segments (R6). R5 reuses one clip under two centre IDs.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import yaml

from cloud.engines.reconcile import Session
from edge import IST

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = yaml.safe_load(open(ROOT / "redteam" / "scenarios.yaml"))


@dataclass
class Noise:
    """Detector error model. Defaults are placeholders until eval/metrics.py measures them on MEVA."""
    door_recall: float = 0.9      # entries
    door_precision: float = 0.9   # entries
    count_mae: float = 1.5
    exit_recall: float = 0.9      # exits are measured separately: their errors (people turning back) differ
    exit_precision: float = 0.9


def _hm(day: datetime, hm: str) -> int:
    h, m = map(int, hm.split(":"))
    return int(day.replace(hour=h, minute=m, second=0, microsecond=0).timestamp())


def event_session(sid: str, seed: int, noise: Noise = Noise(), day: datetime | None = None) -> tuple[Session, dict]:
    """Build one simulated session for scenario `sid` (R1–R3, N1–N3). Returns (Session, ground-truth info)."""
    sc, d = SCENARIOS["scenarios"][sid], SCENARIOS["defaults"]
    p = sc["params"]
    rng = np.random.default_rng(seed)
    day = day or datetime(2026, 10, 12, tzinfo=IST)
    start = _hm(day, d["session"]["start"])
    end = start + d["session"]["hours"] * 3600
    present = p.get("present", d["enrolled"])
    n_check = p.get("checkins", present)

    # true arrivals of people physically present
    arrive = np.sort(start - 600 + rng.uniform(0, d["arrival_spread_min"] * 60, present))
    lo, hi = d["checkin_delay_s"]
    honest_ck = list(arrive + rng.uniform(lo, hi, present))
    if sid.startswith("R1"):
        burst = list(start + np.sort(rng.uniform(0, p["burst_s"], n_check)))
        checkins = (honest_ck + burst) if p.get("honest_checkins") else burst
    elif sid.startswith("R2"):
        extra = n_check - present
        checkins = honest_ck + list(start - 600 + rng.uniform(0, 1500, extra))  # proxies spread out, no entry
    else:
        checkins = honest_ck

    exits, entries = [], list(arrive)
    breaks = []
    # occupancy truth per 10 s
    occ_t = np.arange(start, end, 10)
    people = np.zeros(occ_t.size)
    for a in arrive:
        people += occ_t >= a
    if sid.startswith("R3"):
        t_leave = start + p["leave_after_min"] * 60 + 900
        lv = np.sort(t_leave + rng.uniform(0, 300, p["leave"]))
        exits = list(lv)
        for t in lv:
            people -= occ_t >= t
    if sid == "N2":
        b0, b1 = _hm(day, p["lunch"][0]), _hm(day, p["lunch"][1])
        breaks = [(b0, b1)]
        out_t = np.sort(b0 + rng.uniform(0, 180, present)); back_t = np.sort(b1 - 300 + rng.uniform(0, 420, present))
        exits += list(out_t); entries += list(back_t)
        for t1, t2 in zip(out_t, back_t):
            people -= (occ_t >= t1) & (occ_t < t2)
    if sid == "N3":
        # Practical in the workshop: the timetable says this batch is in another room → the session in this
        # room ends at the move; the workshop session is reconciled against the workshop camera.
        end = _hm(day, p["move"][0])
        occ_t, people = occ_t[occ_t < end], people[: (occ_t < end).sum()]
        mv = np.sort(end - 120 + rng.uniform(0, 240, present))
        exits += [t for t in mv if t < end]
    trainers = d["trainers"]
    occ_true = people + trainers

    # --- detector noise --------------------------------------------------------------------------------
    keep = rng.random(len(entries)) < noise.door_recall
    det_entries = [e for e, k in zip(entries, keep) if k]
    n_fp = rng.poisson(len(det_entries) * (1 / noise.door_precision - 1)) if noise.door_precision < 1 else 0
    det_entries += list(rng.uniform(start - 1800, end, n_fp))
    keep = rng.random(len(exits)) < noise.exit_recall
    det_exits = [e for e, k in zip(exits, keep) if k]
    n_fp = rng.poisson(len(det_exits) * (1 / noise.exit_precision - 1)) if noise.exit_precision < 1 else 0
    det_exits += list(rng.uniform(start, end, n_fp))
    sigma = noise.count_mae * np.sqrt(np.pi / 2)            # Gaussian with that MAE
    occ_obs = np.clip(np.round(occ_true + rng.normal(0, sigma, occ_true.size)), 0, None)
    # cloud sees 60 s medians
    mins = (occ_t // 60 * 60).astype(int)
    um = np.unique(mins)
    occ_min = [float(np.median(occ_obs[mins == m])) for m in um]
    s = Session(start=start, end=end, checkins=sorted(checkins), entries=sorted(det_entries),
                exits=sorted(det_exits), occ_t=list(um), occ=occ_min, breaks=breaks, trainers=trainers,
                evidence_level="FULL")
    return s, {"present": present, "claimed": n_check}


# --------------------------------------------------------------------------------------------- series
def r7_asset_days(seed: int, days=14, practical_h=3, use_frac=0.0, honest=False):
    rng = np.random.default_rng(seed)
    out = []
    for i in range(days):
        sched = practical_h * 3600
        frac = rng.uniform(0.25, 0.6) if honest else use_frac + abs(rng.normal(0, 0.01))
        out.append((f"d{i:02d}", sched * frac, sched))
    return out


def r8_identity_days(seed: int, days=10, swap_day=6, same=(0.86, 0.04), other=(0.55, 0.08), honest=False):
    """Cosine similarities. Defaults are placeholders; eval replaces them with DINOv2 sims measured on lab crops."""
    rng = np.random.default_rng(seed)
    return [(f"d{i:02d}", float(np.clip(rng.normal(*(other if (not honest and i >= swap_day) else same)), -1, 1)))
            for i in range(days)]


def r9_centre_days(seed: int, noise: Noise = Noise(), days=75, inspections=3, window=3, honest=False,
                   proxy_frac_outside=0.45):
    """Daily sessions for one centre. Audit performer: honest within ±window days of an inspection,
    proxy check-ins (R2-style) the rest of the time. Returns (sessions, inspection day indices)."""
    rng = np.random.default_rng(seed)
    insp = sorted(rng.choice(np.arange(10, days - 10), size=inspections, replace=False))
    while any(b - a < 2 * window + 4 for a, b in zip(insp, insp[1:])):
        insp = sorted(rng.choice(np.arange(10, days - 10), size=inspections, replace=False))
    base = datetime(2026, 7, 1, tzinfo=IST)
    sessions = []
    for i in range(days):
        near = any(abs(i - j) <= window for j in insp)
        sid = "N1" if (honest or near) else "R2"
        s, _ = event_session(sid, seed * 1000 + i, noise, base + timedelta(days=i))
        if sid == "R2":  # vary how much proxying happens day to day
            k = int(len(s.checkins) * rng.uniform(0.7, 1.0))
            s.checkins = sorted(rng.choice(s.checkins, size=k, replace=False))
        sessions.append(s)
    return sessions, list(map(int, insp))


# --------------------------------------------------------------------------------------------- video
def ffmpeg(*args):
    # TZ=IST so the burned-in DVR clock (pts:localtime) shows centre-local time on any host.
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", *map(str, args)], check=True, env={**os.environ, "TZ": "Asia/Kolkata"})


def _clock_filter(epoch: int, fontsize=40) -> str:
    # DVR-style overlay: white text on a dark box, top-left, advancing with the video's own clock.
    return (f"drawtext=font=monospace:fontsize={fontsize}:fontcolor=white:"
            f"box=1:boxcolor=black@0.6:boxborderw=6:x=24:y=20:"
            f"text='%{{pts\\:localtime\\:{epoch}\\:%d-%m-%Y %H\\\\\\:%M\\\\\\:%S}}'")


def burn_clock(src: Path, dst: Path, start: datetime, scale: str | None = None, extra_vf: str | None = None,
               crf: int = 28, max_s: float | None = None):
    """Re-encode with a burned-in DVR timestamp starting at `start`. scale e.g. '1280:720'."""
    vf = [f for f in [f"scale={scale}" if scale else None, extra_vf, _clock_filter(int(start.timestamp()),
          fontsize=40 if not scale else max(14, int(scale.split(':')[1]) // 27))] if f]
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.stem + ".part.mp4")   # rename only when complete: an interrupted encode never looks done
    ffmpeg("-i", src, *(["-t", max_s] if max_s else []), "-vf", ",".join(vf), "-an", "-c:v", "libx264",
           "-preset", "veryfast", "-crf", crf, tmp)
    tmp.rename(dst)


def freeze_and_cover(src: Path, dst: Path, freeze_s: tuple[float, float], cover_s: tuple[float, float]):
    """R6: hold one frame for freeze_s (a stuck encoder: picture AND burned-in clock stop), then black out
    the lens for cover_s. Input should already carry the DVR clock overlay."""
    f0, f1 = freeze_s
    c0, c1 = cover_s
    enc = ["-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", 8, "-an"]
    tmp = dst.parent / (dst.stem + "_parts")
    tmp.mkdir(parents=True, exist_ok=True)
    ffmpeg("-i", src, "-t", f0, *enc, tmp / "a.mp4")
    ffmpeg("-ss", f0, "-i", src, "-frames:v", 1, tmp / "still.png")
    ffmpeg("-loop", 1, "-i", tmp / "still.png", "-t", f1 - f0, *enc, tmp / "b.mp4")
    ffmpeg("-ss", f1, "-i", src, "-vf",
           f"drawbox=enable='between(t,{c0 - f1},{c1 - f1})':x=0:y=0:w=iw:h=ih:color=black@0.97:t=fill", *enc,
           tmp / "c.mp4")
    (tmp / "list.txt").write_text("".join(f"file '{x}'\n" for x in ("a.mp4", "b.mp4", "c.mp4")))
    part = dst.with_name(dst.stem + ".part.mp4")
    ffmpeg("-f", "concat", "-safe", 0, "-i", tmp / "list.txt", "-c", "copy", part)
    part.rename(dst)
