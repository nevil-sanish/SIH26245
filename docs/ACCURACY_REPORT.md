# Accuracy report (D4) — auto-generated

Generated `2026-10-20T15:59:42` by `python -m eval.metrics` + `python -m eval.report`. Seeds per simulated scenario: **20**. Do not edit by hand.

Labels: **measured** = real model output on real (possibly manipulated) footage · **simulated** = red-team generator · **mock** = stand-in government data.

## Headline

| Metric | Value | Target (PROMPT §14) |
|---|---|---|
| Fraud-flag FN rate, all fraud scenarios incl. subtle variants | 21.9 % | ≤ 10 % |
| Fraud-flag FP rate on honest controls | 0.0 % | ≤ 5 % |
| Door events, any direction (P / R) — measured | 0.863 / 1.000 | ≥ 0.9 |
| Per-frame person count MAE, MEVA door clip — measured | 0.894 | ≤ 1.5 |
| Head-count MAE, SCUT-HEAD Part A test (classroom CCTV, 500 images, mean 34.4 heads) — measured in Colab | 2.168 (5.9 %) | ≤ 1.5 (reference 1.23) |
| Head-count MAE, deployed **ONNX** head model, SCUT-HEAD Part A test (500 images) | 2.206 at thr 0.35 (best 1.862 at 0.3) | ≤ 1.5 |

The fraud FN rate deliberately includes *subtle* variants (R1b–R3b) that sit below the detection threshold. They show where the system stops seeing fraud; the blatant cases are listed separately below.

## Noise model used for simulated detections

door recall 1.000, door precision 0.863, count MAE 0.89 — source: **measured**.

## Per-scenario confusion matrices

