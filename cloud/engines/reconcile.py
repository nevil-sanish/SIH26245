"""H1 — event-level, anonymous attendance reconciliation.

Every check-in from the attendance log (face-auth / AEBAS, via the mock SIDH adapter) must be
explained by a physical door-entry event seen on CCTV. Nobody is identified: we only have
timestamps of check-ins and timestamps of anonymous line crossings.

Pure functions over plain numbers so the engine is testable without a DB. All times are unix
seconds. See docs/ARCHITECTURE.md §H1 for the signal definitions and weights.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import linear_sum_assignment

# Defaults; every one is overridable through `Params` (cloud config / API query).
@dataclass
class Params:
    window_s: float = 300          # check-in ↔ entry must be within ±window_s
    burst_k: int = 10              # ≥ k check-ins ...
    burst_s: float = 60            # ... within s seconds = bulk marking
    leave_grace_s: float = 900     # ignore exits in the first/last 15 min of a session
    leave_frac: float = 0.2        # net departures ≥ 20 % of check-ins → checkin_then_leave
    inflation_frac: float = 0.8    # peak occupancy < 80 % of claimed → inflation
    ghost_occ: float = 0.5         # occupancy ≤ this around a check-in = empty room
    ghost_frac: float = 0.2
    unmatched_frac: float = 0.1
    hours_gap_frac: float = 0.2
    min_coverage: float = 0.7      # occupancy samples must cover ≥ 70 % of session time
    sample_s: float = 60           # occupancy sample spacing in the cloud (Whisper = 60 s)


# Weights of each signal in the 0–100 Integrity Score. Sum = 100.
WEIGHTS = {"unmatched_checkin": 35, "trainee_hours_gap": 25, "inflation": 15,
           "ghost_session": 10, "burst": 10, "checkin_then_leave": 5}


def match_checkins(checkins, entries, window_s=300):
    """Hungarian matching of check-ins to door entries (one entry explains one check-in).

    Returns (matched_pairs, unmatched_checkin_indices).
    """
    checkins = np.asarray(checkins, float)
    entries = np.asarray(entries, float)
    if checkins.size == 0:
        return [], []
    if entries.size == 0:
        return [], list(range(len(checkins)))
    big = 1e9
    cost = np.abs(checkins[:, None] - entries[None, :])
    cost[cost > window_s] = big
    rows, cols = linear_sum_assignment(cost)
    pairs = [(int(r), int(c)) for r, c in zip(rows, cols) if cost[r, c] < big]
    matched = {r for r, _ in pairs}
    return pairs, [i for i in range(len(checkins)) if i not in matched]


def max_in_window(ts, span_s):
    """Largest number of timestamps inside any window of length span_s."""
    ts = np.sort(np.asarray(ts, float))
    if ts.size == 0:
        return 0
    right = np.searchsorted(ts, ts + span_s, side="right")
    return int((right - np.arange(ts.size)).max())


def _in_slots(t, slots):
    t = np.asarray(t, float)
    m = np.zeros(t.shape, bool)
    for s, e in slots:
        m |= (t >= s) & (t < e)
    return m


@dataclass
class Session:
    """One batch-session (a timetable day for one batch in one room)."""
    start: float
    end: float
    checkins: list[float]
    entries: list[float] = field(default_factory=list)   # door camera LineZone 'in'
    exits: list[float] = field(default_factory=list)     # door camera LineZone 'out'
    occ_t: list[float] = field(default_factory=list)     # occupancy sample times (room camera)
    occ: list[float] = field(default_factory=list)       # occupancy values
    breaks: list[tuple[float, float]] = field(default_factory=list)
    trainers: int = 1
    evidence_level: str = "FULL"  # FULL | REDUCED | INSUFFICIENT (from edge + cloud gap check)


def reconcile_session(s: Session, p: Params = Params()) -> dict:
    """Run every H1 signal on one session and return score, signals and evidence."""
    n = len(s.checkins)
    occ_t = np.asarray(s.occ_t, float)
    occ = np.asarray(s.occ, float)
    session_s = s.end - s.start
    break_s = sum(max(0, min(e, s.end) - max(b, s.start)) for b, e in s.breaks)
    teach_s = max(session_s - break_s, 1)

    # Coverage: silence is not compliance. Missing occupancy = data gap, not "OK".
    in_session = (occ_t >= s.start) & (occ_t < s.end) if occ_t.size else np.zeros(0, bool)
    coverage = min(1.0, in_session.sum() * p.sample_s / session_s) if session_s > 0 else 0.0
    ev = s.evidence_level
    if ev != "INSUFFICIENT" and coverage < p.min_coverage:
        ev = "INSUFFICIENT"
    has_door = ev == "FULL"

    signals: dict[str, dict] = {}

    # burst — needs only the check-in log, so it runs at every evidence level.
    peak_burst = max_in_window(s.checkins, p.burst_s)
    signals["burst"] = {"value": peak_burst, "flag": peak_burst >= p.burst_k,
                        "severity": min(1.0, peak_burst / max(n, 1)) if peak_burst >= p.burst_k else 0.0,
                        "detail": f"{peak_burst} check-ins within {p.burst_s:.0f} s (threshold {p.burst_k})"}

    result = {"checkins": n, "coverage": round(coverage, 3), "evidence_level": ev,
              "matched": [], "unmatched": []}

    if ev == "INSUFFICIENT":
        result.update(status="INSUFFICIENT_EVIDENCE", score=None, signals=signals,
                      unverified_trainee_hours=None,
                      reason="evidence insufficient (tamper, low quality or data gap)")
        return result

    if has_door:
        pairs, unmatched = match_checkins(s.checkins, s.entries, p.window_s)
        uf = len(unmatched) / n if n else 0.0
        signals["unmatched_checkin"] = {
            "value": len(unmatched), "flag": uf > p.unmatched_frac and len(unmatched) >= 2,
            "severity": uf, "detail": f"{len(unmatched)}/{n} check-ins have no door entry within ±{p.window_s:.0f} s"}
        result["matched"] = [[float(s.checkins[a]), float(s.entries[b])] for a, b in pairs]
        result["unmatched"] = [float(s.checkins[i]) for i in unmatched]

        # checkin_then_leave — anonymous, count-based: exits in the session interior that
        # are not balanced by re-entries, outside break slots.
        lo, hi = s.start + p.leave_grace_s, s.end - p.leave_grace_s
        ex = np.asarray(s.exits, float); en = np.asarray(s.entries, float)
        ex = ex[(ex >= lo) & (ex < hi) & ~_in_slots(ex, s.breaks)] if ex.size else ex
        en = en[(en >= lo) & (en < hi) & ~_in_slots(en, s.breaks)] if en.size else en
        departures = max(0, len(ex) - len(en))
        lf = departures / n if n else 0.0
        signals["checkin_then_leave"] = {"value": departures, "flag": lf >= p.leave_frac,
                                         "severity": min(1.0, lf),
                                         "detail": f"{departures} net departures mid-session (not breaks)"}

    # Occupancy-based signals (room camera; available at FULL and REDUCED).
    teach_mask = in_session & ~_in_slots(occ_t, s.breaks)
    trainee_occ = np.clip(occ[teach_mask] - s.trainers, 0, None) if occ.size else np.zeros(0)
    peak = float(np.percentile(trainee_occ, 95)) if trainee_occ.size else 0.0
    inf_ratio = peak / n if n else 1.0
    signals["inflation"] = {"value": round(peak, 1), "flag": n > 0 and inf_ratio < p.inflation_frac,
                            "severity": max(0.0, 1 - inf_ratio) if n else 0.0,
                            "detail": f"peak trainee occupancy {peak:.0f} vs {n} claimed"}

    ghosts = 0
    if occ.size:
        for c in s.checkins:
            near = (occ_t >= c - 120) & (occ_t <= c + 600)
            if near.any() and np.median(np.clip(occ[near] - s.trainers, 0, None)) <= p.ghost_occ:
                ghosts += 1
    gf = ghosts / n if n else 0.0
    signals["ghost_session"] = {"value": ghosts, "flag": gf > p.ghost_frac, "severity": gf,
                                "detail": f"{ghosts}/{n} check-ins while the room was empty"}

    # trainee-hours: claimed (check-ins × teaching time) vs area under the occupancy curve.
    claimed_h = n * teach_s / 3600
    observed_h = float(np.minimum(trainee_occ, n).sum() * p.sample_s / 3600) if trainee_occ.size else 0.0
    observed_h /= max(coverage, 1e-9)  # scale up for sampled coverage (coverage ≥ min_coverage here)
    observed_h = min(observed_h, claimed_h)
    gap = claimed_h - observed_h
    hf = gap / claimed_h if claimed_h else 0.0
    signals["trainee_hours_gap"] = {"value": round(gap, 2), "flag": hf > p.hours_gap_frac, "severity": hf,
                                    "detail": f"claimed {claimed_h:.1f} trainee-h, observed {observed_h:.1f} trainee-h"}

    # Integrity Score: 100 − Σ weight × severity, over the signals we could compute.
    # REDUCED evidence (no door camera) drops door-based signals and renormalises the rest.
    used = {k: WEIGHTS[k] for k in signals}
    total_w = sum(used.values())
    penalty = sum(used[k] * min(1.0, signals[k]["severity"]) for k in used) / total_w
    score = round(100 * (1 - penalty), 1)
    flagged = [k for k, v in signals.items() if v["flag"]]
    result.update(status="DISCREPANCY" if flagged else "CONSISTENT", score=score, signals=signals,
                  flags=flagged, claimed_trainee_hours=round(claimed_h, 2),
                  observed_trainee_hours=round(observed_h, 2),
                  unverified_trainee_hours=round(gap, 2))
    return result
