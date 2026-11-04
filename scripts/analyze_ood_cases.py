"""Phân tích chẩn đoán theo trường hợp khó trên các tập ngoài miền gộp (tuần 10). Không phải phép thử mù: phép thử cuối là
OOD-4 (reports/ood4/plan.md); bảng này chỉ ra mô hình yếu ở trường hợp nào, với đủ mẫu hơn từng tập riêng.

Tiêu chí (chốt 2026-11-04 trước khi chạy):
- Tập gộp: OOD-2 + OOD-3 + OOD-4 (nhãn sau rà soát, docs/huong_dan_gan_nhan_ngoai_mien.md). Bỏ OOD-1 vì đã dùng để tìm lỗi rồi
  làm M3 / M3b. Mô hình: M2 (đối chứng) và M3b (mô hình cuối), ngưỡng vận hành của từng mô hình (threshold.json: lớp vi phạm theo
  Wilson trên val, lớp có mũ 0,399), chưa áp các quy tắc của app.
- Nhóm theo hộp nhãn: loại mũ (người không đội mũ bảo hộ: cột headwear; người đội: "mũ bảo hộ"); chiều cao người khi ảnh thu về
  cạnh dài imgsz: < 80, 80–160, ≥ 160 px (160 = ngưỡng của app).
- Nhóm theo ảnh: ánh sáng (độ sáng trung bình ảnh xám 0–255 < 90 là "tối"); độ đông (số người gán + vùng bỏ qua trong ảnh: 1–2,
  3–6, ≥ 7); khung cảnh ("cận cảnh" khi người cao nhất ≥ 50% chiều cao ảnh, còn lại "toàn cảnh").
- Mỗi hộp nhãn lấy dự đoán người có IoU lớn nhất ≥ 0,5 (như eval_ood.py): đúng lớp / nhầm lớp / bỏ sót. Precision lớp vi phạm
  theo nhóm ảnh: dự đoán vi phạm ghép tham lam (độ tin cậy giảm dần) với nhãn vi phạm chưa ghép, IoU ≥ 0,5; dự đoán thuộc vùng bỏ
  qua bị loại như eval_ood.py. Tỉ lệ kèm KTC 95% Wilson; nhóm < MIN_N mẫu ghi "ít mẫu".

    .venv/bin/python scripts/analyze_ood_cases.py --out reports/ood_cases
"""
import argparse, json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageOps
from ultralytics import YOLO

from summarize_label_audit import wilson

SETS = {"OOD-2": ["ood2", "ood2b"], "OOD-3": ["ood3", "ood3b"], "OOD-4": ["ood4"]}
MODELS = {"M2": "M2_yolo26n", "M3b": "M3b_yolo26n_bg"}
PWH, PNH, OTHER_CONF, IOU, MIN_N, IMGSZ = "person_with_helmet", "person_no_helmet", 0.399, 0.5, 20, 800
DARK, CLOSE = 90, 0.5

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
args = ap.parse_args()


def iou(a, b):
    w, h = min(a[2], b[2]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[1], b[1])
    return 0.0 if w <= 0 or h <= 0 else w * h / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - w * h)


# nhãn, vùng bỏ qua và thuộc tính ảnh (không phụ thuộc mô hình)
gts, images = [], []
for name, roots in SETS.items():
    for r in roots:
        b = pd.read_csv(f"reports/{r}/boxes.csv").fillna({"headwear": ""})
        ign = pd.read_csv(f"reports/{r}/ignore.csv")
        for img, g in b.groupby("image"):
            im = ImageOps.exif_transpose(Image.open(f"data/{r}/images/{img}"))
            W, H = im.size
            n_people = len(g) + int((ign["image"] == img).sum())
            images.append({"set": name, "root": r, "image": img, "W": W, "H": H,
                           "light": "tối" if np.asarray(im.convert("L")).mean() < DARK else "đủ sáng",
                           "crowd": "1–2 người" if n_people <= 2 else "3–6 người" if n_people <= 6 else "≥ 7 người",
                           "shot": "cận cảnh" if ((g["y2"] - g["y1"]) / H).max() >= CLOSE else "toàn cảnh",
                           "ignore": ign.loc[ign["image"] == img, ["x1", "y1", "x2", "y2"]].values.tolist()})
            h = (g["y2"] - g["y1"]) * IMGSZ / max(W, H)
            for row, hh in zip(g.itertuples(), h):
                gts.append({"set": name, "root": r, "image": img, "cls": PNH if row.cls == "pnh" else PWH,
                            "box": [row.x1, row.y1, row.x2, row.y2], "headwear": row.headwear or "mũ bảo hộ",
                            "size": "< 80 px" if hh < 80 else "80–160 px" if hh < 160 else "≥ 160 px"})
