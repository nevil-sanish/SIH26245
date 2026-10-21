"""Render data/work/accuracy.json → docs/ACCURACY_REPORT.md (D4). Never hand-edit the report.

    python -m eval.report
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _f(v, pct=False):
    if v is None:
        return "—"
    return f"{v * 100:.1f} %" if pct else (f"{v:.3f}" if isinstance(v, float) else str(v))


def render(r: dict) -> str:
    L = ["# Accuracy report (D4) — auto-generated", "",
         f"Generated `{r['generated']}` by `python -m eval.metrics` + `python -m eval.report`. "
         f"Seeds per simulated scenario: **{r['seeds']}**. Do not edit by hand.", "",
         "Labels: **measured** = real model output on real (possibly manipulated) footage · "
         "**simulated** = red-team generator · **mock** = stand-in government data.", ""]
    o = r["overall"]
    L += ["## Headline", "",
          "| Metric | Value | Target (PROMPT §14) |", "|---|---|---|",
          f"| Fraud-flag FN rate, all fraud scenarios incl. subtle variants | {_f(o['fraud_fn_rate'], True)} | ≤ 10 % |",
          f"| Fraud-flag FP rate on honest controls | {_f(o['honest_fp_rate'], True)} | ≤ 5 % |"]
    if r.get("door"):
        d = r["door"]
        L.append(f"| Door events, any direction (P / R) — measured | {_f(d['any_direction']['precision'])} / "
                 f"{_f(d['any_direction']['recall'])} | ≥ 0.9 |")
    if r.get("count_door_clip"):
        L.append(f"| Per-frame person count MAE, MEVA door clip — measured | {_f(r['count_door_clip']['mae'])} | ≤ 1.5 |")
    hm = r.get("head_model")
    if hm and isinstance(hm.get("test_A_classroom"), dict):
        a = hm["test_A_classroom"]
        L.append(f"| Head-count MAE, SCUT-HEAD Part A test (classroom CCTV, {a['images']} images, "
                 f"mean {a['mean_heads']:.1f} heads) — measured in Colab | {_f(a['count_mae'])} "
                 f"({a['count_mae_pct']:.1f} %) | ≤ 1.5 (reference 1.23) |")
    ho = r.get("head_onnx")
    if ho:
        best = min(ho["mae_by_threshold"], key=ho["mae_by_threshold"].get)
        L.append(f"| Head-count MAE, deployed **ONNX** head model, SCUT-HEAD Part A test ({ho['images']} images) | "
                 f"{ho['mae_by_threshold'].get('0.35', ho['mae_by_threshold'].get(0.35))} at thr 0.35 (best {ho['mae_by_threshold'][best]} at {best}) | ≤ 1.5 |")
    L += ["", "The fraud FN rate deliberately includes *subtle* variants (R1b–R3b) that sit below the "
          "detection threshold. They show where the system stops seeing fraud; the blatant cases are "
          "listed separately below.", ""]

    L += ["## Noise model used for simulated detections", "",
          f"door recall {r['noise_model']['door_recall']:.3f}, door precision {r['noise_model']['door_precision']:.3f}, "
          f"count MAE {r['noise_model']['count_mae']:.2f} — source: **{r['noise_model']['source']}**.", ""]

    L += ["## Per-scenario confusion matrices", "",
          "| Scenario | Label | n | TP | FN | TN | FP | Rate | Flags fired |", "|---|---|---|---|---|---|---|---|---|"]
    for sid, v in r["confusion"].items():
        if v["kind"] == "fraud":
            L.append(f"| **{sid}** {v['name']} | {v['label']} | {v['n']} | {v['TP']} | {v['FN']} | – | – | "
                     f"FN {_f(v['fn_rate'], True)} | {', '.join(v['fired']) or '—'} |")
        else:
            L.append(f"| **{sid}** {v['name']} | {v['label']} | {v['n']} | – | – | {v['TN']} | {v['FP']} | "
                     f"FP {_f(v['fp_rate'], True)} | {', '.join(v['false_flags']) or '—'} |")
    misses = [(s, v) for s, v in r["confusion"].items() if v.get("FN") or v.get("FP")]
    L += ["", "## Failures (kept on purpose)", ""]
    if misses:
        for s, v in misses:
            L.append(f"- **{s}** — {v['name']}: " + (f"{v['FN']}/{v['n']} missed." if v["kind"] == "fraud"
                                                      else f"{v['FP']}/{v['n']} honest runs falsely flagged ({', '.join(v['false_flags'])})."))
    else:
        L.append("- none in this run")

    if r.get("door"):
        d = r["door"]
        L += ["", "## Door events vs MEVA ground truth (measured)", "",
              f"Clip: MEVA G420 school entrance, 5 min, 2018-03-11 12:00 (re-stamped). Tolerance ±{d['tolerance_s']} s.", "",
              "| Direction | GT | TP | FP | FN | Precision | Recall |", "|---|---|---|---|---|---|---|"]
        for k in ("in", "out"):
            x = d[k]
            L.append(f"| {k} | {x['gt']} | {x['tp']} | {x['fp']} | {x['fn']} | {_f(x['precision'])} | {_f(x['recall'])} |")
    if r.get("door_sweep"):
        L += ["", "## Door crossing hysteresis sweep (measured)", "",
              "`door_min_frames` = frames a track must stay on the new side before a crossing counts (5 fps door sampling). "
              "Both annotated MEVA G420 clips: busy arrival slot (entries) and the 11:15 slot (42 exits).", "",
              "| door_min_frames | Clip | In GT | In P | In R | Out GT | Out P | Out R |", "|---|---|---|---|---|---|---|---|"]
        for v in r["door_sweep"]:
            i, o = v["in"], v["out"]
            L.append(f"| {v['door_min_frames']} | {v['clip']} | {i['gt']} | {_f(i['precision'])} | {_f(i['recall'])} | "
                     f"{o['gt']} | {_f(o['precision'])} | {_f(o['recall'])} |")
    if r.get("robustness"):
        L += ["", "## Robustness curves (measured)", "",
              "| Variant | Edge fps | Door P (any) | Door R (any) | Count MAE |", "|---|---|---|---|---|"]
        for v in r["robustness"]:
            L.append(f"| {v['variant']} | {v['fps_measured']} | {_f(v['door_any']['precision'])} | "
                     f"{_f(v['door_any']['recall'])} | {_f(v['count']['mae'])} |")
    if r.get("bandwidth"):
        L += ["", "## Bandwidth (measured from the edge outbox)", "",
              "| Camera | Packets | Whisper mean B | Whisper KB/h | Observed KB/h (with Normal-tier thumbnails) |",
              "|---|---|---|---|---|"]
        for cam, b in r["bandwidth"].items():
            L.append(f"| {cam} | {b['packets']} | {_f(b['whisper_mean_B'])} | {_f(b['whisper_KB_per_hour'])} | "
                     f"{_f(b['observed_KB_per_hour'])} |")
    if r.get("edge_runs"):
        L += ["", "## Edge runs (measured)", "", "| Centre | Camera | Clip | Frames | fps | Detector provider | Packets | Unavailable modules |",
              "|---|---|---|---|---|---|---|---|"]
        for e in r["edge_runs"]:
            L.append(f"| {e['centre']} | {e['camera']} | {e['clip']} | {e['frames']} | {e['fps_measured']} | "
                     f"{e.get('provider', 'CPUExecutionProvider')} | {e['packets']} | {', '.join(e['unavailable']) or '—'} |")
    if r.get("cpu_benchmark"):
        b = r["cpu_benchmark"]
        L += ["", "## Edge CPU throughput (measured)", "",
              f"Door camera, RF-DETR Nano 384, ByteTrack, all integrity checks, ONNX Runtime **CPU**: "
              f"**{b.get('fps_measured')} processed frames/s** over {b.get('frames')} frames on the hardware below "
              f"(PROMPT D1 target ≥ 1 fps per camera). Scenario runs above may use the CUDA provider for turnaround; "
              f"the graph and outputs are the same."]
    L += ["", "## Hardware", "", r.get("hardware", "—"), "",
          "## Known limits", "",
          "- MEVA is US school footage with adult actors; Indian skilling-centre footage (own recordings) will be "
          "evaluated with the same scripts and reported separately.",
          "- Per-frame count ground truth on MEVA covers annotated actors; on the door camera that is effectively "
          "everyone in view, on the busy lobby it is not, so lobby MAE is not reported.",
          "- Simulated scenarios inherit the measured detector noise but not every real-world failure mode "
          "(e.g. occlusion bursts at the door)."]
    return "\n".join(L) + "\n"


def main():
    r = json.loads((ROOT / "data" / "work" / "accuracy.json").read_text())
    (ROOT / "docs" / "ACCURACY_REPORT.md").write_text(render(r))
    print("wrote docs/ACCURACY_REPORT.md")


if __name__ == "__main__":
    main()
