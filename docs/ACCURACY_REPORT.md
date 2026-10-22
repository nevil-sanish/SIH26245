# Accuracy report (D4) — auto-generated

Generated `2026-10-22T14:29:04` by `python -m eval.metrics` + `python -m eval.report`. Seeds per simulated scenario: **20**. Do not edit by hand.

Labels: **measured** = real model output on real (possibly manipulated) footage · **simulated** = red-team generator · **mock** = stand-in government data.

## Headline

| Metric | Value | Target (PROMPT §14) |
|---|---|---|
| Fraud-flag FN rate, all fraud scenarios incl. subtle variants | 13.1 % | ≤ 10 % |
| Fraud-flag FP rate on honest controls | 0.8 % | ≤ 5 % |
| Door events, any direction (P / R) — measured | 1.000 / 0.955 | ≥ 0.9 |
| Per-frame person count MAE, MEVA door clip — measured | 0.887 | ≤ 1.5 |
| Head-count MAE, SCUT-HEAD Part A test (classroom CCTV, 500 images, mean 34.4 heads) — measured in the fine-tune run (640 px, Tesla T4
Tesla T4) | 1.618 (4.5 %) | ≤ 1.5 (reference 1.23) |
| Head-count MAE, deployed **ONNX** head model, SCUT-HEAD Part A test (500 images; tile 640, threshold 0.5 chosen on 149 valid images) | 1.648 (bias -0.32) | ≤ 1.5 |

The fraud FN rate deliberately includes *subtle* variants (R1b–R3b) that sit below the detection threshold. They show where the system stops seeing fraud; the blatant cases are listed separately below.

## Head model: tiling and threshold (measured)

Threshold chosen per option on SCUT-HEAD Part A *valid*; MAE on Part A *test*. The deployed option has the lowest valid MAE. Relative error SD = SD of (predicted − true) / true per image.

| Tile | Threshold | Valid MAE | Test MAE | Test bias | Rel. error SD |
|---|---|---|---|---|---|
| none | 0.375 | 1.879 | 1.544 | -0.21 | 0.1148 |
| 640 | 0.5 | 1.671 | 1.648 | -0.32 | 0.1504 |

## Noise model used for simulated detections

door entries recall 0.905 / precision 1.000, exits recall 0.756 / precision 0.912, count MAE 0.89 — source: **measured**.

## Per-scenario confusion matrices

