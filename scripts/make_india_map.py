"""Build dashboard/public/india.json: India outline from Natural Earth admin-0, *India point-of-view* edition
(public domain; follows India's official boundaries), simplified (Douglas–Peucker) and projected to an SVG path.

    python scripts/make_india_map.py [--print]
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_0_countries_ind.geojson"
OUT = Path(__file__).resolve().parents[1] / "dashboard" / "public" / "india.json"
LON, LAT, W, H = (67.5, 98.0), (6.0, 37.5), 600, 640
TOL = 0.04  # degrees


def dp(pts, tol):
    """Douglas–Peucker line simplification."""
    if len(pts) < 3:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    norm = (dx * dx + dy * dy) ** 0.5 or 1e-12
    d = [abs(dy * (x - x1) - dx * (y - y1)) / norm for x, y in pts[1:-1]]
    i = max(range(len(d)), key=d.__getitem__)
    if d[i] <= tol:
        return [pts[0], pts[-1]]
    return dp(pts[: i + 2], tol)[:-1] + dp(pts[i + 1:], tol)


def main():
    sys.setrecursionlimit(100000)
    with urllib.request.urlopen(URL) as r:
        geo = json.load(r)
    f = next(x for x in geo["features"] if x["properties"].get("ADM0_A3") == "IND")
    g = f["geometry"]
    polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    proj = lambda x, y: (round((x - LON[0]) / (LON[1] - LON[0]) * W, 1), round((LAT[1] - y) / (LAT[1] - LAT[0]) * H, 1))
    parts = []
    for poly in polys:
        ring = dp(poly[0], TOL)
        if len(ring) < 4:
            continue
        parts.append("M" + "L".join(f"{a},{b}" for a, b in (proj(x, y) for x, y in ring)) + "Z")
    out = {"path": "".join(parts), "lon": LON, "lat": LAT, "w": W, "h": H,
           "source": "Natural Earth admin-0, India POV edition (public domain)"}
    OUT.write_text(json.dumps(out, separators=(",", ":")))
    print(f"{len(parts)} rings, {len(out['path'])} chars → {OUT}")
    if "--print" in sys.argv:
        print("INDIA_JSON_BEGIN" + json.dumps(out, separators=(",", ":")) + "INDIA_JSON_END")


if __name__ == "__main__":
    main()
