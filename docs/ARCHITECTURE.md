# SAKSHI architecture — start here

SAKSHI turns passive CCTV in government-funded skilling centres into **ranked, explainable exceptions** for scheme
monitoring officers, without identifying anyone. The build contract is [`PROMPT.md`](../PROMPT.md); this file says
where each part of it lives. Deviations from the prompt's letter are in [`DECISIONS.md`](DECISIONS.md).

## 1. The flow in one picture

```
 CENTRE (edge, CPU)                                                   CLOUD                          BROWSER
 ┌──────────────────────────────────────────────────────────┐   ┌──────────────────────────────┐   ┌──────────────┐
 │ edge/ingest   RTSP | DVR folder | MP4 → (frame, wall t)    │   │ cloud/ingest  verify Ed25519, │   │ dashboard/   │
 │ edge/detect   RF-DETR Nano ONNX (person / head) [+tiling]  │   │   hash chain, seq → gaps      │   │ Next.js EN/HI│
 │ edge/track    ByteTrack, IDs reset every session           │   │   expand → door_events,       │   │ risk queue → │
 │ edge/zones    LineZone(door) PolygonZone(room/trainer/asset)│  │   occupancy, integrity, hashes│   │ case file →  │
 │ edge/events   per-minute: entry/exit offsets, occupancy    │   │ cloud/sidh_mock (MOCK data)   │   │ batch H1 →   │
 │ edge/integrity frozen·covered·moved·OCR clock·pHash loop   │──▶│ cloud/analyze → engines:      │──▶│ evidence →   │
 │ edge/assets   OWLv2 discovery · DINOv2 identity (15 min)   │   │   H1 reconcile  H2 registry   │   │ review       │
 │ edge/privacy  face blur before any image leaves            │   │   H3 shadow  S1/S2 assets     │   │ inspector    │
 │ edge/evidence per-camera OK / INSUFFICIENT                 │   │   S3/S4 risk → flags          │   │ fleet, calib │
 │ edge/packet   Whisper/Normal, canonical JSON, Ed25519, chain│  │ cloud/cases  human review     │   │ accuracy     │
 │ edge/outbox   SQLite store-and-forward → HTTPS / MQTT QoS1 │   │ cloud/api    FastAPI + JWT    │   │ privacy/audit│
 └──────────────────────────────────────────────────────────┘   └──────────────────────────────┘   └──────────────┘
        ▲ signed server time in every ack (clock check)               Postgres+Timescale | SQLite
```

## 2. Repository map

