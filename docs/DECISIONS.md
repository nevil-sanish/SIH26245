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
| RF-DETR Nano licence | Apache-2.0 (code + N–L weights); default resolution 384; fine-tuned at 512 (Colab, 2026-10-20), then 640 (Kaggle, 2026-10-22) | rfdetr 1.11.2 wheel, 2026-10-20 |
| Whisper packet size `[Guessing]` 150–250 B | 245 B for a typical minute (self-check `python -m edge.packet`) | 2026-10-20 |
| PaddleOCR on DVR overlay | `en_PP-OCRv5_mobile_rec` read the burned clock exactly (12:01:05 at t = 65 s), 0.12 s per read | 2026-10-20 |
| Honest-control FP of `unmatched_checkin` | 20–35 % with a fixed 10 % threshold at 90 % door recall → replaced by a binomial test against the *measured* recall: 1/120 | redteam sims, 2026-10-20 |
| `react-leaflet` licence | Hippocratic-2.1 → rejected | npm registry, 2026-10-20 |
| Edge CPU fps `[Guessing]` | **4.94 fps** on Kaggle's 4 vCPU Xeon 2.0 GHz (door camera, RF-DETR Nano COCO @384 + ByteTrack + all integrity checks, 301 frames, 251 B per packet); was 2.3 on Colab's 2 vCPU; target-PC figure still to measure | `data/work/cpu_benchmark.json`, Kaggle 2026-10-22 |
| Door P/R (MEVA G420, ±4 s) | at `door_min_frames` 2: entries **P 1.000 / R 0.905** (42 GT); exits on the 42-exit clip **P 0.912 / R 0.756**; any-direction 1.000 / 0.955 at 720p, 0.949 / 0.841 in low light. Was entries 0.977 / 1.000, exits P 0.25 on 2 GT (Colab 2026-10-20) | ACCURACY_REPORT, Kaggle T4 2026-10-22 |
| Count MAE (SCUT-HEAD Part A test, 500 images, mean 34.4 heads) | 640 px model, deployed ONNX via `edge.detect`: **1.52 @ thr 0.35** (target 1.5; PyTorch 1.618 @ 0.40, early stop at epoch 45/80). Was 2.21 for the 512 px model. Per-frame person count on the MEVA door clip: 0.887 | `data/work/head_onnx_check.json`, Kaggle T4 2026-10-22 |
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

## Accuracy changes, 2026-10-22 (Kaggle run)

Made after reading the 2026-10-20 report against the PROMPT §14 targets. Each is a fix of a modelling error or a
rule made consistent with its sibling, not a threshold moved to pass a test. The two marked † were changed after
seeing R2b / R3b fail, and are listed so a reader can discount them. Numbers: ACCURACY_REPORT of the Kaggle run.

| Change | Why |
|---|---|
| Head model fine-tuned at **640 px** (was 512); score threshold picked on the **Part A (classroom) images of valid** (was all of valid, half web images) | head-count MAE 2.2 vs target 1.5; back-row heads are a few pixels at 512; deployment domain is classroom CCTV |
| Door **crossing hysteresis** `door_min_frames` (supervision `minimum_crossing_threshold`), chosen by `eval.robustness --door-sweep` on the **42-exit** G420 11:15 clip; the busy clip's entries stay held out | exit precision 0.25 came from people stepping over the line and turning back; and it was measured on only 2 GT exits — the annotated exit clip was downloaded but never evaluated |
| Red-team door noise **per direction**: entries from measured entry P/R, exits from the exit clip at the deployed `door_min_frames`; false exits injected | the simulator used any-direction precision (0.863, dragged down by false exits) for entries: ~14 % phantom entries instead of ~2 %, which "explained" proxy check-ins (R2b) |
| † `checkin_then_leave`: 10 % floor **+ Poisson test** against the measured false-exit rate (was a fixed 20 % cut) | same structure as `unmatched_checkin`; a walk-out is evidence only if door errors cannot explain it — so the flag depends on measured exit quality, and stays silent on noisy doors |
| † `unmatched_checkin` floor is `>=` 10 % (was `>`) | documented as a minimum share; exactly 3/30 could never flag |

### Results of the 2026-10-22 run, and fixes found in the dashboard click-through

Fraud FN **13.1 %** (was 21.9 %; target 10 %), honest FP **0.8 %** (1/120, N3). Every blatant scenario R1–R9 is caught.
The remaining FN is almost all **R2b** (3 of 30 absent, 19/20 missed): with door entry recall 0.905, ≈ 3 of 30 genuine
trainees are expected to have no detected entry anyway, so 3 proxies cannot be told apart from detector misses by the
door alone. This is the detectability floor of one door camera, not a threshold to move.

Found by running `docker compose up` and clicking through (2026-10-22), not after any test failure:

| Fix | Why |
|---|---|
| ₹ at risk sums `unverified_trainee_hours` of `DISCREPANCY` sessions only | honest centres with 0 flags showed ≈ ₹3.4k from sub-threshold late arrivals |
| H3 `inspection_shadow` and `asset_missing` labels come from their own input rows | both took the centre's `mock` label and fell through to "measured" on simulated series |
| Overview "Data gaps" counts open `data_gap` flags | it counted uplink-outage rows only and showed 0 next to five centres with data-gap flags |
| Demo seed: honest measured centres claim room peak **minus the scheduled trainer** | the claim included the trainer, so honest TC0421 got `trainee_hours_gap` (claimed 1.33 vs observed 1.0 trainee-h). Its gap is still near the 20 % line, because the 5-min MEVA arrival clip fills during the session; a real 1-h class would be far below it |
| Fleet page: a model is available when pinned in `models/checksums.txt` (copied into the cloud image) | the cloud container never holds the ONNX files (they run on the edge), so both models always showed "unavailable" |

### Changes of 2026-10-22 afternoon (second Kaggle run)

| Change | Why |
|---|---|
| Head ONNX threshold and SAHI tile chosen on SCUT-HEAD Part A **valid** (the fine-tune's seeded split, no training images), MAE reported on **test**; `lab_room.yaml` gets the chosen setting | the earlier "1.52" was test MAE at 0.35, a threshold picked for the 512 px model; valid picks 0.40 for the 640 px model, where test MAE was 1.64. Reporting the test-best threshold is choosing on test |
| † `unmatched_checkin` uses the room camera as a second witness: peak trainee occupancy vs the claim, tested against the **measured room-level count bias** (SD of per-image relative error on SCUT-HEAD), Fisher-combined with the door binomial test when room data exists | R2b (3 of 30 absent) is invisible to one door camera (see above). Made after seeing R2b fail, hence †. The simulator now draws one count bias per session from the same measured SD: per-sample noise alone averaged out over a session and would have made any occupancy test look far better than it is |
