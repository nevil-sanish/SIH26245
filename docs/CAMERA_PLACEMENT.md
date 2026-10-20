# Camera placement standard (one page)

Most centres already have CCTV. SAKSHI needs **two views per training room**; everything else is optional.

## 1. Door camera (enables H1 event-level attendance → evidence FULL)

- Covers the **only** entrance used by trainees (close or monitor other doors, else they are a blind spot).
- Mounted 2.5–3.5 m high, looking **across** the doorway at 30–60° down, so people walk *through* the frame, not
  straight at the lens. Whole body visible for ~2 m on both sides of the threshold.
- Door line drawn on the floor just inside the threshold (calibration UI), perpendicular to the walking path.
- ≥ 720p, ≥ 5 fps for the door ROI (edge samples 5 fps); IR on for evening batches.

## 2. Room camera (occupancy, trainer zone, equipment)

- Corner mount, 2.5–3 m, covering every seat/bench; back rows should be ≥ 20 px head height at 720p
  (seated rooms use the head detector; far rows benefit from tiling).
- Trainer zone (board / demo bench) visible and drawn as its own polygon.
- Sanctioned equipment fully visible, each machine drawn as an asset zone; monitors facing the camera where possible
  (screen-on check).
- One room = one owning camera: no zone may be counted by two cameras.

## 3. DVR / NVR

- Burned-in timestamp **ON**, large font, fixed position; draw its box in calibration (OCR clock check, H2).
- NVR clock synced by NTP; the edge additionally compares against the cloud's signed time.
- RTSP sub-stream enabled (720p is enough) or periodic DVR export folder for file-pull mode.

## 4. Calibration checklist (≈ 10 min per camera)

1. `python -m edge.calibrate --camera edge/cameras/<cam>.yaml` (or dashboard → Calibration with a snapshot).
2. Draw door line (2 clicks), room polygon, trainer zone, asset zones (+ label from the QP list), timestamp box.
3. Save → YAML; first run registers asset identity crops and the "moved" reference frame.
4. Walk in and out once: the fleet page must show 1 entry + 1 exit within a minute.

## 5. Without a door camera

The system still works at evidence **REDUCED**: occupancy-only signals (inflation, ghost session, trainee-hours
gap, burst). The dashboard shows REDUCED next to every decision and risk is discounted.
