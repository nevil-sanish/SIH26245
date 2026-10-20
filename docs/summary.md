# HANDOFF — read this first (state as of 2026-10-20 20:45 IST)

You are continuing the SAKSHI build for SIH 2026 problem statement **SIH26245** (MSDE): anonymous, tamper-evident
CCTV compliance monitoring for skilling centres. The build contract is [`PROMPT.md`](../PROMPT.md) (a copy of
`~/Downloads/SIH26245_BUILD_PROMPT.md`). The code map is [`ARCHITECTURE.md`](ARCHITECTURE.md). Every deviation from
the prompt is in [`DECISIONS.md`](DECISIONS.md). This file covers **where things stand, how we work, and what is left**.

## 1. Rules the user set (must follow)

| Rule | Detail |
|---|---|
| **Run nothing locally** | No model inference, edge runs, eval, red-team, ffmpeg or tests on the laptop. Write code locally → `git push` → run in **Google Colab** via the Claude-in-Chrome extension. Trivial file edits and `git` are fine. |
| **Colab account** | `sanishnevil@gmail.com` = Colab `?authuser=5`. Do **not** use authuser 0 (that is nevilsanish@gmail.com). |
| **Commits** | Commit and push to `https://github.com/nevil-sanish/SIH26245` (branch `main`) after each completed step, authored **nevil-sanish <nevilsanish@gmail.com>** (repo-local git config is set). **No Claude / Co-Authored-By / session trailers.** |
| **Drive** | The user approved clicking "Connect to Google Drive" for these SAKSHI notebooks only. |
| **Style** | Follow `PROMPT.md` exactly. Lean code, no unnecessary files, everything explained in `docs/` so another AI can continue. The user wants speed and minimal chatter. |
| **Footage** | Public data for now (MEVA CC BY 4.0 + Wikimedia Commons). The user will later supply their own college footage, and the eval must re-run on it unchanged. |
| **Repo visibility** | The repo is **public**; PROMPT §15 says private until evaluation. The user was told and hasn't decided. Don't change visibility yourself. |

## 2. Where everything is

