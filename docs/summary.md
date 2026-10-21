# HANDOFF — read this first (state as of 2026-10-22 01:00 IST)

You are continuing the SAKSHI build for SIH 2026 problem statement **SIH26245** (MSDE): anonymous, tamper-evident
CCTV compliance monitoring for skilling centres. The build contract is [`PROMPT.md`](../PROMPT.md). The code map is
[`ARCHITECTURE.md`](ARCHITECTURE.md). Every deviation from the prompt is in [`DECISIONS.md`](DECISIONS.md). This file
covers **where things stand, how we work, and what is left**.

## 0. RESUME HERE (session of 2026-10-22 stopped at ~01:00 IST with Kaggle jobs still running)

All compute now runs on **Kaggle** (Colab hit its rate limit). Kaggle CLI on the laptop is logged in as
**`anonymousguy011`** (`kaggle config view`; browser account guyanonymous013@gmail.com, phone-verified, 30 GPU h/week).
Kernels run on Kaggle's servers and keep running with the laptop off; output is kept per kernel version.

| Kernel | What | State at handoff |
|---|---|---|
| `anonymousguy011/sakshi-finetune-long` (v2) | **the main job.** `models/finetune_heads_kaggle.py` with `THEN_PIPELINE = True`: RF-DETR Nano head fine-tune at 640 px, up to 80 epochs, early stopping (patience 10) → ONNX export to `out/` → clones the repo **at that moment** and runs `scripts/kaggle_pipeline.py` → `scripts/gpu_runs.sh` (full measured run) → `results/` + `gpu_runs.log` | started 00:55 IST; ~4 min/epoch → training done 04:00–06:20, pipeline +~1 h |
| `anonymousguy011/sakshi-finetune` (v2) | same fine-tune, 30 epochs fixed, no pipeline (fallback model) | started 00:36, done ~02:45 |
| `anonymousguy011/sakshi-smoke` (v5) | CPU check of the venv install fix (`UV_SYSTEM_PYTHON`), full pytest, `demo_check` | **passed 01:01**: py3.11.14 venv (ORT 1.31.0, torch 2.14.1+cu130), **30/30 tests**, `demo_check` ok (video centres show only `data_gap` because the smoke run has no measured packets; the long run brings them) |
| `sakshi-setup`, `notebook622e4b2bd7` | old one-offs | done / idle; may be deleted |

**Steps to resume** (from the repo root):
1. (Done 01:01: smoke v5 passed, so the pipeline fix is verified.) For any later smoke run: `kaggle kernels status anonymousguy011/sakshi-smoke`, then read its log:
   `kaggle kernels output anonymousguy011/sakshi-smoke -p /tmp/smoke` and look at `/tmp/smoke/sakshi-smoke.log`
   (tests passed? `demo_check` ok?). If something fails, fix it and push to GitHub **before the long kernel's training
   ends**. The chained pipeline clones `main` only then, so a fix pushed in time is picked up.
2. `kaggle kernels status anonymousguy011/sakshi-finetune-long`. When it shows COMPLETE:
   `kaggle kernels output anonymousguy011/sakshi-finetune-long -p /tmp/long`
   - `/tmp/long/out/`: `rfdetr_nano_head.onnx`, `rfdetr_nano_coco.onnx`, `head_metrics.json`, `SHA256SUMS`
   - `/tmp/long/results/`: result files with their repo paths (`docs/ACCURACY_REPORT.md`, `data/work/*.json`,
     `data/demo/packets.jsonl`, `data/demo/device_keys.json`, `models/checksums.txt`, `models/head_metrics.json`,
     `edge/cameras/meva_G420_door.yaml` with the chosen `door_min_frames`, `dashboard/public/india.json`)
   - `/tmp/long/gpu_runs.log`: full log.
   Copy them into the repo with `cp -r /tmp/long/results/. .`, review the diff, update `DECISIONS.md` (verified
   facts: head MAE, door P/R and the sweep, FN/FP), `README.md` status and this file, then commit.
3. If the chained pipeline failed but `out/` exists: fix, push, and run `scripts/kaggle_pipeline.py` as its own kernel
   (metadata: GPU + internet on, `kernel_sources: ["anonymousguy011/sakshi-finetune-long"]`).
4. **Do not push a new version of `sakshi-finetune-long` before fetching its output.** `kernels output` returns the
   latest version only.
5. Kaggle allows **2 batch GPU sessions** at once. Pushing a new version does **not** stop the old one. Stop runs in
   the browser: kaggle.com/work → "View Active Events" → ⋯ → Stop Session.

## 1. Rules the user set (must follow)

