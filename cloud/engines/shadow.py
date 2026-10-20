"""H3 — inspection-shadow detector.

Flags centres whose daily behaviour (Integrity Score, or 1 − OAI) shifts around inspection dates:
"performing for audits". Two complementary tests:

1. Change points (ruptures PELT) on the daily series; count how many land within ±window days
   of an inspection.
2. A permutation test: mean score inside audit windows minus mean outside, compared with the same
   statistic for randomly placed pseudo-inspections. Gives a judge-friendly p-value.
"""
from __future__ import annotations

import numpy as np
import ruptures as rpt


def _window_mask(n: int, idx: list[int], w: int) -> np.ndarray:
    m = np.zeros(n, bool)
    for i in idx:
        m[max(0, i - w): i + w + 1] = True
    return m


def permutation_test(series, inspection_idx, window=3, n_perm=2000, seed=0):
    """One-sided: is the series higher inside inspection windows than outside?"""
    y = np.asarray(series, float)
    n = len(y)
    mask = _window_mask(n, inspection_idx, window)
    if mask.all() or not mask.any():
        return 0.0, 1.0
    obs = y[mask].mean() - y[~mask].mean()
    rng = np.random.default_rng(seed)
    k = len(inspection_idx)
    count = 0
    for _ in range(n_perm):
        fake = rng.choice(np.arange(window, n - window), size=k, replace=False) if n > 2 * window + k else rng.choice(n, size=k, replace=False)
        m = _window_mask(n, list(fake), window)
        if m.all() or not m.any():
            continue
        if y[m].mean() - y[~m].mean() >= obs:
            count += 1
    return float(obs), (count + 1) / (n_perm + 1)


def change_points(series, penalty=None):
    """PELT change points (indices where a new segment starts). Penalty defaults to a BIC-like 2·σ²·ln n."""
    y = np.asarray(series, float).reshape(-1, 1)
    if len(y) < 6:
        return []
    sigma2 = max(float(np.var(np.diff(y[:, 0]))) / 2, 1e-6)
    pen = penalty if penalty is not None else 2 * sigma2 * np.log(len(y)) * 2
    bkps = rpt.Pelt(model="l2", min_size=2, jump=1).fit(y).predict(pen=pen)
    return [b for b in bkps if b < len(y)]


def shadow(series, inspection_idx, window=3, alpha=0.05) -> dict:
    """Flag = significant permutation test AND change points near most inspections (≥ 2 audits)."""
    obs, p = permutation_test(series, inspection_idx, window)
    cps = change_points(series)
    near = sum(any(abs(c - i) <= window + 1 for c in cps) for i in inspection_idx)
    enough = len(inspection_idx) >= 2
    flag = bool(enough and p < alpha and obs > 0 and near >= max(1, len(inspection_idx) // 2))
    return {"flag": flag, "p_value": round(p, 4), "lift": round(obs, 2), "change_points": cps,
            "inspections_with_shift": near, "inspections": len(inspection_idx),
            "detail": f"score {obs:+.1f} higher within ±{window} d of {len(inspection_idx)} inspections (p={p:.3f}); "
                      f"{near} inspections coincide with a change point"}
