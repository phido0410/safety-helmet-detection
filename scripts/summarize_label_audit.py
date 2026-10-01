"""Tổng hợp kết quả kiểm định nhãn từ tệp CSV xuất ra bởi review.html.

Tính trên mẫu ngẫu nhiên (set = random):
- Tỉ lệ ảnh có lỗi, kèm khoảng tin cậy 95% (Wilson).
- Tỉ lệ lỗi theo hộp cho từng loại lỗi, kèm khoảng tin cậy 95%, và số hộp lỗi ước tính trên toàn bộ SHEL5K.
- Độ chính xác của gợi ý YOLO (số gợi ý là lỗi thật / số gợi ý đã xét).
Nhóm kiểm tra riêng (set = targeted) chỉ được thống kê mô tả, không dùng để ước lượng tỉ lệ.

Cách chạy:
    .venv/bin/python scripts/summarize_label_audit.py --csv reports/audit/label_audit_results.csv
"""

import argparse
import csv
import json
import math
from pathlib import Path

ERRORS = {"wrong_class": "Sai lớp", "missing": "Thiếu nhãn", "duplicate": "Trùng nhãn",
          "loose": "Hộp không khít", "spurious": "Hộp thừa"}
TOTAL_IMAGES = 5000
TOTAL_BOXES = 75578


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("reports/audit/audit_summary.json"))
    args = parser.parse_args()

    with open(args.csv, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    num = lambda r, k: int(r[k] or 0)
    random_rows = [r for r in rows if r["set"] == "random"]
    reviewed = [r for r in random_rows if r["reviewed"] == "1"]
    if len(reviewed) < len(random_rows):
        print(f"CẢNH BÁO: mới xem {len(reviewed)}/{len(random_rows)} ảnh của mẫu ngẫu nhiên; kết quả chưa đầy đủ.")

    n_img = len(reviewed)
    n_boxes = sum(num(r, "n_boxes") for r in reviewed)
    n_missing = sum(num(r, "missing") for r in reviewed)
    img_with_error = sum(1 for r in reviewed if any(num(r, k) for k in ERRORS))

    per_type = {}
    for key, name in ERRORS.items():
        k = sum(num(r, key) for r in reviewed)
        denom = n_boxes + n_missing if key == "missing" else n_boxes
        lo, hi = wilson(k, denom)
        rate = k / denom if denom else 0.0
        per_type[key] = {
            "name": name, "count": k, "denominator": denom, "rate": rate, "ci95": [lo, hi],
            "images_affected": sum(1 for r in reviewed if num(r, key)),
            # số lỗi trên mỗi hộp đã gán nhãn × tổng số hộp của SHEL5K
            "estimated_boxes_in_dataset": round(k / n_boxes * TOTAL_BOXES) if n_boxes else 0,
        }

    flags_total = sum(num(r, "n_yolo_flags") for r in reviewed)
    confirmed = sum(num(r, "yolo_confirmed") for r in reviewed)
    rejected = sum(num(r, "yolo_rejected") for r in reviewed)
    in_mirror = sum(num(r, "yolo_mirror") for r in reviewed)
    decided = confirmed + rejected + in_mirror

    summary = {
        "random_sample": {
            "images_reviewed": n_img, "boxes": n_boxes,
            "images_with_error": img_with_error,
            "image_error_rate": img_with_error / n_img if n_img else 0.0,
            "image_error_rate_ci95": list(wilson(img_with_error, n_img)),
            "estimated_images_with_error_in_dataset": round(img_with_error / n_img * TOTAL_IMAGES) if n_img else 0,
            "errors": per_type,
            "mirror_images": sum(1 for r in reviewed if r["mirror"] == "1"),
            "mirror_unlabeled_boxes": sum(num(r, "mirror_unlabeled") for r in reviewed),
            "mirror_labeled_boxes": sum(num(r, "mirror_labeled") for r in reviewed),
            "yolo": {"flags": flags_total, "confirmed": confirmed, "rejected": rejected, "in_mirror": in_mirror,
                     "undecided": flags_total - decided, "precision": confirmed / decided if decided else None},
        },
        "targeted": {
            "images_reviewed": sum(1 for r in rows if r["set"] == "targeted" and r["reviewed"] == "1"),
            "errors": {k: sum(num(r, k) for r in rows if r["set"] == "targeted" and r["reviewed"] == "1") for k in ERRORS},
        },
    }
    args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    rs = summary["random_sample"]
    pct = lambda x: f"{100 * x:.2f}%"
    print(f"Mẫu ngẫu nhiên: {n_img} ảnh, {n_boxes} hộp")
    print(f"Ảnh có ít nhất 1 lỗi: {img_with_error} ({pct(rs['image_error_rate'])}, "
          f"KTC95% {pct(rs['image_error_rate_ci95'][0])}–{pct(rs['image_error_rate_ci95'][1])})")
    print(f"\n{'Loại lỗi':16} {'Số hộp':>7} {'Tỉ lệ':>8} {'KTC 95%':>18} {'Ước tính toàn bộ':>17}")
    for v in per_type.values():
        print(f"{v['name']:16} {v['count']:>7} {pct(v['rate']):>8} {pct(v['ci95'][0]) + '–' + pct(v['ci95'][1]):>18} {v['estimated_boxes_in_dataset']:>17}")
    print(f"\nẢnh có vùng phản chiếu: {rs['mirror_images']} | Hộp trong vùng phản chiếu: không nhãn {rs['mirror_unlabeled_boxes']}, có nhãn {rs['mirror_labeled_boxes']}")
    y = rs["yolo"]
    prec = "—" if y["precision"] is None else pct(y["precision"])
    print(f"YOLO gợi ý: {y['flags']} | đúng lỗi: {y['confirmed']} | không phải lỗi: {y['rejected']} | "
          f"vùng phản chiếu: {y['in_mirror']} | chưa xét: {y['undecided']} | độ chính xác gợi ý: {prec}")
    print(f"\nĐã ghi {args.out}")


if __name__ == "__main__":
    main()