| Rule | Detail |
|---|---|
| **Run nothing locally** | No model inference, edge runs, eval, red-team, ffmpeg or tests on the laptop. Write code locally → `git push` → run on **Kaggle** (CLI `kaggle kernels push`; Colab is rate-limited). Trivial file edits and `git` are fine. Open question to the user: may `docker compose up` + a dashboard click-through run locally? |
| **Commits** | Commit and push to `https://github.com/nevil-sanish/SIH26245` (branch `main`) after each completed step, authored **nevil-sanish <nevilsanish@gmail.com>** (repo-local git config is set). **No Claude / Co-Authored-By / session trailers.** |
| **Quality** | The user wants the *results* to be as good as possible, not just a working build. Train long; fix real modelling errors; never tune a threshold to pass a test (DECISIONS records which changes came after seeing a failure). |
| **Style** | Follow `PROMPT.md` exactly. Lean code, no unnecessary files, everything explained in `docs/` so another AI can continue. The user wants speed, minimal chatter, and token economy. |
| **Footage** | Public data for now (MEVA CC BY 4.0 + Wikimedia Commons). The user will later supply their own college footage, and the eval must re-run on it unchanged. |
| **Repo visibility** | The repo is **public**; PROMPT §15 says private until evaluation. The user was told and hasn't decided. Don't change visibility yourself. |
| **Local reference files** | `files/` (papers, PS PDF, proposal decks, explainer video, a copy of the prompt) is git-ignored. Do not commit it. |

## 2. Where everything is

- Code: `~/NEVIL/code/sih 2026/sih 2nd/` (its own git repo).
- Kaggle scripts: `models/finetune_heads_kaggle.py` (fine-tune; `THEN_PIPELINE` chains the run),
  `scripts/kaggle_pipeline.py` (finds the ONNX in `/kaggle/working/out` or `/kaggle/input`, runs `scripts/gpu_runs.sh`),
  `scripts/gpu_runs.sh` (platform-neutral measured run in a py3.11 venv; was `colab_gpu_runs.sh`).
- Kernel metadata for re-pushing lives only in the pushed kernels (`kaggle kernels pull <id> -m`).
- Colab artefacts (historical): `models/finetune_heads_colab.ipynb`; Drive `MyDrive/sakshi_models/` on sanishnevil
  (512 px model of 2026-10-20). Not needed any more.

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


**Session 2026-10-22 (00:00–01:00 IST), committed, measured numbers pending on Kaggle:**
- Door crossing hysteresis `door_min_frames`, chosen by `eval.robustness --door-sweep` on the **42-exit** MEVA clip.
  Exits had been measured on only 2 GT, and the exit clip was downloaded but never evaluated.
- Red-team door noise per direction. Entries had been simulated with the any-direction precision 0.863, which is about
  7× too many phantom entries, and those masked proxy check-ins (R2b).
- `checkin_then_leave`: a 10 % floor plus a Poisson test against the measured false-exit rate (was a fixed 20 %).
  `unmatched_checkin` floor changed to `>=`. Both are flagged in DECISIONS as made after seeing R2b/R3b fail.
- Head fine-tune at 640 px with a classroom-only threshold choice. 80 epochs with early stopping. Early val mAP50:95
  of the 640 run: 0.458 at epoch 3, versus 0.454 final for the 512 px Colab model.
- Lab clip TC0198: the Commons source is **11.1 s**, which is why it gives 23 frames and 1 packet. Documented in the
  report's Known limits. The India lab clip is 41 s, also under one 60 s packet.
- `.gitignore`: `data/server.key` (secret), `*.db-shm/wal`, `files/`. Dashboard `package-lock.json` committed.
- Tests added: per-direction noise model, walk-out vs exit precision. They will run in the Kaggle pipeline's pytest.

