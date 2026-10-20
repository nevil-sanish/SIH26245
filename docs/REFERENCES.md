# References — papers, government documents and components

Everything read or relied on while building SAKSHI. Status column:
`verified` = opened/checked during the build (date in brackets), `from-prompt` = taken from `PROMPT.md`, not yet re-opened.

## 1. Problem statement and government context

| # | Document | Link | What we use it for | Status |
|---|---|---|---|---|
| G1 | SIH 2026 Problem Statement SIH26245 (MSDE, Smart Education) | sih.gov.in | Five deliverables D1–D5 | from-prompt |
| G2 | MSDE — PMKVY 4.0 Guidelines | https://www.msde.gov.in/static/uploads/2024/02/PMKVY-4.0-Guidelines_final-copy.pdf | CCTV Command Centre, virtual verification, non-compliance alerts | from-prompt |
| G3 | NSDC RFP — Virtual Verification of PMKVY Training Centres (Skill Reporter) | https://www.skillreporter.com/business-opportunities/request-for-proposal/nsdc-rfp-tender-virtual-verification-pmkvy-skill-training-centres/ | Self-assessment app, "poor" rating → physical inspection | from-prompt |
| G4 | OpenGov Asia — Skill India monitoring (AEBAS → face authentication) | https://opengovasia.com/india-expands-skill-development-network-under-skill-india-mission/ | Check-in log is our *input to verify* | from-prompt |
| G5 | NextIAS — Skilling reforms / PMKVY 4.0 blacklisting (178 TPs/TCs) | https://www.nextias.com/ca/current-affairs/10-02-2026/skilling-reforms-india | Motivation for H1 | from-prompt |
| G6 | Moneylife — CAG audit of PMKVY | https://www.moneylife.in/article/94-percentage-bank-details-missing-underage-candidates-certified-placements-unverifiable-in-pm-kaushal-vikas-yojana-cag/79358/128462.html | Same photo at multiple centres; missing biometric devices → H2 registry | from-prompt |
| G7 | Digital Personal Data Protection Act 2023 / DPDP Rules 2025 | https://en.wikipedia.org/wiki/Digital_Personal_Data_Protection_Rules,_2025 | D3 privacy note mapping | from-prompt |
| G8 | Reskilll — SIH 2026 timeline | https://blogs.reskilll.com/smart-india-hackathon-2026-launched-timeline-registration-how-to-participate/ | Schedule | from-prompt |
| G9 | FirstVidya — SIH 2026 guide | https://firstvidya.com/sih-2026-guide/ | Team/PS rules | from-prompt |

## 2. Research papers