| Path | What it is | Key entry points |
|---|---|---|
| `PROMPT.md` | the build contract (copied verbatim) | — |
| `edge/` | per-camera pipeline (Python 3.11+, CPU) | `python -m edge.run --camera edge/cameras/X.yaml --uplink http://host:8000` |
| `edge/cameras/*.yaml` | camera configs: role, source, door line, zones, timestamp ROI, detector | schema in `edge/zones.py` docstring |
| `edge/calibrate.py` | local calibration web UI (snapshot never leaves the device) | `python -m edge.calibrate --camera …` |
| `cloud/db.py` | all tables of PROMPT §9 (+ `reconciliations`) | `init_db()` |
| `cloud/ingest.py` | packet verification + expansion into observation rows | `ingest(db, packets)` |
| `cloud/engines/` | pure functions, no DB: `reconcile` (H1), `registry` (H2), `shadow` (H3), `assets` (S1/S2), `risk` (S3/S4) | unit tests in `tests/test_engines.py` |
| `cloud/analyze.py` | builds engine inputs from the DB, upserts flags (idempotent, keeps review status) | `run_centre(db, id)` |
| `cloud/cases.py` | review workflow: confirm / false alarm / request response / centre response / appeal | `act(...)` |
| `cloud/sidh_mock.py` | MOCK Skill India Digital Hub adapter + password hashing | `load(db, seed)` |
| `cloud/api.py` | REST API (PROMPT §10), JWT roles, MQTT bridge, hourly retention purge | `uvicorn cloud.api:app` |
| `cloud/demo_seed.py` | the demo story (PROMPT §22) through the real engines | `python -m cloud.demo_seed --fresh` |
| `redteam/` | `scenarios.yaml` (R1–R9, subtle R1b–R3b, N1–N3), `generators.py`, `runner.py` | `python -m redteam.runner prepare|video|sims` |
| `eval/` | `metrics.py` (D4), `robustness.py`, `report.py` → `docs/ACCURACY_REPORT.md`; `robustness.py --door-sweep` | run on the GPU VM (`scripts/gpu_runs.sh`) |
| `models/` | `finetune_heads_kaggle.py` (RF-DETR head fine-tune, Kaggle T4; Colab notebook kept), `download.py`, `checksums.txt` | no weights in git |
| `data/` | `download.py` (MEVA, Commons), `sanctioned_inventory/` (mock QP lists), `demo/` (users, measured packets) | `raw/`, `work/`, `edge_state/` are git-ignored |
| `dashboard/` | Next.js 16 static export, Tailwind 4, recharts; `i18n/{en,hi}.json` | `npm run build` |
| `deploy/`, `docker-compose.yml` | Timescale, Mosquitto, cloud, dashboard (nginx) | `docker compose up` |
| `scripts/check_licenses.py` | fails on AGPL/GPL/Hippocratic or banned packages (CI) | `make licences` |
| `tests/` | engines, chaos (2 h outage, forged/reordered/duplicate packets) | `make test` |

## 3. Data contracts

**Whisper packet** (one per camera per minute, ~250 B; `edge/packet.py`):

```json
{"c":"TC0421","cam":"CAM-DOOR","t":1792391400,"seq":12,"tier":"W","prev":"9f2c…16hex",
 "in":3,"out":1,"ei":[4,31,50],"eo":[12],"occ":17,"oc":[16,17,17,18,17,17],"tr":1,
 "use":{"LATHE-01":0},"aid":{"LATHE-01":0.91},"clk":-4.0,"ph":"c3d1f0a29b7e4411",
 "ev":"OK","flags":["loop"],"q":143.2,"na":["ocr"],"sig":"<ed25519 b64>"}
```
`ei`/`eo` = second offsets of door entries/exits inside the minute (H1 needs event times); `oc` = six 10-s
occupancy samples; `clk` = OCR clock − device clock (s); `ph` = pHash of a people-present keyframe; `ev` = camera
evidence; `na` = modules unavailable (fail loudly); `prev` = SHA-256 prefix of the previous packet incl. its sig.
**Normal** tier adds `thumb` (96×54 face-blurred JPEG, anomalies only). **Audit** tier = sealed clips on the edge.

**Labels.** Every observation/flag row has `label ∈ {measured, simulated, mock}`. Measured = real model output from
a signed packet; simulated = red-team generator; mock = stand-in government data (SIDH, QP lists, ₹ rate).

**Evidence level** (per batch session, `edge/evidence.py::batch_level`): FULL = door + room cameras OK;
REDUCED = room only (H1 falls back to occupancy signals); INSUFFICIENT = tamper / low quality / data gap → the
engine abstains (`INSUFFICIENT_EVIDENCE`) and a `data_gap` flag is raised — silence is never compliance.

## 4. Engines (what fires and why)

