"""Phân tích hộp của lớp vi phạm bị bỏ sót / nhầm lớp trên tập val, để chọn tăng cường có định hướng cho M2 (tuần 7).

Mỗi hộp nhãn thật của lớp được xếp vào: đúng (ghép một-một với dự đoán cùng lớp IoU ≥ 0,5, xét dự đoán theo độ tin cậy
giảm dần), nhầm lớp (không ghép được nhưng có dự đoán lớp khác IoU ≥ 0,5), bỏ sót (không có dự đoán nào). Ngưỡng tin cậy
0,25 như ma trận nhầm lẫn của Ultralytics. Tỉ lệ lỗi chia theo kích thước hộp (mốc COCO), nhóm độ sáng ảnh (Tuần 3,
reports/eda/image_stats.csv) và số đối tượng trong ảnh; nhóm có tỉ lệ lỗi ≥ 1,5 lần mức chung và ≥ 30 hộp là điểm yếu.

    .venv/bin/python scripts/analyze_misses.py --weights runs/M1_yolo26n_img800/weights/best.pt --imgsz 800 \\
        --out reports/training/M1_yolo26n_img800
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from ultralytics import YOLO
from ultralytics.utils.metrics import box_iou

WEAK_RATIO, WEAK_MIN = 1.5, 30
SIZE_BINS, SIZE_LABELS = [0, 32**2, 96**2, np.inf], ["nhỏ (< 32²)", "vừa (32²–96²)", "lớn (≥ 96²)"]
CROWD_BINS, CROWD_LABELS = [0, 5, 15, np.inf], ["1–5 đối tượng", "6–15 đối tượng", "> 15 đối tượng"]

ap = argparse.ArgumentParser()
ap.add_argument("--weights", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--data", default="data/SHEL5K_processed")
ap.add_argument("--cls", default="person_no_helmet")
ap.add_argument("--imgsz", type=int, default=640)
ap.add_argument("--conf", type=float, default=0.25)
ap.add_argument("--iou", type=float, default=0.5)
args = ap.parse_args()

model = YOLO(args.weights)
names = model.names
k = list(names.values()).index(args.cls)
stats = pd.read_csv("reports/eda/image_stats.csv", index_col="filename")
light = stats["light_group"]
# độ sáng ảnh so với trung vị: so với khoảng nhân độ sáng 1 ± hsv_v của tăng cường HSV
bright_q = (stats["brightness"].quantile([0.01, 0.05, 0.95, 0.99]) / stats["brightness"].median()).round(2)
img_dir, lbl_dir = Path(args.data, "images/val"), Path(args.data, "labels/val")

rows = []
for r in model.predict(source=str(img_dir), imgsz=args.imgsz, conf=args.conf, device="mps", stream=True, verbose=False):
    stem = Path(r.path).stem
    h, w = r.orig_shape
    lab = np.array([l.split() for l in (lbl_dir / f"{stem}.txt").read_text().splitlines()], float).reshape(-1, 5)
    cx, cy, bw, bh = lab[:, 1] * w, lab[:, 2] * h, lab[:, 3] * w, lab[:, 4] * h
    gt = torch.tensor(np.stack([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2], 1), dtype=torch.float32)
    is_k = lab[:, 0] == k
    if not is_k.any():
        continue
    gt_k, area_k = gt[is_k], (bw * bh)[is_k]
    pb, pc, pconf = r.boxes.xyxy.cpu(), r.boxes.cls.cpu().int(), r.boxes.conf.cpu()

    status = ["bỏ sót"] * len(gt_k)
    same = (pc == k).nonzero().flatten()
    if len(same):
        iou = box_iou(pb[same], gt_k)
        for i in pconf[same].argsort(descending=True):
            free = torch.tensor([s == "bỏ sót" for s in status])
            cand = torch.where(free & (iou[i] >= args.iou), iou[i], torch.tensor(-1.0))
            if cand.max() >= 0:
                status[int(cand.argmax())] = "đúng"
    other = (pc != k).nonzero().flatten()
    if len(other):
        iou_o = box_iou(pb[other], gt_k)
        for j, s in enumerate(status):
            if s == "bỏ sót" and iou_o[:, j].max() >= args.iou:
                status[j] = f"nhầm lớp → {names[int(pc[other][iou_o[:, j].argmax()])]}"
    rows += [{"image": stem, "status": s, "area": a, "light": light[stem], "n_obj": len(lab)} for s, a in zip(status, area_k)]

df = pd.DataFrame(rows)
df["kết quả"] = df["status"].str.split(" →").str[0]
df["kích thước"] = pd.cut(df["area"], SIZE_BINS, labels=SIZE_LABELS, right=False)
df["độ sáng"] = df["light"]
df["mật độ"] = pd.cut(df["n_obj"], CROWD_BINS, labels=CROWD_LABELS)
err = df["kết quả"] != "đúng"
overall = err.mean()

lines = [f"{args.weights}, tập val, lớp {args.cls}: {len(df)} hộp ở {df['image'].nunique()} ảnh "
         f"(conf {args.conf}, IoU {args.iou})",
         "Kết quả: " + ", ".join(f"{s} {n} ({n / len(df):.1%})" for s, n in df["status"].value_counts().items()),
         f"Tỉ lệ lỗi chung (bỏ sót + nhầm lớp): {overall:.1%}; điểm yếu = nhóm có tỉ lệ lỗi ≥ {WEAK_RATIO} lần "
         f"({WEAK_RATIO * overall:.1%}) và ≥ {WEAK_MIN} hộp",
         "Độ sáng ảnh (5.000 ảnh, Tuần 3) so với trung vị: " + ", ".join(f"p{q * 100:g} {v}" for q, v in bright_q.items()), ""]
big = df[df["area"] >= 32**2]  # tách ảnh hưởng kích thước: ảnh tối/sáng có nhiều hộp nhỏ hơn
for col, sub, note in [("kích thước", df, ""), ("độ sáng", df, ""), ("mật độ", df, ""),
                       ("độ sáng", big, ", chỉ hộp ≥ 32²"), ("mật độ", big, ", chỉ hộp ≥ 32²")]:
    t = pd.crosstab(sub[col], sub["kết quả"])
    t = t.reindex(columns=["đúng", "nhầm lớp", "bỏ sót"], fill_value=0)
    n = t.sum(axis=1)
    rate = 1 - t["đúng"] / n
    out = pd.DataFrame({"số hộp": n, "tỉ trọng": (n / n.sum()).map("{:.1%}".format),
                        "nhầm lớp": (t["nhầm lớp"] / n).map("{:.1%}".format),
                        "bỏ sót": (t["bỏ sót"] / n).map("{:.1%}".format), "tỉ lệ lỗi": rate.map("{:.1%}".format),
                        "điểm yếu": np.where((rate >= WEAK_RATIO * overall) & (n >= WEAK_MIN), "có", "")})
    lines += [f"Theo {col}{note}", out.to_string(), ""]
print("\n".join(lines))
Path(args.out, "misses_output.txt").write_text("\n".join(lines))