| # | Topic | Paper | Link | Status |
|---|---|---|---|---|
| P1 | Detector | Robinson et al., *RF-DETR: Real-Time Detection Transformer*, ICLR 2026 | https://arxiv.org/abs/2511.09554 | from-prompt |
| P2 | Backbone / embeddings | Oquab et al., *DINOv2: Learning Robust Visual Features without Supervision* | https://arxiv.org/abs/2304.07193 | from-prompt |
| P3 | Detector alt | Chen et al., *LW-DETR* | https://arxiv.org/abs/2406.03459 | from-prompt |
| P4 | Detector alt | Peng et al., *D-FINE* | https://arxiv.org/abs/2410.13842 | from-prompt |
| P5 | Tracking | Zhang et al., *ByteTrack*, ECCV 2022 | https://arxiv.org/abs/2110.06864 | from-prompt |
| P6 | Tracking | Cao et al., *OC-SORT* | https://arxiv.org/abs/2203.14360 | from-prompt |
| P7 | Tracking | Aharon et al., *BoT-SORT* | https://arxiv.org/abs/2206.14651 | from-prompt |
| P8 | Small objects | Akyon et al., *SAHI: Slicing Aided Hyper Inference* | https://arxiv.org/abs/2202.06934 | from-prompt |
| P9 | Head detection | Peng et al., *Detecting Heads using Feature Refine Net and Cascaded Multi-Scale Architecture* (SCUT-HEAD) | https://arxiv.org/abs/1803.09256 | verified (2026-10-20, via dataset README citation) |
| P10 | Crowd counting | Song et al., *Rethinking Counting and Localization in Crowds* (P2PNet), ICCV 2021 | https://arxiv.org/abs/2107.12746 | from-prompt |
| P11 | Classroom occupancy | *Edge-Based Transfer Learning for Classroom Occupancy Detection in a Smart Campus Context*, Sensors 2022 (MAE 1.23) | https://doi.org/10.3390/s22103692 · https://doaj.org/article/29a73b80257f4d7d9e118c6befd60ca8 | from-prompt |
| P12 | Open-vocab detection | Liu et al., *Grounding DINO* | https://arxiv.org/abs/2303.05499 | from-prompt |
| P13 | Open-vocab detection | Minderer et al., *Scaling Open-Vocabulary Object Detection* (OWLv2) | https://arxiv.org/abs/2306.09683 | from-prompt |
| P14 | Segmentation | *SAM 3* | https://arxiv.org/abs/2511.16719 | from-prompt |
| P15 | Camera tamper | *Unified Camera Tamper Detection Based on Edge and Object Information*, Sensors 2015 | https://doi.org/10.3390/s150510315 | from-prompt |
| P16 | Camera tamper | *A Survey of Feature Types and Their Contributions for Camera Tampering Detection* | https://arxiv.org/abs/2310.07886 | from-prompt |
| P17 | Camera tamper | *Comparative study and enhancement of Camera Tampering Detection algorithms* | https://arxiv.org/abs/1608.02385 | from-prompt |
| P18 | Replay / spoofing | *Live Spoofing Detection for Automatic Human Activity Recognition Applications*, Sensors 2021 | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8587143/ | from-prompt |
| P19 | Replay / loop | IETF draft *MVPS Video-Surveillance and CCTV Profile: Fleet-Coherence Detection of Feed Replay and Loop Injection* | https://datatracker.ietf.org/doc/draft-melegassi-ippm-mvps-video-surveillance/ | from-prompt |
| P20 | Perceptual hashing | Zauner, *Implementation and Benchmarking of Perceptual Image Hash Functions*, 2010 | — | from-prompt |
| P21 | Change-point | Killick, Fearnhead & Eckley, *Optimal detection of changepoints with a linear computational cost* (PELT), JASA 2012 | https://doi.org/10.1080/01621459.2012.737745 | from-prompt |
| P22 | Change-point | Truong, Oudre & Vayatis, *Selective review of offline change point detection methods* (ruptures), Signal Processing 2020 | https://arxiv.org/abs/1801.00826 | from-prompt |
| P23 | Matching | Kuhn, *The Hungarian Method for the Assignment Problem*, 1955 | https://doi.org/10.1002/nav.3800020109 | from-prompt |
| P24 | Uncertainty | Angelopoulos & Bates, *A Gentle Introduction to Conformal Prediction* | https://arxiv.org/abs/2107.07511 | from-prompt |
| P25 | Classroom video | Sharma et al., *EduNet: A New Video Dataset for Understanding Human Activity in the Classroom Environment*, Sensors 2021 | https://www.mdpi.com/1424-8220/21/17/5699 | verified (2026-10-20) |
| P26 | Classroom behaviour | Yang & Wang, *SCB-Dataset3: A Benchmark for Detecting Student Classroom Behavior* | https://arxiv.org/abs/2310.02522 | verified (2026-10-20) |
| P27 | Multi-camera | Chavdarova et al., *WILDTRACK: A Multi-camera HD Dataset for Dense Unscripted Pedestrian Detection*, CVPR 2018 | https://arxiv.org/abs/1707.09299 | verified (2026-10-20) |
| P28 | Surveillance video | Corona et al., *MEVA: A Large-Scale Multiview, Multimodal Video Dataset for Activity Detection*, WACV 2021 | https://arxiv.org/abs/2012.00914 | from-search |

## 3. Open-source components (licences checked on PyPI, 2026-10-20)

| Component | Version checked | Licence | Repo |
|---|---|---|---|
| rfdetr | 1.11.2 | Apache-2.0 (N–L weights; XL/2XL are PML — not used) | https://github.com/roboflow/rf-detr |
| supervision | 0.31.0 | MIT | https://github.com/roboflow/supervision |
| trackers | 2.6.1 | Apache-2.0 | https://github.com/roboflow/trackers |
| onnxruntime | 1.31.0 | MIT | https://github.com/microsoft/onnxruntime |
| sahi | 0.12.8 | MIT | https://github.com/obss/sahi |
| transformers (OWLv2, DINOv2) | 5.20.2 | Apache-2.0 | https://github.com/huggingface/transformers |
| paddleocr | 3.7.0 | Apache-2.0 | https://github.com/PaddlePaddle/PaddleOCR |
| imagehash | 4.3.2 | BSD-2-Clause | https://github.com/JohannesBuchner/imagehash |
| ruptures | 1.1.10 | BSD-2-Clause (needs Python < 3.14) | https://github.com/deepcharles/ruptures |
| deface | 1.5.0 | MIT | https://github.com/ORB-HD/deface |
| pynacl | 1.6.2 | Apache-2.0 | https://github.com/pyca/pynacl |
| fastapi | 0.151.0 | MIT | https://github.com/fastapi/fastapi |
| **Banned** | — | AGPL/GPL | Ultralytics YOLO, BoxMOT, YOLO-World |

Pinned versions actually installed live in `edge/requirements.txt`, `cloud/requirements.txt` and `THIRD_PARTY_LICENSES.md`.

## 4. Competitor repos (ideas only — no licence, never copied)

See `PROMPT.md` §4 for the list and the idea taken from each. None of their code, prompts, UI or text is in this repo.
