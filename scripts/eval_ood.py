"""Tuần 9: đánh giá mô hình trên tập ngoài miền (data/ood, nhãn từ label_ood.py) và so với tập test SHEL5K trên cùng 2 lớp
person_with_helmet, person_no_helmet (tập ngoài miền không gán 4 lớp còn lại; dự đoán các lớp đó không ảnh hưởng AP của 2 lớp
này vì AP tính riêng từng lớp). Tiêu chí của đề cương: chênh mAP@0.5 nội bộ (test) − ngoài miền ≤ 0,15. Lớp vi phạm còn
được báo Recall / Precision ở ngưỡng chính thức (threshold.json tuần 8), Recall kèm KTC 95% Wilson, và chia theo loại mũ
người đó đội (cột headwear khi gán nhãn): mỗi hộp nhãn lấy dự đoán người (2 lớp trên, ở ngưỡng vận hành: lớp vi phạm theo
threshold.json, lớp còn lại 0,399 như tuần 8) có IoU lớn nhất ≥ 0,5 và ghi lớp của dự đoán đó, không có thì là bỏ sót.
Bảng thứ hai chia cùng kết quả theo chiều cao người khi ảnh được thu về imgsz (SIZE_BINS), để so thành phần kích thước giữa các tập.

    .venv/bin/python scripts/eval_ood.py --weights runs/M2_yolo26n/weights/best.pt --imgsz 800 \\
        --test-metrics reports/training/M2_yolo26n/test_metrics.json \\
        --threshold reports/error_analysis/M2_yolo26n/threshold.json --out reports/ood/M2_yolo26n
    (tập thứ hai gồm 2 đợt thu thập: --data data/ood2/ood.yaml data/ood2b/ood.yaml --out reports/ood2/<RUN>; nhiều --data thì
    gộp ảnh và nhãn các tập lại để đánh giá chung)
"""
import argparse, json, os
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from PIL import Image
from ultralytics import YOLO
from ultralytics.utils.metrics import box_iou

from summarize_label_audit import wilson

CLASSES, MAX_GAP = ("person_with_helmet", "person_no_helmet"), 0.15
OTHER_CONF, IOU = 0.399, 0.5  # ngưỡng chung của M2 cho các lớp khác (tuần 8)
SIZE_BINS, SIZE_LABELS = [0, 40, 80, 160, np.inf], ["< 40", "40–80", "80–160", "≥ 160"]  # chiều cao người (pixel) ở imgsz
SHORT = {"pwh": "person_with_helmet", "pnh": "person_no_helmet"}

