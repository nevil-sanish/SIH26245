"""Unit tests for the cloud engines (H1, H2, H3, S1/S2, S4). Run: make test"""
import numpy as np

from cloud.engines import assets, registry, risk, shadow
from cloud.engines.reconcile import Params, Session, match_checkins, max_in_window, reconcile_session

T0 = 1_760_000_000  # session start
H = 3600


def honest(n=30, seed=0, door=True):
    rng = np.random.default_rng(seed)
    arrive = np.sort(T0 - 600 + rng.uniform(0, 1200, n))           # trickle in over 20 min
    checkins = list(arrive + rng.uniform(5, 60, n))                  # check-in after entering
    occ_t = np.arange(T0, T0 + 4 * H, 60)
    occ = np.full(occ_t.shape, n + 1.0) + rng.normal(0, 1, occ_t.size)  # trainees + 1 trainer
    return Session(start=T0, end=T0 + 4 * H, checkins=checkins,
                   entries=list(arrive) if door else [], exits=[],
                   occ_t=list(occ_t), occ=list(occ), trainers=1,
                   evidence_level="FULL" if door else "REDUCED")


# --- matching edge cases -----------------------------------------------------------------
def test_match_no_entries():
    assert match_checkins([1, 2, 3], []) == ([], [0, 1, 2])


def test_match_no_checkins():
    assert match_checkins([], [1, 2]) == ([], [])


def test_more_entries_than_checkins():
    pairs, un = match_checkins([100, 200], [90, 110, 190, 210, 500])
    assert un == [] and len(pairs) == 2


def test_simultaneous_arrivals_one_to_one():
    # 5 check-ins at the same second but only 3 entries: exactly 2 unmatched (no double use).
    _, un = match_checkins([100] * 5, [99, 100, 101])
    assert len(un) == 2


def test_clock_skew_within_window_still_matches():
    _, un = match_checkins([1000, 1100], [1000 + 280, 1100 + 280], window_s=300)
    assert un == []
    _, un = match_checkins([1000], [1000 + 400], window_s=300)
    assert un == [0]


def test_burst_window():
    assert max_in_window([0, 1, 2, 100], 60) == 3
    assert max_in_window([], 60) == 0


# --- session-level signals -----------------------------------------------------------------
def test_honest_session_is_consistent():
    r = reconcile_session(honest())
    assert r["status"] == "CONSISTENT", r["signals"]
    assert r["score"] > 85


def test_lunch_break_not_flagged():
    s = honest()
    b0, b1 = T0 + 2 * H, T0 + 2 * H + 1800
    s.breaks = [(b0, b1)]
    occ_t = np.asarray(s.occ_t); occ = np.asarray(s.occ)
    occ[(occ_t >= b0) & (occ_t < b1)] = 0
    s.exits = list(np.linspace(b0, b0 + 120, 30)); s.entries = s.entries + list(np.linspace(b1 - 120, b1, 30))
    s.occ = list(occ)
    assert reconcile_session(s)["status"] == "CONSISTENT"


def test_bulk_checkin_empty_room_R1():
    s = Session(start=T0, end=T0 + 4 * H, checkins=list(T0 + np.linspace(0, 40, 25)),
                entries=[], occ_t=list(np.arange(T0, T0 + 4 * H, 60)),
                occ=[1.0] * 240, trainers=1)
    r = reconcile_session(s)
    assert {"unmatched_checkin", "burst", "ghost_session", "inflation"} <= set(r["flags"])
    assert r["score"] < 30


def test_proxy_R2():
    s = honest(30)
    s.entries = s.entries[:18]
    s.occ = list(np.full(len(s.occ_t), 19.0))
    r = reconcile_session(s)
    assert "unmatched_checkin" in r["flags"] and "inflation" in r["flags"]


def test_checkin_then_leave_R3():
    s = honest(30)
    t_leave = T0 + 20 * 60 + 900
    s.exits = list(np.linspace(t_leave, t_leave + 300, 20))
    occ_t = np.asarray(s.occ_t); occ = np.asarray(s.occ)
    occ[occ_t > t_leave + 300] = 11
    s.occ = list(occ)
    r = reconcile_session(s)
    assert "checkin_then_leave" in r["flags"] and "trainee_hours_gap" in r["flags"]


def test_reduced_evidence_falls_back_to_occupancy():
    r = reconcile_session(honest(door=False))
    assert r["evidence_level"] == "REDUCED" and "unmatched_checkin" not in r["signals"]
    assert r["status"] == "CONSISTENT"


