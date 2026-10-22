# SIH26245 — SAKSHI

Anonymous, tamper-evident compliance monitoring for government-funded skilling centres
(Smart India Hackathon 2026 · PS SIH26245 · MSDE · Smart Education).

SAKSHI turns existing centre CCTV into ranked, explainable exceptions for scheme monitoring officers:
every face-auth check-in must be explained by an anonymous door entry (**H1**), replayed / frozen / duplicated
feeds are caught by an OCR'd DVR clock, cross-day and cross-centre hashes (**H2**), and centres that perform only
around inspections are found by change-point analysis (**H3**). Nobody is identified; a human officer decides.

| Read this | For |
|---|---|
| [`docs/summary.md`](docs/summary.md) | **current status + handoff for a new session** |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | **start here** — flow, repo map, data contracts, engines, how to run |
| [`PROMPT.md`](PROMPT.md) | the build contract |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | verified facts and every deviation from the prompt |
| [`docs/REQUIREMENT_AUDIT.md`](docs/REQUIREMENT_AUDIT.md) | PS sentence / D1–D5 → module → proof |
| [`docs/ACCURACY_REPORT.md`](docs/ACCURACY_REPORT.md) | D4, generated from runs (includes failures) |
| [`docs/PRIVACY_DESIGN.md`](docs/PRIVACY_DESIGN.md) · [`docs/LOW_BANDWIDTH.md`](docs/LOW_BANDWIDTH.md) | D3 · D5 |
| [`docs/DATASETS.md`](docs/DATASETS.md) · [`docs/REFERENCES.md`](docs/REFERENCES.md) · [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md) | data, papers, licences |
| [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) · [`docs/CAMERA_PLACEMENT.md`](docs/CAMERA_PLACEMENT.md) · [`docs/COST.md`](docs/COST.md) | demo, field setup, cost |

## Running

All compute runs on a cloud GPU VM, not the developer laptop (project rule). Kaggle (T4, via the `kaggle` CLI):
push [`models/finetune_heads_kaggle.py`](models/finetune_heads_kaggle.py) as kernel `sakshi-finetune`, then
[`scripts/kaggle_pipeline.py`](scripts/kaggle_pipeline.py) with that kernel attached as input; it runs
[`scripts/gpu_runs.sh`](scripts/gpu_runs.sh) and `kaggle kernels output` brings the result files home. (Colab
equivalents: `models/finetune_heads_colab.ipynb`, then `scripts/gpu_runs.sh`.) On a demo machine: `docker compose up` →
dashboard http://localhost:3000 (accounts in `data/demo/users.yaml`), API http://localhost:8000/docs.

## Status

Built: edge pipeline, cloud API + engines, red-team simulator, evaluation suite, dashboard (EN/HI), docs.
Measured on Kaggle T4, 2026-10-22 (`docs/ACCURACY_REPORT.md`): door P/R 1.000 / 0.955 on MEVA, per-frame count MAE 0.89,
head-count MAE 1.52 on SCUT-HEAD classroom images (target 1.5), fraud missed 13.1 % (all blatant cases caught; target 10 %),
honest controls falsely flagged 0.8 %, edge 4.9 fps on 4 CPU cores, ≈ 16–18 KB/h per camera (Whisper tier).
Own college footage: to be added; every eval script re-runs on it unchanged.

Data attribution: MEVA dataset by Kitware Inc. and IARPA, CC BY 4.0.
