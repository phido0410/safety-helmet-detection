"""Tuần 10 (demo): chiều cao tối thiểu để app tính một người là vi phạm và tự lưu ảnh. Người ở xa (khung nhỏ) vừa khó đoán đúng
vừa không dùng được làm bằng chứng; người nhỏ hơn ngưỡng vẫn được vẽ khung mờ nhưng không tính, không lưu (anh chốt 2026-11-03).

Dự đoán đi qua đúng phần hậu xử lý của app (demo/src/lib/model.js people()): ngưỡng riêng từng lớp (bộ phận τ, vi phạm theo
part_rule.json, có mũ 0,399), quy tắc bộ phận – toàn thể, bỏ khung có mũ trùng khung không mũ (IoU > 0,7). Chiều cao người tính
trên ảnh đưa vào mô hình: chiều cao khung × imgsz / cạnh dài ảnh. Ghép một-một khung người dự đoán với nhãn cùng lớp (IoU ≥ 0,5,
xét dự đoán theo độ tin cậy giảm dần); Recall theo chiều cao nhãn, Precision theo chiều cao khung dự đoán.

Tiêu chí (chốt trước khi chạy): trên val SHEL5K, chia theo EDGES (nhóm có < MIN_N nhãn hoặc < MIN_N dự đoán vi phạm thì gộp với nhóm
lớn hơn liền kề); H = mép dưới của nhóm nhỏ nhất mà nó và mọi nhóm lớn hơn đều có Recall và Precision lớp vi phạm ≥ TARGET. H áp một
lần lên test SHEL5K và 3 tập ngoài miền: so Recall / Precision vi phạm khi tính mọi người và khi chỉ tính người ≥ H, kèm tỉ lệ người
vi phạm (nhãn) bị bỏ qua vì nhỏ hơn H.

    .venv/bin/python scripts/eval_min_size.py --weights runs/M3b_yolo26n_bg/weights/best.pt --imgsz 800 \\
        --part-rule reports/deployment/M3b_yolo26n_bg/part_rule/part_rule.json --out reports/deployment/M3b_yolo26n_bg/min_size

Bản 2 (chốt 2026-11-04 trước khi chạy, sau khi thử video: người đội mũ bị báo vi phạm, và H = 160 chọn trên ảnh SHEL5K bị phóng to
gần như loại hết người trong video HD):
- --dup-rule score: khung có mũ và khung không mũ trùng nhau (IoU > 0,7) thì giữ khung có độ tin cậy cao hơn (bản 1 luôn giữ khung
  không mũ). Nhận nếu trên val SHEL5K (ngưỡng vi phạm giữ nguyên, tính mọi người) cận dưới KTC 95% của Recall vi phạm vẫn ≥ 0,80
  (tiêu chí chọn ngưỡng của tuần 8); không đạt thì giữ quy tắc cũ.
- --height effective: chiều cao hiệu dụng = chiều cao khung × min(1, imgsz / cạnh dài): ảnh lớn được thu nhỏ thì tính trên ảnh đã thu
  nhỏ (như bản 1), ảnh nhỏ bị phóng to thì tính trên ảnh gốc (phóng to không thêm chi tiết). --select gộp val của cả ba nguồn huấn
  luyện (SHEL5K 416 px, SH17 và Open Images 800 px); EDGES, MIN_N, TARGET giữ như bản 1. H áp một lần lên test SHEL5K và 4 tập ngoài
  miền (OOD-4 đã được xem kết quả của bản 1 nên lần này không còn mù với ứng dụng).

    .venv/bin/python scripts/eval_min_size.py --weights runs/M3b_yolo26n_bg/weights/best.pt --imgsz 800 \\
        --part-rule reports/deployment/M3b_yolo26n_bg/part_rule/part_rule.json --dup-rule score --height effective \\
        --select "val SHEL5K" "val SH17" "val Open Images" --sets "test SHEL5K" OOD-1 OOD-2 OOD-3 OOD-4 \\
        --out reports/deployment/M3b_yolo26n_bg/min_size_v2
"""
import argparse, json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from ultralytics import YOLO
from ultralytics.data.utils import exif_size

from summarize_label_audit import wilson