def test_data_gap_abstains():
    s = honest()
    s.occ_t, s.occ = s.occ_t[:60], s.occ[:60]      # only 1 of 4 hours delivered
    r = reconcile_session(s)
    assert r["status"] == "INSUFFICIENT_EVIDENCE" and r["score"] is None


# --- H2 registry ---------------------------------------------------------------------------
def test_cross_centre_duplicate():
    known = [("TC1", "c3d1f0a29b7e4411", 10, 1), ("TC2", "0000000000000000", 20, 2)]
    hits = registry.cross_centre_duplicates([("TC9", "c3d1f0a29b7e4413", 99, 3)], known)
    assert len(hits) == 1 and hits[0]["other_centre"] == "TC1" and hits[0]["hamming"] == 1
    assert registry.cross_centre_duplicates([("TC1", "c3d1f0a29b7e4411", 99, 3)], known) == []
    # the original sender is not flagged when a copier's frame (arrival 5) matches its own (arrival 1)
    assert registry.cross_centre_duplicates([("TC1", "c3d1f0a29b7e4411", 10, 1)], [("TC9", "c3d1f0a29b7e4413", 99, 5)]) == []


def test_clock_anomalies():
    a = registry.clock_anomalies([(1, -4), (2, 86400), (3, None)])
    assert a["over"] == 1 and a["worst"] == 86400


# --- H3 shadow -----------------------------------------------------------------------------
def test_shadow_flags_audit_performer_R9():
    rng = np.random.default_rng(1)
    y = 55 + rng.normal(0, 3, 90)
    insp = [20, 50, 75]
    for i in insp:
        y[i - 2:i + 3] += 30
    r = shadow.shadow(y, insp)
    assert r["flag"] and r["p_value"] < 0.05


def test_shadow_quiet_on_honest_series():
    y = 88 + np.random.default_rng(2).normal(0, 3, 90)
    assert not shadow.shadow(y, [20, 50, 75])["flag"]


# --- S1/S2 ---------------------------------------------------------------------------------
def test_ornamental_R7():
    days = [(f"d{i}", 0, 3 * 3600) for i in range(14)]
    assert assets.ornamental(days)["flag"]
    days = [(f"d{i}", 1800, 3 * 3600) for i in range(14)]
    assert not assets.ornamental(days)["flag"]


def test_swapped_R8_needs_persistence():
    assert not assets.swapped([("d1", 0.9), ("d2", 0.6), ("d3", 0.9)])["flag"]
    assert assets.swapped([("d1", 0.9), ("d2", 0.6), ("d3", 0.55)])["flag"]


def test_inventory_gap():
    assert assets.inventory_gap({"sewing machine": 20}, {"sewing machine": 12}) == [
        {"item": "sewing machine", "sanctioned": 20, "observed": 12, "missing": 8}]


# --- S3/S4 ---------------------------------------------------------------------------------
def test_risk_reduced_evidence_discounted_and_top3():
    full = risk.centre_risk([{"type": "burst", "severity": 1, "evidence_level": "FULL"}])["risk"]
    red = risk.centre_risk([{"type": "burst", "severity": 1, "evidence_level": "REDUCED"}])["risk"]
    assert red < full
    many = risk.centre_risk([{"type": t, "severity": 1} for t in ["loop", "burst", "frozen", "data_gap"]])
    assert len(many["reasons"]) == 3 and many["risk"] <= 100
    assert risk.rupees_at_risk(10, 50) == 500


def test_noise_model_is_per_direction():
    # Entry noise must come from entries, not the any-direction mix inflated by false exits (red-team realism).
    from eval.metrics import measured_noise
    pr = lambda p, r, gt: {"precision": p, "recall": r, "gt": gt}
    door = {"in": pr(0.977, 1.0, 43), "out": pr(0.25, 1.0, 2), "any_direction": pr(0.863, 1.0, 45)}
    n = measured_noise(door, None)
    assert (n.door_precision, n.door_recall) == (0.977, 1.0)
    assert (n.exit_precision, n.exit_recall) == (0.977, 1.0)      # 2 GT exits: too few, entry figures used
    sweep = [{"clip": "G420_exits", "door_min_frames": k, "out": pr(0.8, 0.9, 42), "in": pr(None, None, 0)} for k in range(1, 9)]
    n = measured_noise(door, None, sweep)
    assert (n.exit_precision, n.exit_recall) == (0.8, 0.9)