images, gts = pd.DataFrame(images), pd.DataFrame(gts)
gts = gts.merge(images[["root", "image", "light", "crowd", "shot"]], on=["root", "image"])

lines = [f"Phân tích chẩn đoán trên {' + '.join(SETS)} ({len(images)} ảnh, {(gts.cls == PWH).sum()} người đội mũ bảo hộ, "
         f"{(gts.cls == PNH).sum()} người không đội; nhãn sau rà soát 2026-11-04). Không phải phép thử mù (phép thử cuối: OOD-4).",
         f"Ngưỡng vận hành từng mô hình, chưa áp quy tắc của app. Nhóm < {MIN_N} mẫu: ít mẫu, chỉ tham khảo."]
fmt = lambda k, n: f"{k / n:.2f} ({k}/{n}, {wilson(k, n)[0]:.2f}–{wilson(k, n)[1]:.2f}){' ít mẫu' if n < MIN_N else ''}" if n else "–"
report = {}
for short, run in MODELS.items():
    thr = json.loads(Path(f"reports/error_analysis/{run}/threshold.json").read_text())
    model = YOLO(f"runs/{run}/weights/best.pt")
    names = list(model.names.values())
    cut = {PNH: thr["conf"], PWH: OTHER_CONF}
    out_gt, tp_fp = [], []
    for im in images.itertuples():
        b = model.predict(f"data/{im.root}/images/{im.image}", imgsz=IMGSZ, conf=min(cut.values()), device="mps", verbose=False)[0].boxes
        preds = [(xy, names[int(c)], float(f)) for xy, c, f in zip(b.xyxy.cpu().tolist(), b.cls.cpu(), b.conf.cpu())
                 if names[int(c)] in cut and float(f) >= cut[names[int(c)]]]
        g = gts[(gts["root"] == im.root) & (gts["image"] == im.image)]
        for row in g.itertuples():
            best = max(preds, key=lambda p: iou(p[0], row.box), default=None)
            out_gt.append("bỏ sót" if best is None or iou(best[0], row.box) < IOU else best[1])
        bad_gt, used = [r.box for r in g.itertuples() if r.cls == PNH], set()
        for xy, c, f in sorted((p for p in preds if p[1] == PNH), key=lambda p: -p[2]):
            m_ign = max((iou(xy, q) for q in im.ignore), default=0)
            if m_ign >= IOU and m_ign > max((iou(xy, r.box) for r in g.itertuples()), default=0):
                continue
            j = max((j for j in range(len(bad_gt)) if j not in used), key=lambda j: iou(xy, bad_gt[j]), default=None)
            hit = j is not None and iou(xy, bad_gt[j]) >= IOU
            used |= {j} if hit else set()
            tp_fp.append({"root": im.root, "image": im.image, "tp": hit})
    gt = gts.assign(pred=[*out_gt])
    pr = pd.DataFrame(tp_fp).merge(images[["root", "image", "light", "crowd", "shot"]], on=["root", "image"])
    report[short] = {}
    lines += ["", f"== {short} ({run}, ngưỡng vi phạm {thr['conf']:.3f})"]
    for col, title in [("headwear", "loại mũ"), ("size", "chiều cao người"), ("light", "ánh sáng"), ("crowd", "độ đông"), ("shot", "khung cảnh")]:
        lines.append(f"  Theo {title}:")
        for key in sorted(gt[col].unique()):
            bad, ok = gt[(gt[col] == key) & (gt.cls == PNH)], gt[(gt[col] == key) & (gt.cls == PWH)]
            cells = []
            if len(bad):
                cells.append(f"không mũ: Recall {fmt((bad.pred == PNH).sum(), len(bad))}, → có mũ {(bad.pred == PWH).mean():.2f}, "
                             f"bỏ sót {(bad.pred == 'bỏ sót').mean():.2f}")
            if len(ok):
                cells.append(f"có mũ bị báo vi phạm {fmt((ok.pred == PNH).sum(), len(ok))}")
            if col in ("light", "crowd", "shot"):
                p = pr[pr[col] == key]
                cells.append(f"Precision vi phạm {fmt(int(p.tp.sum()), len(p))}")
            report[short][f"{col}={key}"] = {"pnh": len(bad), "pnh_recall": float((bad.pred == PNH).mean()) if len(bad) else None,
                                            "pnh_as_pwh": float((bad.pred == PWH).mean()) if len(bad) else None,
                                            "pwh": len(ok), "pwh_as_pnh": float((ok.pred == PNH).mean()) if len(ok) else None}
            lines.append(f"    {key:<14} " + " | ".join(cells))
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
print("\n".join(lines))
(out / "cases_output.txt").write_text("\n".join(lines) + "\n")
(out / "cases.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
(out / "image_attributes.csv").write_text(images.drop(columns="ignore").to_csv(index=False))
