# SAKSHI head-detector fine-tune (RF-DETR Nano on SCUT-HEAD) for a Kaggle T4 kernel (internet + GPU on).
# Port of models/finetune_heads_colab.ipynb; changes: 640 px (was 512), threshold picked on the Part A (classroom)
# images of valid only, data in /tmp, outputs in /kaggle/working/out (attach that kernel as input to scripts/gpu_runs.sh).
import os, sys, glob, json, shutil, random, subprocess, xml.etree.ElementTree as ET
from pathlib import Path

def sh(c, check=True):
    print("$", c, flush=True)
    r = subprocess.run(c, shell=True)
    if check and r.returncode:
        raise SystemExit(f"FAILED ({r.returncode}): {c}")

# Data + checkpoints in /tmp (not saved); only /kaggle/working/out is kept as kernel output.
W = Path('/tmp/work'); SCUT = W / 'scut'; OUT = Path('/kaggle/working/out'); TRAIN = W / 'train_heads'
W.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)
sh("nvidia-smi -L")
sh('pip install -q "rfdetr[train,onnx]==1.11.2" gdown==5.2.0 patool==4.0.1')
sh("apt-get -qq install -y unrar >/dev/null 2>&1 || true", check=False)

# 1. SCUT-HEAD (research use only; never redistributed).
SCUT.mkdir(exist_ok=True)
for name, fid in [('PartA', '1yaOF9os5wPVNNG4GVzNyULLVe74vdrBE'), ('PartB', '1LZ_KlTPStDEcqycfqUkDkqQ-aNMMC3cl')]:
    if not glob.glob(str(SCUT / f'*{name}*')):
        sh(f"gdown --fuzzy 'https://drive.google.com/open?id={fid}' -O '{SCUT / (name + '.archive')}'")
import patoolib
for f in list(SCUT.glob('*.archive')):
    patoolib.extract_archive(str(f), outdir=str(SCUT / f.stem), verbosity=-1)
sh(f"find {SCUT} -maxdepth 3 -type d | head -30")

# 2. Pascal VOC -> COCO in RF-DETR's folder layout (train/ valid/ test/).
def voc_root(part):
    for p in (SCUT / part).rglob('JPEGImages'):
        return p.parent
    raise FileNotFoundError(part)

def ids(root, split):
    f = root / 'ImageSets' / 'Main' / f'{split}.txt'
    return [l.strip() for l in f.read_text().split() if l.strip()]

def to_coco(items, out_dir):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    images, anns, aid = [], [], 1
    for iid, (root, stem) in enumerate(items, 1):
        x = ET.parse(root / 'Annotations' / f'{stem}.xml').getroot()
        w, h = int(x.find('size/width').text), int(x.find('size/height').text)
        fname = f'{root.parent.name}_{stem}.jpg'
        shutil.copy(root / 'JPEGImages' / f'{stem}.jpg', out / fname)
        images.append({'id': iid, 'file_name': fname, 'width': w, 'height': h})
        for o in x.findall('object'):
            b = o.find('bndbox')
            x1, y1, x2, y2 = (float(b.find(k).text) for k in ('xmin', 'ymin', 'xmax', 'ymax'))
            if x2 <= x1 or y2 <= y1:
                continue
            anns.append({'id': aid, 'image_id': iid, 'category_id': 1, 'bbox': [x1, y1, x2 - x1, y2 - y1],
                         'area': (x2 - x1) * (y2 - y1), 'iscrowd': 0}); aid += 1
    json.dump({'images': images, 'annotations': anns, 'categories': [{'id': 1, 'name': 'head', 'supercategory': 'person'}]},
              open(out / '_annotations.coco.json', 'w'))
    return len(images), len(anns)

A, B = voc_root('PartA'), voc_root('PartB')
trainval = [(A, s) for s in ids(A, 'trainval')] + [(B, s) for s in ids(B, 'trainval')]
random.Random(0).shuffle(trainval)
n_val = len(trainval) // 10
D = W / 'heads'
print('train', to_coco(trainval[n_val:], D / 'train'))
print('valid', to_coco(trainval[:n_val], D / 'valid'))
print('test_A (classroom CCTV)', to_coco([(A, s) for s in ids(A, 'test')], W / 'heads_testA/test'))
print('test_B (web)', to_coco([(B, s) for s in ids(B, 'test')], W / 'heads_testB/test'))
shutil.copytree(W / 'heads_testA/test', D / 'test', dirs_exist_ok=True)