ap = argparse.ArgumentParser()
ap.add_argument("--weights", required=True)
ap.add_argument("--test-metrics", required=True)
ap.add_argument("--threshold", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--data", nargs="+", default=["data/ood/ood.yaml"])
ap.add_argument("--imgsz", type=int, default=640)
args = ap.parse_args()
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
thr = json.loads(Path(args.threshold).read_text())
test = {c["Class"]: c for c in json.loads(Path(args.test_metrics).read_text())["per_class"]}

roots = [Path(d).parent for d in args.data]  # data/<tên>/: ảnh ở images/, nhãn duyệt ở reports/<tên>/boxes.csv
data = Path(os.environ.get("TMPDIR", "/tmp"), "eval_ood.yaml")
data.write_text("\n".join(f"{s}: {[str(r.resolve() / 'images') for r in roots]}" for s in ("train", "val", "test"))
                + "\n" + Path(args.data[0]).read_text().split("nc:", 1)[1].join(["nc:", ""]))
model = YOLO(args.weights)
v = model.val(data=str(data), split="test", imgsz=args.imgsz, batch=8, plots=True, verbose=False, device="mps",
              project=os.environ.get("TMPDIR", "/tmp"), name="eval_ood", exist_ok=True)
names = list(model.names.values())
assert sorted(names[i] for i in v.box.ap_class_index) == sorted(CLASSES), "tập ngoài miền chỉ có 2 lớp người"
ap50 = {names[c]: v.box.ap50[k] for k, c in enumerate(v.box.ap_class_index)}
n_box = {names[c]: int(v.nt_per_class[c]) for c in v.box.ap_class_index}
ood_map, test_map = np.mean(list(ap50.values())), np.mean([test[c]["mAP50"] for c in CLASSES])

k = list(v.box.ap_class_index).index(names.index(thr["cls"]))
j = np.abs(np.linspace(0, 1, 1000) - thr["conf"]).argmin()
r, p = v.box.r_curve[k, j], v.box.p_curve[k, j]
lo, hi = wilson(round(r * n_box[thr["cls"]]), n_box[thr["cls"]])
n_img = sum(len(list((r / "images").glob("*.jpg"))) for r in roots)
lines = [f"{args.weights} trên tập ngoài miền {' + '.join(r.name for r in roots)} ({n_img} ảnh, imgsz {args.imgsz}) so với tập test SHEL5K, cùng 2 lớp:"]
lines += [f"  {c:<20} hộp {n_box[c]:>4} | AP50 ngoài miền {ap50[c]:.3f}  test {test[c]['mAP50']:.3f}  (chênh {test[c]['mAP50'] - ap50[c]:+.3f})"
          for c in CLASSES]
gap = test_map - ood_map
lines += [f"  mAP@0.5 2 lớp: ngoài miền {ood_map:.3f}, test {test_map:.3f}, chênh {gap:+.3f} "
          f"({'đạt' if gap <= MAX_GAP else 'KHÔNG đạt'} mục tiêu ≤ {MAX_GAP:.2f})",
          f"  {thr['cls']} ở ngưỡng chính thức {thr['conf']:.3f}: Recall {r:.3f} (KTC 95% {lo:.3f}–{hi:.3f}), Precision {p:.3f} "
          f"(test: Recall {thr['test']['recall']:.3f}, Precision {thr['test']['precision']:.3f})"]

gt = pd.concat([pd.read_csv(Path("reports", r.name, "boxes.csv")).assign(root=str(r)) for r in roots], ignore_index=True).fillna({"headwear": ""})
pred_cls = []
for (img, root), g in gt.groupby(["image", "root"], sort=False):
    b = model.predict(Path(root) / "images" / img, imgsz=args.imgsz, conf=min(thr["conf"], OTHER_CONF),
                      device="mps", verbose=False)[0].boxes
    cls = [names[int(c)] for c in b.cls]
    keep = [i for i, (c, f) in enumerate(zip(cls, b.conf.tolist())) if c in CLASSES and f >= (thr["conf"] if c == thr["cls"] else OTHER_CONF)]
    iou = box_iou(torch.tensor(g[["x1", "y1", "x2", "y2"]].values, dtype=torch.float32), b.xyxy.cpu()[keep])
    for row in iou:
        pred_cls.append(cls[keep[int(row.argmax())]] if len(keep) and row.max() >= IOU else "bỏ sót")
gt["pred"] = pred_cls
gt["true"] = gt["cls"].map(SHORT)
gt["group"] = np.where(gt["cls"] == "pnh", gt["headwear"], "(mũ bảo hộ)")
scale = {(i, r): args.imgsz / max(Image.open(Path(r) / "images" / i).size) for i, r in set(zip(gt["image"], gt["root"]))}
gt["h_px"] = [(y2 - y1) * scale[(i, r)] for i, r, y1, y2 in zip(gt["image"], gt["root"], gt["y1"], gt["y2"])]
gt["size"] = pd.cut(gt["h_px"], SIZE_BINS, right=False, labels=SIZE_LABELS)
gt.drop(columns="root").to_csv(out / "ood_boxes_pred.csv", index=False)  # từng hộp nhãn + dự đoán, cho khảo sát định tính
tab = pd.crosstab([gt["true"], gt["group"]], gt["pred"])
tab = tab.reindex(columns=[c for c in (*CLASSES, "bỏ sót") if c in tab.columns], fill_value=0)
lines += ["", f"Dự đoán cho từng hộp nhãn theo loại mũ (ngưỡng vận hành, IoU ≥ {IOU}):"]
for (t, grp), row in tab.iterrows():
    n = row.sum()
    lines.append(f"  {t:<20} {grp:<13} {n:>4} hộp | " + "  ".join(f"{c} {row[c]:>3} ({row[c] / n:.0%})" for c in tab.columns))
stab = pd.crosstab([gt["true"], gt["size"]], gt["pred"]).reindex(columns=tab.columns, fill_value=0)
stab = stab[stab.sum(axis=1) > 0]  # nhóm kích thước trống (cột category) không in
lines += ["", f"Dự đoán theo chiều cao người (pixel khi ảnh thu về cạnh dài {args.imgsz}; % hộp = tỉ lệ trong lớp đó):"]
for (t, sz), row in stab.iterrows():
    n = row.sum()
    lines.append(f"  {t:<20} {sz:<8} {n:>4} hộp ({n / (gt['true'] == t).sum():>4.0%}) | "
                 + "  ".join(f"{c} {row[c]:>3} ({row[c] / n:.0%})" for c in tab.columns))
print("\n".join(lines))
(out / "ood_output.txt").write_text("\n".join(lines) + "\n")
(out / "ood_metrics.json").write_text(json.dumps({"weights": args.weights, "imgsz": args.imgsz, "data": args.data, "images": n_img, "ap50": ap50, "boxes": n_box,
    "map50_ood": ood_map, "map50_test": test_map, "gap": gap, "recall_pri": r, "recall_pri_ci95": [lo, hi], "precision_pri": p,
    **{k: {t: {g: row.to_dict() for (tt, g), row in x.iterrows() if tt == t} for t in CLASSES} for k, x in (("by_group", tab), ("by_size", stab))}},
    ensure_ascii=False, indent=2, default=float))
for f in ("confusion_matrix_normalized.png", "BoxPR_curve.png"):
    (out / f).write_bytes(Path(v.save_dir, f).read_bytes())
for cache in (c for r in roots for c in r.glob("*.cache")):
    cache.unlink()
