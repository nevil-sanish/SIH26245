"""S3 ₹-at-risk + S4 explainable risk queue.

Risk is a ranking aid for inspectors, never a penalty. Each centre gets a 0–100 score from its open
flags, with REDUCED evidence discounted, and the top-3 reasons are listed with links to evidence.
"""
from __future__ import annotations

import math

# Flag weights (how much one open, unreviewed flag of this type moves centre risk).
FLAG_WEIGHT = {
    "unmatched_checkin": 30, "burst": 20, "ghost_session": 25, "inflation": 15,
    "checkin_then_leave": 10, "trainee_hours_gap": 15,
    "clock_drift": 25, "clock_non_monotonic": 25, "loop": 25, "cross_centre_duplicate": 35,
    "frozen": 15, "covered": 15, "moved": 10,
    "ornamental_asset": 15, "asset_swapped": 25, "asset_missing": 20,
    "inspection_shadow": 30, "data_gap": 5,
}
EVIDENCE_DISCOUNT = {"FULL": 1.0, "REDUCED": 0.6, "INSUFFICIENT": 0.3}

# ₹ per trainee-hour. ASSUMPTION until a cited PMKVY cost norm replaces it (see docs/DECISIONS.md).
RATE_PER_TRAINEE_HOUR = 50.0


def rupees_at_risk(unverified_trainee_hours: float, rate: float = RATE_PER_TRAINEE_HOUR) -> float:
    return round(max(0.0, unverified_trainee_hours) * rate, 0)


def centre_risk(flags: list[dict]) -> dict:
    """flags: dicts with type, severity (0–1), evidence_level, explanation, id. Open flags only."""
    contrib = []
    for f in flags:
        w = FLAG_WEIGHT.get(f["type"], 10) * min(1.0, max(0.2, f.get("severity", 1.0)))
        w *= EVIDENCE_DISCOUNT.get(f.get("evidence_level", "FULL"), 1.0)
        contrib.append((w, f))
    # Saturating sum: many small flags approach but never exceed 100.
    score = 100 * (1 - math.prod(1 - min(w, 95) / 100 for w, _ in contrib))
    top = sorted(contrib, key=lambda x: -x[0])[:3]
    return {"risk": round(score, 1),
            "reasons": [{"flag_id": f.get("id"), "type": f["type"], "weight": round(w, 1),
                         "evidence_level": f.get("evidence_level"), "explanation": f.get("explanation")}
                        for w, f in top]}
