"""Đánh giá lại trọng số trên tập val ở máy cá nhân và in Precision/Recall của một lớp theo ngưỡng tin cậy (IoU 0,5).

Dùng để (1) xác nhận kết quả huấn luyện trên Colab tái lập được, (2) xem Recall lớp vi phạm thay đổi theo ngưỡng.
Với --split test (tuần 7): đánh giá trên tập test, lớp vi phạm dùng ngưỡng đã chọn trên val (thresholds_output.txt, phải
chạy val trước), không chọn lại ngưỡng trên test; ghi test_output.txt và test_metrics.json.

    .venv/bin/python scripts/eval_thresholds.py --weights runs/M0_yolo11n/weights/best.pt --out reports/training/M0_yolo11n
    (thêm --imgsz 800 cho mô hình huấn luyện ở ảnh 800, --split test cho tập test)
"""
import argparse, json, os, re
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
ap.add_argument("--imgsz", type=int, default=640)  # đánh giá ở đúng kích thước ảnh đã huấn luyện
ap.add_argument("--split", default="val", choices=["val", "test"])
args = ap.parse_args()

model = YOLO(args.weights)
v = model.val(data=args.data, split=args.split, imgsz=args.imgsz, batch=16, plots=False, verbose=False, device="mps",
              project=os.environ.get("TMPDIR", "/tmp"), name="eval_thresholds", exist_ok=True)
k = list(v.box.ap_class_index).index(list(model.names.values()).index(args.cls))
conf = np.linspace(0, 1, 1000)  # lưới ngưỡng Ultralytics dùng cho p_curve, r_curve
i = smooth(v.box.f1_curve.mean(0), 0.1).argmax()  # cách Ultralytics chọn ngưỡng chung (ap_per_class)
f1_conf = conf[i]
assert (v.box.p[k], v.box.r[k]) == (v.box.p_curve[k, i], v.box.r_curve[k, i])

lines = [f"{'Đánh giá lại' if args.split == 'val' else 'Đánh giá'} {args.weights} trên tập {args.split}: mAP@0.5 = {v.box.map50:.3f}, mAP@0.5:0.95 = {v.box.map:.3f}",
         f"Ngưỡng chung (F1 trung bình 6 lớp lớn nhất): {f1_conf:.3f}", f"{args.cls}, IoU 0,5:"]
for c in (0.10, 0.15, 0.20, 0.25, f1_conf):
    j = np.abs(conf - c).argmin()
    lines.append(f"  conf {c:.3f}: Recall {v.box.r_curve[k, j]:.3f}  Precision {v.box.p_curve[k, j]:.3f}")
if args.split == "val":
    j = np.where(v.box.r_curve[k] >= args.target)[0].max()
    lines.append(f"  ngưỡng lớn nhất còn Recall >= {args.target:.2f}: conf {conf[j]:.3f}, Precision {v.box.p_curve[k, j]:.3f}")
    out_name = "thresholds_output.txt"
else:
    val_txt = Path(args.out, "thresholds_output.txt").read_text()
    val_conf = float(re.search(r"Recall >= [\d.]+: conf ([\d.]+)", val_txt)[1])
    j = np.abs(conf - val_conf).argmin()
    r_at, p_at = v.box.r_curve[k, j], v.box.p_curve[k, j]
    lines.append(f"  ngưỡng chọn trên val (Recall >= {args.target:.2f}) {val_conf:.3f}: Recall {r_at:.3f}  Precision {p_at:.3f}")
    out_name = "test_output.txt"
    Path(args.out, "test_metrics.json").write_text(json.dumps(
        {"weights": args.weights, "split": "test", "imgsz": args.imgsz, "results": v.results_dict,
         "per_class": v.summary(), "val_conf_R80": val_conf, "R_at_val_conf": r_at, "P_at_val_conf": p_at},
        ensure_ascii=False, indent=2, default=lambda o: o.item()))
print("\n".join(lines))
Path(args.out, out_name).write_text("\n".join(lines) + "\n")
for cache in Path(args.data).parent.glob("labels/*.cache"):  # giữ thư mục dữ liệu như bản đã nén
    cache.unlink()
