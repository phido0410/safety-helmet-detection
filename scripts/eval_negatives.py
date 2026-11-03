"""Tuần 10: báo nhầm trên ảnh không có người (data/negatives: 200 ảnh Open Images V7 đã được người xác minh là không có người,
scripts/prepare_negatives.py), trừ ảnh soát bằng mắt thấy có người (reports/negatives/review.csv; tiêu chí chốt trước: thấy bất
kỳ phần cơ thể người thật nào, mọi kích thước, kể cả phản chiếu; tranh vẽ, đồ chơi, tượng không tính). Mỗi mô hình chạy như demo
(predict, ngưỡng lớp vi phạm theo threshold.json của mô hình đó, lớp khác OTHER_CONF; mô hình không có threshold.json dùng
OTHER_CONF cho mọi lớp). Báo: số ảnh có ≥ 1 dự đoán "người" (2 lớp người), ≥ 1 "người không đội mũ" (KTC 95% Wilson), số khung
"người" báo nhầm và số khung chiếm ≥ BIG diện tích ảnh.

    .venv/bin/python scripts/eval_negatives.py --runs M1_yolo26n_img800 M2_yolo26n M3_yolo26n_extra --imgsz 800
"""
import argparse, json
from pathlib import Path

import pandas as pd
from ultralytics import YOLO

from summarize_label_audit import wilson

OTHER_CONF, BIG = 0.399, 0.5  # ngưỡng chung các lớp khác (tuần 8, như eval_ood.py); khung "to" = ≥ 50% diện tích ảnh
PERSONS, VIOLATION = ("person_with_helmet", "person_no_helmet"), "person_no_helmet"
IMAGES, REVIEW = Path("data/negatives/yolo/images/val"), Path("reports/negatives/review.csv")


def negative_images(images=IMAGES):
    """Ảnh của tập không người, bỏ ảnh soát thấy có người; review.csv phải phủ đúng các ảnh đang có."""
    review = pd.read_csv(REVIEW).set_index("image")
    imgs = sorted(images.glob("*.jpg"))
    assert imgs and sorted(review.index) == [p.name for p in imgs], f"{REVIEW} không khớp ảnh trong {images}"
    return [p for p in imgs if review.loc[p.name, "has_person"] == 0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--out", default="reports/negatives")
    ap.add_argument("--imgsz", type=int, default=640)
    args = ap.parse_args()
    imgs, out = negative_images(), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    pct = lambda k, n: f"{k:>3} ({k / n:5.1%}, KTC 95% {wilson(k, n)[0]:.1%}–{wilson(k, n)[1]:.1%})"
    lines = [f"{len(imgs)} ảnh không có người ({IMAGES}, trừ ảnh có người theo {REVIEW}), imgsz {args.imgsz}, ngưỡng như demo:"]
    result = {}
    for run in args.runs:
        thr_file = Path("reports/error_analysis", run, "threshold.json")
        thr = json.loads(thr_file.read_text())["conf"] if thr_file.exists() else OTHER_CONF
        model = YOLO(Path("runs", run, "weights", "best.pt"))
        any_person = violation = boxes = big = 0
        for f in imgs:
            r = model.predict(f, imgsz=args.imgsz, conf=min(thr, OTHER_CONF), device="mps", verbose=False)[0]
            h, w = r.orig_shape
            found = [(model.names[int(c)], (b[2] - b[0]) * (b[3] - b[1]) / (w * h))
                     for b, c, s in zip(r.boxes.xyxy.tolist(), r.boxes.cls.tolist(), r.boxes.conf.tolist())
                     if model.names[int(c)] in PERSONS and s >= (thr if model.names[int(c)] == VIOLATION else OTHER_CONF)]
            any_person += bool(found)
            violation += any(c == VIOLATION for c, _ in found)
            boxes += len(found)
            big += sum(a >= BIG for _, a in found)
        n = len(imgs)
        result[run] = {"threshold": thr, "images": n, "any_person": any_person, "violation": violation,
                       "violation_ci95": list(wilson(violation, n)), "boxes": boxes, "big_boxes": big}
        lines.append(f"  {run:<20} ngưỡng vi phạm {thr:.3f} | ảnh có \"người\" {pct(any_person, n)} | có \"người không đội mũ\" "
                     f"{pct(violation, n)} | khung báo nhầm {boxes}, ≥ {BIG:.0%} diện tích ảnh {big}")
    print("\n".join(lines))
    (out / "negatives_eval.txt").write_text("\n".join(lines) + "\n")
    (out / "negatives_eval.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