| Scenario | Label | n | TP | FN | TN | FP | Rate | Flags fired |
|---|---|---|---|---|---|---|---|---|
| **N-video** N-video | measured | 1 | – | – | 1 | 0 | FP 0.0 % | — |
| **N-video-lab** N-video-lab | measured | 1 | – | – | 1 | 0 | FP 0.0 % | — |
| **N1** Normal session | simulated | 20 | – | – | 20 | 0 | FP 0.0 % | — |
| **N2** Lunch break | simulated | 20 | – | – | 20 | 0 | FP 0.0 % | — |
| **N3** Trainees move to a workshop (practical slot in another room) | simulated | 20 | – | – | 20 | 0 | FP 0.0 % | — |
| **R1** Bulk check-in, empty room | simulated | 20 | 20 | 0 | – | – | FN 0.0 % | burst, ghost_session, inflation, trainee_hours_gap, unmatched_checkin |
| **R1b** Bulk check-in into a half-full room (subtle) | simulated | 20 | 20 | 0 | – | – | FN 0.0 % | burst, inflation, trainee_hours_gap, unmatched_checkin |
| **R2** Proxy check-ins | simulated | 20 | 20 | 0 | – | – | FN 0.0 % | inflation, trainee_hours_gap, unmatched_checkin |
| **R2b** Mild proxying: 3 of 30 absent (subtle) | simulated | 20 | 0 | 20 | – | – | FN 100.0 % | — |
| **R3** Check-in and leave | simulated | 20 | 20 | 0 | – | – | FN 0.0 % | checkin_then_leave, trainee_hours_gap |
| **R3b** Small walk-out: 5 of 30 leave (subtle) | simulated | 20 | 0 | 20 | – | – | FN 100.0 % | — |
| **R4** Replayed footage (yesterday's DVR clip) | measured | 1 | 1 | 0 | – | – | FN 0.0 % | clock_drift, cross_centre_duplicate, loop |
| **R5** Same clip from two centres | measured | 1 | 1 | 0 | – | – | FN 0.0 % | cross_centre_duplicate |
| **R6** Frozen / covered camera | measured | 1 | 1 | 0 | – | – | FN 0.0 % | clock_non_monotonic, covered, cross_centre_duplicate, frozen |
| **R7** Ornamental equipment (14 days unused) | simulated | 20 | 20 | 0 | – | – | FN 0.0 % | ornamental_asset |
| **R7-control** Ornamental equipment (14 days unused) | simulated | 20 | – | – | 20 | 0 | FP 0.0 % | — |
| **R8** Rented-for-inspection asset | simulated | 20 | 20 | 0 | – | – | FN 0.0 % | asset_swapped |
| **R8-control** Rented-for-inspection asset | simulated | 20 | – | – | 20 | 0 | FP 0.0 % | — |
| **R9** Performing for audits | simulated | 20 | 20 | 0 | – | – | FN 0.0 % | inspection_shadow |
| **R9-control** Performing for audits | simulated | 20 | – | – | 20 | 0 | FP 0.0 % | — |

## Failures (kept on purpose)

- **R2b** — Mild proxying: 3 of 30 absent (subtle): 20/20 missed.
- **R3b** — Small walk-out: 5 of 30 leave (subtle): 20/20 missed.

## Door events vs MEVA ground truth (measured)

Clip: MEVA G420 school entrance, 5 min, 2018-03-11 12:00 (re-stamped). Tolerance ±4.0 s.

| Direction | GT | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|---|
| in | 42 | 42 | 1 | 0 | 0.977 | 1.000 |
| out | 2 | 2 | 6 | 0 | 0.250 | 1.000 |

## Robustness curves (measured)

| Variant | Edge fps | Door P (any) | Door R (any) | Count MAE |
|---|---|---|---|---|
| 1080p | 18.94 | 0.800 | 1.000 | 0.921 |
| 720p | 33.76 | 0.863 | 1.000 | 0.894 |
| 360p | 47.1 | 0.936 | 1.000 | 0.841 |
| 720p_crf40 | 35.26 | 0.863 | 1.000 | 0.921 |
| 720p_lowlight | 34.39 | 0.913 | 0.955 | 0.715 |

## Bandwidth (measured from the edge outbox)

| Camera | Packets | Whisper mean B | Whisper KB/h | Observed KB/h (with Normal-tier thumbnails) |
|---|---|---|---|---|
| CAM-DOOR | 36 | 324.400 | 19.010 | 19.010 |
| CAM-ROOM | 24 | 286.800 | 16.810 | 16.810 |
| CAM-LAB | 1 | 322.000 | 18.870 | 18.870 |

## Edge runs (measured)

| Centre | Camera | Clip | Frames | fps | Detector provider | Packets | Unavailable modules |
|---|---|---|---|---|---|---|---|
| TC0421 | CAM-DOOR | G420_busy | 1501 | 34.73 | CUDAExecutionProvider | 6 | faceblur |
| TC0421 | CAM-ROOM | G421_room | 301 | 13.14 | CUDAExecutionProvider | 6 | faceblur |
| TC0777 | CAM-DOOR | R4 | 1501 | 34.37 | CUDAExecutionProvider | 6 | faceblur |
| TC0777 | CAM-DOOR | R4 | 1501 | 34.16 | CUDAExecutionProvider | 6 | faceblur |
| TC0555 | CAM-ROOM | G421_room | 301 | 13.3 | CUDAExecutionProvider | 6 | faceblur |
| TC0612 | CAM-ROOM | R6 | 301 | 29.44 | CUDAExecutionProvider | 6 | faceblur |
| TC0198 | CAM-LAB | lab | 23 | 15.6 | CUDAExecutionProvider | 1 | faceblur |

## Edge CPU throughput (measured)

Door camera, RF-DETR Nano 384, ByteTrack, all integrity checks, ONNX Runtime **CPU**: **2.3 processed frames/s** over 301 frames on the hardware below (PROMPT D1 target ≥ 1 fps per camera). Scenario runs above may use the CUDA provider for turnaround; the graph and outputs are the same.

## Hardware

Intel(R) Xeon(R) CPU @ 2.00GHz · 2 logical CPUs · ONNX Runtime CPU · Linux-6.6.122+-x86_64-with-glibc2.39

## Known limits

- MEVA is US school footage with adult actors; Indian skilling-centre footage (own recordings) will be evaluated with the same scripts and reported separately.
- Per-frame count ground truth on MEVA covers annotated actors; on the door camera that is effectively everyone in view, on the busy lobby it is not, so lobby MAE is not reported.
- Simulated scenarios inherit the measured detector noise but not every real-world failure mode (e.g. occlusion bursts at the door).
