# BUILD PROMPT — SAKSHI: Anonymous, Tamper-Evident Compliance Monitoring for Skilling Centres
### Smart India Hackathon 2026 · Problem Statement SIH26245 · MSDE · Software · Smart Education

> **How to use this file:** paste the whole file into Claude Opus (Claude Code / agentic session) as the task prompt, or save it as `PROMPT.md` / `CLAUDE.md` at the repo root. Everything below the line is addressed to the building agent.
>
> **Confidence tags:** `[Certain]` verified from a source or from code, `[Likely]` strong inference, `[Guessing]` an estimate the agent must verify or replace with a measured value.

---

## 0. Your role and mission

You are the lead engineer building **SAKSHI**, a working prototype for SIH26245. Build a complete, runnable system (edge pipeline, cloud backend, dashboard, red-team simulator, evaluation suite and the required documents) that:

1. satisfies **all five** deliverables of the problem statement (Section 2), and
2. clearly beats the **12 public competitor repos** for this PS (Section 4) on the three headline novelties (Section 5), while matching them on the baseline features.

Work in the build order of Section 18. After each milestone, run its acceptance checks and fix failures before moving on. When a fact in this prompt is marked `[Likely]` or `[Guessing]`, verify it (check the docs, measure it) and record the true value in `docs/DECISIONS.md`.

---

## 1. Non-negotiable rules

1. **No competitor code.** Twelve public repos exist for this PS. None has a licence, so they are all rights reserved `[Certain]`. You may use the *ideas* summarised in Section 4. Do not clone, copy, paraphrase or port their code, prompts, UI or text.
2. **Permissive licences only:** MIT, Apache-2.0, BSD, ISC.
   - **Banned:** AGPL (Ultralytics YOLOv8/11/26, BoxMOT) and GPL (YOLO-World).
   - Before adding any dependency, check its licence *and its model weights' licence*. Record each in `THIRD_PARTY_LICENSES.md`.
3. **Privacy:**
   - No face recognition. No identity embeddings. No persistent person IDs: tracker IDs reset every session.
   - Faces are blurred **on the edge** before any image leaves the device.
   - No engagement or behaviour scoring.
4. **No automatic penalties.** The system flags, explains and ranks; a human officer decides. Every flag has "confirm / false alarm / centre response".
5. **Honesty labels.** Every number on screen is labelled as one of: `measured` (real model output), `simulated` (red-team or seeded data), or `mock` (stand-in for a government system). Never mix them silently.
6. **Abstain when evidence is weak.** If camera quality, coverage or integrity is insufficient, output `INSUFFICIENT_EVIDENCE`, not `COMPLIANT` or `NON_COMPLIANT`.
7. **Silence is not compliance.** Missing data (power cut, offline, camera down) shows as a data gap, never as "OK".
8. Pin every dependency version. Everything must run with `docker compose up` plus one documented edge command, fully offline after setup.

---

## 2. The problem statement and the five deliverables

**PS text (summary):** Government-funded skilling schemes rely on dispersed, empanelled training centres that are physically inspected only periodically. Two integrity risks follow:
- attendance records that don't match actual physical presence;
- approved infrastructure (equipment, seating, workshops) that isn't consistently available between inspections.

Existing cameras only record passively. The system must process live or periodic camera feeds and:
- estimate attendance and cross-check it against the centre's records;
- detect presence/absence and **apparent operability** of sanctioned infrastructure;
- flag discrepancies to a monitoring dashboard instead of requiring manual review of footage;
- operate under rural bandwidth and camera-quality limits;
- preserve privacy using aggregate presence detection instead of facial identification. `[Certain]`

**Dataset:** "NA – sample/dummy training-centre camera footage to be provided for hackathon evaluation." Do not depend on it. Build our own data (Section 13).

| # | Deliverable (from PS) | What you must ship | Acceptance criteria |
|---|---|---|---|
| D1 | Working video-analytics pipeline on sample/simulated centre footage | `edge/` pipeline: ingest → detect → track → zones → events → integrity → signed packets | Runs on recorded MP4 and RTSP; processes ≥ 1 fps per camera on a laptop CPU; produces packets for all red-team clips |
| D2 | Attendance-discrepancy and infrastructure-compliance dashboard for scheme monitoring units | `dashboard/` (Next.js) + `cloud/` (FastAPI) | Risk queue, centre case file, evidence view, inspector view, model-health view; English + Hindi; every flag explained |
| D3 | Privacy-preserving design note | `docs/PRIVACY_DESIGN.md` | States exactly what is and isn't identified, what leaves the centre, retention, access, DPDP alignment, threat model |
| D4 | False-positive / false-negative accuracy assessment on the demo dataset | `eval/` + `docs/ACCURACY_REPORT.md` (auto-generated) | Per-scenario confusion matrices for R1–R9 and N1–N3, count MAE, door-event P/R, robustness curves |
| D5 | Low-bandwidth deployment mode | Tiered packets + store-and-forward + `docs/LOW_BANDWIDTH.md` | Measured bytes per hour per camera for each tier; survives 2 h of disconnection with no data loss |

---

## 3. Government context the system must fit into

| Existing system / fact | Source | How SAKSHI relates |
|---|---|---|
| PMKVY 4.0 sets up a **CCTV Command Centre** with non-compliance alerts, plus **virtual verification** | PMKVY 4.0 Guidelines `[Certain]` | We don't replace the command centre. We turn it from *watching video* into *reviewing ranked exceptions* |
| **Virtual verification** via a TC self-assessment app; centres rated "poor" get a physical inspection, which costs money | NSDC RFP `[Certain]` | Our risk queue tells inspectors **where to go first** |
| Attendance via **Aadhaar-enabled biometric (AEBAS)**, recently replaced by **face authentication**; payments to centres linked to attendance | MSDE / OpenGov Asia `[Certain]` | The face-auth / AEBAS check-in log is our **input to verify**. We don't do identification ourselves |
| **CAG audit:** same photograph used at different locations as training evidence; biometric devices missing or non-functional in at least 24 centres | Moneylife report on CAG audit `[Certain]` | Motivates the cross-centre duplicate registry and feed-integrity checks |
| **178 TPs/TCs blacklisted under PMKVY 4.0**; centres found closed during working hours while biometric attendance was recorded; alleged AEBAS manipulation | NextIAS `[Certain]` | Motivates event-level attendance proof (H1) |
| Programme data lives in **Skill India Digital Hub (SIDH)** | `[Likely]` | Build a **mock SIDH adapter** (batches, timetable, enrolment, check-ins), clearly labelled `mock` |
| **DPDP Rules 2025** notified Nov 2025 with phased rollout | Wikipedia / law-firm notes `[Certain]` | Privacy note maps each data flow to purpose, minimisation, retention and notice |
| Equipment requirements per job role are defined in **Qualification Pack (QP) / model curriculum** documents | `[Likely]` (one competitor uses a QP-code equipment BOM) | Sanctioned inventory = QP equipment list × batch size, stored per centre |
| **Payouts are linked to outcomes/attendance**; cost norms per training hour exist | `[Likely]` | ₹-at-risk = unverified trainee-hours × configurable rate. Cite the source if found, else label it an assumption |

