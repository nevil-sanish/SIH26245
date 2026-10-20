
Done
- Code, M0–M7 all written: edge pipeline, cloud (FastAPI, all §9 tables and §10 endpoints, H1/H2/H3/S1–S4 engines, review workflow, mock SIDH), red-team simulator, evaluation suite, dashboard, Docker Compose, Makefile, licence check in CI.
- Docs:
  - D3 privacy note and D5 low-bandwidth note.
  - Supporting docs: architecture handoff for another AI, decisions log, references, datasets, requirement audit, demo script, camera placement, cost, third-party licences.
- Tests: 25 of 25 passed in Colab, including the 2-hour outage with zero data loss.
- Dashboard build: all 12 pages build cleanly, English and Hindi.
- Head-detector training (Colab T4): finished. Validation mAP@50 is 0.902. On the classroom CCTV test set the head-count MAE is 2.17 against about 34 heads per image. Both ONNX models are saved to Drive in MyDrive/sakshi_models.
- Demo and red-team clips: all prepared and copied to MyDrive/sakshi_work. The first real packets came back correct: clock drift 0 s, evidence OK.

Still to do (next session)
1. Check the head model before using it. On one classroom image the exported ONNX head model found only 5 heads, while PyTorch evaluation suggests it should find far more. That image may simply be the wrong one, but the preprocessing or threshold needs checking before the lab scenario can be trusted.
2. Run the scenarios. On a Colab T4, mount Drive, copy MyDrive/sakshi_models to /content/out, then run bash scripts/colab_gpu_runs.sh. That covers every video scenario, the robustness curves, accuracy metrics, ACCURACY_REPORT.md and a CPU speed benchmark.
3. Bring results back. Copy the printed results bundle into the repo (measured numbers, demo packets, dashboard lockfile, India map), then commit.
4. Your college footage. Run the same scripts on it when it's ready.
5. Repo visibility. The repo is public; the prompt says to keep it private until evaluation, so you may want to switch it to private.