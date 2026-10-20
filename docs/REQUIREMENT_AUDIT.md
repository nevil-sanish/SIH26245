# Requirement audit — every PS sentence and deliverable → module → proof

| Requirement (SIH26245) | Where | Proof |
|---|---|---|
| Process live or periodic camera feeds | `edge/ingest.py` (RTSP with backoff, DVR export folder, MP4) | edge runs in ACCURACY_REPORT (measured) |
| Estimate attendance | `edge/zones.py` + `edge/events.py` (occupancy every 10 s, door events) | count MAE + door P/R in ACCURACY_REPORT |
| Cross-check attendance against centre records | `cloud/engines/reconcile.py` (H1 Hungarian matching, burst, leave, inflation, ghost, hours gap) | `tests/test_engines.py`; R1–R3/N1–N3 confusion matrices |
| Detect presence/absence of sanctioned infrastructure | `edge/assets.py` (OWLv2 discovery), `cloud/engines/assets.py::inventory_gap`, QP mock list | `asset_missing` flag; R8 |
| Apparent operability of infrastructure | `edge/events.py` (person-in-zone + motion, screen-on), OAI in `cloud/engines/assets.py` | R7 confusion matrix |
| Flag discrepancies to a dashboard instead of manual footage review | `cloud/analyze.py` → `flags`; `dashboard/` risk queue, case file, evidence | demo seed; DEMO_SCRIPT |
| Operate under rural bandwidth limits | Whisper/Normal/Audit tiers, outbox | LOW_BANDWIDTH.md; `test_two_hour_outage_no_data_loss` |
| Operate under camera-quality limits | evidence level, abstain, tamper checks, robustness curves | ACCURACY_REPORT robustness; `test_data_gap_abstains` |
| Preserve privacy via aggregate presence, not identification | no face recognition anywhere; face blur on edge; session-scoped IDs | PRIVACY_DESIGN.md; licence/model inventory |
| **D1** working analytics pipeline on sample/simulated footage | `edge/run.py` on MEVA + Commons + red-team clips | `eval/colab_pipeline.ipynb` run; `data/demo/packets.jsonl` |
| **D2** discrepancy + compliance dashboard for monitoring units | `dashboard/` (all PROMPT §12 pages, EN/HI) + `cloud/api.py` | DEMO_SCRIPT |
| **D3** privacy-preserving design note | `docs/PRIVACY_DESIGN.md` | — |
| **D4** FP/FN accuracy assessment | `eval/metrics.py`, `eval/robustness.py`, `eval/report.py` → `docs/ACCURACY_REPORT.md` | generated from runs, includes failures |
| **D5** low-bandwidth mode | `edge/packet.py`, `edge/outbox.py`, `docs/LOW_BANDWIDTH.md` | chaos tests; measured bytes/hour |

## PROMPT.md rules

| Rule | Where enforced |
|---|---|
| No competitor code | written from scratch; ideas credited in PROMPT §4 only |
| Permissive licences only | `scripts/check_licenses.py` in CI; `THIRD_PARTY_LICENSES.md` |
| No face recognition / identity embeddings / persistent IDs | `edge/track.py` (session reset), no such models in deps |
| No automatic penalties | `cloud/cases.py` (human actions only) |
| Honesty labels measured/simulated/mock | `label` column on every analytic row; `LabelTag` in every dashboard view |
| Abstain when evidence is weak | `reconcile_session` → `INSUFFICIENT_EVIDENCE` |
| Silence ≠ compliance | coverage check + `data_gap` flags + seq-gap detection |
| Pinned deps, `docker compose up`, offline after setup | `*/requirements.txt`, `package.json` exact versions, `docker-compose.yml`, `models/download.py` |