- Code: `~/NEVIL/code/sih 2026/sih 2nd/` (its own git repo, nested inside the user's `~/NEVIL` backup repo).
- Notebooks (open from GitHub with `?authuser=5`):
  - `models/finetune_heads_colab.ipynb`: RF-DETR Nano head fine-tune on SCUT-HEAD (**done**). The currently running GPU evaluation cell was inserted at the top of this notebook.
  - `eval/colab_pipeline.ipynb`: older CPU pipeline notebook (superseded by `scripts/colab_gpu_runs.sh`).
- Google Drive (sanishnevil):
  - `MyDrive/sakshi_models/`: `rfdetr_nano_head.onnx` (116 MB), `rfdetr_nano_coco.onnx` (115 MB), `head_metrics.json`, `SHA256SUMS`.
  - `MyDrive/sakshi_work/`: 12 prepared clips (`clips/*.mp4`) + `rfdetr_nano_coco.onnx`. When the run finishes, `bundle.txt` is written here.
- Local venv `.venv` (py3.11) exists but must not be used to run things (see rule 1).

## 3. What is DONE

**Code (all PROMPT milestones written, M0–M7):**
- `edge/`: ingest (RTSP / DVR folder / MP4), detect (RF-DETR ONNX, optional tiling, opt-in CUDA via `SAKSHI_GPU=1`), track (ByteTrack, session-scoped), zones, events, integrity (frozen / covered / moved / OCR clock / pHash loop), assets (OWLv2 + DINOv2), privacy (face blur, sealed clip ring), evidence, packet (Ed25519 + hash chain), outbox (SQLite store-and-forward, HTTPS / MQTT, SMS summary), calibrate (local UI), run (main loop). Camera configs are in `edge/cameras/`.
- `cloud/`: db (all §9 tables), ingest (verify signature / chain / seq, gaps, reorder, duplicates), engines (`reconcile` H1, `registry` H2, `shadow` H3, `assets` S1/S2, `risk` S3/S4), analyze (orchestration → flags), cases (human review), sidh_mock, api (all §10 endpoints + auth / roles / audit / MQTT bridge / retention purge), demo_seed (the §22 story).
- `redteam/`: scenarios.yaml (R1–R9, subtle R1b–R3b, N1–N3), generators.py (event / series / video manipulations), runner.py (`prepare | video | sims`).
- `eval/`: metrics.py, robustness.py, report.py (→ `docs/ACCURACY_REPORT.md`).
- `dashboard/`: Next.js 16 static export, all §12 pages, EN/HI, colour-blind safe, offline inspector.
- Infrastructure: `docker-compose.yml`, `deploy/`, `Makefile`, `.github/workflows/ci.yml`, `scripts/check_licenses.py`.
- `tests/`: engines, chaos (2 h outage, forged / reordered / duplicate packets), API integration.
- Docs: `ARCHITECTURE`, `DECISIONS`, `REFERENCES`, `DATASETS`, `PRIVACY_DESIGN` (D3), `LOW_BANDWIDTH` (D5), `CAMERA_PLACEMENT`, `COST`, `REQUIREMENT_AUDIT`, `DEMO_SCRIPT`, `THIRD_PARTY_LICENSES`, `README`.

**Verified in Colab:**
- 25/25 tests pass (before `test_api.py` and the SMS test were added; those haven't run yet).
- The dashboard builds (12 routes), and TypeScript is clean.
- Head model trained 30 epochs: val mAP@50 **0.902**, mAP@50:95 0.454. PyTorch head-count MAE on SCUT-HEAD Part A test is **2.17** (mean 34.4 heads per image) at threshold **0.35**. ONNX export: input `[1,3,512,512]`, outputs `dets [1,300,4]` and `labels [1,300,2]`. **Head = logit column 0.**
- COCO ONNX: input 384, `labels [1,300,91]`, person = column 1 (0.92 on a real MEVA door frame).
- PaddleOCR reads the burned DVR clock exactly. The first edge packet had clock drift 0.0, evidence OK, and no false tamper flags.
- Simulated red-team: all blatant fraud caught. Subtle R2b / R3b are mostly missed, on purpose (no false alarms on honest controls).

## 4. RUNNING NOW

Started ~20:38 IST on a **T4**, in the top cell of `models/finetune_heads_colab.ipynb` (authuser=5). The cell:
1. mounts Drive;
2. copies `MyDrive/sakshi_models/*` → `/content/out/`;
3. downloads `scripts/colab_gpu_runs.sh` from GitHub and runs it.

The script runs: clone → install (Colab torch, `onnxruntime-gpu`) → clips and models from Drive → `data/download.py` → `models/download.py` → pytest → `scripts/eval_head_onnx.py` (MAE of the **deployed ONNX** head model, writes `data/work/head_onnx_check.json`) → CPU fps benchmark → `redteam.runner video` (all 7 video runs, GPU) → `eval.robustness` → `eval.metrics` → `eval.report` → `make_india_map.py` → npm lockfile → `scripts/bundle_results.py` > `/content/bundle.txt` (also copied to `MyDrive/sakshi_work/bundle.txt`).

The expected finish was **~21:20–21:40 IST**. Output only appears at the end (`| tail -60`). Check progress with Colab's **Terminal** button: `ps aux | grep -E 'runner|eval|pytest'`, `ls /content/sakshi/data/edge_state`.

## 5. What is LEFT (in order)

1. **Collect results.** When the cell prints `ALL_DONE`, read `/content/bundle.txt` (the text between `RESULTS_B64_BEGIN` and `RESULTS_B64_END`, the base64 of a tar.gz). Read it from the cell output with `get_page_text`, or `cat` it in a new cell. Locally: `base64 -d | tar xz` from the repo root. That restores:
   - `docs/ACCURACY_REPORT.md`;
   - `data/work/*.json`;
   - `data/demo/packets.jsonl` + `device_keys.json` (measured demo data for the seeder);
   - `models/checksums.txt`, `models/head_metrics.json`;
   - `dashboard/package-lock.json`, `dashboard/public/india.json`.

   Commit them. `.gitignore` excludes `data/work/`. Either commit the json under `data/work` with `git add -f`, or rely on the report. `data/demo/` is tracked.
2. **Sanity-check the measured numbers** in ACCURACY_REPORT:
   - door P/R vs MEVA GT (43 entries; if in/out are swapped, flip `entry_direction` in `edge/cameras/meva_G420_door.yaml`);
   - honest centre TC0421 has no fraud flags;
   - R4 (TC0777) flags clock_drift + loop;
   - R5 (TC0555) flags cross_centre_duplicate;
   - R6 (TC0612) flags frozen / covered;
   - ONNX head MAE (`head_onnx_check.json`) is close to PyTorch's 2.17. If it's much worse, the cause is in `edge/detect.py` preprocessing (ImageNet mean/std, RGB, direct resize to 512).

   An earlier one-image check showing "5 vs 63 heads" was probably comparing against the wrong image's annotations.
3. **Fill DECISIONS.md "pending" rows** with the measured values: door P/R, count MAE, CPU fps (`data/work/cpu_benchmark.json`), bytes/hour. Also update the "pending" text in `LOW_BANDWIDTH.md`, `COST.md`, `PRIVACY_DESIGN.md` (the face-blur miss rate stays pending until own footage) and the README status.
4. **Run the new tests in Colab:** `test_api.py` and the SMS test. The GPU script runs pytest; check its output line.
5. **End-to-end demo check (§22) in Colab:** `python -m cloud.demo_seed --fresh` with SQLite, then `uvicorn cloud.api:app` plus the static dashboard. Verify:
   - the risk queue order (TC0880 / TC0777 / TC0915 / TC0307 high; TC0421 and fillers clean);
   - the batch view;
   - the evidence page;
   - the review flow;
   - Hindi.

   Docker can't run in Colab: build-check the images on a demo machine later (`docker compose up`; the seed runs automatically via `--if-empty`).
6. **Lab scenario (TC0198):** uses the head model, `class_ids: [0]`, thr 0.35. Verify the monitor asset zone `[[300,170],[380,240]]` against a frame (`scripts/preview_calibration.py`).
7. **Own college footage** (when the user provides it): add camera YAMLs, label a 5-min clip, re-run `eval/robustness` and `metrics`, and report it separately.
8. **Optional / not done:**
   - SMS gateway integration (only the builder exists);
   - SCB-Dataset extra fine-tune;
   - EduNet (not obtainable);
   - a real QP equipment list (the inventory is mock);
   - a cited ₹ rate (₹50 assumption in `cloud/engines/risk.py`);
   - Alembic migrations;
   - face-blur miss rate on own footage;
   - Raspberry Pi tier.

## 6. Gotchas learned the hard way

- **Colab terminal:** click inside it before typing. If the panel closes, keystrokes land in the notebook and create stray cells.
- **Background jobs in the Colab terminal:** use `nohup … < /dev/null &`. ffmpeg reads stdin (`-nostdin` is now in code), otherwise the job gets "Stopped".
- **Clip writes are atomic** (`.part.mp4` → rename). Never run two `prepare`s at once.
- **Colab CPU (2 vCPU) runs RF-DETR at only ~0.5–1.4 fps.** Batch runs use the T4 (`SAKSHI_GPU=1`) and report the provider. CPU fps is benchmarked separately.
- **All wall-clock values are IST** (`edge/__init__.py::IST`). Colab is UTC.
- **Demo timeline:** MEVA 2018-03-11 footage is re-stamped onto 2026-10-19. The lobby clip (11:55 slot) is stamped 12:00 to pair with the door clip.
- **Colab's "Notebook not authored by Google" dialog:** click Run anyway (it's our own repo).
- **The browser `find` tool can hit rate limits.** Prefer `get_page_text` / `javascript_tool`.
