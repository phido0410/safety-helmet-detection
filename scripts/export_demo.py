"""Tuần 9: chuẩn bị mô hình và thư viện cho ứng dụng web demo/ (PWA chạy mô hình ngay trên điện thoại bằng onnxruntime-web).

Xuất ONNX nhánh một-nhiều (mặc định của Ultralytics; NMS chạy trong demo/detector.js, giống Ultralytics predict), ghi
demo/model/config.json (tên lớp, ngưỡng vận hành từ threshold.json của tuần 8, imgsz, IoU NMS) và tải các file onnxruntime-web
đúng phiên bản ORT_VERSION vào demo/vendor/. Các file sinh ra không commit (.gitignore). Với --fixtures: ghi đầu ra thô của
ONNX và kết quả NMS của Ultralytics trên vài ảnh test vào demo/test/fixtures/ để kiểm tra hậu xử lý JS (node demo/test/run.mjs).

    .venv/bin/python scripts/export_demo.py --weights runs/M2_yolo26n/weights/best.pt --imgsz 800 \\
        --threshold reports/error_analysis/M2_yolo26n/threshold.json --fixtures
"""
import argparse, json, shutil
from pathlib import Path

import numpy as np
import requests
from ultralytics import YOLO

ORT_VERSION = "1.30.0"  # onnxruntime-web, phát hành 2026-09-14
ORT_FILES = ("ort.wasm.min.mjs", "ort-wasm-simd-threaded.mjs", "ort-wasm-simd-threaded.wasm")
OTHER_CONF, IOU, MAX_DET = 0.399, 0.7, 300  # ngưỡng chung của M2 (tuần 8), IoU và số hộp tối đa mặc định của Ultralytics
FIXTURE_IMAGES = 3
DEMO = Path("demo")

ap = argparse.ArgumentParser()
ap.add_argument("--weights", required=True)
ap.add_argument("--threshold", required=True)
ap.add_argument("--imgsz", type=int, default=640)
ap.add_argument("--data", default="data/SHEL5K_processed")
ap.add_argument("--fixtures", action="store_true")
args = ap.parse_args()

thr = json.loads(Path(args.threshold).read_text())
model = YOLO(args.weights)
names = list(model.names.values())
onnx = Path(model.export(format="onnx", imgsz=args.imgsz, simplify=True))
(DEMO / "model").mkdir(parents=True, exist_ok=True)
shutil.copy(onnx, DEMO / "model" / "model.onnx")
conf = [thr["conf"] if n == thr["cls"] else OTHER_CONF for n in names]
(DEMO / "model" / "config.json").write_text(json.dumps(
    {"weights": args.weights, "imgsz": args.imgsz, "names": names, "conf": conf, "iou": IOU, "maxDet": MAX_DET,
     "violation": names.index(thr["cls"])}, ensure_ascii=False, indent=2))

(DEMO / "vendor").mkdir(exist_ok=True)
for f in ORT_FILES:
    dst = DEMO / "vendor" / f
    if not dst.exists():
        r = requests.get(f"https://cdn.jsdelivr.net/npm/onnxruntime-web@{ORT_VERSION}/dist/{f}", timeout=600)
        r.raise_for_status()
        dst.write_bytes(r.content)
print(f"{DEMO / 'model'}: model.onnx ({onnx.stat().st_size / 1e6:.1f} MB), config.json; vendor: onnxruntime-web {ORT_VERSION}")

if args.fixtures:
    import onnxruntime as ort
    from ultralytics.data.augment import LetterBox
    from ultralytics.utils.nms import non_max_suppression
    from PIL import Image
    import torch

    out = DEMO / "test" / "fixtures"
    out.mkdir(parents=True, exist_ok=True)
    sess = ort.InferenceSession(str(DEMO / "model" / "model.onnx"))
    imgs = sorted(Path(args.data, "images", "test").glob("*.png"))[:FIXTURE_IMAGES]
    for p in imgs:
        im = np.asarray(Image.open(p).convert("RGB"))
        lb = LetterBox((args.imgsz, args.imgsz), auto=False)(image=im)
        x = (lb.transpose(2, 0, 1)[None].astype(np.float32) / 255)
        raw = sess.run(None, {sess.get_inputs()[0].name: x})[0]
        raw.astype("<f4").tofile(out / f"{p.stem}.f32")
        # NMS của Ultralytics ở ngưỡng thấp nhất rồi lọc theo ngưỡng từng lớp (NMS theo lớp nên thứ tự lọc không đổi kết quả)
        det = non_max_suppression(torch.from_numpy(raw), conf_thres=min(conf), iou_thres=IOU, max_det=MAX_DET)[0].numpy()
        det = det[det[:, 4] > np.array(conf)[det[:, 5].astype(int)]]
        (out / f"{p.stem}.json").write_text(json.dumps({"shape": list(raw.shape), "boxes": det.round(3).tolist()}))
    print(f"{len(imgs)} fixture → {out}")
