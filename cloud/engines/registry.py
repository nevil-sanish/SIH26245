"""H2 (cloud half) — fleet-wide feed-integrity registry.

* cross_centre_duplicate: the same people-present keyframe pHash arriving from two different
  centres (CAG finding: the same photograph used as evidence at different locations). Only the later
  arrival is flagged: the centre that sent the frame first is presumed to own it.
* clock anomalies: edge reports OCR-vs-device drift per packet; the cloud aggregates them.

The edge half (frozen / covered / moved / OCR clock / cross-day loop) lives in edge/integrity.py.
"""
from __future__ import annotations

import numpy as np

HAMMING_MAX = 6          # ≤ 6 of 64 bits differ = same frame after re-encoding (measured, see DECISIONS)
CLOCK_DRIFT_MAX_S = 120


def _bits(h: str) -> int:
    return int(h, 16)


def popcount64(x: np.ndarray) -> np.ndarray:
    """Vectorised popcount for uint64 arrays."""
    x = x.astype(np.uint64)
    return np.unpackbits(x.view(np.uint8).reshape(-1, 8), axis=1).sum(axis=1)


def cross_centre_duplicates(new: list[tuple[str, str, int, int]], known: list[tuple[str, str, int, int]],
                            max_dist: int = HAMMING_MAX) -> list[dict]:
    """Compare new (centre_id, phash_hex, t, arrival_seq) against the registry; return matches across centres
    that arrived earlier than the new hash.

    ponytail: brute-force XOR over the whole registry (fine to ~10^6 hashes);
    switch to a multi-index hash / BK-tree if the fleet outgrows that.
    """
    if not new or not known:
        return []
    kc = np.array([k[0] for k in known])
    kh = np.array([_bits(k[1]) for k in known], dtype=np.uint64)
    kt = np.array([k[2] for k in known])
    ks = np.array([k[3] for k in known])
    out = []
    for centre, h, t, seq in new:
        d = popcount64(kh ^ np.uint64(_bits(h)))
        hit = np.where((d <= max_dist) & (kc != centre) & (ks < seq))[0]
        for i in hit:
            out.append({"centre_id": centre, "t": t, "phash": h, "other_centre": str(kc[i]),
                        "other_t": int(kt[i]), "hamming": int(d[i])})
    return out


def clock_anomalies(drifts: list[tuple[int, float | None]], max_drift: float = CLOCK_DRIFT_MAX_S) -> dict:
    """drifts: (t, OCR − device seconds). Returns worst drift and how many readings exceed max."""
    vals = [(t, d) for t, d in drifts if d is not None]
    if not vals:
        return {"readings": 0, "over": 0, "worst": None}
    over = [(t, d) for t, d in vals if abs(d) > max_drift]
    worst = max(vals, key=lambda x: abs(x[1]))
    return {"readings": len(vals), "over": len(over), "worst": worst[1], "worst_t": worst[0]}
