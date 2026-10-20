"""S1 Ornamental Asset Index + S2 same-asset identity + sanctioned-vs-observed inventory.

OAI = 1 − observed_interaction_seconds / scheduled_practical_seconds, per asset.
"Interaction" is computed on the edge: a person inside the asset zone AND motion inside the asset
region (plus screen-on for monitors). Wording stays conservative: "no use observed", never "broken".
"""
from __future__ import annotations

OAI_FLAG = 0.95          # ≥ 95 % of scheduled practical time with no observed use ...
OAI_MIN_DAYS = 10        # ... sustained over ≥ 10 practical days
IDENTITY_MIN = 0.75      # DINOv2 cosine similarity below this = probably a different physical unit
IDENTITY_PERSIST = 2     # need this many consecutive low scans before flagging


def oai(interaction_s: float, scheduled_practical_s: float) -> float | None:
    if scheduled_practical_s <= 0:
        return None
    return round(max(0.0, 1 - interaction_s / scheduled_practical_s), 3)


def ornamental(daily: list[tuple[str, float, float]]) -> dict:
    """daily: (date, interaction_s, scheduled_practical_s) for one asset."""
    days = [(d, oai(i, s)) for d, i, s in daily if s > 0]
    vals = [v for _, v in days if v is not None]
    if not vals:
        return {"oai": None, "flag": False, "days": 0, "detail": "no practical sessions scheduled"}
    total_i = sum(i for _, i, s in daily if s > 0)
    total_s = sum(s for _, _, s in daily if s > 0)
    o = oai(total_i, total_s)
    unused_days = sum(v >= OAI_FLAG for v in vals)
    flag = o >= OAI_FLAG and unused_days >= OAI_MIN_DAYS
    return {"oai": o, "flag": flag, "days": len(vals), "unused_days": unused_days,
            "detail": f"no use observed on {unused_days}/{len(vals)} practical days (OAI {o:.2f})"}


def swapped(scores: list[tuple[str, float]], threshold=IDENTITY_MIN, persist=IDENTITY_PERSIST) -> dict:
    """scores: (date, cosine similarity to the registration crop), in date order."""
    run, first = 0, None
    for d, s in scores:
        if s < threshold:
            run += 1
            first = first or d
            if run >= persist:
                return {"flag": True, "since": first, "min_sim": round(min(x for _, x in scores), 3),
                        "detail": f"asset looks like a different unit since {first} (similarity < {threshold})"}
        else:
            run, first = 0, None
    return {"flag": False, "min_sim": round(min((x for _, x in scores), default=1.0), 3)}


def inventory_gap(sanctioned: dict[str, int], observed: dict[str, int]) -> list[dict]:
    """Sanctioned (QP list × batch size) vs observed counts per item label."""
    out = []
    for item, need in sanctioned.items():
        have = observed.get(item, 0)
        if have < need:
            out.append({"item": item, "sanctioned": need, "observed": have, "missing": need - have})
    return out
