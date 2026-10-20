# Decisions and verified facts

Every `[Likely]` / `[Guessing]` item from `PROMPT.md`, plus every place the build deviates from the prompt's letter,
with the reason. Numbers marked *pending* are filled from Colab runs (`eval/colab_pipeline.ipynb`).

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
| D-9 | All runs | nothing executes on the developer laptop: training, inference, eval, red-team run in Google Colab | user rule 2026-10-20; edge fps is therefore measured on Colab CPU (reported with CPU model) |
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
| Edge CPU fps `[Guessing]` | *pending* (Colab CPU) | — |
| Door P/R | *pending* | — |
| Count MAE (SCUT-HEAD Part A, MEVA door clip) | *pending* | — |
| ₹ per trainee-hour `[Likely]` | **assumption ₹50** until a PMKVY cost-norm citation is added (`cloud/engines/risk.py`) | — |
| QP codes for demo trades `[Likely]` | SSC/Q2212, AMH/Q0301, ELE/Q3104 — **mock**, to verify against NSDC QP documents | — |
| SIDH export format `[Likely]` | not public → mock adapter defines the expected shape (`cloud/sidh_mock.py`) | — |
| Raspberry Pi 5 tier `[Guessing]` ₹15–20k | not verified; no hardware promise made | — |

## Door line (G420)

Derived from MEVA ground-truth trajectories: entering people's feet move from ≈(1280, 750) at the right-hand doors to
≈(1160, 870) (1920×1080 frame). The line `[[1150,700],[1400,950]]` (×2/3 for 720p → `[[767,467],[933,633]]`) cuts
that path perpendicularly. `entry_direction` is checked against the 43 GT entries in the first Colab run.
