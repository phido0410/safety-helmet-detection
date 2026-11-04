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
from ultralytics.models.yolo.detect.val import DetectionValidator
from ultralytics.utils.metrics import DetMetrics, ap_per_class, box_iou

from summarize_label_audit import wilson

CLASSES, MAX_GAP = ("person_with_helmet", "person_no_helmet"), 0.15
OTHER_CONF, IOU = 0.399, 0.5  # ngưỡng chung của M2 cho các lớp khác (tuần 8)
SIZE_BINS, SIZE_LABELS = [0, 40, 80, 160, np.inf], ["< 40", "40–80", "80–160", "≥ 160"]  # chiều cao người (pixel) ở imgsz
SHORT = {"pwh": "person_with_helmet", "pnh": "person_no_helmet"}
IGNORE_IOU = 0.5  # vùng bỏ qua (người bị che > 40%, reports/<tập>/ignore.csv): dự đoán người trùng vùng đó không tính đúng / sai


def ignored(pred, gt, ign):
    """True cho dự đoán thuộc về một vùng bỏ qua: IoU với vùng đó ≥ IGNORE_IOU và lớn hơn IoU với mọi hộp nhãn."""
    io_ign = box_iou(pred, ign).max(1).values if len(ign) else torch.zeros(len(pred))
    io_gt = box_iou(pred, gt).max(1).values if len(gt) else torch.zeros(len(pred))
    return (io_ign >= IGNORE_IOU) & (io_ign > io_gt)


# tự kiểm tra: dự đoán khớp vùng bỏ qua bị loại, dự đoán khớp hộp nhãn bên cạnh (dù chạm vùng bỏ qua) được giữ
_t = lambda *b: torch.tensor(b, dtype=torch.float32)
assert ignored(_t([0, 0, 10, 20], [12, 0, 22, 20], [30, 0, 40, 20]), _t([11, 0, 21, 20]), _t([0, 0, 10, 20], [13, 0, 23, 20])).tolist() \
    == [True, False, False]

