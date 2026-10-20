"""Tiền xử lý SHEL5K và chia tập (Tuần 4).

1. Xóa nhãn trùng đã được người kiểm định xác nhận (CONFIRMED_DUPLICATES).
2. Cắt bỏ dải đệm phản chiếu (phát hiện ở CV-EDA, reports/eda/image_stats.csv); bỏ các hộp có tâm nằm trong dải đệm
   (bản sao phản chiếu), cắt các hộp còn lại theo vùng ảnh thật.
3. Chia train/val/test 70/15/15: phân tầng theo số hộp của từng lớp, giữ mỗi nhóm ảnh gần trùng
   (reports/eda/duplicate_groups.csv) nằm trọn trong một tập để tránh rò rỉ dữ liệu.
4. Ghi tập dữ liệu dạng YOLO (images/<tập>, labels/<tập>) kèm data.yaml, và báo cáo trong reports/preprocessing/.

Không đổi kích thước ảnh trên đĩa: Ultralytics tự đưa ảnh về imgsz=640 khi huấn luyện.

Cách chạy:
    .venv/bin/python scripts/prepare_dataset.py
"""

import argparse
import csv
import json
import random
import shutil
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

CLASSES = ["helmet", "head", "head_with_helmet", "person_with_helmet", "person_no_helmet", "face"]
SPLITS = {"train": 0.70, "val": 0.15, "test": 0.15}
PAD_THRESHOLD = 0.3  # như notebook CV-EDA

# Nhãn trùng trong các ảnh được người kiểm định ghi nhận có trùng (Tuần 2): số thứ tự hộp như trong review.html, bắt đầu
# từ 1. Hộp bị xóa là hộp sau trong cặp cùng lớp có IoU > 0,7 (cùng tiêu chí đã dùng để lập danh sách kiểm tra riêng).
# hard_hat_workers2967 được ghi nhận có 1 hộp trùng nhưng không có cặp nào đạt tiêu chí (IoU lớn nhất 0,39) nên giữ nguyên.
CONFIRMED_DUPLICATES = {
    "hard_hat_workers1404": [28],  # person_with_helmet 27 ~ 28, IoU 0,94
    "hard_hat_workers1561": [16],  # person_no_helmet 11 ~ 16, IoU 0,81
    "hard_hat_workers2152": [63],  # person_with_helmet 62 ~ 63, IoU 0,92
    "hard_hat_workers352": [17],   # head_with_helmet 16 ~ 17, IoU 0,82
    "hard_hat_workers1125": [33],  # person_with_helmet 28 ~ 33, IoU 0,88
    "hard_hat_workers3226": [10],  # head 4 ~ 10, IoU 0,71
    "hard_hat_workers3423": [9],   # helmet 2 ~ 9, IoU 0,71
    "hard_hat_workers964": [2],    # helmet 1 ~ 2, IoU 0,70
}


def crop_labels(boxes, width, height, axis, pad):
    """Cắt dải đệm khỏi nhãn. boxes: [(cls, x1, y1, x2, y2)] theo pixel ảnh gốc.
    Trả về (hộp theo pixel của ảnh đã cắt, (rộng, cao) ảnh đã cắt, số hộp trong dải đệm, số hộp bị cắt bớt)."""
    if axis is None:
        return list(boxes), (width, height), 0, 0
    x0, y0, x1, y1 = (0, pad, width, height - pad) if axis == "tb" else (pad, 0, width - pad, height)
    kept, in_pad, clipped = [], 0, 0
    for c, bx1, by1, bx2, by2 in boxes:
        cx, cy = (bx1 + bx2) / 2, (by1 + by2) / 2
        if not (x0 <= cx < x1 and y0 <= cy < y1):
            in_pad += 1
            continue
        nb = (max(bx1, x0), max(by1, y0), min(bx2, x1), min(by2, y1))
        clipped += max(x0 - bx1, y0 - by1, bx2 - x1, by2 - y1) > 0.5  # bỏ qua sai số làm tròn của tọa độ chuẩn hóa
        kept.append((c, nb[0] - x0, nb[1] - y0, nb[2] - x0, nb[3] - y0))
    return kept, (x1 - x0, y1 - y0), in_pad, clipped