---

## 4. Competitive landscape — 12 public repos for SIH26245 (ideas only)

All were shallow-cloned and their **source code** was searched feature by feature. Every one was pushed between 3 and 18 Oct 2026. **None has a licence.** `[Certain]`

| Repo | Approach (summary) | Good idea to learn from | Weakness we exploit |
|---|---|---|---|
| syedrahmanghouse/centre-watch-platform | Local platform; tiled person detection + duplicate removal; YOLO-World inventory; pose "seated" geometry | Tiling for small/distant people; fail loudly if a model is missing | Ultralytics/YOLO-World (AGPL/GPL); no event reconciliation; no clock checks |
| Mannjain26/Drishti | FastAPI + Supabase; **face recognition** (YuNet + SFace); red-team scenarios incl. looped/frozen footage; Merkle audit | Numbered red-team scenarios with a benchmark runner | Face recognition goes against the PS privacy line |
| Roshani-patil07/skill_sentinel | Large full stack; YOLOv8 + ByteTrack; claims-vs-headcount; risk score; WhatsApp alerts | Thorough docs (architecture, privacy, QA, security) | Mismatch logic largely in frontend mock data |
| Santhosh-006-30/SkillGaurd-AI | Reconciliation endpoint; "activity observed / operational status uncertain" labels | Conservative operability wording | Count-level reconciliation only |
| anveshreddy-techin/real-ai | Next.js + Python; **equipment BOM per QP code / sector**; snapshot feeds | **Use official per-job-role equipment lists as the sanctioned inventory** | Ultralytics (AGPL); no event-level proof |
| varun16-dev/Evidence-Intelligence | "Detection confidence ≠ decision confidence"; Evidence Sufficiency Engine with hard vetoes (e.g. Laplacian < 22 → ABSTAIN) | **Abstain when evidence is weak** | Ultralytics; no reconciliation against check-ins; no cross-centre registry |
| Donomite101/Aicameradetection | Edge config per camera with ROI polygons; custom Roboflow dataset (CC BY 4.0) | Per-camera YAML config with ROIs | Ultralytics; generic |
| tamilselvan840/SIH-project | Browser-only ONNX; **dHash duplicate evidence**; demo-mode labelling | "Live model vs demo" labels | Duplicates checked only within one store; browser face-api |
| Himanshu-hub-oss/CENTRAI | YOLOv8 count; engagement classifier; Isolation Forest | Requirement-audit doc | Engagement scoring is beyond scope and a privacy risk |
| tgnaneshwar007-cell/skillwatch-ai | CRUD dashboard (5th at its internal round) | — | Little AI |
| dharanitham1210-lang/TrustCentre | README only | — | No code |
| smilingmerchant/skill-centre-compliance-monitor | PDFs: ESP32 rotating room code + face match + liveness | "Works without CCTV" fallback idea | Hardware-heavy; face match |
| (8+ more likely exist; 176+ ideas were submitted) | — | — | Assume baseline features are common |

### 4.1 Feature matrix — what is taken vs open

| Feature | Seen in competitor code? | Our stance |
|---|---|---|
| Person detection + headcount | All | Baseline (do it better: heads + tiling + MAE report) |
| Open-vocabulary equipment detection | Yes (centre-watch, real-ai) | Baseline (do it with Apache models + identity embeddings) |
| Loop/frozen-feed checks | Yes (Drishti, Evidence-Intelligence) | Baseline → **extend** with OCR clock + cross-day + cross-centre |
| Red-team scenarios | Yes (Drishti) | Baseline → **extend** to R1–R9 + honest controls |
| Signed/hashed evidence | Common | Baseline (Ed25519 per packet + hash chain) |
| Claims-vs-headcount | Count-level only | **Replace** with event-level H1 |
| Duplicate hashing | Within one store only | **Extend** to cross-centre registry |
| Abstain on weak evidence | Yes (Evidence-Intelligence) | **Adopt and improve**: Evidence Level per decision (Section 5.3) |
| QP-based equipment BOM | Yes (real-ai) | **Adopt**: sanctioned inventory from QP lists |
| **Hungarian matching of check-ins ↔ door crossings** | **Not found in any** | **Headline H1** |
| **OCR of DVR timestamp vs signed server time** | **Not found in any** | **Headline H2** |
| **Change-point "inspection-shadow" detector** | **Not found in any** | **Headline H3** |
| Usage-hours operability (OAI) + same-asset identity | Only simple "activity observed" | **Supporting S1–S2** |

---

## 5. Novelty — what makes SAKSHI better than all of them

### 5.1 Headline novelties

**H1 — Event-level, anonymous attendance proof.**
Every check-in in the face-auth/AEBAS log must be explained by a **physical door-entry event** seen by CCTV within a window (default ±300 s, configurable).
- Match check-ins to anonymous `LineZone` entry events with the **Hungarian algorithm** (`scipy.optimize.linear_sum_assignment`).
- Combine with the **occupancy curve** (count every 10 s) and **exit events**.

Signals:
- `unmatched_checkin`: check-in with no plausible physical entry (bulk/proxy marking).
- `burst`: ≥ k check-ins within s seconds (bulk marking).
- `checkin_then_leave`: matched entry, then a matching exit within m minutes, and occupancy drops.
- `inflation`: peak occupancy never reaches the claimed count.
- `ghost_session`: check-ins while occupancy ≈ 0.
- `trainee_hours_gap`: claimed trainee-hours vs the area under the occupancy curve (minus trainers, minus breaks, timetable-aware).

Output: **Attendance Integrity Score (0–100)** per batch per day, with an evidence list. Nobody is identified.