ap = argparse.ArgumentParser()
ap.add_argument("--weights", required=True)
ap.add_argument("--test-metrics", required=True)
ap.add_argument("--threshold", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--data", nargs="+", default=["data/ood/ood.yaml"])
ap.add_argument("--imgsz", type=int, default=640)
ap.add_argument("--bootstrap", type=int, default=0, help="số lần lấy mẫu lặp theo ảnh cho KTC 95% của mAP@0.5 ngoài miền, test và độ chênh")
ap.add_argument("--test-data", default="data/SHEL5K_processed/data.yaml")
args = ap.parse_args()
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
thr = json.loads(Path(args.threshold).read_text())
test = {c["Class"]: c for c in json.loads(Path(args.test_metrics).read_text())["per_class"]}

roots = [Path(d).parent for d in args.data]  # data/<tên>/: ảnh ở images/, nhãn duyệt ở reports/<tên>/boxes.csv
data = Path(os.environ.get("TMPDIR", "/tmp"), "eval_ood.yaml")
data.write_text("\n".join(f"{s}: {[str(r.resolve() / 'images') for r in roots]}" for s in ("train", "val", "test"))
                + "\n" + Path(args.data[0]).read_text().split("nc:", 1)[1].join(["nc:", ""]))
ign_csv = [Path("reports", r.name, "ignore.csv") for r in roots]
ign = pd.concat([pd.read_csv(p) for p in ign_csv if p.exists()] or [pd.DataFrame(columns=["image", "x1", "y1", "x2", "y2"])])
ign_by = {i: torch.tensor(g[["x1", "y1", "x2", "y2"]].values, dtype=torch.float32) for i, g in ign.groupby("image")}
update_metrics = DetectionValidator.update_metrics


def update_without_ignored(self, preds, batch):
    """Bỏ dự đoán người thuộc vùng bỏ qua trước khi Ultralytics ghép dự đoán với nhãn (tọa độ ảnh letterbox)."""
    for si, pred in enumerate(preds):
        b = ign_by.get(Path(batch["im_file"][si]).name)
        if b is None or not len(pred["cls"]):
            continue
        (gy, gx), (px, py) = batch["ratio_pad"][si]
        b = (b * torch.tensor([gx, gy, gx, gy]) + torch.tensor([px, py, px, py])).to(pred["bboxes"].device)
        person = torch.isin(pred["cls"], torch.tensor([names.index(c) for c in CLASSES], device=pred["cls"].device).float())
        drop = person & ignored(pred["bboxes"], self._prepare_batch(si, batch)["bboxes"], b).to(person.device)
        for k in pred:
            pred[k] = pred[k][~drop]
    return update_metrics(self, preds, batch)


model = YOLO(args.weights)
names = list(model.names.values())
per_image, update_stats = [], DetMetrics.update_stats
DetMetrics.update_stats = lambda self, stat: (per_image.append({k: stat[k] for k in ("tp", "conf", "pred_cls", "target_cls")}),
                                              update_stats(self, stat))[1]  # giữ thống kê từng ảnh cho --bootstrap
DetectionValidator.update_metrics = update_without_ignored
try:
    v = model.val(data=str(data), split="test", imgsz=args.imgsz, batch=8, plots=True, verbose=False, device="mps",
                  project=os.environ.get("TMPDIR", "/tmp"), name="eval_ood", exist_ok=True)
finally:
    DetectionValidator.update_metrics = update_metrics
ood_images, per_image = per_image, []
if args.bootstrap:  # thống kê từng ảnh của tập test SHEL5K (batch 16 như eval_thresholds.py → test_metrics.json)
    model.val(data=args.test_data, split="test", imgsz=args.imgsz, batch=16, plots=False, verbose=False, device="mps",
              project=os.environ.get("TMPDIR", "/tmp"), name="eval_ood_test", exist_ok=True)
DetMetrics.update_stats = update_stats
assert sorted(names[i] for i in v.box.ap_class_index) == sorted(CLASSES), "tập ngoài miền chỉ có 2 lớp người"
ap50 = {names[c]: v.box.ap50[k] for k, c in enumerate(v.box.ap_class_index)}
n_box = {names[c]: int(v.nt_per_class[c]) for c in v.box.ap_class_index}
ood_map, test_map = np.mean(list(ap50.values())), np.mean([test[c]["mAP50"] for c in CLASSES])

k = list(v.box.ap_class_index).index(names.index(thr["cls"]))
j = np.abs(np.linspace(0, 1, 1000) - thr["conf"]).argmin()
r, p = v.box.r_curve[k, j], v.box.p_curve[k, j]
lo, hi = wilson(round(r * n_box[thr["cls"]]), n_box[thr["cls"]])
n_img = sum(len(list((r / "images").glob("*.jpg"))) for r in roots)
lines = [f"{args.weights} trên tập ngoài miền {' + '.join(r.name for r in roots)} ({n_img} ảnh, {len(ign)} vùng bỏ qua, imgsz {args.imgsz}) so với tập test SHEL5K, cùng 2 lớp:"]
lines += [f"  {c:<20} hộp {n_box[c]:>4} | AP50 ngoài miền {ap50[c]:.3f}  test {test[c]['mAP50']:.3f}  (chênh {test[c]['mAP50'] - ap50[c]:+.3f})"
          for c in CLASSES]
gap = test_map - ood_map


def map2(stats, idx):
    """mAP@0.5 của 2 lớp người trên các ảnh idx (thống kê từng ảnh của Ultralytics, ghép lại rồi tính AP như validator)."""
    cat = {k: np.concatenate([stats[i][k] for i in idx], 0) for k in ("tp", "conf", "pred_cls", "target_cls")}
    ap, cls = (lambda r: (r[5], r[6]))(ap_per_class(cat["tp"], cat["conf"], cat["pred_cls"], cat["target_cls"]))
    return np.mean([ap[list(cls).index(names.index(c)), 0] if names.index(c) in cls else 0.0 for c in CLASSES])


boot = {}
if args.bootstrap:
    full_ood, full_test = map2(ood_images, range(len(ood_images))), map2(per_image, range(len(per_image)))
    assert abs(full_ood - ood_map) < 1e-6, (full_ood, ood_map)  # tính lại từ thống kê từng ảnh phải trùng số của Ultralytics
    assert abs(full_test - test_map) < 2e-3, (full_test, test_map)  # test_metrics.json: cùng mô hình, batch 16
    rng = np.random.default_rng(42)
    bo = np.array([map2(ood_images, rng.integers(0, len(ood_images), len(ood_images))) for _ in range(args.bootstrap)])
    bt = np.array([map2(per_image, rng.integers(0, len(per_image), len(per_image))) for _ in range(args.bootstrap)])
    ci = lambda x: [float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))]
    boot = {"n": args.bootstrap, "ood_ci95": ci(bo), "test_ci95": ci(bt), "gap_ci95": ci(bt - bo), "p_gap_le_max": float(np.mean(bt - bo <= MAX_GAP))}
lines += [f"  mAP@0.5 2 lớp: ngoài miền {ood_map:.3f}, test {test_map:.3f}, chênh {gap:+.3f} "
          f"({'đạt' if gap <= MAX_GAP else 'KHÔNG đạt'} mục tiêu ≤ {MAX_GAP:.2f})",
          *([f"  KTC 95% (bootstrap {boot['n']} lần theo ảnh): mAP ngoài miền {boot['ood_ci95'][0]:.3f}–{boot['ood_ci95'][1]:.3f}, test "
               f"{boot['test_ci95'][0]:.3f}–{boot['test_ci95'][1]:.3f}, chênh {boot['gap_ci95'][0]:.3f}–{boot['gap_ci95'][1]:.3f}; "
               f"tỉ lệ lần lấy mẫu có chênh ≤ {MAX_GAP:.2f}: {boot['p_gap_le_max']:.0%}"] if boot else []),
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
(out / "ood_metrics.json").write_text(json.dumps({"weights": args.weights, "imgsz": args.imgsz, "data": args.data, "images": n_img, "ignore": len(ign), "bootstrap": boot, "ap50": ap50, "boxes": n_box,
    "map50_ood": ood_map, "map50_test": test_map, "gap": gap, "recall_pri": r, "recall_pri_ci95": [lo, hi], "precision_pri": p,
    **{k: {t: {g: row.to_dict() for (tt, g), row in x.iterrows() if tt == t} for t in CLASSES} for k, x in (("by_group", tab), ("by_size", stab))}},
    ensure_ascii=False, indent=2, default=float))
for f in ("confusion_matrix_normalized.png", "BoxPR_curve.png"):
    (out / f).write_bytes(Path(v.save_dir, f).read_bytes())
for cache in (c for r in roots for c in r.glob("*.cache")):
    cache.unlink()
