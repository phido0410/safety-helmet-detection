"""Tuần 9: chuẩn bị mô hình và thư viện cho ứng dụng web demo/ (PWA chạy mô hình ngay trên điện thoại bằng onnxruntime-web).

Xuất ONNX nhánh một-nhiều (mặc định của Ultralytics; NMS chạy trong demo/detector.js, giống Ultralytics predict), ghi
demo/public/model/config.json (tên lớp, ngưỡng vận hành từ threshold.json của tuần 8, imgsz, IoU NMS) và tải các file onnxruntime-web
đúng phiên bản ORT_VERSION vào demo/public/vendor/ (Vite phục vụ public/ ở gốc trang). Các file sinh ra không commit (.gitignore). Với --fixtures: ghi đầu ra thô của
ONNX và kết quả NMS của Ultralytics trên vài ảnh test vào demo/test/fixtures/ để kiểm tra hậu xử lý JS (node demo/test/run.mjs).
Nhiều --imgsz: cỡ đầu là cỡ dùng chính (model.onnx, dữ liệu mẫu), các cỡ sau xuất thêm model_<cỡ>.onnx để trang demo/bench.html
so tốc độ; config.json ghi mọi cỡ trong "models". Tải cả bản WebGPU của onnxruntime-web để so với WASM.

    .venv/bin/python scripts/export_demo.py --weights runs/M3_yolo26n_extra/weights/best.pt --imgsz 800 640 \\
        --threshold reports/error_analysis/M3_yolo26n_extra/threshold.json --fixtures
"""
import argparse, json, shutil
from pathlib import Path

import numpy as np
import requests
from ultralytics import YOLO

ORT_VERSION = "1.30.0"  # onnxruntime-web, phát hành 2026-09-14
ORT_FILES = ("ort.wasm.min.mjs", "ort-wasm-simd-threaded.mjs", "ort-wasm-simd-threaded.wasm",
             "ort.webgpu.min.mjs", "ort-wasm-simd-threaded.asyncify.mjs", "ort-wasm-simd-threaded.asyncify.wasm")
OTHER_CONF, IOU, MAX_DET = 0.399, 0.7, 300  # ngưỡng chung của M2 (tuần 8), IoU và số hộp tối đa mặc định của Ultralytics
FIXTURE_IMAGES = 10
LETTERBOX_SHAPES = [(416, 416), (1080, 1920), (1920, 1080), (1000, 1500), (4032, 3024), (801, 799), (720, 1281)]  # (cao, rộng)
DEMO, PUBLIC = Path("demo"), Path("demo/public")

ap = argparse.ArgumentParser()
ap.add_argument("--weights", required=True)
ap.add_argument("--threshold", required=True)
ap.add_argument("--imgsz", type=int, nargs="+", default=[640])
ap.add_argument("--data", default="data/SHEL5K_processed")
ap.add_argument("--fixtures", action="store_true")
args = ap.parse_args()

thr = json.loads(Path(args.threshold).read_text())
model = YOLO(args.weights)
names = list(model.names.values())
(PUBLIC / "model").mkdir(parents=True, exist_ok=True)
models = {}
for k, size in enumerate(args.imgsz):  # mỗi lần xuất đều ghi đè best.onnx nên chép ra ngay
    models[size] = "model.onnx" if k == 0 else f"model_{size}.onnx"
    shutil.copy(model.export(format="onnx", imgsz=size, simplify=True), PUBLIC / "model" / models[size])
conf = [thr["conf"] if n == thr["cls"] else OTHER_CONF for n in names]
(PUBLIC / "model" / "config.json").write_text(json.dumps(
    {"weights": args.weights, "name": Path(args.weights).parents[1].name.split("_")[0],  # runs/M3b_yolo26n_bg/… → M3b
     "imgsz": args.imgsz[0], "models": models, "names": names, "conf": conf, "iou": IOU,
     "maxDet": MAX_DET, "violation": names.index(thr["cls"])}, ensure_ascii=False, indent=2))
args.imgsz = args.imgsz[0]  # dữ liệu mẫu theo cỡ chính

(PUBLIC / "vendor").mkdir(exist_ok=True)
for f in ORT_FILES:
    dst = PUBLIC / "vendor" / f
    if not dst.exists():
        r = requests.get(f"https://cdn.jsdelivr.net/npm/onnxruntime-web@{ORT_VERSION}/dist/{f}", timeout=600)
        r.raise_for_status()
        dst.write_bytes(r.content)
sizes = ", ".join(f"{m} ({(PUBLIC / 'model' / m).stat().st_size / 1e6:.1f} MB)" for m in models.values())
print(f"{PUBLIC / 'model'}: {sizes}, config.json; vendor: onnxruntime-web {ORT_VERSION}")

if args.fixtures:
    import onnxruntime as ort
    from ultralytics.data.augment import LetterBox
    from ultralytics.utils.nms import non_max_suppression
    from ultralytics.utils.ops import scale_boxes
    from PIL import Image
    import torch

    out = DEMO / "test" / "fixtures"
    out.mkdir(parents=True, exist_ok=True)
    sess = ort.InferenceSession(str(PUBLIC / "model" / "model.onnx"))
    imgs = sorted(Path(args.data, "images", "test").glob("*.png"))[:FIXTURE_IMAGES]
    for p in imgs:
        im = np.asarray(Image.open(p).convert("RGB"))
        lb = LetterBox((args.imgsz, args.imgsz), auto=False)(image=im)
        x = (lb.transpose(2, 0, 1)[None].astype(np.float32) / 255)
        raw = sess.run(None, {sess.get_inputs()[0].name: x})[0]
        raw.astype("<f4").tofile(out / f"{p.stem}.f32")
        # NMS của Ultralytics ở ngưỡng thấp nhất rồi lọc theo ngưỡng từng lớp (NMS theo lớp nên thứ tự lọc không đổi kết quả)
        det = non_max_suppression(torch.from_numpy(raw), conf_thres=min(conf), iou_thres=IOU, max_det=MAX_DET)[0].numpy()
        det = det[det[:, 4] >= np.array(conf)[det[:, 5].astype(int)]]  # >= như eval_ood.py
        scaled = scale_boxes((args.imgsz, args.imgsz), det[:, :4].copy(), im.shape[:2])  # về tọa độ ảnh gốc
        (out / f"{p.stem}.json").write_text(json.dumps({"shape": list(raw.shape), "orig_hw": list(im.shape[:2]),
                                                        "boxes": det.round(3).tolist(), "scaled": scaled.round(3).tolist()}))
    # thông số letterbox của Ultralytics cho các cỡ ảnh hay gặp (ảnh dọc, ngang, lẻ) để kiểm tra phần tiền xử lý JS
    lb = LetterBox((args.imgsz, args.imgsz), auto=False)
    params = [{k: (list(v) if isinstance(v, tuple) else v) for k, v in lb.get_params({"img": np.zeros((h, w, 1), np.uint8)}).items()}
              for h, w in LETTERBOX_SHAPES]
    (out / "letterbox.json").write_text(json.dumps(params))
    print(f"{len(imgs)} fixture + {len(params)} cỡ ảnh letterbox → {out}")