EDGES = [0, 32, 48, 64, 80, 96, 128, 160, np.inf]
MIN_N, TARGET, IOU_MATCH, DUP_IOU, OTHER_CONF = 20, 0.70, 0.5, 0.7, 0.399
PARTS, PWH, PNH = ("helmet", "head", "head_with_helmet", "face"), "person_with_helmet", "person_no_helmet"
SETS = {"val SHEL5K": ["data/SHEL5K_processed/images/val"], "test SHEL5K": ["data/SHEL5K_processed/images/test"],
        "OOD-1": ["data/ood/images"], "OOD-2": ["data/ood2/images", "data/ood2b/images"], "OOD-3": ["data/ood3/images", "data/ood3b/images"],
        "OOD-4": ["data/ood4/images"],  # OOD-4: đánh giá độc lập bản triển khai (reports/ood4/plan.md), chỉ chạy bằng --apply
        "val SH17": ["data/external/sh17/yolo/images/val"], "val Open Images": ["data/external/openimages/yolo/images/val"]}

ap = argparse.ArgumentParser()
ap.add_argument("--weights", required=True)
ap.add_argument("--part-rule", required=True)
ap.add_argument("--imgsz", type=int, default=800)
ap.add_argument("--out", required=True)
ap.add_argument("--apply", help="min_size.json đã chọn: dùng lại H của nó, không chọn lại trên val (MPS không tất định), chỉ áp lên --sets")
ap.add_argument("--sets", nargs="+", default=["test SHEL5K", "OOD-1", "OOD-2", "OOD-3"])
ap.add_argument("--select", nargs="+", default=["val SHEL5K"], help="tập dùng để chọn H (gộp)")
ap.add_argument("--dup-rule", choices=["pnh", "score"], default="pnh", help="khung có mũ trùng khung không mũ: luôn giữ không mũ / giữ khung điểm cao hơn")
ap.add_argument("--height", choices=["model", "effective"], default="model", help="chiều cao trên ảnh vào mô hình / chiều cao hiệu dụng (không tính phóng to)")
args = ap.parse_args()
rule = json.loads(Path(args.part_rule).read_text())
model = YOLO(args.weights)
names = list(model.names.values())
part_ids, pwh, pnh = [names.index(n) for n in PARTS], names.index(PWH), names.index(PNH)
thr = np.array([rule["tau"] if i in part_ids else rule["conf"] if i == pnh else OTHER_CONF for i in range(len(names))])


def iou(a, b):
    w, h = min(a[2], b[2]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[1], b[1])
    return 0.0 if w <= 0 or h <= 0 else w * h / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - w * h)


def app_people(boxes, cls, conf):
    """Người như app thấy: [(box, vi_phạm, conf)] sau ngưỡng từng lớp, quy tắc bộ phận và bỏ khung có mũ trùng khung không mũ."""
    keep = conf >= thr[cls]
    boxes, cls, conf = boxes[keep], cls[keep], conf[keep]
    centers = [((b[0] + b[2]) / 2, (b[1] + b[3]) / 2) for b, c in zip(boxes, cls) if c in part_ids]
    inside = lambda b: any(b[0] <= x <= b[2] and b[1] <= y <= b[3] for x, y in centers)
    persons = [(b, c == pnh, f) for b, c, f in zip(boxes, cls, conf) if c in (pwh, pnh) and inside(b)]
    if args.dup_rule == "score":
        return [(b, v, f) for b, v, f in persons if not any(v2 != v and f2 > f and iou(b, q) > DUP_IOU for q, v2, f2 in persons)]
    bad = [b for b, v, _ in persons if v]
    return [(b, v, f) for b, v, f in persons if v or not any(iou(b, q) > DUP_IOU for q in bad)]


