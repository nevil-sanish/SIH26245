# Cost per centre

Rule (PROMPT §15): only measured or cited numbers. Anything not yet measured or cited is marked *pending* — no guesses.

| Item | Tier T1 (existing centre PC / NVR box) | Source |
|---|---|---|
| New cameras | ₹0 where the centre already has CCTV (PMKVY 4.0 requires CCTV) | PMKVY 4.0 Guidelines |
| Edge compute | ₹0 (runs on an existing PC, ONNX Runtime CPU) | design; CPU fps in ACCURACY_REPORT |
| Edge CPU budget | measured **2.3 fps** for one door camera on Colab's 2 vCPU (RF-DETR Nano @384 + tracking + OCR), below the 5 fps the door config samples at: a 2-core box needs a faster CPU or one camera per core. Figure on a typical centre PC still to measure | `data/work/cpu_benchmark.json` |
| Bandwidth | ≈ 14.4 KB/h per camera (Whisper), ≈ 115 KB per 8-h day for a door + room pair | docs/LOW_BANDWIDTH.md (packet size measured) |
| Mobile data cost | *pending* — needs a cited per-MB tariff | — |
| Cloud | one small VM + Postgres for a state; *pending* sizing from a load test | — |
| T2 (Raspberry Pi 5 + accelerator) | not promised: model support on the accelerator is unverified | DECISIONS.md |
| Inspection savings | the risk queue orders physical visits; the saving per avoided visit needs a cited inspection cost | NSDC virtual-verification RFP (context) |