**Verified in Colab (2026-10-20):**
- 25/25 tests pass (before `test_api.py` and the SMS test were added; those haven't run yet).
- The dashboard builds (12 routes), and TypeScript is clean.
- Head model trained 30 epochs: val mAP@50 **0.902**, mAP@50:95 0.454. PyTorch head-count MAE on SCUT-HEAD Part A test is **2.17** (mean 34.4 heads per image) at threshold **0.35**. ONNX export: input `[1,3,512,512]`, outputs `dets [1,300,4]` and `labels [1,300,2]`. **Head = logit column 0.**
- COCO ONNX: input 384, `labels [1,300,91]`, person = column 1 (0.92 on a real MEVA door frame).
- PaddleOCR reads the burned DVR clock exactly. The first edge packet had clock drift 0.0, evidence OK, and no false tamper flags.
- Simulated red-team: all blatant fraud caught. Subtle R2b / R3b are mostly missed, on purpose (no false alarms on honest controls).

## 4. Session 2026-10-20 evening: what was found and fixed (all verified in Colab)

- GPU script died at install: `edge/requirements.txt` has `-r ../cloud/requirements.txt`, broken when copied to /tmp → filtered copy now lives in `edge/`.
- `python scripts/X.py` can't import `edge` → run them as `python -m scripts.X`.
- Door G420 line covered one doorway only (16/44 GT paths crossed it) and direction was inverted → refit across both doorways (42/44), `in_is_right_to_left`. Door entries now P 0.977 / R 1.000.
- `moved` fired on the honest busy door (crowds hide the background) → needs 3 consecutive low-ORB checks.
- `cross_centre_duplicate` flagged the original centre too → only the later arrival (KeyframeHash.id) is flagged.
- Face blur was unavailable in every run (deface needs the `onnx` package) → added `onnx==1.23.2`. Fail-closed held: no thumbnails left.
- Lobby clip G421 03-11 11:55 is an EMPTY lobby (room occupancy 0 → honest TC0421 got ghost_session) → switched to 03-15 15:15 (busiest annotated slot); demo-day check-ins = measured room peak.
- New: `scripts/demo_check.py` (seed §22 demo into fresh SQLite, walk the API, assert queue order / scoping). 28 tests pass.
- Results: `docs/ACCURACY_REPORT.md`. Honest FP 0 %; all blatant fraud caught; subtle R2b/R3b missed (on purpose); head-count MAE 2.2 (target 1.5 not met); edge CPU 2.3 fps on 2 vCPU.

Colab VM (T4, `finetune_heads_colab.ipynb`, authuser=5) holds `/content/sakshi` with all clips + edge_state. Logs: `/content/gpu.log`, `/content/rerun.log`, `/content/rerun2.log`, `/content/demo.log`. If the VM is recycled: re-run `scripts/colab_gpu_runs.sh` (clips + models come from Drive; the new lobby clip is re-made by `redteam.runner prepare`).

## 5. What is LEFT (in order)

1. Fetch the long kernel's output, copy `results/` in, update DECISIONS / README / this file, and commit (§0 step 2).
   This also closes old items: measured `data/demo/packets.jsonl` + `device_keys.json` come home, the TC0421 clean
   check and queue order are re-run by `demo_check`, and the exits are re-measured.
2. Ask the user whether `docker compose up` and a dashboard click-through may run locally; otherwise leave them for
   the demo machine.
3. **Own college footage** (when the user provides it): add camera YAMLs, label a 5-min clip, re-run `eval/robustness`
   and `metrics`, and report it separately.
4. **Optional / not done:** a MOT17 tracker benchmark (ByteTrack idea from the user's link; research-use data, keep it
   out of the repo); SMS gateway integration (only the builder exists); SCB-Dataset or CrowdHuman extra fine-tune;
   a real QP equipment list (the inventory is mock); a cited ₹ rate (₹50 assumption in `cloud/engines/risk.py`);
   Alembic migrations; face-blur miss rate on own footage; Raspberry Pi tier.

## 6. Gotchas learned the hard way

- **Colab terminal:** click inside it before typing. If the panel closes, keystrokes land in the notebook and create stray cells.
- **Background jobs in the Colab terminal:** use `nohup … < /dev/null &`. ffmpeg reads stdin (`-nostdin` is now in code), otherwise the job gets "Stopped".
- **Clip writes are atomic** (`.part.mp4` → rename). Never run two `prepare`s at once.
- **Colab CPU (2 vCPU) runs RF-DETR at only ~0.5–1.4 fps.** Batch runs use the T4 (`SAKSHI_GPU=1`) and report the provider. CPU fps is benchmarked separately.
- **All wall-clock values are IST** (`edge/__init__.py::IST`). Colab is UTC.
- **Demo timeline:** MEVA 2018-03-11 footage is re-stamped onto 2026-10-19. The lobby clip (11:55 slot) is stamped 12:00 to pair with the door clip.
- **Colab's "Notebook not authored by Google" dialog:** click Run anyway (it's our own repo).
- **The browser `find` tool can hit rate limits.** Prefer `get_page_text` / `javascript_tool`.
- **Kaggle:** `kernels logs` / `kernels output` only return a log after the run ends. The live log is in the browser
  (kernel page → Logs). Avoid `get_page_text` on log pages, because the output is huge; use a short JS filter.
- **Kaggle image sets `UV_SYSTEM_PYTHON`:** `uv pip install` then writes into the VM's Python 3.13. `gpu_runs.sh` unsets
  it and installs with `--python /tmp/venv/bin/python`.
- Kaggle's system Python is 3.13; our pins target 3.11, hence the uv venv.