**H2 — Clock-proof, fleet-aware feed integrity.**
- **OCR clock check:** read the DVR's burned-in timestamp (PaddleOCR) every 30–60 s inside a calibrated ROI. Compare it with the device's NTP time and the last **signed server time**. Flag `clock_drift` (|Δ| > 120 s, configurable) and `clock_non_monotonic` (doesn't advance ≈ 1 s/s). A replayed recording carries a stale or jumping clock.
- **Cross-day loop detection:** pHash of keyframes **only when people are present** (an empty room legitimately looks the same daily), against a 7-day local index. Flag identical people-configurations on different days.
- **Cross-centre duplicate registry (cloud):** the same keyframe hash arriving from two different centres → `cross_centre_duplicate`.
- **Physical tamper:** frozen (frame difference below the sensor-noise floor for > T s), covered/defocused (Laplacian variance, uniformity), moved (ORB match vs a reference frame).

**H3 — Inspection-shadow detector.**
- Run change-point detection (`ruptures`, PELT) on each centre's daily Integrity Score and OAI series, aligned with inspection dates.
- Flag centres whose behaviour shifts repeatedly within ±3 days of audits.
- Also report a judge-friendly permutation test: mean score inside audit windows vs outside, with a p-value.

### 5.2 Supporting novelties

| ID | Feature | Definition |
|---|---|---|
| S1 | **Ornamental Asset Index (OAI)** | `OAI = 1 − observed_interaction_seconds / scheduled_practical_seconds`, per asset. Interaction = person inside the asset zone **and** motion inside the asset region (plus screen-on for monitors) |
| S2 | **Same-asset identity** | At registration, store a DINOv2 embedding per sanctioned asset (crop). Daily, compare crops: cosine similarity below a threshold → `asset_swapped`. Catches rented-for-inspection equipment |
| S3 | **₹-at-risk** | `unverified_trainee_hours × rate_per_trainee_hour` (config; cite the cost norm or label it an assumption) |
| S4 | **Explainable risk queue** | Weighted, explainable centre risk; each item lists its top 3 reasons with links to evidence |
| S5 | **Tiered packets** | Whisper / Normal / Audit modes with measured bytes per hour (Section 11) |
| S6 | **Red-team simulator** | Generates R1–R9 fraud and N1–N3 honest controls; drives D4 automatically |
| S7 | **Camera placement & calibration kit** | Setup UI to draw the door line, room polygon, asset zones and timestamp ROI; prints a one-page placement standard |

### 5.3 Adopted-and-improved ideas from competitors

- **Evidence Level (improves Evidence-Intelligence's "abstain"):** every decision carries `evidence_level ∈ {FULL, REDUCED, INSUFFICIENT}`.
  - FULL = door camera + room camera + integrity OK.
  - REDUCED = room camera only (no door events, so H1 falls back to occupancy-only).
  - INSUFFICIENT = tamper, low quality, or data gap → abstain.
  - The dashboard shows evidence level next to every flag, and risk scoring discounts REDUCED evidence.
- **QP-based sanctioned inventory (from real-ai):** per job role, required equipment from QP / model-curriculum lists, scaled by batch size. Store it as `sanctioned_inventory` with a source note. If the official list can't be fetched, create a clearly labelled mock for 3 demo trades (Computer/IT lab, Tailoring, Electrician/Welding workshop).
- **Fail loudly (from centre-watch):** if a model or weights are missing, refuse to run that module and show "module unavailable". Never silently substitute.

### 5.4 Explicitly out of scope

Face recognition, engagement/emotion scoring, automatic penalties, cloud video streaming, IoT/power sensors (one future-work slide only), ESP32 room beacons (future work only).

---

## 6. Technical decisions — compared, with the chosen option

> Benchmarks below come from the RF-DETR README (T4 GPU, TensorRT FP16, batch 1). **Edge CPU speed will be far lower.** Measure on the target hardware and record it in `docs/DECISIONS.md`.

### 6.1 Detector

| Option | Licence | COCO AP50:95 / latency (T4) | Verdict |
|---|---|---|---|
| **RF-DETR Nano / Small** | Apache-2.0 | N 48.4 @ 2.3 ms · S 53.0 @ 3.5 ms `[Certain]` | **Choose** (export to ONNX; run with ONNX Runtime / OpenVINO on CPU) |
| D-FINE N / S | Apache-2.0 | N 42.7 @ 2.1 ms · S 50.6 @ 3.5 ms `[Certain]` | Backup if RF-DETR export or CPU speed fails |
| LW-DETR T/S | Apache-2.0 | T 42.9 @ 1.9 ms · S 48.0 @ 2.6 ms `[Certain]` | Second backup |
| YOLO11 / YOLO26 (Ultralytics) | AGPL-3.0 | YOLO26-N 40.3 @ 1.7 ms `[Certain]` | **Banned** (licence) |
| YOLOX-nano | Apache-2.0 | Older, lower accuracy `[Likely]` | Outdated |
| SAM 3 | see its licence | Strong open-vocab, ~850 M params `[Certain]` | Too big for edge; optional offline tool for asset registration only |

### 6.2 What to detect

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| Full-body person | Works out of the box | Bodies hidden by desks/benches | Doors, workshops, standing areas |
| **Head detection** (fine-tune RF-DETR on SCUT-HEAD + own frames) | Heads stay visible in seated rooms | Needs fine-tuning; check SCUT-HEAD terms | **Seated classrooms/labs** |
| + **SAHI** tiling | Small back-row heads | ~2–4× compute `[Likely]` | Run at 0.5–1 fps for occupancy |
| Point-based crowd counting (P2PNet) | Very dense rooms | Licence/weights must be checked; no boxes for tracking | Optional fallback for > 60 people |

### 6.3 Attendance counting

| Option | Measures | Weakness | Verdict |
|---|---|---|---|
| Single-frame headcount | One moment | Easy to stage | Not enough alone |
| **Occupancy curve** (every 10 s, median-filtered) | Presence over time | Can't link to check-ins | **Use** |
| **Door line-crossings** (supervision `LineZone` + tracker) | Timestamped entry/exit | Needs a door camera | **Use → enables H1** |
| Face recognition | Identity | Against the PS privacy line; duplicates govt face auth | **Banned** |

**Chosen:** occupancy curve + door events + Hungarian matching + timetable awareness.

### 6.4 Tracking

| Option | Licence | Verdict |
|---|---|---|
| **roboflow/trackers — ByteTrack** | Apache-2.0 | **Choose** (fast, `sv.Detections`-native) |
| roboflow/trackers — OC-SORT / BoT-SORT | Apache-2.0 | Try if ID switches at the door are high |
| BoxMOT | AGPL-3.0 | **Banned** |

### 6.5 Equipment presence and identity

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| Closed-set fine-tuned detector | Most accurate | Labels per trade | Only for 3 demo trades, if time allows |
| **Zero-shot: Grounding DINO / OWLv2** (Apache) | Any trade from a text list | Slower, lower precision | **Use for discovery + registration**, run every 10–30 min, not per frame |
| YOLO-World | — | GPL-3.0 | **Banned** |
| **Reference embeddings (DINOv2)** | Verifies the *same* physical asset | One registration crop per asset | **Use for identity (S2)** |

### 6.6 Operability

| Option | Verdict |
|---|---|
| Presence only | Insufficient |
| **Person-in-zone time (supervision `PolygonZone` / time-in-zone) + motion energy inside the asset ROI** | **Choose** (cheap, explainable) |
| Screen-on detection (mean brightness/variance inside monitor boxes) | Add for computer labs |
| Pose keypoints near the machine (RF-DETR keypoint preview, Apache) | Optional; never use AGPL pose models |
| Power/IoT sensors | Out of scope; future-work slide |

### 6.7 Feed integrity

| Check | Method | Cost |
|---|---|---|
| Frozen | Mean absolute frame difference below the noise floor for > T s | Trivial |
| Covered / defocused | Laplacian variance, histogram uniformity, entropy | Trivial |
| Moved | ORB keypoint match ratio vs reference frame | Low |
| **Stale/jumping clock** | PaddleOCR in timestamp ROI vs signed server time; monotonic check | Low (every 30–60 s) |
| **Cross-day loop** | pHash (imagehash) of people-present keyframes vs 7-day index | Low |
| **Cross-centre duplicate** | Cloud hash registry | Low |

### 6.8 Privacy

| Option | Verdict |
|---|---|
| Upload raw video | **Reject** |
| **Edge inference; upload counts + events + face-blurred thumbnails only on anomaly** | **Choose** |
| Track IDs across days | **Reject** (reset every session) |
| **Encrypted local clip retention (7–30 days), released only on a formal audit request** | **Choose** (key held by the state nodal officer; document the procedure) |

### 6.9 Edge hardware tiers

| Tier | Example | Notes |
|---|---|---|
| T0 (demo) | Laptop CPU | Must work: ONNX Runtime CPU, 1 fps per camera |
| T1 | Existing centre PC / NVR box | Preferred: no new hardware |
| T2 | Raspberry Pi 5 + AI accelerator | ~₹15–20k `[Guessing]`; verify model support before promising |

---

## 7. Final architecture

```
┌──────────────────────────────────── EDGE (inside the centre) ─────────────────────────────────────┐
│ Sources: RTSP (live) | DVR file pull (periodic) | MP4 (demo)                                      │
│   → Frame sampler (motion-gated; 1 fps occupancy, 5–10 fps at door ROI)                            │
│   → Detector: RF-DETR (heads/persons) [+ SAHI for room cams]                                      │
│   → Tracker: ByteTrack (session-scoped IDs)                                                       │
│   → Zones (supervision): LineZone(door) · PolygonZone(room) · PolygonZone(asset_i) · trainer zone │
│   → Event builder: entries, exits, occupancy(10 s), asset interaction seconds                     │
│   → Integrity: frozen · covered · moved · OCR clock · pHash keyframes (people present)            │
│   → Asset service (every 10–30 min): OWLv2/Grounding DINO + DINOv2 identity check                 │
│   → Privacy: face blur (deface/CenterFace) on any image; no raw video leaves                       │
│   → Evidence level calculator                                                                     │
│   → Packetizer (Whisper/Normal/Audit) → Ed25519 sign → hash chain → SQLite outbox                  │
│   → Uplink: MQTT (QoS1) or HTTPS batch; store-and-forward; sequence numbers                       │
│   → Encrypted clip ring buffer (7–30 days) for formal audits only                                 │
└──────────────────────────────────────────────┬────────────────────────────────────────────────────┘
                                               │ 2G-tolerant; resumable
┌──────────────────────────────────────────────▼──────────── CLOUD ─────────────────────────────────┐
│ Ingest (FastAPI + Mosquitto bridge) → verify signature + chain + seq → TimescaleDB/Postgres       │
│ Mock SIDH adapter: batches, timetable, enrolment, trainers, check-in logs (labelled "mock")        │
│ Engines:                                                                                         │
│   H1 Reconciliation (Hungarian, burst, leave, inflation, ghost, hours gap) → Integrity Score      │
│   H2 Integrity registry (cross-centre hashes, clock anomalies)                                    │
│   H3 Inspection-shadow (ruptures PELT + permutation test)                                         │
│   S1 OAI · S2 asset identity · S3 ₹-at-risk · S4 risk queue                                        │
│ Case management: flags → review → centre response → officer decision (audit-logged)               │
│ Alerts: dashboard + email/SMS stub                                                                │
└──────────────────────────────────────────────┬────────────────────────────────────────────────────┘
                                               ▼
                       Next.js dashboard (EN/HI): national/state/district → risk queue → case file
```

**Timing defaults** (all configurable): occupancy sample 10 s; door ROI 5–10 fps; integrity every 30 s; OCR every 60 s; pHash keyframe every 5 min when people are present; asset scan every 15 min; Whisper packet every 60 s; reconciliation at the end of each session plus hourly partials.

---

## 8. Module specifications

### 8.1 Edge (`edge/`, Python 3.11)

| Module | Responsibility | Key output |
|---|---|---|
| `ingest/` | RTSP via OpenCV/FFmpeg; reconnect with backoff; file-pull mode for DVR exports; MP4 for demo | Frames + capture timestamps |
| `detect/` | RF-DETR ONNX wrapper; optional SAHI; class map {person, head} | `sv.Detections` |
| `track/` | ByteTrack (roboflow/trackers); reset per session | Track IDs |
| `zones/` | Load camera YAML; LineZone for door; PolygonZones for room, assets, trainer zone | Crossings, in-zone counts |
| `events/` | Entry/exit with timestamps; occupancy series (median over 3 samples); asset interaction seconds | Event records |
| `integrity/` | Frozen, covered, moved, OCR clock, pHash index (SQLite, 7 days) | Integrity events |
| `assets/` | Zero-shot discovery; DINOv2 embeddings; registration flow | Asset presence + identity score |
| `privacy/` | Face blur on any image crop/thumbnail; strip EXIF; never write unblurred images outside the encrypted ring buffer | Safe thumbnails |
| `evidence/` | Compute evidence level per camera per window | FULL/REDUCED/INSUFFICIENT |
| `packet/` | Build tiered packets; canonical JSON; Ed25519 sign (PyNaCl); `prev_hash` chain | Signed packets |
| `outbox/` | SQLite queue; MQTT QoS1 / HTTPS; retry; ack carries signed server time (used by OCR clock check) | Delivery |
| `calibrate/` | Small local web UI: draw door line, polygons, timestamp ROI on a snapshot; save camera YAML | `cameras/*.yaml` |

Camera config example:
```yaml
camera_id: TC0421-CAM2
centre_id: TC0421
role: door            # door | room | workshop
source: rtsp://user:pass@192.168.1.20:554/stream1   # or file:///data/dvr_exports/
door_line: [[412, 120], [415, 470]]
entry_direction: in_is_left_to_right
room_polygon: [[0,0],[1280,0],[1280,720],[0,720]]
trainer_zone: [[900,40],[1270,40],[1270,300],[900,300]]
assets:
  - {asset_id: LATHE-01, label: "lathe machine", zone: [[100,400],[380,400],[380,700],[100,700]]}
timestamp_roi: [20, 20, 360, 40]
timestamp_format: "%d-%m-%Y %H:%M:%S"
```

### 8.2 Cloud (`cloud/`, FastAPI + SQLAlchemy + TimescaleDB)

| Engine | Inputs | Output |
|---|---|---|
| `ingest` | Packets | Verified rows; chain/sequence gap events |
| `sidh_mock` | Seeded batches, timetable, enrolment, trainers, check-ins | Same shape as a plausible SIDH export, labelled `mock` |
| `reconcile` (H1) | Check-ins + door events + occupancy + timetable | Per-batch Integrity Score + signals |
| `registry` (H2) | Keyframe hashes, clock anomalies from all centres | Cross-centre duplicate flags |
| `shadow` (H3) | Daily scores + inspection dates | Shadow flag + p-value |
| `assets` (S1/S2) | Interaction seconds, identity scores, sanctioned inventory | OAI, missing/swapped flags |
| `risk` (S3/S4) | All flags + evidence levels + ₹ rate | Ranked queue with top-3 reasons |
| `cases` | Flags | Review workflow, centre response, decision, full audit log |

Reference implementation for H1 (write your own tests around it):
```python
import numpy as np
from scipy.optimize import linear_sum_assignment

def reconcile(checkins, entries, window_s=300):
    checkins = np.asarray(checkins, float); entries = np.asarray(entries, float)
    if checkins.size == 0: return [], 0.0
    if entries.size == 0:  return list(range(len(checkins))), 1.0
    BIG = 1e6
    cost = np.abs(checkins[:, None] - entries[None, :])
    cost[cost > window_s] = BIG
    rows, cols = linear_sum_assignment(cost)
    matched = {r for r, c in zip(rows, cols) if cost[r, c] < BIG}
    unmatched = [i for i in range(len(checkins)) if i not in matched]
    return unmatched, len(unmatched) / len(checkins)
```

---

## 9. Data model (minimum tables)

`centres`, `cameras`, `batches`, `timetable_slots` (room, start, end, type: theory/practical/break), `enrolments` (counts only), `trainers_schedule`, `checkins` (batch_id, ts; no names in the analytics store), `door_events`, `occupancy_samples` (hypertable), `asset_registry` (asset_id, label, zone, embedding, source), `sanctioned_inventory` (job role / QP code, item, qty, source_note), `asset_observations`, `integrity_events`, `keyframe_hashes`, `packets` (seq, prev_hash, sig, received_at), `data_gaps`, `inspections` (date, outcome), `flags` (type, severity, evidence_level, explanation, links), `cases`, `case_actions`, `audit_log`, `users` (roles: admin, state_monitor, district_officer, inspector, centre_operator).

---

## 10. API contract (minimum)

| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/ingest/packets` | Batch upload of signed packets (HTTPS fallback to MQTT) |
| GET | `/v1/centres?state=&risk_min=` | List centres with risk and evidence level |
| GET | `/v1/centres/{id}/summary` | Integrity Score trend, OAI, integrity events, ₹-at-risk |
| GET | `/v1/batches/{id}/reconciliation?date=` | H1 detail: matched/unmatched check-ins (timestamps only), occupancy curve |
| GET | `/v1/risk-queue` | Ranked centres with top-3 reasons |
| GET | `/v1/flags/{id}` | Evidence: blurred thumbnails, charts, packet signatures |
| POST | `/v1/flags/{id}/review` | Confirm / false alarm / request centre response |
| POST | `/v1/cases/{id}/response` | Centre operator response |
| GET | `/v1/health/fleet` | Camera status, data gaps, model availability |
| POST | `/v1/redteam/run` | Run scenarios; returns metrics (dev only) |

Authentication: JWT with role-based access. Centre operators see only their own centre.

---

## 11. Packet tiers (low-bandwidth mode)

| Tier | Contents | Target size `[Guessing]`, measure it |
|---|---|---|
| **Whisper** | Every 60 s: in/out counts, occupancy, asset seconds, clock drift, integrity flags, seq, prev_hash, sig | ~150–250 B per packet → ~9–15 KB/h per camera |
| **Normal** | Whisper + one 96×54 face-blurred JPEG thumbnail per anomaly + keyframe pHash | Add ~3–6 KB per anomaly |
| **Audit** | Encrypted short clips uploaded overnight and resumable, only on a formal request | MB-scale, scheduled |

Example Whisper packet:
```json
{"c":"TC0421","cam":"CAM2","t":1729412400,"seq":5812,"in":3,"out":1,"occ":17,
 "use":{"LATHE-01":0,"BENCH-03":420},"clk":-4,"ph":"c3d1f0a29b7e4411",
 "ev":"FULL","flags":["loop?"],"prev":"9f2c...","sig":"<ed25519-b64>"}
```
SMS fallback: a compressed daily summary (one SMS) when the data link is down for > 6 h.

---

## 12. Dashboard specification (Next.js + TypeScript + Tailwind; EN + HI)

**Principle: exception-first, not a video wall.** No live video grid by default.

| Page | Contents |
|---|---|
| **National / state overview** | Map of centres coloured by risk (colour-blind-safe palette with shape/icon redundancy); totals: centres monitored, flags open, ₹-at-risk, data gaps |
| **Risk queue** (home for state/district officers) | Ranked list: centre, risk score, evidence level badge, ₹-at-risk, top-3 reasons, last inspection, "assign inspector" |
| **Centre case file** | Integrity Score trend (30 days) with inspection dates marked (H3); batch table; OAI per asset; integrity timeline; sanctioned vs observed inventory; open flags |
| **Batch reconciliation view** (H1) | Occupancy curve with check-in markers (matched = filled, unmatched = hollow), door entry/exit ticks, timetable bands (theory/practical/break), trainer subtraction noted |
| **Evidence viewer** | Blurred thumbnails, clock-drift chart, hash-match explanation ("frame matches Centre TC0198 on 12 Oct"), packet signature verification status |
| **Inspector app (mobile web)** | Today's visits, checklist generated from the flags, field confirmation upload (blurred), offline-capable |
| **Fleet & model health** | Camera online/offline, packet gaps, model availability ("module unavailable"), edge fps |
| **Calibration** | Per-camera snapshot with drawable door line, zones and timestamp ROI |
| **Red-team & accuracy** | Run scenarios; confusion matrices; robustness curves; download the accuracy report |
| **Privacy & audit log** | What data exists, retention timers, who viewed what |

UX rules:
- Every flag shows *what*, *why*, *evidence level*, *how confident* and *what to do next*.
- Labels `measured / simulated / mock` everywhere.
- Keyboard navigable.
- Hindi strings via i18n files.
- No red/green-only encoding.

---

## 13. Data sources

| Need | Source | Notes |
|---|---|---|
| **Own footage (primary)** | Record 2–3 rooms at college: classroom, computer lab, workshop. Fixed CCTV-like angle, door camera + room camera, 1080p/720p/360p, day and evening, DVR-style timestamp overlay ON | Get consent from people filmed; blur in all stored derivatives |
| Head detection fine-tune | **SCUT-HEAD** (classroom surveillance heads) `[Likely]` | Check terms of use; research use `[Guessing]` |
| General persons / crowds | COCO (person), CrowdHuman | CrowdHuman is non-commercial research `[Likely]` |
| Tracking eval | MOT17 | Research use |
| Equipment images | Roboflow Universe datasets (choose CC BY 4.0 / CC0 only, attribute them); own photos of lab equipment | Record each dataset's licence in `DATASETS.md` |
| Sanctioned inventory | QP / model-curriculum equipment lists per job role (NSDC/SSC) `[Likely]` | If unobtainable, a labelled mock for 3 trades |
| Programme data | **Mock SIDH adapter** (batches, timetable, enrolment, trainers, check-ins) | Label `mock`; never imply real government data |
| ₹ rate | PMKVY cost norms per training hour `[Likely]` | Config value with citation, else "assumption" |
| Fraud data | Red-team generator (Section 14) | Label `simulated` |
| Organiser footage | When provided | Run the same eval; report separately |

---

## 14. Red-team scenarios and evaluation (drives D4)

| ID | Fraud | How we stage it | Expected detector |
|---|---|---|---|
| R1 | Bulk check-in, empty room | 25 synthetic check-ins in 40 s; room footage empty | H1 unmatched + burst |
| R2 | Proxy check-ins | 30 check-ins, only 18 door entries | H1 unmatched |
| R3 | Check-in and leave | Group enters, exits after 20 min | Door exits + occupancy drop |
| R4 | Replayed footage | Play yesterday's clip with its old DVR timestamp | OCR clock + pHash |
| R5 | Same clip from two centres | Submit one clip under two centre IDs | Cross-centre registry |
| R6 | Frozen / covered camera | Freeze frame; cover the lens | Integrity checks |
| R7 | Ornamental equipment | Machine present, unused for "14 days" (synthetic series) | OAI |
| R8 | Rented-for-inspection asset | Swap a monitor/machine between days | Embedding identity mismatch |
| R9 | Performing for audits | Synthetic daily series that spikes around inspection dates | H3 |
| N1–N3 | **Honest controls** | Normal session; lunch break; trainees moving to a workshop | Must **not** flag (false-positive test) |

Drishti covers looped/frozen footage. **R1–R5 and R7–R9 are where we beat the competitors.**

| Metric | Target `[Guessing]`, set from first runs |
|---|---|
| Occupancy count MAE (people) | ≤ 1.5 in seated classrooms; reference: an edge classroom counter reported MAE 1.23 `[Certain]` |
| Door event precision / recall | ≥ 0.9 |
| Fraud-flag FP rate (honest controls) | ≤ 5% |
| Fraud-flag FN rate (R1–R9) | ≤ 10% |
| Robustness curves | Count MAE at 1080p / 720p / 360p, day vs low light, heavy compression |
| Bandwidth | Measured bytes per hour per camera, by tier |
| Latency | Edge fps on target hardware; event → dashboard delay |

`eval/` must generate `docs/ACCURACY_REPORT.md` with confusion matrices per scenario, including failures. Judges trust numbers that include failures.

---

## 15. Operational realities — required implementation

| Reality | Required handling |
|---|---|
| Trainers counted as trainees | Trainer zone and/or subtract scheduled trainer count |
| Multi-camera double counting | Each zone owned by exactly one camera; attendance from door events where available |
| Practical sessions move rooms | Timetable-aware scoring (room × time × session type) |
| Breaks and lunch | Exclude timetable break slots |
| No door camera | Evidence level REDUCED; H1 falls back to occupancy-only; shown on dashboard |
| DVR access | Live RTSP pull **and** periodic file pull |
| Power cuts / connectivity | Outbox, sequence numbers, `data_gap` events; silence never equals compliance |
| Human-in-the-loop | Review workflow, centre response, appeals, audit log; no auto-penalty |
| DPDP | Notice board template, purpose limitation, retention timers, minimisation, access logs |
| Camera placement | `docs/CAMERA_PLACEMENT.md` one-pager + calibration UI |
| Licence hygiene | `THIRD_PARTY_LICENSES.md`, CI check that fails on AGPL/GPL |
| Clock sync | NTP on edge + signed server time in every ack |
| Cost per centre | `docs/COST.md` with measured or cited numbers only |
| Language & accessibility | EN + HI; colour-blind-safe; keyboard navigation |
| Finale readiness | Offline mode, seeded demo, recorded demo video script, one-command start |
| Plagiarism | Our repo private until evaluation; no competitor code |

---

## 16. Privacy design note (D3) — required contents

1. What is processed on the edge vs what leaves the centre (a table per data type).
2. What is **never** done: identification, face embeddings, cross-day tracking, behaviour scoring.
3. Face blur pipeline and its measured miss rate on our footage.
4. Retention: Whisper data (long-term, aggregate), thumbnails (e.g. 90 days), encrypted clips (7–30 days, audit-only release).
5. Access control by role; audit log; centre's right to respond.
6. DPDP Act 2023 / Rules 2025 alignment: notice, purpose, minimisation, retention, security safeguards, breach procedure.
7. Threat model: centre operator (fraud), insider misuse, network attacker (signatures + chain), data leak (minimisation).

---

## 17. Repository structure

```
sakshi/
├─ edge/            ingest/ detect/ track/ zones/ events/ integrity/ assets/ privacy/ evidence/ packet/ outbox/ calibrate/
├─ cloud/           api/ engines/{reconcile,registry,shadow,assets,risk}/ cases/ sidh_mock/ db/ migrations/
├─ dashboard/       Next.js app (EN/HI)
├─ redteam/         generators/ scenarios.yaml runner.py
├─ eval/            metrics.py robustness.py report.py
├─ models/          download scripts + checksums (no weights committed)
├─ data/            sample footage (blurred), seeds, sanctioned_inventory/
├─ docs/            ARCHITECTURE.md PRIVACY_DESIGN.md ACCURACY_REPORT.md LOW_BANDWIDTH.md
│                   CAMERA_PLACEMENT.md DECISIONS.md COST.md DATASETS.md REQUIREMENT_AUDIT.md DEMO_SCRIPT.md
├─ THIRD_PARTY_LICENSES.md
├─ docker-compose.yml   (postgres+timescale, mosquitto, cloud, dashboard)
└─ Makefile             (setup, edge-demo, redteam, eval, report)
```

`docs/REQUIREMENT_AUDIT.md` maps every PS sentence and deliverable D1–D5 to the module and the test that proves it.

---

## 18. Build order and milestones

| Milestone | Build | Acceptance check |
|---|---|---|
| M0 Setup | Repo skeleton, compose, licence CI, model download scripts | `make setup` works offline afterwards; licence check passes |
| M1 Edge core | Ingest → RF-DETR → ByteTrack → zones → door events + occupancy on one MP4 | Door P/R and count MAE computed on a labelled 5-min clip |
| M2 H1 | Mock SIDH + reconciliation + Integrity Score; R1–R3, N1–N3 | R1–R3 flagged; N1–N3 not flagged |
| M3 H2 | Integrity checks + OCR clock + pHash + cross-centre registry; R4–R6 | R4–R6 flagged; no false loops on empty-room days |
| M4 Assets | Zero-shot discovery, registration, DINOv2 identity, OAI; R7–R8 | R7–R8 flagged |
| M5 H3 + risk | ruptures shadow detector, ₹-at-risk, risk queue; R9 | R9 flagged with p-value |
| M6 Low bandwidth | Tiers, signing, chain, outbox, 2 h disconnect test | Bytes/hour measured; zero data loss |
| M7 Dashboard | All pages in Section 12, EN/HI | Demo script runs end to end |
| M8 Reports | Accuracy report, privacy note, low-bandwidth doc, requirement audit, demo script | All D1–D5 artefacts present and generated from real runs |

---

## 19. Testing

- Unit tests for each engine (pytest), especially reconciliation edge cases: no entries, more entries than check-ins, simultaneous arrivals, clock skew.
- Golden tests: fixed clips → fixed counts/events (tolerance bands).
- Integration: edge → MQTT → cloud → dashboard with a seeded centre.
- Chaos: kill the uplink for 2 h; corrupt a packet signature; reorder packets; duplicate packets.
- Licence CI: fail on AGPL/GPL in the dependency tree.

---

## 20. Research references (cite in docs; verify each link)

| Topic | Reference |
|---|---|
| Detector | RF-DETR: Real-Time Detection Transformer, ICLR 2026, arXiv:2511.09554 `[Certain]` |
| Detector backbone | DINOv2, arXiv:2304.07193 `[Certain]` |
| Detector alt | LW-DETR, arXiv:2406.03459 `[Certain]`; D-FINE, arXiv:2410.13842 `[Likely]` |
| Tracking | ByteTrack, arXiv:2110.06864 (ECCV 2022) `[Certain]`; OC-SORT, arXiv:2203.14360 `[Likely]`; BoT-SORT, arXiv:2206.14651 `[Likely]` |
| Small objects | SAHI — Slicing Aided Hyper Inference, arXiv:2202.06934 `[Likely]` |
| Head detection | SCUT-HEAD: "Detecting Heads using Feature Refine Net and Cascaded Multi-Scale Architecture", arXiv:1803.09256 `[Certain]` |
| Crowd counting | P2PNet: "Rethinking Counting and Localization in Crowds", ICCV 2021, arXiv:2107.12746 `[Certain]` |
| Classroom occupancy on edge | "Edge-Based Transfer Learning for Classroom Occupancy Detection in a Smart Campus Context", Sensors 2022, doi:10.3390/s22103692 (MAE 1.23) `[Certain]` |
| Open-vocabulary detection | Grounding DINO, arXiv:2303.05499 `[Likely]`; OWLv2 "Scaling Open-Vocabulary Object Detection", arXiv:2306.09683 `[Likely]`; SAM 3, arXiv:2511.16719 `[Certain]` |
| Camera tamper | "Unified Camera Tamper Detection Based on Edge and Object Information", Sensors 2015, doi:10.3390/s150510315 `[Certain]`; "A Survey of Feature Types and Their Contributions for Camera Tampering Detection", arXiv:2310.07886 `[Certain]`; "Comparative study and enhancement of Camera Tampering Detection algorithms", arXiv:1608.02385 `[Certain]` |
| Replay / spoofing | "Live Spoofing Detection for Automatic Human Activity Recognition Applications", Sensors 2021 (video replay attacks) `[Certain]`; IETF draft "MVPS Video-Surveillance and CCTV Profile: Fleet-Coherence Detection of Feed Replay and Loop Injection" `[Certain]` |
| Perceptual hashing | Zauner, "Implementation and Benchmarking of Perceptual Image Hash Functions", 2010 `[Likely]` |
| Change-point | Killick, Fearnhead & Eckley, "Optimal detection of changepoints with a linear computational cost" (PELT), JASA 2012 `[Likely]`; Truong, Oudre & Vayatis, "Selective review of offline change point detection methods" (ruptures), Signal Processing 2020 `[Likely]` |
| Matching | Kuhn, "The Hungarian Method for the Assignment Problem", 1955 `[Certain]` |
| Uncertainty (optional) | Angelopoulos & Bates, "A Gentle Introduction to Conformal Prediction", arXiv:2107.07511 `[Likely]` |

---

## 21. Open-source components (licence verified by cloning, Oct 2026)

| Component | Repo | Licence | Use |
|---|---|---|---|
| Detector | roboflow/rf-detr | Apache-2.0 (N–L; XL/2XL are PML) | Heads/persons |
| Detector alt | Peterande/D-FINE | Apache-2.0 | Backup |
| Zones/counting | roboflow/supervision | MIT | LineZone, PolygonZone, annotators |
| Tracking | roboflow/trackers | Apache-2.0 | ByteTrack/OC-SORT/BoT-SORT |
| Tiling | obss/sahi | MIT | Small heads |
| Zero-shot | IDEA-Research/GroundingDINO | Apache-2.0 | Asset discovery |
| Zero-shot alt | OWLv2 (HF Transformers) | Apache-2.0 `[Likely]` | Asset discovery |
| Embeddings | DINOv2 | Apache-2.0 `[Likely]` | Asset identity |
| OCR | PaddlePaddle/PaddleOCR | Apache-2.0 | DVR timestamp |
| Hashing | JohannesBuchner/imagehash | MIT | pHash |
| Change-point | deepcharles/ruptures | BSD-2 | H3 |
| Face blur | ORB-HD/deface | MIT | Edge blur |
| Signing | pyca/pynacl | Apache-2.0 | Ed25519 |
| Matching | SciPy | BSD | Hungarian |
| Edge NVR pattern (optional) | blakeblackshear/frigate | MIT (code; name is trademarked) | Motion-gating pattern reference |
| **Banned** | Ultralytics YOLO, BoxMOT, YOLO-World | AGPL/GPL | — |
| **Read-only (no licence)** | ctd-devkit, chandan54 tamper, Camera-Tampering-Tech, all competitor repos | None | Ideas only |

---

## 22. Definition of done

- `docker compose up` + `make edge-demo` shows the full story on seeded data in under 5 minutes:
  - a bulk-check-in centre (H1),
  - a replayed-feed centre (H2),
  - an audit-performing centre (H3),
  - an ornamental-lathe centre (S1),
  - an honest centre that stays clean.
- D1–D5 artefacts exist and are generated from real runs.
- No AGPL/GPL dependency; no competitor code; all data labelled measured/simulated/mock.
- `docs/DECISIONS.md` records every `[Likely]`/`[Guessing]` item from this prompt with its verified value.

---

## 23. Sources

**Government / context**
- [MSDE – PMKVY 4.0 Guidelines](https://www.msde.gov.in/static/uploads/2024/02/PMKVY-4.0-Guidelines_final-copy.pdf)
- [Skill Reporter – NSDC RFP for Virtual Verification of PMKVY Training Centres](https://www.skillreporter.com/business-opportunities/request-for-proposal/nsdc-rfp-tender-virtual-verification-pmkvy-skill-training-centres/)
- [OpenGov Asia – PMKVY monitoring (AEBAS → face authentication)](https://opengovasia.com/india-expands-skill-development-network-under-skill-india-mission/)
- [NextIAS – Skilling reforms / PMKVY 4.0 blacklisting](https://www.nextias.com/ca/current-affairs/10-02-2026/skilling-reforms-india)
- [Moneylife – CAG audit of PMKVY](https://www.moneylife.in/article/94-percentage-bank-details-missing-underage-candidates-certified-placements-unverifiable-in-pm-kaushal-vikas-yojana-cag/79358/128462.html)
- [Wikipedia – Digital Personal Data Protection Rules, 2025](https://en.wikipedia.org/wiki/Digital_Personal_Data_Protection_Rules,_2025)
- [Reskilll – SIH 2026 timeline (Oct–Nov screening, 36-hour December finale)](https://blogs.reskilll.com/smart-india-hackathon-2026-launched-timeline-registration-how-to-participate/)
- [FirstVidya – SIH 2026 guide (2 PS per team, 500-idea cap per PS)](https://firstvidya.com/sih-2026-guide/)

**Research**
- [Sensors – Edge-based classroom occupancy detection (MAE 1.23)](https://doaj.org/article/29a73b80257f4d7d9e118c6befd60ca8)
- [IETF draft – CCTV feed replay / loop detection](https://datatracker.ietf.org/doc/draft-melegassi-ippm-mvps-video-surveillance/)
- [Unified Camera Tamper Detection Based on Edge and Object Information (Sensors, 2015)](https://doi.org/10.3390/s150510315)
- [A Survey of Feature Types and Their Contributions for Camera Tampering Detection (arXiv 2310.07886)](https://arxiv.org/abs/2310.07886)
- [Comparative study and enhancement of Camera Tampering Detection algorithms (arXiv 1608.02385)](https://arxiv.org/abs/1608.02385)
- [Live Spoofing Detection for Automatic HAR Applications (Sensors 2021)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8587143/)
- [SCUT-HEAD paper (arXiv 1803.09256)](https://arxiv.org/abs/1803.09256) · [SCUT-HEAD dataset page](https://datasetninja.com/scut-head)
- [P2PNet (arXiv 2107.12746)](https://arxiv.org/abs/2107.12746)
- [ByteTrack (arXiv 2110.06864)](https://arxiv.org/abs/2110.06864)
- [RF-DETR (arXiv 2511.09554)](https://arxiv.org/abs/2511.09554)

**Competitor repos (ideas only — no licence, do not copy)**
- [syedrahmanghouse/centre-watch-platform](https://github.com/syedrahmanghouse/centre-watch-platform) · [Mannjain26/Drishti](https://github.com/Mannjain26/Drishti) · [Roshani-patil07/skill_sentinel](https://github.com/Roshani-patil07/skill_sentinel) · [Santhosh-006-30/SkillGaurd-AI](https://github.com/Santhosh-006-30/SkillGaurd-AI) · [anveshreddy-techin/real-ai](https://github.com/anveshreddy-techin/real-ai) · [varun16-dev/Evidence-Intelligence](https://github.com/varun16-dev/Evidence-Intelligence) · [Donomite101/Aicameradetection](https://github.com/Donomite101/Aicameradetection) · [tamilselvan840/SIH-project](https://github.com/tamilselvan840/SIH-project) · [Himanshu-hub-oss/CENTRAI](https://github.com/Himanshu-hub-oss/CENTRAI) · [tgnaneshwar007-cell/skillwatch-ai](https://github.com/tgnaneshwar007-cell/skillwatch-ai) · [dharanitham1210-lang/TrustCentre](https://github.com/dharanitham1210-lang/TrustCentre) · [smilingmerchant/skill-centre-compliance-monitor](https://github.com/smilingmerchant/skill-centre-compliance-monitor)

**Open-source components:** see Section 21.
