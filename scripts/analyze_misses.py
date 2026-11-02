"""Phân tích hộp của một lớp bị bỏ sót / nhầm lớp và các dự đoán báo nhầm (tuần 7: chọn tăng cường cho M2; tuần 8: phân
tích lỗi của mô hình chính trên tập test).

Mỗi hộp nhãn thật của lớp được xếp vào: đúng (ghép một-một với dự đoán cùng lớp IoU ≥ 0,5, xét dự đoán theo độ tin cậy
giảm dần), nhầm lớp (không ghép được nhưng có dự đoán lớp khác IoU ≥ 0,5), bỏ sót (không có dự đoán nào). Mặc định ngưỡng
tin cậy 0,25 như ma trận nhầm lẫn của Ultralytics. Tỉ lệ lỗi chia theo kích thước hộp (mốc COCO), nhóm độ sáng ảnh (Tuần 3,
reports/eda/image_stats.csv), số đối tượng trong ảnh, mức chồng lấn với đối tượng cùng nhóm (đại diện cho che khuất), hộp
chạm mép ảnh và độ mờ; nhóm có tỉ lệ lỗi ≥ 1,5 lần mức chung và ≥ 30 hộp là điểm yếu. Dự đoán của lớp không ghép được nhãn
nào (báo nhầm) được xếp vào: trùng (IoU ≥ 0,5 với hộp cùng lớp đã được ghép), nhầm lớp (IoU ≥ 0,5 với hộp lớp khác), lệch
vị trí (IoU 0,1–0,5 với hộp cùng lớp), nền. --cases ghi từng ca lỗi ra CSV để khảo sát định tính.

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
# che khuất: phần diện tích hộp bị một hộp khác cùng nhóm đè lên lớn nhất (dữ liệu không có nhãn che khuất)
GROUPS = {"helmet": ("helmet",), "head": ("head", "head_with_helmet"), "head_with_helmet": ("head", "head_with_helmet"),
          "person_with_helmet": ("person_with_helmet", "person_no_helmet"),
          "person_no_helmet": ("person_with_helmet", "person_no_helmet"), "face": ("face",)}
OCC_BINS, OCC_LABELS = [-np.inf, 0, 0.3, np.inf], ["không chồng lấn", "chồng lấn ≤ 30%", "chồng lấn > 30%"]
EDGE_PX = 2
BLUR_QUANTILE = 0.10

ap = argparse.ArgumentParser()
ap.add_argument("--weights", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--out-file", default="misses_output.txt")
ap.add_argument("--cases", help="CSV ghi từng ca lỗi (bỏ sót, nhầm lớp, báo nhầm)")
ap.add_argument("--data", default="data/SHEL5K_processed")
ap.add_argument("--split", default="val", choices=["val", "test"])
ap.add_argument("--cls", default="person_no_helmet")
ap.add_argument("--imgsz", type=int, default=640)
ap.add_argument("--conf", type=float, default=0.25)
ap.add_argument("--iou", type=float, default=0.5)
args = ap.parse_args()

model = YOLO(args.weights)
names = model.names
k = list(names.values()).index(args.cls)
group = [list(names.values()).index(c) for c in GROUPS[args.cls]]
stats = pd.read_csv("reports/eda/image_stats.csv", index_col="filename")
light = stats["light_group"]
# độ sáng ảnh so với trung vị: so với khoảng nhân độ sáng 1 ± hsv_v của tăng cường HSV
bright_q = (stats["brightness"].quantile([0.01, 0.05, 0.95, 0.99]) / stats["brightness"].median()).round(2)
blur_cut = stats["blur_laplacian_var"].quantile(BLUR_QUANTILE)
img_dir, lbl_dir = Path(args.data, "images", args.split), Path(args.data, "labels", args.split)


def inter_area(a, b):
    lt, rb = np.maximum(a[:, None, :2], b[None, :, :2]), np.minimum(a[:, None, 2:], b[None, :, 2:])
    return np.clip(rb - lt, 0, None).prod(2)


rows, fps, n_img = [], [], 0
for r in model.predict(source=str(img_dir), imgsz=args.imgsz, conf=args.conf, device="mps", stream=True, verbose=False):
    n_img += 1
    stem = Path(r.path).stem
    h, w = r.orig_shape
    lab = np.array([l.split() for l in (lbl_dir / f"{stem}.txt").read_text().splitlines()], float).reshape(-1, 5)
    cx, cy, bw, bh = lab[:, 1] * w, lab[:, 2] * h, lab[:, 3] * w, lab[:, 4] * h
    gt = torch.tensor(np.stack([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2], 1), dtype=torch.float32)
    is_k = lab[:, 0] == k
    gt_k, area_k = gt[is_k], (bw * bh)[is_k]
    pb, pc, pconf = r.boxes.xyxy.cpu(), r.boxes.cls.cpu().int(), r.boxes.conf.cpu()
    blur = "mờ (10% thấp nhất)" if stats.loc[stem, "blur_laplacian_var"] < blur_cut else "bình thường"

    status, matched = ["bỏ sót"] * len(gt_k), set()
    same = (pc == k).nonzero().flatten()
    iou = box_iou(pb[same], gt_k) if len(same) and len(gt_k) else torch.zeros(len(same), len(gt_k))
    for i in pconf[same].argsort(descending=True):
        free = torch.tensor([s == "bỏ sót" for s in status], dtype=torch.bool)
        cand = torch.where(free & (iou[i] >= args.iou), iou[i], torch.tensor(-1.0))
        if len(cand) and cand.max() >= 0:
            status[int(cand.argmax())] = "đúng"
            matched.add(int(i))
    other = (pc != k).nonzero().flatten()
    if len(other) and len(gt_k):
        iou_o = box_iou(pb[other], gt_k)
        for j, s in enumerate(status):
            if s == "bỏ sót" and iou_o[:, j].max() >= args.iou:
                status[j] = f"nhầm lớp → {names[int(pc[other][iou_o[:, j].argmax()])]}"

    gt_np, idx_k, idx_g = gt.numpy(), np.where(is_k)[0], np.where(np.isin(lab[:, 0], group))[0]
    over = inter_area(gt_np[idx_k], gt_np[idx_g])
    over[idx_k[:, None] == idx_g[None, :]] = 0  # bỏ chính hộp đó
    cover = over.max(1, initial=0) / area_k
    b = gt_np[idx_k]
    edge = (b[:, 0] <= EDGE_PX) | (b[:, 1] <= EDGE_PX) | (b[:, 2] >= w - EDGE_PX) | (b[:, 3] >= h - EDGE_PX)
    rows += [{"image": stem, "status": s, "area": a, "light": light[stem], "n_obj": len(lab), "cover": c,
              "edge": "chạm mép ảnh" if e else "không chạm mép", "blur": blur, "box": bx.round(1).tolist()}
             for s, a, c, e, bx in zip(status, area_k, cover, edge, b)]

    gt_other = gt[~torch.tensor(is_k)]
    for i in set(range(len(same))) - matched:
        p = pb[same[i]][None]
        best_same = float(iou[i].max()) if len(gt_k) else 0.0
        o = box_iou(p, gt_other)[0] if len(gt_other) else torch.zeros(0)
        if best_same >= args.iou:
            kind = "trùng"
        elif len(o) and o.max() >= args.iou:
            kind = f"nhầm lớp ← {names[int(lab[~is_k][int(o.argmax()), 0])]}"
        elif best_same >= 0.1:
            kind = "lệch vị trí"
        else:
            kind = "nền"
        fps.append({"image": stem, "status": f"báo nhầm: {kind}", "conf": float(pconf[same[i]]),
                    "area": float((p[0, 2] - p[0, 0]) * (p[0, 3] - p[0, 1])), "light": light[stem], "blur": blur,
                    "box": p[0].numpy().round(1).tolist()})

assert n_img == len(list(lbl_dir.glob("*.txt"))), "chưa xử lý hết ảnh của tập"
df = pd.DataFrame(rows)
df["kết quả"] = df["status"].str.split(" →").str[0]
df["kích thước"] = pd.cut(df["area"], SIZE_BINS, labels=SIZE_LABELS, right=False)
df["độ sáng"] = df["light"]
df["mật độ"] = pd.cut(df["n_obj"], CROWD_BINS, labels=CROWD_LABELS)
df["che khuất"] = pd.cut(df["cover"], OCC_BINS, labels=OCC_LABELS)
df["vị trí"], df["độ mờ"] = df["edge"], df["blur"]
err = df["kết quả"] != "đúng"
overall = err.mean()
fp = pd.DataFrame(fps, columns=["image", "status", "conf", "area", "light", "blur", "box"])
tp = int((df["kết quả"] == "đúng").sum())

lines = [f"{args.weights}, tập {args.split}, lớp {args.cls}: {len(df)} hộp ở {df['image'].nunique()} ảnh "
         f"(conf {args.conf}, IoU {args.iou})",
         "Kết quả: " + ", ".join(f"{s} {n} ({n / len(df):.1%})" for s, n in df["status"].value_counts().items()),
         f"Tỉ lệ lỗi chung (bỏ sót + nhầm lớp): {overall:.1%}; điểm yếu = nhóm có tỉ lệ lỗi ≥ {WEAK_RATIO} lần "
         f"({WEAK_RATIO * overall:.1%}) và ≥ {WEAK_MIN} hộp",
         "Độ sáng ảnh (5.000 ảnh, Tuần 3) so với trung vị: " + ", ".join(f"p{q * 100:g} {v}" for q, v in bright_q.items()), ""]
big = df[df["area"] >= 32**2]  # tách ảnh hưởng kích thước: ảnh tối/sáng có nhiều hộp nhỏ hơn
for col, sub, note in [("kích thước", df, ""), ("độ sáng", df, ""), ("mật độ", df, ""),
                       ("độ sáng", big, ", chỉ hộp ≥ 32²"), ("mật độ", big, ", chỉ hộp ≥ 32²"),
                       ("che khuất", df, " (chồng lấn lớn nhất với đối tượng cùng nhóm)"), ("vị trí", df, ""),
                       ("độ mờ", df, ""), ("che khuất", big, ", chỉ hộp ≥ 32²")]:
    t = pd.crosstab(sub[col], sub["kết quả"])
    t = t.reindex(columns=["đúng", "nhầm lớp", "bỏ sót"], fill_value=0)
    n = t.sum(axis=1)
    assert n.sum() == len(sub)
    rate = 1 - t["đúng"] / n
    out = pd.DataFrame({"số hộp": n, "tỉ trọng": (n / n.sum()).map("{:.1%}".format),
                        "nhầm lớp": (t["nhầm lớp"] / n).map("{:.1%}".format),
                        "bỏ sót": (t["bỏ sót"] / n).map("{:.1%}".format), "tỉ lệ lỗi": rate.map("{:.1%}".format),
                        "điểm yếu": np.where((rate >= WEAK_RATIO * overall) & (n >= WEAK_MIN), "có", "")})
    lines += [f"Theo {col}{note}", out.to_string(), ""]
lines += [f"Báo nhầm (dự đoán {args.cls} không ghép được nhãn): {len(fp)}; Precision = {tp} / ({tp} + {len(fp)}) = "
          f"{tp / max(tp + len(fp), 1):.3f}",
          "  " + ", ".join(f"{s.removeprefix('báo nhầm: ')} {n} ({n / max(len(fp), 1):.1%})"
                           for s, n in fp["status"].value_counts().items())]
print("\n".join(lines))
Path(args.out, args.out_file).write_text("\n".join(lines))
if args.cases:
    cases = pd.concat([df[err].assign(kind=df.loc[err, "status"]), fp.assign(kind=fp["status"])], ignore_index=True)
    cases[["image", "kind", "box", "conf", "area", "light", "blur", "cover", "edge"]].to_csv(args.cases, index=False)