def stratified_group_split(unit_counts, unit_sizes, ratios, seed):
    """Chia các đơn vị (nhóm ảnh) theo tỉ lệ, phân tầng theo số hộp mỗi lớp (iterative stratification, Sechidis 2011):
    lần lượt xét lớp hiếm nhất còn lại, gán từng đơn vị chứa lớp đó vào tập đang thiếu lớp đó nhiều nhất."""
    rng = random.Random(seed)
    names = list(ratios)
    counts = {u: np.asarray(v, dtype=float) for u, v in unit_counts.items()}
    total = sum(counts.values())
    need = {s: ratios[s] * total for s in names}
    need_n = {s: ratios[s] * sum(unit_sizes.values()) for s in names}
    assign, todo = {}, set(counts)

    def put(u, c):
        # c = None: đơn vị không có nhãn, chỉ cân theo số ảnh
        s = max(names, key=lambda s: (need_n[s] if c is None else need[s][c], need_n[s]))
        assign[u] = s
        need[s] -= counts[u]
        need_n[s] -= unit_sizes[u]
        todo.discard(u)

    while todo:
        remaining = sum(counts[u] for u in todo)
        if not remaining.any():  # các ảnh không còn nhãn: chia theo số ảnh
            for u in sorted(todo):
                put(u, None)
            break
        c = min((k for k in range(len(remaining)) if remaining[k] > 0), key=lambda k: remaining[k])
        cand = sorted(u for u in todo if counts[u][c] > 0)
        rng.shuffle(cand)
        for u in cand:
            put(u, c)
    return assign


