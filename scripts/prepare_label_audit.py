"""Chuẩn bị kiểm định nhãn SHEL5K (Tuần 2).

1. Lấy mẫu ngẫu nhiên N ảnh với seed cố định.
2. Lập danh sách ảnh kiểm tra riêng: có nhãn trùng (IoU > 0,7 cùng lớp) hoặc mâu thuẫn (head vs head_with_helmet).
3. Chạy YOLO huấn luyện sẵn trên COCO để gợi ý người có thể bị thiếu nhãn: dự đoán lớp `person`
   không khớp (IoU < 0,5) với hộp person_with_helmet / person_no_helmet nào. Chỉ là gợi ý, người kiểm định quyết định.
4. Sinh trang review.html (mở trực tiếp bằng trình duyệt) để xem ảnh và ghi lỗi.

Cách chạy:
    .venv/bin/python scripts/prepare_label_audit.py
"""

import argparse
import json
import random
from itertools import combinations
from pathlib import Path

CLASSES = ["helmet", "head", "head_with_helmet", "person_with_helmet", "person_no_helmet", "face"]
PERSON_IDS = {3, 4}
DUP_IOU = 0.7
MATCH_IOU = 0.5


def read_labels(path: Path) -> list[list[float]]:
    return [[float(v) for v in line.split()] for line in path.read_text().splitlines() if line.strip()]


def to_xyxy(xc: float, yc: float, w: float, h: float) -> tuple[float, float, float, float]:
    return xc - w / 2, yc - h / 2, xc + w / 2, yc + h / 2


def iou(a, b) -> float:
    iw = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    ih = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = iw * ih
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def targeted_reason(labels: list[list[float]]) -> str | None:
    reasons = set()
    for (ca, *a), (cb, *b) in combinations(labels, 2):
        if iou(to_xyxy(*a), to_xyxy(*b)) <= DUP_IOU:
            continue
        if ca == cb:
            reasons.add(f"trùng {CLASSES[int(ca)]}")
        elif {int(ca), int(cb)} == {1, 2}:
            reasons.add("mâu thuẫn head / head_with_helmet")
    return "; ".join(sorted(reasons)) or None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--images", type=Path, default=Path("data/SHEL5K/Images"))
    parser.add_argument("--labels", type=Path, default=Path("data/SHEL5K_yolo/labels"))
    parser.add_argument("--out", type=Path, default=Path("reports/audit"))
    parser.add_argument("--n", type=int, default=300)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--model", default="weights/yolo26l.pt", help="Mô hình COCO dùng để gợi ý nhãn thiếu")
    parser.add_argument("--conf", type=float, default=0.4)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    stems = sorted(p.stem for p in args.labels.glob("*.txt"))
    labels = {s: read_labels(args.labels / f"{s}.txt") for s in stems}
    sample = sorted(random.Random(args.seed).sample(stems, args.n))
    targeted = {s: r for s in stems if s not in sample and (r := targeted_reason(labels[s]))}

    from ultralytics import YOLO  # import muộn để phần lấy mẫu chạy được cả khi chưa cài ultralytics

    model = YOLO(args.model)
    audit_stems = sample + sorted(targeted)
    flags: dict[str, list[dict]] = {}
    for stem in audit_stems:
        result = model.predict(args.images / f"{stem}.png", classes=[0], conf=args.conf, verbose=False)[0]
        persons = [to_xyxy(*l[1:]) for l in labels[stem] if int(l[0]) in PERSON_IDS]
        flags[stem] = []
        for box, conf in zip(result.boxes.xyxyn.tolist(), result.boxes.conf.tolist()):
            best = max((iou(box, p) for p in persons), default=0.0)
            if best < MATCH_IOU:
                flags[stem].append({"box": [round(v, 4) for v in box], "conf": round(conf, 3), "best_iou": round(best, 3)})

    items = [{"set": "random", "stem": s} for s in sample] + [{"set": "targeted", "stem": s, "reason": targeted[s]} for s in sorted(targeted)]
    for item in items:
        item["labels"] = [[int(l[0]), *(round(v, 4) for v in to_xyxy(*l[1:]))] for l in labels[item["stem"]]]
        item["flags"] = flags[item["stem"]]

    meta = {"seed": args.seed, "n": args.n, "model": args.model, "conf": args.conf, "match_iou": MATCH_IOU,
            "classes": CLASSES, "image_dir": Path("../..", args.images).as_posix()}
    (args.out / "audit_items.json").write_text(json.dumps({"meta": meta, "items": items}, ensure_ascii=False, indent=1), encoding="utf-8")

    template = (Path(__file__).parent / "audit_review_template.html").read_text(encoding="utf-8")
    html = template.replace("/*__AUDIT_DATA__*/null", json.dumps({"meta": meta, "items": items}, ensure_ascii=False))
    (args.out / "review.html").write_text(html, encoding="utf-8")

    n_flags = sum(len(flags[s]) for s in sample)
    print(f"Mẫu ngẫu nhiên: {len(sample)} ảnh (seed={args.seed}), {sum(len(labels[s]) for s in sample)} hộp")
    print(f"Kiểm tra riêng: {len(targeted)} ảnh")
    print(f"YOLO gợi ý thiếu nhãn người: {n_flags} gợi ý trên {sum(1 for s in sample if flags[s])} ảnh của mẫu ngẫu nhiên")
    print(f"Đã ghi {args.out / 'audit_items.json'} và {args.out / 'review.html'}")


if __name__ == "__main__":
    main()
