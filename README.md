# Safety helmet detection on construction sites

Graduation thesis (Data Science, Hanoi University of Mining and Geology, 2026) by Đỗ Ngọc Phi: a YOLO26n detector for people and
safety helmets, with label auditing, error analysis, out-of-domain evaluation on Vietnamese construction-site photos, and an
on-device web demo.

**Demo: [helmetcheck.vercel.app](https://helmetcheck.vercel.app)**. The model runs in the browser (ONNX Runtime Web, WASM). Photos,
videos and the camera never leave the device. It works on iPhone and iPad with iOS 16.4+ and on desktop browsers.

## Classes

`0 helmet, 1 head, 2 head_with_helmet, 3 person_with_helmet, 4 person_no_helmet, 5 face`. A person counts as a violation when
`person_no_helmet` is detected. Any headwear that is not a safety helmet counts as no helmet (cloth hats, caps, conical hats);
motorbike helmets count as helmets.

## Results (final model M3b)

| Set | mAP@0.5 | `person_no_helmet` recall / precision |
|---|---|---|
| SHEL5K test (727 images, 6 classes) | 0.908 | 0.833 / 0.790 |
| Out-of-domain 1 (104 images, 2 person classes) | 0.806 | 0.812 / 0.669 |
| Out-of-domain 2 (109 images) | 0.716 | 0.752 / 0.486 |
| Out-of-domain 3 (104 images, final hold-out) | 0.679 | 0.607 / 0.569 |

- The violation threshold is 0.213: the highest confidence whose 95% Wilson lower bound on validation recall is ≥ 0.80. Other
  classes use 0.399.
- The target gap between in-domain and out-of-domain mAP@0.5 (≤ 0.15) is met on set 1 and missed on sets 2 and 3. On set 3, 85% of
  missed people are under 80 px tall at the 800 px input.
- On 199 person-free images (Open Images V7), 6.5% are flagged as containing a person without a helmet (95% CI 3.9–10.9%). The
  target was ≤ 5%, so this criterion is not met.
- Speed on iPhone 11 Pro Max (Safari, WASM, 800 px input): 229 ms per frame.

Model history, all on the same SHEL5K test split:

| Model | Change | Test mAP@0.5 |
|---|---|---|
| M0 | YOLO11n, defaults | 0.896 |
| M1 | YOLO26n, defaults; then image size 800 | 0.889; 0.908 |
| M2 | + class weights, targeted augmentation | 0.906 |
| M3 | + Open Images (non-helmet hats) and SH17 | 0.907 |
| M3b | + ~10% background images | 0.908 |

M3 fixed the main out-of-domain error: people in cloth hats or conical hats were taken as wearing helmets. M3b fixed M3 flagging
objects as people (47.2% → 6.5% of person-free images).

## Repository

- `scripts/`: data checks, VOC → YOLO conversion, label audit, preprocessing and splits, evaluation, thresholds, error analysis,
  out-of-domain collection and labelling, export and benchmarks.
- `notebooks/`: CV-EDA, preprocessing, and training notebooks (Google Colab, T4).
- `reports/`: every number above, as script outputs (`*_output.txt`, `*.json`, figures).
- `demo/`: the HelmetCheck web app (React + Vite). It handles photos, videos and the live camera. Tracking stops the same violator
  from being saved twice. Detections match Ultralytics (`npm test`).

Not included: images and labels (download SHEL5K from Mendeley Data; the other sets are rebuilt by `scripts/prepare_*.py`),
trained weights, and the out-of-domain news photos. Those photos are copyrighted and were used only for internal evaluation;
`reports/ood*/` lists their sources only. The thesis report is not included.

## Running

```bash
python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt   # Python 3.11, ultralytics 8.4.164

# Web demo: export a trained model to demo/public/model (--fixtures adds the test data for npm test and needs
# the preprocessed SHEL5K in data/SHEL5K_processed, built by scripts/prepare_dataset.py)
.venv/bin/python scripts/export_demo.py --weights runs/M3b_yolo26n_bg/weights/best.pt --imgsz 800 \
  --threshold reports/error_analysis/M3b_yolo26n_bg/threshold.json --fixtures
cd demo && npm install && npm test && npm run dev   # HTTPS on port 8443 (self-signed certificate)
```

## Data and licenses

- Code: [AGPL-3.0](LICENSE), because the models are trained with [Ultralytics YOLO](https://github.com/ultralytics/ultralytics) (AGPL-3.0).
- [SHEL5K](https://data.mendeley.com/datasets/9rcv8mm682/4): CC BY 4.0.
- [SH17](https://www.kaggle.com/datasets/mugheesahmad/sh17-dataset-for-ppe-detection): labels CC BY-NC-SA 4.0, images from Pexels. Because M3 and M3b are trained
  on it, use the models for non-commercial purposes only.
- [Open Images V7](https://storage.googleapis.com/openimages/web/index.html): labels CC BY 4.0; each image has its own license.
- [ONNX Runtime Web](https://github.com/microsoft/onnxruntime): MIT.
