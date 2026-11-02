"""Chọn ngưỡng tin cậy chính thức cho lớp vi phạm trên tập val (tuần 8) rồi đánh giá một lần trên tập test.

Ngưỡng = ngưỡng lớn nhất mà cận dưới khoảng tin cậy Wilson 95% của Recall (IoU 0,5) trên val vẫn ≥ mục tiêu, để còn
dư địa khi sang dữ liệu khác (tuần 7: ngưỡng chọn sát Recall = 0,80 trên val chỉ cho 0,785 trên test). Ngưỡng được áp
nguyên sang test; lần đánh giá test lưu hình của Ultralytics (ma trận nhầm lẫn, đường cong PR) vào <out>/val_test/.

    .venv/bin/python scripts/select_threshold.py --weights runs/M2_yolo26n/weights/best.pt --imgsz 800 \\
        --out reports/error_analysis/M2_yolo26n
"""
import argparse, json, os
from pathlib import Path

import numpy as np
from ultralytics import YOLO

from summarize_label_audit import wilson

ap = argparse.ArgumentParser()
ap.add_argument("--weights", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--data", default="data/SHEL5K_processed/data.yaml")
ap.add_argument("--cls", default="person_no_helmet")
ap.add_argument("--target", type=float, default=0.80)
ap.add_argument("--imgsz", type=int, default=640)
args = ap.parse_args()
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)

model = YOLO(args.weights)
conf = np.linspace(0, 1, 1000)  # lưới ngưỡng Ultralytics dùng cho p_curve, r_curve


def evaluate(split):
    plots = split == "test"
    v = model.val(data=args.data, split=split, imgsz=args.imgsz, batch=16, plots=plots, verbose=False, device="mps",
                  project=str(out.resolve()) if plots else os.environ.get("TMPDIR", "/tmp"), name=f"val_{split}",
                  exist_ok=True)
    k = list(v.box.ap_class_index).index(list(model.names.values()).index(args.cls))
    n = next(c["Instances"] for c in v.summary() if c["Class"] == args.cls)
    return v.box.r_curve[k], v.box.p_curve[k], n, v


def at(r, p, n, j):
    lo, hi = wilson(round(r[j] * n), n)
    return {"recall": float(r[j]), "recall_ci95": [lo, hi], "precision": float(p[j]), "boxes": int(n)}


r, p, n, _ = evaluate("val")
lower = np.array([wilson(round(x * n), n)[0] for x in r])
j = np.where(lower >= args.target)[0].max()
j_plain = np.where(r >= args.target)[0].max()
assert j <= j_plain  # đòi cận dưới ≥ mục tiêu thì ngưỡng không thể cao hơn ngưỡng chỉ đòi Recall ≥ mục tiêu
thr = conf[j]
val_res, val_plain = at(r, p, n, j), at(r, p, n, j_plain)

rt, pt, nt, vt = evaluate("test")
jt = np.abs(conf - thr).argmin()
test_res, test_plain = at(rt, pt, nt, jt), at(rt, pt, nt, np.abs(conf - conf[j_plain]).argmin())

fmt = lambda d: (f"Recall {d['recall']:.3f} (KTC 95% {d['recall_ci95'][0]:.3f}–{d['recall_ci95'][1]:.3f}), "
                 f"Precision {d['precision']:.3f}")
lines = [f"{args.weights}, lớp {args.cls}, IoU 0,5, mục tiêu Recall ≥ {args.target:.2f}",
         f"Tập val ({n} hộp):",
         f"  ngưỡng lớn nhất còn Recall ≥ {args.target:.2f} (tuần 7): conf {conf[j_plain]:.3f}: {fmt(val_plain)}",
         f"  ngưỡng lớn nhất có cận dưới KTC 95% ≥ {args.target:.2f} (chọn): conf {thr:.3f}: {fmt(val_res)}",
         f"Tập test ({nt} hộp), áp nguyên ngưỡng chọn trên val:",
         f"  conf {conf[j_plain]:.3f} (tuần 7): {fmt(test_plain)}",
         f"  conf {thr:.3f} (chọn): {fmt(test_res)}",
         f"  mAP@0.5 = {vt.box.map50:.3f}, mAP@0.5:0.95 = {vt.box.map:.3f}"]
print("\n".join(lines))
(out / "threshold_output.txt").write_text("\n".join(lines) + "\n")
(out / "threshold.json").write_text(json.dumps({"weights": args.weights, "cls": args.cls, "conf": float(thr),
                                                "val": val_res, "test": test_res}, ensure_ascii=False, indent=2))
for cache in Path(args.data).parent.glob("labels/*.cache"):  # giữ thư mục dữ liệu như bản đã nén
    cache.unlink()
for jpg in (out / "val_test").glob("val_batch*.jpg"):  # ảnh lô mẫu nặng, báo cáo không dùng
    jpg.unlink()
