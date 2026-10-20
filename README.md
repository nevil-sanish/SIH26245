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

All compute runs in Google Colab (project rule): open
[`models/finetune_heads_colab.ipynb`](models/finetune_heads_colab.ipynb) (T4) then
[`eval/colab_pipeline.ipynb`](eval/colab_pipeline.ipynb) (CPU). On a demo machine: `docker compose up` →
dashboard http://localhost:3000 (accounts in `data/demo/users.yaml`), API http://localhost:8000/docs.

## Status

Built: edge pipeline, cloud API + engines, red-team simulator, evaluation suite, dashboard (EN/HI), docs.
Pending from Colab runs: head-model metrics, measured door P/R / count MAE / fps / bytes-per-hour, demo packets.
Own college footage: to be added; every eval script re-runs on it unchanged.

Data attribution: MEVA dataset by Kitware Inc. and IARPA, CC BY 4.0.
