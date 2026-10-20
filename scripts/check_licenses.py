"""Licence gate (PROMPT §1.2, §15): fail if any installed Python or npm package is AGPL/GPL, or a banned package.

    python scripts/check_licenses.py            # CI runs this after installing requirements
"""
from __future__ import annotations

import json
import re
import sys
from importlib.metadata import distributions
from pathlib import Path

BANNED_NAMES = {"ultralytics", "boxmot", "yolo-world", "yoloworld"}
COPYLEFT = re.compile(r"\b(A?GPL|GNU (Affero )?General Public)", re.I)
LGPL_OK = re.compile(r"\bLGPL|Lesser", re.I)     # LGPL as an unmodified dynamic dependency is allowed (e.g. paddle deps)
ROOT = Path(__file__).resolve().parents[1]


def lic(d) -> str:
    m = d.metadata
    parts = [m.get("License-Expression") or "", m.get("License") or ""]
    parts += [c for c in m.get_all("Classifier") or [] if c.startswith("License ::")]
    return " | ".join(p for p in parts if p)[:200]


def main() -> int:
    bad = []
    for d in distributions():
        name = (d.metadata.get("Name") or "").lower()
        text = lic(d)
        if name in BANNED_NAMES or (COPYLEFT.search(text) and not LGPL_OK.search(text)):
            bad.append(f"python  {name}=={d.version}: {text or 'unknown'}")
    lock = ROOT / "dashboard" / "package-lock.json"
    if lock.exists():
        for path, p in json.loads(lock.read_text()).get("packages", {}).items():
            l = str(p.get("license", ""))
            if COPYLEFT.search(l) and not LGPL_OK.search(l) or "Hippocratic" in l:
                bad.append(f"npm     {path}: {l}")
    for b in bad:
        print("LICENCE VIOLATION", b)
    print("licence check:", "FAIL" if bad else "ok")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
