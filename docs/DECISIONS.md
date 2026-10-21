# Decisions and verified facts

Every `[Likely]` / `[Guessing]` item from `PROMPT.md`, plus every place the build deviates from the prompt's letter,
with the reason. Numbers marked *pending* are filled from GPU-VM runs (`scripts/gpu_runs.sh`).

## Deviations from PROMPT.md (architecture unchanged)

| # | Prompt says | Built | Why |
|---|---|---|---|
| D-1 | `edge/ingest/ detect/ …` folders | one file per module (`edge/ingest.py`, …), same names | each module is < 250 lines; folders would add only `__init__` boilerplate |
| D-2 | SAHI (obss/sahi) for tiling | `supervision.InferenceSlicer` | same slicing-aided method (SAHI paper), MIT, already a dependency — no extra package |
| D-3 | `cloud/migrations/` | `cloud/db.py` `init_db()` = SQLAlchemy `create_all` + Timescale `create_hypertable` | single source of truth while the schema is moving; add Alembic when the first production DB exists |
| D-4 | engines list includes `ingest` | `cloud/ingest.py` (verify/expand) + `cloud/analyze.py` (orchestrates engines → flags) beside `cloud/engines/` | engines stay pure functions (unit-testable without a DB) |
| D-5 | Map of centres | offline SVG map from Natural Earth *India point-of-view* boundaries (public domain) | `react-leaflet` is Hippocratic-licensed (not permissive); tile servers break offline mode |
| D-6 | i18n library | plain JSON dictionaries `dashboard/i18n/{en,hi}.json` + a 30-line provider | no extra dependency |
| D-7 | Whisper packet fields | adds `ei`/`eo` (entry/exit second offsets), `oc` (six 10-s occupancy samples), `tier`, `q` (sharpness), `na` (unavailable modules), `aid` (asset identity scores) | Hungarian matching needs per-event times, not per-minute counts; still ~250 B |
| D-8 | Footage from own college | MEVA (CC BY 4.0) + Wikimedia Commons now; own footage later | user decision 2026-10-20; eval scripts re-run unchanged on new footage |
| D-9 | All runs | nothing executes on the developer laptop: training, inference, eval, red-team run on a cloud VM — Google Colab until 2026-10-21, Kaggle T4 kernels since 2026-10-22 (Colab rate limit) | user rule 2026-10-20; edge fps is therefore measured on the VM CPU (reported with CPU model) |
| D-11 | (implicit) host local time | every wall-clock value is **IST** (`edge/__init__.py::IST`): DVR overlay, OCR parse, date bucketing, timetables, dashboard display | Colab runs in UTC, centres and demo machines in IST; naive local times shifted measured packets 5.5 h away from the timetable |
| D-10 | Edge clips 1080p | demo/red-team clips re-encoded to 1280×720 | CPU budget; 1080p/360p still measured in the robustness curves |

## Verified facts

| Item (prompt tag) | Verified value | Source / date |
|---|---|---|
| MEVA licence | CC BY 4.0 — `MEVA-data-license.txt` | mevadata.org, 2026-10-20 |
| MEVA door-event GT | `person_enters/exits_scene_through_structure` activities with frame spans; G420 2018-03-11 12:00 has 43 entries, 11:15 has 42 exits | kitware annotations, 2026-10-20 |
| SCUT-HEAD terms `[Guessing]` | no licence file in the release repo → treated as research-only; weights trained on it are not redistributed beyond the prototype | github HCIILAB, 2026-10-20 |
| SCUT-HEAD size | 4,405 images / 111,251 heads; converted: train 3,065 · valid 340 · Part A test 500 · Part B test 500 | Colab run, 2026-10-20 |
| RF-DETR Nano licence | Apache-2.0 (code + N–L weights); default resolution 384, we fine-tune at 512 | rfdetr 1.11.2 wheel, 2026-10-20 |
| Whisper packet size `[Guessing]` 150–250 B | 245 B for a typical minute (self-check `python -m edge.packet`) | 2026-10-20 |
| PaddleOCR on DVR overlay | `en_PP-OCRv5_mobile_rec` read the burned clock exactly (12:01:05 at t = 65 s), 0.12 s per read | 2026-10-20 |
| Honest-control FP of `unmatched_checkin` | 20–35 % with a fixed 10 % threshold at 90 % door recall → replaced by a binomial test against the *measured* recall: 1/120 | redteam sims, 2026-10-20 |
| `react-leaflet` licence | Hippocratic-2.1 → rejected | npm registry, 2026-10-20 |
| Edge CPU fps `[Guessing]` | **2.3 fps** on Colab's 2 vCPU (door camera, RF-DETR Nano COCO @384 + OCR, 1 min, 251 B per packet); target-PC figure still to measure | `data/work/cpu_benchmark.json`, Colab 2026-10-20 |
| Door P/R (MEVA G420, 42 in / 2 out, ±4 s) | entries **P 0.977 / R 1.000**; exits P 0.25 (6 FP vs 2 GT: people turning back at the line); any-direction 0.863 / 1.000 at 720p, 0.913 / 0.955 in low light | ACCURACY_REPORT, Colab T4 2026-10-20 |
| Count MAE (SCUT-HEAD Part A test, 500 images, mean 34.4 heads) | deployed ONNX via `edge.detect`: **2.21 @ thr 0.35** (PyTorch 2.17); best 1.86 @ 0.30 | `scripts/eval_head_onnx.py`, Colab T4 2026-10-20 |
| ₹ per trainee-hour `[Likely]` | **assumption ₹50** until a PMKVY cost-norm citation is added (`cloud/engines/risk.py`) | — |
| QP codes for demo trades `[Likely]` | SSC/Q2212, AMH/Q0301, ELE/Q3104 — **mock**, to verify against NSDC QP documents | — |
| SIDH export format `[Likely]` | not public → mock adapter defines the expected shape (`cloud/sidh_mock.py`) | — |
| Raspberry Pi 5 tier `[Guessing]` ₹15–20k | not verified; no hardware promise made | — |

## Door line (G420)

First line `[[767,467],[933,633]]` (720p) was drawn from one doorway only. Measured on Colab 2026-10-20: only 16 of
the 44 GT door paths (feet of each `*_through_structure` actor, MEVA geom) cross it — most people use the middle
doorway (feet ≈(660,455) → (570,535)) — and supervision counted entries as "out". Door recall was 0.50.
Refit: principal axis through the midpoints of all 44 GT paths, extended 40 px each side →
`[[559,479],[873,559]]`, which 42 of 44 paths cross; `entry_direction: in_is_right_to_left` (start→end orientation
kept). Re-measured in the next Colab run (ACCURACY_REPORT). The same check needs doing for each new door camera.