| Flag | Engine | Rule (defaults in code) |
|---|---|---|
| `unmatched_checkin` | H1 | Hungarian match check-ins ↔ door entries within ±300 s; flag if unmatched share > 10 % **and** binomially improbable given the measured door recall (p < 0.01) |
| `burst` | H1 | ≥ 10 check-ins in 60 s |
| `checkin_then_leave` | H1 | net mid-session exits (outside breaks, first/last 15 min ignored) ≥ 20 % of check-ins |
| `inflation` | H1 | 95th-pct trainee occupancy (minus trainers, breaks excluded) < 80 % of check-ins |
| `ghost_session` | H1 | > 20 % of check-ins while the room is empty |
| `trainee_hours_gap` | H1 | claimed trainee-hours − area under occupancy > 20 % → also ₹-at-risk |
| `clock_drift`, `clock_non_monotonic` | H2 edge | OCR'd DVR clock off by > 120 s, or not advancing ≈ 1 s/s |
| `loop` | H2 edge | people-present keyframe pHash within 6 bits of another day's (7-day index) |
| `cross_centre_duplicate` | H2 cloud | same pHash (≤ 6 bits) from two centres |
| `frozen`, `covered`, `moved` | H2 edge | frame diff < noise floor for > 20 s · Laplacian < 22 or uniform histogram · ORB match ratio < 0.25 |
| `ornamental_asset` | S1 | OAI ≥ 0.95 on ≥ 10 practical days |
| `asset_swapped` | S2 | DINOv2 cosine < 0.75 on 2 consecutive scans |
| `asset_missing` | S1 | observed < sanctioned (QP list × enrolment) |
| `inspection_shadow` | H3 | permutation test (score higher within ±3 d of audits, p < 0.05) **and** PELT change points near ≥ half the audits |
| `data_gap` | ingest/H1 | seq gap, chain break, or occupancy coverage < 70 % of a scheduled session |

Integrity Score (0–100) = 100 − Σ weight × severity over the H1 signals computable at that evidence level
(weights in `cloud/engines/reconcile.py::WEIGHTS`). Centre risk (0–100) = saturating combination of open flags
× evidence discount (REDUCED 0.6), top-3 reasons listed (`cloud/engines/risk.py`).

## 5. Running

**Rule for this project: nothing executes on the developer laptop** (DECISIONS D-9). Everything runs on a GPU VM
(Kaggle T4 since 2026-10-22; Colab before):
1. `models/finetune_heads_kaggle.py` (kernel `sakshi-finetune`): SCUT-HEAD → RF-DETR Nano head model at 640 px,
   metrics, ONNX export of head + COCO person models → kernel output `out/`.
2. `scripts/kaggle_pipeline.py` (kernel `sakshi-pipeline`, fine-tune attached) runs `scripts/gpu_runs.sh`: py3.11
   venv with pinned deps → `data/download.py` → models → tests → `redteam.runner prepare` → head ONNX check → CPU
   benchmark → `eval.robustness --door-sweep` (sets `door_min_frames`) → `redteam.runner video` (exports
   `data/demo/packets.jsonl`) → `eval.robustness` → `eval.metrics` → `eval.report` → `scripts.demo_check`.
   `kaggle kernels output anonymousguy011/sakshi-pipeline` returns the result files with their repo paths.

Demo machine (when allowed): `docker compose up` (seeds the demo on first start) → http://localhost:3000,
accounts in `data/demo/users.yaml`. Optional live edge: `make edge-demo`.

## 6. Where each PROMPT requirement is

See [`REQUIREMENT_AUDIT.md`](REQUIREMENT_AUDIT.md) — every PS sentence and D1–D5 mapped to module + test.

## 7. Conventions for whoever edits next

- Engines stay pure (inputs = numbers/lists, outputs = dicts with `flag`, `severity`, `detail`); DB access only in
  `cloud/analyze.py` / `cloud/api.py`.
- New flag type → add to `FLAG_WEIGHT` (risk), `NEXT_STEP` (analyze), `FRAUD_FLAGS` (eval) and the dashboard text.
- Any image leaving the edge goes through `edge/privacy.py`. No face recognition, no person embeddings, no
  cross-session IDs, no behaviour scoring, no automatic penalties.
- Pin every dependency; run `scripts/check_licenses.py` after adding one; record it in `THIRD_PARTY_LICENSES.md`.
- Never hand-edit `docs/ACCURACY_REPORT.md`; regenerate it.
