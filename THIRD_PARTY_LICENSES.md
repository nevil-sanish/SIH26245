# Third-party licences

Policy (PROMPT §1.2): MIT, Apache-2.0, BSD, ISC only — for code **and** model weights. Banned: Ultralytics
YOLOv8/11/26 and BoxMOT (AGPL-3.0), YOLO-World (GPL-3.0), react-leaflet (Hippocratic-2.1). CI gate:
`scripts/check_licenses.py`. Versions are the exact pins in `cloud/requirements.txt`, `edge/requirements.txt`,
`dashboard/package.json`.

## Models / weights

| Model | Use | Licence | Source |
|---|---|---|---|
| RF-DETR Nano (COCO) | person detection (door cameras) | Apache-2.0 | roboflow/rf-detr |
| RF-DETR Nano fine-tuned on SCUT-HEAD | head detection (seated rooms) | weights: Apache-2.0 base; **training data research-only** (see DATASETS.md) | models/finetune_heads_colab.ipynb |
| DINOv2-small | equipment identity embeddings | Apache-2.0 | facebook/dinov2-small |
| OWLv2 base patch16 ensemble | zero-shot equipment discovery | Apache-2.0 | google/owlv2-base-patch16-ensemble |
| PP-OCRv5 mobile rec (en) | DVR timestamp OCR | Apache-2.0 | PaddlePaddle/PaddleOCR |
| CenterFace (in deface) | face detection for blurring only | MIT | ORB-HD/deface |

## Python

| Package | Version | Licence |
|---|---|---|
| fastapi | 0.151.0 | MIT |
| uvicorn | 0.54.0 | BSD-3-Clause |
| pydantic | 2.14.1 | MIT |
| python-multipart | 0.0.32 | Apache-2.0 |
| sqlalchemy | 2.1.5 | MIT |
| psycopg | 3.3.6 | LGPL-3.0 (unmodified, dynamically used database driver) |
| pyjwt | 2.15.1 | MIT |
| pynacl | 1.6.2 | Apache-2.0 |
| numpy | 2.3.5 | BSD-3-Clause |
| scipy | 1.17.1 | BSD-3-Clause |
| ruptures | 1.1.10 | BSD-2-Clause |
| pyyaml | 6.0.2 | MIT |
| requests | 2.34.2 | Apache-2.0 |
| httpx | 0.28.1 | BSD-3-Clause |
| paho-mqtt | 2.1.0 | EPL-2.0 / EDL-1.0 (EDL = BSD-3-Clause; used under EDL) |
| onnxruntime | 1.31.0 | MIT |
| onnx | 1.23.2 | Apache-2.0 |
| opencv-python-headless | 5.0.0.93 | Apache-2.0 |
| supervision | 0.31.0 | MIT |
| trackers | 2.6.1 | Apache-2.0 |
| imagehash | 4.3.2 | BSD-2-Clause |
| pillow | 13.0.0 | MIT-CMU (HPND) |
| deface | 1.5.0 | MIT |
| paddlepaddle | 3.3.1 | Apache-2.0 |
| paddleocr | 3.7.0 | Apache-2.0 |
| torch / torchvision | 2.14.1 / 0.29.1 | BSD-3-Clause |
| transformers | 5.20.2 | Apache-2.0 |
| rfdetr (Colab training only) | 1.11.2 | Apache-2.0 |
| pytest | 9.1.1 | MIT |

## JavaScript (dashboard)

| Package | Version | Licence |
|---|---|---|
| next | 16.4.2 | MIT |
| react / react-dom | 19.3.1 | MIT |
| recharts | 3.10.1 | MIT |
| tailwindcss / @tailwindcss/postcss | 4.3.3 | MIT |
| typescript | 5.9.3 | Apache-2.0 |

## Containers

timescale/timescaledb (Apache-2.0 edition), eclipse-mosquitto (EPL-2.0/EDL-1.0), python:slim (PSF), node:alpine (MIT),
nginx:alpine (BSD-2-Clause).

## Data

See `docs/DATASETS.md` (MEVA CC BY 4.0 with attribution; Wikimedia Commons PD / CC BY-SA 4.0; Natural Earth public
domain; SCUT-HEAD research-only, not redistributed).
