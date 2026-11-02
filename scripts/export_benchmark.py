"""Tuần 9: chuyển trọng số sang ONNX và Core ML rồi đo độ chính xác (tập test) và tốc độ trên MacBook cho từng cách chạy.

Ultralytics 8.4 mặc định (nms=None) đánh giá và dự đoán YOLO26 bằng nhánh một-nhiều kèm NMS; mọi kết quả tuần 6–8 dùng
nhánh này, nên bản triển khai cũng xuất nhánh đó. Bảng có thêm dòng PyTorch và ONNX dùng nhánh NMS-free (nms=False) để so sánh.
Core ML được xuất hai bản: FP32 (mặc định của Ultralytics, Neural Engine không chạy được nên thực tế chạy trên CPU) và FP16
(chạy được trên Neural Engine). Độ chính xác: mAP@0.5, mAP@0.5:0.95 và Recall / Precision lớp vi phạm ở ngưỡng chính thức (threshold.json của tuần 8),
để kiểm tra việc chuyển định dạng không làm giảm chất lượng. Tốc độ: xử lý từng ảnh một (batch 1, như video), chạy làm nóng
trước, lấy thời gian tiền xử lý / suy luận / hậu xử lý Ultralytics ghi cho mỗi ảnh trên N ảnh đầu của tập test.

    .venv/bin/python scripts/export_benchmark.py --weights runs/M2_yolo26n/weights/best.pt --imgsz 800 \\
        --threshold reports/error_analysis/M2_yolo26n/threshold.json --out reports/deployment/M2_yolo26n
"""
import argparse, json, os, platform, shutil
from pathlib import Path

import numpy as np
from ultralytics import YOLO

WARMUP, N_SPEED = 10, 200

ap = argparse.ArgumentParser()
ap.add_argument("--weights", required=True)
ap.add_argument("--threshold", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--data", default="data/SHEL5K_processed/data.yaml")
ap.add_argument("--imgsz", type=int, default=640)
args = ap.parse_args()
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
thr = json.loads(Path(args.threshold).read_text())
conf_grid = np.linspace(0, 1, 1000)

pt = Path(args.weights)
# Mặc định: nhánh một-nhiều, đầu ra (1, 4 + số lớp, số anchor), NMS chạy bên ngoài. nms=False: nhánh NMS-free một-một,
# đầu ra (1, 300, 6) = x1, y1, x2, y2, độ tin cậy, lớp
# hai bản cùng tên best.onnx: xuất và đổi tên bản NMS-free trước, nếu không bản sau ghi đè bản trước
onnx_e2e = Path(shutil.move(YOLO(pt).export(format="onnx", imgsz=args.imgsz, simplify=True, nms=False), pt.with_name(f"{pt.stem}_e2e.onnx")))
onnx_path = Path(YOLO(pt).export(format="onnx", imgsz=args.imgsz, simplify=True))


def export_coreml(dst, **kw):
    if dst.exists():
        shutil.rmtree(dst)
    return Path(shutil.move(YOLO(pt).export(format="coreml", imgsz=args.imgsz, **kw), dst))


coreml32 = export_coreml(pt.with_name(f"{pt.stem}_fp32.mlpackage"))
coreml16 = export_coreml(pt.with_name(f"{pt.stem}_fp16.mlpackage"), half=True)
RUNS = [("PyTorch, CPU", pt, "cpu", {}), ("PyTorch, GPU M1 (MPS)", pt, "mps", {}),
        ("PyTorch, MPS, nhánh NMS-free", pt, "mps", {"nms": False}), ("ONNX Runtime, CPU", onnx_path, "cpu", {}),
        ("ONNX Runtime, CPU, nhánh NMS-free", onnx_e2e, "cpu", {"nms": False}),
        ("Core ML FP32 (thực tế chạy CPU)", coreml32, "cpu", {}), ("Core ML FP16 (Neural Engine)", coreml16, "cpu", {})]
images = sorted(Path(args.data).parent.glob("images/test/*.png"))[:N_SPEED]


def size_mb(p):
    return sum(f.stat().st_size for f in ([p] if p.is_file() else p.rglob("*") if p.is_dir() else [])) / 1e6


rows = []
for name, weights, device, extra in RUNS:
    model = YOLO(weights, task="detect")
    v = model.val(data=args.data, split="test", imgsz=args.imgsz, batch=1, device=device, plots=False, verbose=False,
                  project=os.environ.get("TMPDIR", "/tmp"), name="export_benchmark", exist_ok=True, **extra)
    k = list(v.box.ap_class_index).index(list(v.names.values()).index(thr["cls"]))
    j = np.abs(conf_grid - thr["conf"]).argmin()
    for im in images[:WARMUP]:
        model.predict(im, imgsz=args.imgsz, device=device, verbose=False, **extra)
    sp = np.array([[r.speed[s] for s in ("preprocess", "inference", "postprocess")]
                   for im in images for r in model.predict(im, imgsz=args.imgsz, device=device, verbose=False, **extra)])
    total = sp.sum(1)
    rows.append({"backend": name, "file": weights.name, "size_mb": round(size_mb(weights), 1),
                 "mAP50": v.box.map50, "mAP50-95": v.box.map, "recall_pri": v.box.r_curve[k, j],
                 "precision_pri": v.box.p_curve[k, j], "pre_ms": sp[:, 0].mean(), "infer_ms": sp[:, 1].mean(),
                 "post_ms": sp[:, 2].mean(), "total_ms": total.mean(), "p95_ms": np.percentile(total, 95),
                 "fps": 1000 / total.mean()})
    print(name, round(v.box.map50, 3), round(total.mean(), 1), flush=True)

base = rows[0]
lines = [f"{args.weights} → ONNX, Core ML; tập test, imgsz {args.imgsz}, batch 1; máy {platform.machine()} "
         f"({platform.mac_ver()[0] and 'macOS ' + platform.mac_ver()[0]}); lớp {thr['cls']} ở ngưỡng {thr['conf']:.3f}",
         f"Tốc độ: trung bình trên {len(images)} ảnh test sau {WARMUP} ảnh làm nóng (ms/ảnh)", ""]
for r in rows:
    lines.append(f"{r['backend']:<36} {r['file']:<20} {r['size_mb']:>5.1f} MB | mAP50 {r['mAP50']:.3f} mAP50-95 "
                 f"{r['mAP50-95']:.3f} (lệch {r['mAP50'] - base['mAP50']:+.3f}) | R/P {thr['cls']} {r['recall_pri']:.3f}/"
                 f"{r['precision_pri']:.3f} | {r['pre_ms']:.1f} + {r['infer_ms']:.1f} + {r['post_ms']:.1f} = "
                 f"{r['total_ms']:.1f} ms (p95 {r['p95_ms']:.1f}), {r['fps']:.1f} FPS")
print("\n".join(lines))
(out / "export_benchmark.txt").write_text("\n".join(lines) + "\n")
(out / "export_benchmark.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2, default=float))
for cache in Path(args.data).parent.glob("labels/*.cache"):  # giữ thư mục dữ liệu như bản đã nén
    cache.unlink()