| Scenario | Label | n | TP | FN | TN | FP | Rate | Flags fired |
|---|---|---|---|---|---|---|---|---|
| **N-video** N-video | measured | 1 | – | – | 1 | 0 | FP 0.0 % | — |
| **N-video-lab** N-video-lab | measured | 1 | – | – | 1 | 0 | FP 0.0 % | — |
| **N1** Normal session | simulated | 20 | – | – | 20 | 0 | FP 0.0 % | — |
| **N2** Lunch break | simulated | 20 | – | – | 20 | 0 | FP 0.0 % | — |
| **N3** Trainees move to a workshop (practical slot in another room) | simulated | 20 | – | – | 19 | 1 | FP 5.0 % | unmatched_checkin |
| **R1** Bulk check-in, empty room | simulated | 20 | 20 | 0 | – | – | FN 0.0 % | burst, ghost_session, inflation, trainee_hours_gap, unmatched_checkin |
| **R1b** Bulk check-in into a half-full room (subtle) | simulated | 20 | 20 | 0 | – | – | FN 0.0 % | burst, inflation, trainee_hours_gap, unmatched_checkin |
| **R2** Proxy check-ins | simulated | 20 | 20 | 0 | – | – | FN 0.0 % | inflation, trainee_hours_gap, unmatched_checkin |
| **R2b** Mild proxying: 3 of 30 absent (subtle) | simulated | 20 | 1 | 19 | – | – | FN 95.0 % | unmatched_checkin |
| **R3** Check-in and leave | simulated | 20 | 20 | 0 | – | – | FN 0.0 % | checkin_then_leave, trainee_hours_gap, unmatched_checkin |
| **R3b** Small walk-out: 5 of 30 leave (subtle) | simulated | 20 | 15 | 5 | – | – | FN 25.0 % | checkin_then_leave, unmatched_checkin |
| **R4** Replayed footage (yesterday's DVR clip) | measured | 1 | 1 | 0 | – | – | FN 0.0 % | cross_centre_duplicate, loop |
| **R5** Same clip from two centres | measured | 1 | 1 | 0 | – | – | FN 0.0 % | cross_centre_duplicate |
| **R6** Frozen / covered camera | measured | 1 | 1 | 0 | – | – | FN 0.0 % | covered, cross_centre_duplicate, frozen |
| **R7** Ornamental equipment (14 days unused) | simulated | 20 | 20 | 0 | – | – | FN 0.0 % | ornamental_asset |
| **R7-control** Ornamental equipment (14 days unused) | simulated | 20 | – | – | 20 | 0 | FP 0.0 % | — |
| **R8** Rented-for-inspection asset | simulated | 20 | 20 | 0 | – | – | FN 0.0 % | asset_swapped |
| **R8-control** Rented-for-inspection asset | simulated | 20 | – | – | 20 | 0 | FP 0.0 % | — |
| **R9** Performing for audits | simulated | 20 | 20 | 0 | – | – | FN 0.0 % | inspection_shadow |
| **R9-control** Performing for audits | simulated | 20 | – | – | 20 | 0 | FP 0.0 % | — |

## Failures (kept on purpose)

- **N3** — Trainees move to a workshop (practical slot in another room): 1/20 honest runs falsely flagged (unmatched_checkin).
- **R2b** — Mild proxying: 3 of 30 absent (subtle): 19/20 missed.
- **R3b** — Small walk-out: 5 of 30 leave (subtle): 5/20 missed.

## Door events vs MEVA ground truth (measured)

Clip: MEVA G420 school entrance, 5 min, 2018-03-11 12:00 (re-stamped). Tolerance ±4.0 s.

| Direction | GT | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|---|
| in | 42 | 38 | 0 | 4 | 1.000 | 0.905 |
| out | 2 | 2 | 2 | 0 | 0.500 | 1.000 |

## Door crossing hysteresis sweep (measured)

`door_min_frames` = frames a track must stay on the new side before a crossing counts (5 fps door sampling). Both annotated MEVA G420 clips: busy arrival slot (entries) and the 11:15 slot (42 exits).

| door_min_frames | Clip | In GT | In P | In R | Out GT | Out P | Out R |
|---|---|---|---|---|---|---|---|
| 1 | G420_busy | 42 | 0.976 | 0.952 | 2 | 0.286 | 1.000 |
| 1 | G420_exits | 0 | 0.000 | — | 41 | 0.791 | 0.829 |
| 2 | G420_busy | 42 | 1.000 | 0.905 | 2 | 0.500 | 1.000 |
| 2 | G420_exits | 0 | 0.000 | — | 41 | 0.912 | 0.756 |
| 3 | G420_busy | 42 | 1.000 | 0.810 | 2 | 0.667 | 1.000 |
| 3 | G420_exits | 0 | 0.000 | — | 41 | 0.900 | 0.659 |
| 5 | G420_busy | 42 | 1.000 | 0.786 | 2 | 1.000 | 1.000 |
| 5 | G420_exits | 0 | 0.000 | — | 41 | 0.926 | 0.610 |

## Robustness curves (measured)

| Variant | Edge fps | Door P (any) | Door R (any) | Count MAE |
|---|---|---|---|---|
| 1080p | 3.9 | 0.977 | 0.955 | 0.914 |
| 720p | 39.99 | 1.000 | 0.955 | 0.887 |
| 360p | 49.26 | 1.000 | 0.909 | 0.901 |
| 720p_crf40 | 40.68 | 1.000 | 0.864 | 0.901 |
| 720p_lowlight | 39.87 | 0.949 | 0.841 | 0.722 |

## Bandwidth (measured from the edge outbox)

| Camera | Packets | Whisper mean B | Whisper KB/h | Observed KB/h (with Normal-tier thumbnails) |
|---|---|---|---|---|
| CAM-DOOR | 36 | 291.200 | 17.060 | 24.040 |
| CAM-ROOM | 24 | 277.800 | 16.280 | 24.540 |
| CAM-LAB | 1 | 317.000 | 18.570 | 18.570 |

## Edge runs (measured)

| Centre | Camera | Clip | Frames | fps | Detector provider | Packets | Unavailable modules |
|---|---|---|---|---|---|---|---|
| TC0421 | CAM-DOOR | G420_busy | 1501 | 4.24 | CPUExecutionProvider | 6 | ocr |
| TC0421 | CAM-ROOM | G421_room | 301 | 15.54 | CUDAExecutionProvider | 6 | ocr |
| TC0777 | CAM-DOOR | R4 | 1501 | 40.14 | CUDAExecutionProvider | 6 | ocr |
| TC0777 | CAM-DOOR | R4 | 1501 | 39.24 | CUDAExecutionProvider | 6 | ocr |
| TC0555 | CAM-ROOM | G421_room | 301 | 16.22 | CUDAExecutionProvider | 6 | ocr |
| TC0612 | CAM-ROOM | R6 | 301 | 33.08 | CUDAExecutionProvider | 6 | ocr |
| TC0198 | CAM-LAB | lab | 23 | 12.63 | CUDAExecutionProvider | 1 | ocr |

## Edge CPU throughput (measured)

Door camera, RF-DETR Nano 384, ByteTrack, all integrity checks, ONNX Runtime **CPU**: **4.24 processed frames/s** over 301 frames on the hardware below (PROMPT D1 target ≥ 1 fps per camera). Scenario runs above may use the CUDA provider for turnaround; the graph and outputs are the same.

## Hardware

Intel(R) Xeon(R) CPU @ 2.00GHz · 4 logical CPUs · ONNX Runtime CPU · Linux-6.18.48+-x86_64-with-glibc2.39

## Known limits

- MEVA is US school footage with adult actors; Indian skilling-centre footage (own recordings) will be evaluated with the same scripts and reported separately.
- Per-frame count ground truth on MEVA covers annotated actors; on the door camera that is effectively everyone in view, on the busy lobby it is not, so lobby MAE is not reported.
- The computer-lab clip (Wikimedia Commons, 11 s) yields one Whisper packet: the TC0198 run only checks that the head model, asset zones and screen-on path run end to end. Asset rules (S1 OAI, S2 identity) are evaluated by the R7/R8 simulations until a longer lab recording (own footage) exists.
- Simulated scenarios inherit the measured detector noise but not every real-world failure mode (e.g. occlusion bursts at the door).
