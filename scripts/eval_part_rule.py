"""Tuần 10 (demo): quy tắc bộ phận – toàn thể cho khung người. Một dự đoán người (person_with_helmet / person_no_helmet) chỉ
được giữ khi có dự đoán bộ phận (helmet, head, head_with_helmet, face) độ tin cậy ≥ τ có tâm nằm trong khung người đó. Lý do:
khi thử camera trên iPhone, M3 báo cả khung hình (bàn phím MacBook) là một người không đội mũ mà không thấy đầu / mũ / mặt nào.

Tiêu chí (chốt trước khi chạy): với mỗi τ trong TAUS (None = không lọc), ngưỡng lớp vi phạm được chọn lại trên val SHEL5K đúng
như select_threshold.py (ngưỡng lớn nhất có cận dưới Wilson 95% của Recall ≥ 0,80); chọn τ có Precision val ở ngưỡng đó cao
nhất, với điều kiện AP50 person_with_helmet trên val không giảm quá MAX_PWH_DROP so với không lọc; không τ nào hơn "không lọc"
thì không dùng quy tắc. τ và ngưỡng đã chọn được áp một lần lên test SHEL5K, 3 tập ngoài miền và tập ảnh không có người
(data/negatives, prepare_negatives.py, bỏ ảnh soát thấy có người — eval_negatives.negative_images; đo tỉ lệ ảnh có ≥ 1 dự đoán "người" / "người không đội mũ", cấu hình như demo: ngưỡng
riêng từng lớp rồi mới áp quy tắc; từng dự đoán ghi vào negatives_pred.csv để xem lại).
Quy tắc được chèn vào sau NMS của bộ đánh giá Ultralytics nên số liệu "không lọc" trùng với threshold.json của tuần 8–9.

    .venv/bin/python scripts/eval_part_rule.py --weights runs/M3_yolo26n_extra/weights/best.pt --imgsz 800 \\
        --out reports/deployment/M3_yolo26n_extra/part_rule
"""
import argparse, json, os
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from ultralytics import YOLO
from ultralytics.models.yolo.detect.val import DetectionValidator

from eval_negatives import negative_images
from summarize_label_audit import wilson

TAUS = (None, 0.05, 0.10, 0.25, 0.399)
PARTS, PERSONS = ("helmet", "head", "head_with_helmet", "face"), ("person_with_helmet", "person_no_helmet")
VIOLATION, TARGET, MAX_PWH_DROP = "person_no_helmet", 0.80, 0.01
OTHER_CONF = 0.399  # ngưỡng chung các lớp khác (tuần 8, như eval_ood.py, export_demo.py)
OOD = {"OOD-1": ["data/ood"], "OOD-2": ["data/ood2", "data/ood2b"], "OOD-3": ["data/ood3", "data/ood3b"]}
CONF_GRID = np.linspace(0, 1, 1000)  # lưới ngưỡng Ultralytics dùng cho p_curve, r_curve