# 3. Fine-tune RF-DETR Nano at 512 px.
from rfdetr import RFDETRNano
import numpy as np
from PIL import Image
EPOCHS = 30
RES = 640   # was 512 in Colab: small back-row heads get more pixels (SCUT-HEAD Part A mean 34 heads/image)
model = RFDETRNano()
model.train(dataset_dir=str(D), epochs=EPOCHS, batch_size='auto', lr=1e-4, resolution=RES,
            output_dir=str(TRAIN), checkpoint_interval=5,
            notes={'project': 'SAKSHI SIH26245', 'data': 'SCUT-HEAD A+B trainval'})

# 4. Evaluate; pick the score threshold on valid (not test).
best = sorted(glob.glob(str(TRAIN / 'checkpoint_best*.pth')))[0]
print('best checkpoint:', best)
head = RFDETRNano(pretrain_weights=best, resolution=RES)

def counts(split_dir, thr_list):
    ann = json.load(open(f'{split_dir}/_annotations.coco.json'))
    gt = {i['id']: 0 for i in ann['images']}
    for a in ann['annotations']:
        gt[a['image_id']] += 1
    pred = {t: [] for t in thr_list}; truth = []
    for im in ann['images']:
        det = head.predict(Image.open(f"{split_dir}/{im['file_name']}").convert('RGB'), threshold=min(thr_list))
        for t in thr_list:
            pred[t].append(int((det.confidence >= t).sum()))
        truth.append(gt[im['id']])
    return np.array(truth), {t: np.array(v) for t, v in pred.items()}

thrs = [round(x, 2) for x in np.arange(0.2, 0.75, 0.05)]
# Threshold chosen on the classroom (Part A) images of valid only: that is the deployment domain.
va = json.load(open(D / 'valid' / '_annotations.coco.json'))
keep = {i['id'] for i in va['images'] if i['file_name'].startswith(A.parent.name + '_')}
VA = W / 'valid_A'; VA.mkdir(exist_ok=True)
for i in va['images']:
    if i['id'] in keep:
        shutil.copy(D / 'valid' / i['file_name'], VA / i['file_name'])
json.dump({'images': [i for i in va['images'] if i['id'] in keep], 'annotations': [a for a in va['annotations'] if a['image_id'] in keep],
           'categories': va['categories']}, open(VA / '_annotations.coco.json', 'w'))
print('valid Part A images', len(keep))
gt_v, pv = counts(str(VA), thrs)
mae_v = {t: float(np.abs(pv[t] - gt_v).mean()) for t in thrs}
thr = min(mae_v, key=mae_v.get)
res = {'chosen_threshold': thr, 'valid_mae_by_threshold': mae_v, 'resolution': RES, 'epochs': EPOCHS, 'threshold_split': 'valid (Part A classroom images only)', 'valid_A_images': len(keep)}
for name, d in [('test_A_classroom', W / 'heads_testA/test'), ('test_B_web', W / 'heads_testB/test')]:
    gt, p = counts(str(d), [thr])
    res[name] = {'images': len(gt), 'mean_heads': float(gt.mean()), 'count_mae': float(np.abs(p[thr] - gt).mean()),
                 'count_mae_pct': float((np.abs(p[thr] - gt) / np.maximum(gt, 1)).mean() * 100)}
try:
    res['test_A_coco_metrics'] = {k: float(v) for k, v in head.evaluate(dataset_dir=str(D), split='test').items()}
except Exception as e:
    res['test_A_coco_metrics'] = f'evaluate() failed: {e!r}'
res['gpu'] = subprocess.run("nvidia-smi --query-gpu=name --format=csv,noheader", shell=True, capture_output=True, text=True).stdout.strip()
json.dump(res, open(OUT / 'head_metrics.json', 'w'), indent=2, default=str)
print(json.dumps(res, indent=2, default=str))

# 5. Export ONNX (head + COCO person model) into /kaggle/working/out.
p = head.export(output_dir=str(W / 'export_head'), format='onnx', fp16=False)
shutil.copy(p, OUT / 'rfdetr_nano_head.onnx')
coco = RFDETRNano()
p = coco.export(output_dir=str(W / 'export_coco'), format='onnx', fp16=False)
shutil.copy(p, OUT / 'rfdetr_nano_coco.onnx')
sh(f"cd {OUT} && sha256sum rfdetr_nano_*.onnx head_metrics.json | tee SHA256SUMS && ls -la")
print("FINETUNE_DONE")