# tự kiểm tra: cùng bộ dữ liệu với keep_mask (eval_part_rule.py) và demo/test/people.mjs → chỉ khung người đầu được giữ
_b = np.array([[0, 0, 10, 20], [2, 1, 6, 5], [20, 0, 30, 20], [40, 0, 50, 20], [41, 1, 45, 5], [60, 0, 70, 20], [75, 1, 79, 5.]])
_c = np.array([names.index(n) for n in (PNH, "head", PWH, PNH, "face", PNH, "head")])
_saved, thr = thr, np.where(np.isin(np.arange(len(names)), part_ids), 0.1, 0.0)
assert [b[0] for b, _, _ in app_people(_b, _c, np.array([0.9, 0.5, 0.9, 0.9, 0.05, 0.9, 0.9]))] == [0]
# một người có cả khung có mũ (0,8) lẫn khung không mũ (0,4) gần trùng: bản 1 giữ không mũ, --dup-rule score giữ có mũ
_b2, _c2 = np.array([[0, 0, 10, 20], [0, 0, 10, 19.], [2, 1, 6, 5]]), np.array([pwh, pnh, names.index("head")])
assert [v for _, v, _ in app_people(_b2, _c2, np.array([0.8, 0.4, 0.5]))] == ([False] if args.dup_rule == "score" else [True])
thr = _saved


def labels(img):
    p = Path(str(img).replace("/images/", "/labels/")).with_suffix(".txt")
    w, h = exif_size(Image.open(img))  # kích thước sau khi xoay theo EXIF, như Ultralytics (ảnh báo chụp điện thoại)
    rows = [list(map(float, line.split())) for line in p.read_text().splitlines() if line.strip()] if p.exists() else []
    return [((cx - bw / 2) * w, (cy - bh / 2) * h, (cx + bw / 2) * w, (cy + bh / 2) * h, int(c) == pnh)
            for c, cx, cy, bw, bh in rows if int(c) in (pwh, pnh)], max(w, h)


def ignore_boxes(roots):
    """Vùng bỏ qua của tập ngoài miền (reports/<tập>/ignore.csv, label_ood.py): người bị che > 40%, không gán nhãn."""
    files = [Path("reports", Path(r).parent.name, "ignore.csv") for r in roots]
    ign = pd.concat([pd.read_csv(f) for f in files if f.exists()] or [pd.DataFrame(columns=["image", "x1", "y1", "x2", "y2"])])
    return {i: g[["x1", "y1", "x2", "y2"]].values.tolist() for i, g in ign.groupby("image")}