ap = argparse.ArgumentParser()
ap.add_argument("--weights", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--data", default="data/SHEL5K_processed/data.yaml")
ap.add_argument("--imgsz", type=int, default=640)
args = ap.parse_args()
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
model = YOLO(args.weights)
names = list(model.names.values())
part_ids, person_ids = (torch.tensor([names.index(c) for c in cs]) for cs in (PARTS, PERSONS))
nms_post = DetectionValidator.postprocess


def keep_mask(bboxes, cls, conf, tau):
    """True cho dự đoán được giữ: không phải người, hoặc là người có tâm một bộ phận (conf ≥ tau) nằm trong khung."""
    part = torch.isin(cls, part_ids.to(cls.device)) & (conf >= tau)
    c = (bboxes[part, :2] + bboxes[part, 2:]) / 2
    inside = ((c[None, :, 0] >= bboxes[:, None, 0]) & (c[None, :, 0] <= bboxes[:, None, 2])
              & (c[None, :, 1] >= bboxes[:, None, 1]) & (c[None, :, 1] <= bboxes[:, None, 3])).any(1)
    return ~torch.isin(cls, person_ids.to(cls.device)) | inside


# tự kiểm tra: người có đầu bên trong được giữ, người không có bộ phận / bộ phận dưới τ / bộ phận ở ngoài thì bị bỏ
_b = torch.tensor([[0, 0, 10, 20], [2, 1, 6, 5], [20, 0, 30, 20], [40, 0, 50, 20], [41, 1, 45, 5], [60, 0, 70, 20], [75, 1, 79, 5.]])
_c = torch.tensor([names.index(c) for c in ("person_no_helmet", "head", "person_with_helmet", "person_no_helmet", "face",
                                            "person_no_helmet", "head")], dtype=torch.float)
_f = torch.tensor([0.9, 0.5, 0.9, 0.9, 0.05, 0.9, 0.9])
assert keep_mask(_b, _c, _f, 0.1).tolist() == [True, True, False, False, True, False, True]


def evaluate(data, split, tau, batch=16):
    def post(self, preds):
        res = nms_post(self, preds)
        if tau is not None:
            for d in res:
                k = keep_mask(d["bboxes"], d["cls"], d["conf"], tau)
                for key in d:
                    d[key] = d[key][k]
        return res
    DetectionValidator.postprocess = post
    try:
        v = model.val(data=data, split=split, imgsz=args.imgsz, batch=batch, plots=False, verbose=False, device="mps",
                      project=os.environ.get("TMPDIR", "/tmp"), name="part_rule", exist_ok=True)
    finally:
        DetectionValidator.postprocess = nms_post
    idx = list(v.box.ap_class_index)
    k = idx.index(names.index(VIOLATION))
    n = next(c["Instances"] for c in v.summary() if c["Class"] == VIOLATION)
    ap50 = {names[c]: float(v.box.ap50[i]) for i, c in enumerate(idx) if names[c] in PERSONS}
    return v.box.r_curve[k], v.box.p_curve[k], int(n), ap50


def at(r, p, n, thr):
    j = np.abs(CONF_GRID - thr).argmin()
    lo, hi = wilson(round(r[j] * n), n)
    return {"recall": float(r[j]), "recall_ci95": [lo, hi], "precision": float(p[j]), "boxes": n}


def ood_yaml(name, roots):
    """Gộp các đợt của một tập ngoài miền vào một file yaml tạm riêng cho tập đó (như eval_ood.py)."""
    y = Path(os.environ.get("TMPDIR", "/tmp"), f"part_rule_{name}.yaml")
    y.write_text("\n".join(f"{s}: {[str(Path(r).resolve() / 'images') for r in roots]}" for s in ("train", "val", "test"))
                 + "\n" + Path(roots[0], "ood.yaml").read_text().split("nc:", 1)[1].join(["nc:", ""]))
    return str(y)


fmt = lambda d: (f"Recall {d['recall']:.3f} (KTC 95% {d['recall_ci95'][0]:.3f}–{d['recall_ci95'][1]:.3f}), "
                 f"Precision {d['precision']:.3f}")
tau_txt = lambda t: "không lọc" if t is None else f"τ = {t:.3f}"
lines = [f"{args.weights}, imgsz {args.imgsz}, quy tắc bộ phận – toàn thể (bộ phận: {', '.join(PARTS)})",
         f"Chọn trên val SHEL5K: ngưỡng {VIOLATION} = ngưỡng lớn nhất có cận dưới KTC 95% của Recall ≥ {TARGET:.2f}"]
val = {}
for tau in TAUS:
    r, p, n, ap50 = evaluate(args.data, "val", tau)
    thr = CONF_GRID[np.where(np.array([wilson(round(x * n), n)[0] for x in r]) >= TARGET)[0].max()]
    val[tau] = {"conf": float(thr), **at(r, p, n, thr), "ap50": ap50}
    lines.append(f"  {tau_txt(tau):<14} ngưỡng {thr:.3f}: {fmt(val[tau])} | AP50 pwh {ap50['person_with_helmet']:.3f}, "
                 f"pnh {ap50[VIOLATION]:.3f}")
base = val[None]
ok = [t for t in TAUS if t is not None
      and base["ap50"]["person_with_helmet"] - val[t]["ap50"]["person_with_helmet"] <= MAX_PWH_DROP
      and val[t]["precision"] > base["precision"]]
best = max(ok, key=lambda t: val[t]["precision"], default=None)
lines.append(f"  → chọn: {tau_txt(best)}" + ("" if best is not None else " (không τ nào hơn không lọc: không dùng quy tắc)"))

report = {}
if best is not None:
    lines += ["", f"Áp một lần (ngưỡng vi phạm chọn trên val: không lọc {base['conf']:.3f}, {tau_txt(best)} {val[best]['conf']:.3f}):"]
    # batch như script chính thức (select_threshold.py 16, eval_ood.py 8): Ultralytics ghép ảnh theo lô nên số hơi đổi theo batch
    for name, data, batch in [("test SHEL5K", args.data, 16), *((k, ood_yaml(k, v), 8) for k, v in OOD.items())]:
        report[name] = {}
        for tau in (None, best):
            r, p, n, ap50 = evaluate(data, "test", tau, batch)
            report[name][tau_txt(tau)] = {**at(r, p, n, val[tau]["conf"]), "ap50": ap50}
            d = report[name][tau_txt(tau)]
            lines.append(f"  {name:<12} {tau_txt(tau):<14} {fmt(d)} | AP50 pwh {ap50['person_with_helmet']:.3f}, pnh {ap50[VIOLATION]:.3f}")

    imgs = negative_images()
    preds = {f.name: model.predict(f, imgsz=args.imgsz, conf=min(t for t in TAUS if t is not None), device="mps", verbose=False)[0].boxes.cpu()
             for f in imgs}
    rows = []
    report["ảnh không người"] = {}
    for tau in (None, best):
        cut = torch.tensor([val[tau]["conf"] if c == VIOLATION else OTHER_CONF for c in names])
        any_person = violation = 0
        for img, b in preds.items():
            ok = torch.isin(b.cls, person_ids.float()) & (b.conf >= cut[b.cls.long()])
            if tau is not None:
                ok &= keep_mask(b.xyxy, b.cls, b.conf, tau)
            found = [(names[int(b.cls[i])], float(b.conf[i]), [round(x) for x in b.xyxy[i].tolist()]) for i in torch.where(ok)[0]]
            rows += [{"image": img, "rule": tau_txt(tau), "cls": c, "conf": round(f, 3), "box": box} for c, f, box in found]
            any_person += bool(found)
            violation += any(c == VIOLATION for c, _, _ in found)
        n = len(imgs)
        rate = lambda k: {"images": k, "rate": k / n, "ci95": list(wilson(k, n))}
        report["ảnh không người"][tau_txt(tau)] = {"images": n, "any_person": rate(any_person), "violation": rate(violation)}
        pct = lambda k: f"{k} ({k / n:.1%}, KTC 95% {wilson(k, n)[0]:.1%}–{wilson(k, n)[1]:.1%})"
        lines.append(f"  ảnh không người ({n}) {tau_txt(tau):<14} ảnh có ≥ 1 \"người\": {pct(any_person)}; "
                     f"có ≥ 1 \"người không đội mũ\": {pct(violation)}")
    pd.DataFrame(rows, columns=["image", "rule", "cls", "conf", "box"]).to_csv(out / "negatives_pred.csv", index=False)
print("\n".join(lines))
(out / "part_rule_output.txt").write_text("\n".join(lines) + "\n")
(out / "part_rule.json").write_text(json.dumps({"weights": args.weights, "imgsz": args.imgsz, "parts": PARTS, "tau": best,
    "conf": val[best]["conf"] if best is not None else base["conf"], "val": {tau_txt(t): d for t, d in val.items()}, "apply": report},
    ensure_ascii=False, indent=2))
for cache in [*Path(args.data).parent.glob("labels/*.cache"), *(c for rs in OOD.values() for r in rs for c in Path(r).glob("*.cache"))]:
    cache.unlink()
