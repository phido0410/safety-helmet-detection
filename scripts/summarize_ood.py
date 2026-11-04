"""Bảng tổng hợp các mô hình trên 4 tập ngoài miền (sau rà soát nhãn 2026-11-04, docs/huong_dan_gan_nhan_ngoai_mien.md) từ
reports/<tập>/<RUN>/ood_metrics.json của eval_ood.py. Dấu * đánh dấu ô không khách quan: tập đó đã được dùng để tìm lỗi
hoặc thiết kế mô hình ấy (OOD-1 dùng để tìm lỗi của M2 rồi làm M3, M3b).

    .venv/bin/python scripts/summarize_ood.py
"""
import json
from pathlib import Path

RUNS = ["M0_yolo11n", "M1_yolo26n", "M1_yolo26n_img800", "M2_yolo26n", "M3_yolo26n_extra", "M3b_yolo26n_bg"]
SETS = {"OOD-1": "ood", "OOD-2": "ood2", "OOD-3": "ood3", "OOD-4": "ood4"}
NOT_BLIND = {("OOD-1", "M3_yolo26n_extra"), ("OOD-1", "M3b_yolo26n_bg")}
MAX_GAP = 0.15

lines = ["mAP@0.5 hai lớp người ngoài miền (chênh so với test SHEL5K cùng 2 lớp; mục tiêu ≤ 0,15) | Recall / Precision lớp vi phạm ở"
         " ngưỡng chọn trên val (Wilson)", ""]
lines.append(f"{'Mô hình':<20}" + "  ".join(f"{k:<38}" for k in SETS))
for run in RUNS:
    cells = []
    for k, d in SETS.items():
        m = json.loads(Path("reports", d, run, "ood_metrics.json").read_text())
        ok = "đạt" if round(m["gap"], 3) <= MAX_GAP else "—"
        mark = "*" if (k, run) in NOT_BLIND else " "
        cells.append(f"{m['map50_ood']:.3f}{mark} (chênh {m['gap']:.3f} {ok}) R/P {m['recall_pri']:.2f}/{m['precision_pri']:.2f}")
    lines.append(f"{run:<20}" + "  ".join(f"{c:<38}" for c in cells))
m = {k: json.loads(Path("reports", d, RUNS[-1], "ood_metrics.json").read_text()) for k, d in SETS.items()}
lines += ["", "Số ảnh / hộp người (pwh + pnh) / vùng bỏ qua: " + "; ".join(
    f"{k} {v['images']} ảnh, {sum(v['boxes'].values())} hộp, {v.get('ignore', 0)} vùng" for k, v in m.items()),
    "* tập đã dùng để tìm lỗi / thiết kế mô hình đó (không khách quan)."]
print("\n".join(lines))
Path("reports/ood_summary.txt").write_text("\n".join(lines) + "\n")