def _self_test():
    # Hộp trong dải đệm bị bỏ, hộp trong vùng ảnh thật được dời gốc tọa độ, hộp vắt qua biên bị cắt
    boxes = [(0, 10, 5, 30, 20), (1, 10, 100, 50, 150), (2, 10, 60, 50, 90)]
    kept, size, in_pad, clipped = crop_labels(boxes, 416, 416, "tb", 68)
    assert size == (416, 280) and in_pad == 1 and clipped == 1, (kept, size, in_pad, clipped)
    assert kept == [(1, 10, 32, 50, 82), (2, 10, 0, 50, 22)], kept
    # Chia tập: nhóm không bị tách, tỉ lệ lớp gần đúng
    rng = np.random.default_rng(0)
    uc = {f"u{i}": rng.integers(0, 5, 3) for i in range(400)}
    a = stratified_group_split(uc, {u: 1 for u in uc}, SPLITS, 0)
    share = sum(uc[u] for u in uc if a[u] == "train") / sum(uc.values())
    assert set(a) == set(uc) and np.all(np.abs(share - 0.7) < 0.03), share


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--images", type=Path, default=Path("data/SHEL5K/Images"))
    parser.add_argument("--labels", type=Path, default=Path("data/SHEL5K_yolo/labels"))
    parser.add_argument("--eda", type=Path, default=Path("reports/eda"))
    parser.add_argument("--out", type=Path, default=Path("data/SHEL5K_processed"))
    parser.add_argument("--report", type=Path, default=Path("reports/preprocessing"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    _self_test()

    stats = {r["filename"]: r for r in csv.DictReader(open(args.eda / "image_stats.csv", encoding="utf-8"))}
    group_of = {r["filename"]: f"g{r['dup_group']}" for r in csv.DictReader(open(args.eda / "duplicate_groups.csv", encoding="utf-8"))}

    records, labels_out = {}, {}
    for stem, st in sorted(stats.items()):
        W, H = int(st["width"]), int(st["height"])
        rows = [l.split() for l in (args.labels / f"{stem}.txt").read_text().splitlines() if l.strip()]
        boxes = [(int(c), (float(x) - float(w) / 2) * W, (float(y) - float(h) / 2) * H,
                  (float(x) + float(w) / 2) * W, (float(y) + float(h) / 2) * H) for c, x, y, w, h in rows]
        dup_ids = CONFIRMED_DUPLICATES.get(stem, [])
        boxes_nodup = [b for k, b in enumerate(boxes, 1) if k not in dup_ids]
        has_pad = float(st["pad_score"]) < PAD_THRESHOLD
        axis = st["pad_axis"] if has_pad else None
        pad = int(float(st["pad_width"])) if has_pad else 0
        kept, (cw, ch), in_pad, clipped = crop_labels(boxes_nodup, W, H, axis, pad)
        records[stem] = {
            "filename": stem, "unit": group_of.get(stem, stem), "pad_axis": axis or "", "pad_width": pad,
            "width": W, "height": H, "crop_width": cw, "crop_height": ch,
            "boxes_before": len(boxes), "duplicates_removed": len(boxes) - len(boxes_nodup),
            "boxes_in_pad": in_pad, "boxes_clipped": clipped, "boxes_after": len(kept),
            **{f"before_{c}": sum(b[0] == i for b in boxes) for i, c in enumerate(CLASSES)},
            **{f"after_{c}": sum(b[0] == i for b in kept) for i, c in enumerate(CLASSES)},
        }
        labels_out[stem] = (kept, cw, ch, (axis, pad))

    unit_counts, unit_sizes = defaultdict(lambda: np.zeros(len(CLASSES))), defaultdict(int)
    for r in records.values():
        unit_counts[r["unit"]] += [r[f"after_{c}"] for c in CLASSES]
        unit_sizes[r["unit"]] += 1
    split_of_unit = stratified_group_split(dict(unit_counts), dict(unit_sizes), SPLITS, args.seed)
    for r in records.values():
        r["split"] = split_of_unit[r["unit"]]

    # Ghi tập dữ liệu
    if args.out.exists():
        shutil.rmtree(args.out)
    for s in SPLITS:
        (args.out / "images" / s).mkdir(parents=True)
        (args.out / "labels" / s).mkdir(parents=True)
    for stem, (kept, cw, ch, (axis, pad)) in labels_out.items():
        s = records[stem]["split"]
        img = cv2.imread(str(args.images / f"{stem}.png"))
        if axis == "tb":
            img = img[pad:img.shape[0] - pad]
        elif axis == "lr":
            img = img[:, pad:img.shape[1] - pad]
        assert img.shape[1] == cw and img.shape[0] == ch, (stem, img.shape, cw, ch)
        cv2.imwrite(str(args.out / "images" / s / f"{stem}.png"), img)
        lines = []
        for c, x1, y1, x2, y2 in kept:
            xc, yc, w, h = (x1 + x2) / 2 / cw, (y1 + y2) / 2 / ch, (x2 - x1) / cw, (y2 - y1) / ch
            assert 0 <= xc <= 1 and 0 <= yc <= 1 and 0 < w <= 1 and 0 < h <= 1, (stem, c, xc, yc, w, h)
            lines.append(f"{c} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}")
        (args.out / "labels" / s / f"{stem}.txt").write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    (args.out / "data.yaml").write_text(
        "# SHEL5K đã cắt dải đệm phản chiếu và chia tập (scripts/prepare_dataset.py)\n"
        "# Không khai báo path: Ultralytics lấy thư mục chứa tệp này làm gốc (dùng được cả local và Colab)\n"
        "train: images/train\nval: images/val\ntest: images/test\n"
        f"nc: {len(CLASSES)}\nnames: {json.dumps(CLASSES)}\n", encoding="utf-8")

    # Kiểm tra và báo cáo
    recs = list(records.values())
    tot = lambda key, rs=recs: sum(r[key] for r in rs)
    assert tot("boxes_after") == tot("boxes_before") - tot("duplicates_removed") - tot("boxes_in_pad")
    units_split = defaultdict(set)
    for r in recs:
        units_split[r["unit"]].add(r["split"])
    assert all(len(v) == 1 for v in units_split.values()), "có nhóm gần trùng bị tách giữa các tập"

    args.report.mkdir(parents=True, exist_ok=True)
    with open(args.report / "split.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(recs[0]))
        w.writeheader()
        w.writerows(recs)
    by_split = {s: [r for r in recs if r["split"] == s] for s in SPLITS}
    summary = {
        "seed": args.seed, "images": len(recs),
        "duplicates_removed": tot("duplicates_removed"), "boxes_in_pad_removed": tot("boxes_in_pad"),
        "boxes_clipped": tot("boxes_clipped"), "boxes_before": tot("boxes_before"), "boxes_after": tot("boxes_after"),
        "images_cropped": sum(r["pad_axis"] != "" for r in recs),
        "images_without_labels_after": sum(r["boxes_after"] == 0 for r in recs),
        "per_class": {c: {"before": tot(f"before_{c}"), "after": tot(f"after_{c}")} for c in CLASSES},
        "splits": {s: {"images": len(rs), "boxes": tot("boxes_after", rs),
                       **{c: tot(f"after_{c}", rs) for c in CLASSES}} for s, rs in by_split.items()},
        "groups_kept_together": sum(1 for u in units_split if u.startswith("g")),
    }
    (args.report / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Ảnh: {len(recs)} | đã cắt dải đệm: {summary['images_cropped']} | không còn nhãn sau khi cắt: {summary['images_without_labels_after']}")
    print(f"Hộp: {summary['boxes_before']} → {summary['boxes_after']} "
          f"(xóa {summary['duplicates_removed']} nhãn trùng, bỏ {summary['boxes_in_pad_removed']} hộp trong dải đệm; "
          f"{summary['boxes_clipped']} hộp bị cắt bớt theo biên)")
    print(f"\n{'Lớp':20} {'trước':>7} {'sau':>7}   " + "   ".join(f"{s:>12}" for s in SPLITS))
    for c in CLASSES:
        n = summary["per_class"][c]["after"]
        print(f"{c:20} {summary['per_class'][c]['before']:>7} {n:>7}   "
              + "   ".join(f"{summary['splits'][s][c]:>5} ({summary['splits'][s][c] / n * 100:4.1f}%)" for s in SPLITS))
    print(f"{'Số ảnh':20} {'':>7} {len(recs):>7}   " + "   ".join(f"{len(by_split[s]):>5} ({len(by_split[s]) / len(recs) * 100:4.1f}%)" for s in SPLITS))
    print(f"\n{summary['groups_kept_together']} nhóm ảnh gần trùng đều nằm trọn trong một tập")
    print(f"Đã ghi {args.out} và {args.report}")


if __name__ == "__main__":
    main()
