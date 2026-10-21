"""Đánh giá lại trọng số trên tập val ở máy cá nhân và in Precision/Recall của một lớp theo ngưỡng tin cậy (IoU 0,5).

Dùng để (1) xác nhận kết quả huấn luyện trên Colab tái lập được, (2) xem Recall lớp vi phạm thay đổi theo ngưỡng.

    .venv/bin/python scripts/eval_thresholds.py --weights runs/M0_yolo11n/weights/best.pt --out reports/training/M0_yolo11n
"""
import argparse, os
from pathlib import Path

import numpy as np
from ultralytics import YOLO
from ultralytics.utils.metrics import smooth

ap = argparse.ArgumentParser()
ap.add_argument("--weights", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--data", default="data/SHEL5K_processed/data.yaml")
ap.add_argument("--cls", default="person_no_helmet")
ap.add_argument("--target", type=float, default=0.80)
args = ap.parse_args()

model = YOLO(args.weights)
v = model.val(data=args.data, split="val", imgsz=640, batch=16, plots=False, verbose=False, device="mps",
              project=os.environ.get("TMPDIR", "/tmp"), name="eval_thresholds", exist_ok=True)
k = list(v.box.ap_class_index).index(list(model.names.values()).index(args.cls))
conf = np.linspace(0, 1, 1000)  # lưới ngưỡng Ultralytics dùng cho p_curve, r_curve
i = smooth(v.box.f1_curve.mean(0), 0.1).argmax()  # cách Ultralytics chọn ngưỡng chung (ap_per_class)
f1_conf = conf[i]
assert (v.box.p[k], v.box.r[k]) == (v.box.p_curve[k, i], v.box.r_curve[k, i])

lines = [f"Đánh giá lại {args.weights} trên tập val: mAP@0.5 = {v.box.map50:.3f}, mAP@0.5:0.95 = {v.box.map:.3f}",
         f"Ngưỡng chung (F1 trung bình 6 lớp lớn nhất): {f1_conf:.3f}", f"{args.cls}, IoU 0,5:"]
for c in (0.10, 0.15, 0.20, 0.25, f1_conf):
    j = np.abs(conf - c).argmin()
    lines.append(f"  conf {c:.3f}: Recall {v.box.r_curve[k, j]:.3f}  Precision {v.box.p_curve[k, j]:.3f}")
j = np.where(v.box.r_curve[k] >= args.target)[0].max()
lines.append(f"  ngưỡng lớn nhất còn Recall >= {args.target:.2f}: conf {conf[j]:.3f}, Precision {v.box.p_curve[k, j]:.3f}")
print("\n".join(lines))
Path(args.out, "thresholds_output.txt").write_text("\n".join(lines) + "\n")
for cache in Path(args.data).parent.glob("labels/*.cache"):  # giữ thư mục dữ liệu như bản đã nén
    cache.unlink()
