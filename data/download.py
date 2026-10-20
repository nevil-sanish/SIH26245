"""Fetch the public footage SAKSHI is evaluated on (licences in docs/DATASETS.md). Idempotent.

    python data/download.py            # → data/raw/meva/*.avi + annotations/, data/raw/commons/*

MEVA (CC BY 4.0, Kitware/IARPA): school entrance G420 (busy arrival + exit slots) and lobby G421.
Wikimedia Commons: two computer-lab clips (public domain / CC BY-SA 4.0).
SCUT-HEAD is downloaded inside the Colab fine-tune notebook (research use only; never redistributed).
"""
from __future__ import annotations

import subprocess
import urllib.request
from pathlib import Path

RAW = Path(__file__).resolve().parent / "raw"
MEVA_S3 = "https://mevadata-public-01.s3.amazonaws.com/drops-123-r13/"
MEVA_CLIPS = [
    "2018-03-11/12/2018-03-11.12-00-00.12-05-00.school.G420.r13.avi",   # 43 annotated entries
    "2018-03-11/11/2018-03-11.11-15-00.11-20-00.school.G420.r13.avi",   # 42 annotated exits
    "2018-03-15/15/2018-03-15.15-15-00.15-20-00.school.G421.r13.avi",   # lobby, busiest annotated G421 slot (~9 actors/frame)
]
MEVA_ANN = "https://gitlab.kitware.com/meva/meva-data-repo.git"
COMMONS = {
    "mexico_computer_lab.ogv": "https://upload.wikimedia.org/wikipedia/commons/b/b2/Laboratorio_de_computo.ogv",
    "india_computer_lab.ogv": "https://upload.wikimedia.org/wikipedia/commons/d/d7/Free_Computer_Lab.wmv.ogv",
}
UA = {"User-Agent": "SAKSHI-SIH26245/0.1 (research prototype)"}


def fetch(url: str, dst: Path):
    if dst.exists() and dst.stat().st_size > 0:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".part")
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA)) as r, open(tmp, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    tmp.rename(dst)   # never leave a truncated file under the final name
    print("fetched", dst.name)


def main():
    print("MEVA — CC BY 4.0, Kitware Inc. and IARPA (attribution in docs/DATASETS.md)")
    for k in MEVA_CLIPS:
        fetch(MEVA_S3 + k, RAW / "meva" / Path(k).name)
    ann = RAW / "meva" / "annotations"
    if not ann.exists():
        subprocess.run(["git", "clone", "-q", "--depth", "1", MEVA_ANN, str(ann)], check=True)
    print("Wikimedia Commons — public domain / CC BY-SA 4.0")
    for name, url in COMMONS.items():
        fetch(url, RAW / "commons" / name)


if __name__ == "__main__":
    main()