def collect(roots):
    """Từng nhãn vi phạm: (chiều cao, đúng?); từng dự đoán vi phạm: (chiều cao, đúng?). Dự đoán thuộc vùng bỏ qua (IoU với
    vùng đó ≥ IOU_MATCH và lớn hơn IoU với mọi nhãn) bị loại, như eval_ood.py."""
    gt_rows, pred_rows, ign = [], [], ignore_boxes(roots)
    for img in sorted(p for r in roots for p in Path(r).iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg")):
        gts, side = labels(img)
        b = model.predict(img, imgsz=args.imgsz, conf=float(thr.min()), device="mps", verbose=False)[0].boxes.cpu().numpy()
        preds = sorted(app_people(b.xyxy, b.cls.astype(int), b.conf), key=lambda p: -p[2])
        best_ign = lambda box: max((iou(box, q) for q in ign.get(img.name, [])), default=0)
        preds = [p for p in preds if not (best_ign(p[0]) >= IOU_MATCH and best_ign(p[0]) > max((iou(p[0], g[:4]) for g in gts), default=0))]
        k = args.imgsz / side if args.height == "model" else min(1.0, args.imgsz / side)
        used = set()
        for box, v, _ in preds:
            best = max((j for j, g in enumerate(gts) if j not in used and g[4] == v), key=lambda j: iou(box, gts[j][:4]), default=None)
            hit = best is not None and iou(box, gts[best][:4]) >= IOU_MATCH
            if hit:
                used.add(best)
            if v:
                pred_rows.append(((box[3] - box[1]) * k, hit))
        gt_rows += [((g[3] - g[1]) * k, j in used) for j, g in enumerate(gts) if g[4]]
    return np.array(gt_rows).reshape(-1, 2), np.array(pred_rows).reshape(-1, 2)


def rate(rows, lo=0, hi=np.inf):
    sel = rows[(rows[:, 0] >= lo) & (rows[:, 0] < hi)]
    return int(sel[:, 1].sum()), len(sel)


def bins(gt, pred):
    """Nhóm theo EDGES, gộp nhóm thiếu mẫu vào nhóm lớn hơn liền kề (duyệt từ nhóm lớn nhất xuống)."""
    out, hi = [], np.inf
    for lo in reversed(EDGES[:-1]):
        if rate(gt, lo, hi)[1] >= MIN_N and rate(pred, lo, hi)[1] >= MIN_N or lo == 0:
            out.append((lo, hi))
            hi = lo
    return out[::-1]


fmt = lambda k, n: f"{k / n:.3f} ({k}/{n}, KTC 95% {wilson(k, n)[0]:.3f}–{wilson(k, n)[1]:.3f})" if n else "–"
height_name = f"px trên ảnh {args.imgsz}" if args.height == "model" else f"px hiệu dụng = chiều cao × min(1, {args.imgsz} / cạnh dài)"
lines = [f"{args.weights}, imgsz {args.imgsz}, hậu xử lý như app ({args.part_rule}: τ = {rule['tau']}, ngưỡng vi phạm {rule['conf']:.3f}; "
         f"khung trùng khác lớp: {'giữ khung điểm cao hơn' if args.dup_rule == 'score' else 'luôn giữ không mũ'}; chiều cao: {height_name})",
         f"Tiêu chí: H = mép dưới nhóm nhỏ nhất mà nó và mọi nhóm lớn hơn có Recall và Precision vi phạm ≥ {TARGET} ({' + '.join(args.select)})"]
if args.apply:
    saved = json.loads(Path(args.apply).read_text())
    assert saved.get("height", "model") == args.height, f"{args.apply} chọn H theo chiều cao {saved.get('height', 'model')}"
    H, groups = saved["H"], []
    lines.append(f"Dùng lại H = {H:.0f} px của {args.apply} (không chọn lại trên val)")
else:
    gt, pred = (np.vstack(x) for x in zip(*(collect(SETS[s]) for s in args.select)))
    groups = bins(gt, pred)
    lines.append(f"{' + '.join(args.select)}: {len(gt)} người vi phạm (nhãn), {len(pred)} dự đoán vi phạm; theo chiều cao ({height_name}):")
    ok = []
    for lo, hi in groups:
        (rk, rn), (pk, pn) = rate(gt, lo, hi), rate(pred, lo, hi)
        ok.append(rn and pn and rk / rn >= TARGET and pk / pn >= TARGET)
        lines.append(f"  {lo:>4.0f}–{hi:<4.0f}  Recall {fmt(rk, rn)} | Precision {fmt(pk, pn)}{'' if ok[-1] else '  ← dưới mục tiêu'}")
    first = next((i for i in range(len(groups)) if all(ok[i:])), None)
    H = groups[first][0] if first is not None else None
    lines.append(f"  → H = {H:.0f} px" if H is not None else "  → không nhóm nào đạt: không đặt ngưỡng")

report = {"H": H, "groups": [list(g) for g in groups], "select": args.select, "dup_rule": args.dup_rule, "height": args.height, "apply": {}}
if H is not None:
    lines += ["", f"Áp một lần H = {H:.0f} px (Recall theo nhãn ≥ H, Precision theo dự đoán ≥ H):"]
    for name in args.sets:
        gt, pred = collect(SETS[name])
        (ra, na), (pa, ma), (rh, nh), (ph, mh) = rate(gt), rate(pred), rate(gt, H), rate(pred, H)
        report["apply"][name] = {"all": {"recall": ra / na, "precision": pa / ma, "gt": na, "pred": ma},
                                 "min_H": {"recall": rh / nh, "precision": ph / mh, "gt": nh, "pred": mh}, "gt_below_H": (na - nh) / na}
        lines.append(f"  {name:<12} mọi người: Recall {fmt(ra, na)}, Precision {fmt(pa, ma)}")
        lines.append(f"  {'':<12} người ≥ {H:.0f} px: Recall {fmt(rh, nh)}, Precision {fmt(ph, mh)}; người vi phạm < {H:.0f} px bị bỏ qua: "
                     f"{na - nh}/{na} ({(na - nh) / na:.0%})")
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
print("\n".join(lines))
(out / "min_size_output.txt").write_text("\n".join(lines) + "\n")
(out / "min_size.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=float))
