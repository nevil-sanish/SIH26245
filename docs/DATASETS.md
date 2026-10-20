# Datasets — sources, licences and what each one is used for

Rule: anything shown in the **demo** must be licensed for redistribution (CC BY / CC0 / own footage with consent).
Research-only sets are used for **training and benchmarks only** and are never committed or shown in the demo.

Download scripts: `data/download/` (each script prints the licence before downloading). Raw data lives in `data/raw/` (git-ignored).

| Dataset | What it is | Licence (checked 2026-10-20) | Used for | Where to get it |
|---|---|---|---|---|
| **MEVA** (Kitware / IARPA) | ~328 h multi-camera ground video (indoor + outdoor, scripted actors), 4,259 clips, ~184 h annotated activities | **CC BY 4.0** — verified from `MEVA-data-license.txt` | Door/entrance crossings, tracking, CCTV angles; **demo footage** (attributed) until our own footage arrives | `aws s3 ls --no-sign-request s3://mevadata-public-01/` · https://mevadata.org · https://registry.opendata.aws/mevadata/ · annotations: https://gitlab.kitware.com/meva/meva-data-repo |
| **SCUT-HEAD** | 4,405 images, 111,251 head boxes (Pascal VOC). Part A: 2,000 classroom-surveillance images (1,500 train / 500 test). Part B: 2,405 web images | No licence file → **research use only** `[Guessing]` | Fine-tuning RF-DETR head detector (in Colab) and head-count MAE benchmark | https://github.com/HCIILAB/SCUT-HEAD-Dataset-Release — Part A: https://drive.google.com/open?id=1yaOF9os5wPVNNG4GVzNyULLVe74vdrBE · Part B: https://drive.google.com/open?id=1LZ_KlTPStDEcqycfqUkDkqQ-aNMMC3cl |
| **SCB-Dataset** (v1–v3, ST-4) | Classroom images of student behaviour, incl. a university classroom set; SCB3: 5,686 images / 45,578 labels | GitHub repo has **no licence** → research use only | Extra classroom head/person data for fine-tuning (behaviour labels are **ignored** — no behaviour scoring) | https://github.com/Whiffe/SCB-dataset · paper https://arxiv.org/abs/2310.02522 |
| **EduNet** (C-DAC Pune) | ~7,851 clips, 20 teacher/student action classes, ~12 h of classroom video (sourced from YouTube) | Not stated; release on request | Robustness test on Indian classrooms, if the authors grant access | Paper: https://www.mdpi.com/1424-8220/21/17/5699 — email the authors |
| **SPHAR** | 7,759 surveillance-perspective clips aggregated from CAVIAR, CASIA, UCF-Crime, VIRAT, MEVA, Okutama, … | **Per-source licence** (file names carry the source). MEVA/VIRAT/UT-Interaction parts are usable; UCF-* are research-only; BIT / Live Videos / Okutama are non-commercial | Robustness at CCTV angles (person detection, low quality) | https://github.com/AlexanderMelde/SPHAR-Dataset |
| **Wildtrack** (EPFL CVLab) | 7 synchronised HD cameras, 400 annotated frames per camera, calibration | Research use `[Likely]` — no explicit licence found | Multi-camera double-counting tests (zone ownership) | https://www.epfl.ch/labs/cvlab/data/data-wildtrack/ |
| **DCSASS** (Kaggle) | Short CCTV clips of suspicious activity (UCF-Crime derived) | Check Kaggle page; derived from research-only UCF-Crime | Low-quality / compressed footage tests only | https://www.kaggle.com/datasets/mateohervas/dcsass-dataset |
| **Natural Earth** admin-0, India point-of-view edition | country outline following India's official boundaries | **Public domain** | dashboard map (`scripts/make_india_map.py`) | https://www.naturalearthdata.com · github nvkelso/natural-earth-vector |
| **Wikimedia Commons** computer-lab clips | `Laboratorio de computo.ogv` (568×320), `Free Computer Lab.wmv.ogv` (384×288) | **CC BY-SA 4.0** / **Public domain** | lab room camera, monitor assets (screen-on, identity) | https://commons.wikimedia.org (see `data/download.py`) |
| COCO 2017 (person) | General person boxes | CC BY 4.0 annotations; images per Flickr terms | RF-DETR pretrained weights (already trained on it) | https://cocodataset.org |
| CrowdHuman | Crowded-scene person boxes | Non-commercial research `[Likely]` | Optional dense-room benchmark | https://www.crowdhuman.org |
| MOT17 | Tracking benchmark | Research use (CC BY-NC-SA 3.0) `[Likely]` | Tracker sanity check | https://motchallenge.net/data/MOT17/ |
| Roboflow Universe equipment sets | Lab equipment images | Only **CC BY 4.0 / CC0** sets accepted; each one attributed below when added | Optional closed-set equipment detector | https://universe.roboflow.com |
| **Own college footage** (pending) | 2–3 rooms (classroom, computer lab, workshop), door + room camera, DVR timestamp overlay ON, 1080p/720p/360p, day + evening | Own, with written consent from people filmed | **Primary** demo + accuracy dataset once provided; eval re-runs unchanged | User will supply |
| Red-team generator | R1–R9 fraud + N1–N3 honest controls | Ours | D4 accuracy assessment — labelled `simulated` | `redteam/` |
| Mock SIDH | Batches, timetable, enrolment, trainers, check-ins | Ours | Programme data stand-in — labelled `mock` | `cloud/sidh_mock/` |

## Attribution (required by CC BY 4.0)

> "Multiview Extended Video with Activities" (MEVA) dataset by Kitware Inc. and the Intelligence Advanced Research Projects Activity (IARPA), licensed under CC BY 4.0 (http://creativecommons.org/licenses/by/4.0/). Clips used in the demo are cropped, re-encoded, face-blurred and overlaid with a synthetic DVR timestamp.

## How the demo footage is used (honesty note)

- MEVA clips are re-encoded to 1280×720 and **re-stamped** onto the demo day (2026-10-19) with a burned-in DVR-style
  clock (`redteam/generators.py::burn_clock`). The originals were recorded 2018-03-11.
- The honest demo centre's door clip (G420, 12:00–12:05) and lobby clip (G421, adjacent slot 11:55–12:00) are
  both stamped 12:00 so that one demo session has a door and a room view. Ground truth for door events comes
  from the G420 annotations only.
- Red-team manipulations (replay with yesterday's clock, freeze, lens cover, same clip under two centre IDs) are
  applied to these clips; results on them are **measured** (real model output) on **manipulated** footage.
- Handheld classroom videos found on Commons (Ghana) were rejected: camera motion would trigger "moved".
