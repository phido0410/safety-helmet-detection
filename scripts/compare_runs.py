"""So sánh các lần huấn luyện đã gom ở reports/training/<RUN>/ (collect_training_run.py, eval_thresholds.py).

Ghi compare_output.txt (chỉ số theo lớp, tốc độ, ngưỡng đạt Recall mục tiêu) và fig_compare.png (mAP@0.5:0.95 và
Recall person_no_helmet trên tập val theo epoch). --split test dùng test_metrics.json (eval_thresholds.py --split test):
lớp vi phạm đánh giá ở ngưỡng đã chọn trên val.

    .venv/bin/python scripts/compare_runs.py --runs M0_yolo11n M1_yolo26n M1_yolo26n_img800 --out reports/training/compare_tuan6
"""
import argparse, json, re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"  # thứ tự cố định của bảng màu phân loại
GRAY, INK, INK2, GRID = "#b9b8b2", "#0b0b0b", "#52514e", "#e6e5e0"
COLORS = (BLUE, ORANGE, AQUA, YELLOW)
PRIORITY = "person_no_helmet"

ap = argparse.ArgumentParser()
ap.add_argument("--runs", nargs="+", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--split", default="val", choices=["val", "test"])
args = ap.parse_args()
assert len(args.runs) <= len(COLORS), f"tối đa {len(COLORS)} lần chạy mỗi hình"
root, out = Path("reports/training"), Path(args.out)
out.mkdir(parents=True, exist_ok=True)

rows, curves = [], {}
for run in args.runs:
    d = root / run
    m = json.loads((d / "val_metrics.json").read_text())
    if args.split == "val":
        res, per_class = m["val"], m["per_class"]
        thr = re.search(r"Recall >= [\d.]+: conf ([\d.]+), Precision ([\d.]+)", (d / "thresholds_output.txt").read_text())
        op = {"conf_R80": float(thr[1]), "P_at_R80": float(thr[2])}
    else:
        t = json.loads((d / "test_metrics.json").read_text())
        res, per_class = t["results"], t["per_class"]
        op = {"conf_val": t["val_conf_R80"], "R_at_conf": t["R_at_val_conf"], "P_at_conf": t["P_at_val_conf"]}
    pc = {c["Class"]: c for c in per_class}
    rows.append({"run": run, "model": Path(m["model"]).stem, "imgsz": m["imgsz"], "hours": m["train_hours"],
                 "mAP50": res["metrics/mAP50(B)"], "mAP50-95": res["metrics/mAP50-95(B)"],
                 "P": res["metrics/precision(B)"], "R": res["metrics/recall(B)"],
                 "R_pri": pc[PRIORITY]["Box-R"], "AP50_pri": pc[PRIORITY]["mAP50"], **op,
                 "ms": sum(m["speed_ms"][k] for k in ("preprocess", "inference", "postprocess")),
                 **{f"AP50 {c}": pc[c]["mAP50"] for c in pc}})
    res = pd.read_csv(d / "results.csv").drop_duplicates("epoch", keep="last")
    log = pd.read_csv(d / "epoch_log.csv").drop_duplicates("epoch", keep="last")
    curves[run] = (res["epoch"], res["metrics/mAP50-95(B)"], log["epoch"], log["recall_priority"])

df = pd.DataFrame(rows).set_index("run")
assert len(df) == len(args.runs)
pd.set_option("display.width", 200)
title = {"val": "Chỉ số trên tập val của best.pt (theo val_metrics.json",
         "test": "Chỉ số trên tập test của best.pt (theo test_metrics.json; lớp vi phạm ở ngưỡng chọn trên val"}[args.split]
text = [title + "; thời gian xử lý = tiền xử lý + suy luận + hậu xử lý, đo trên tập val, GPU T4)",
        df[["model", "imgsz", "hours", "mAP50", "mAP50-95", "P", "R", "R_pri", "AP50_pri", *op, "ms"]]
        .round(3).to_string(), "", "AP@0.5 theo lớp", df[[c for c in df.columns if c.startswith("AP50 ")]].round(3).T.to_string()]
print("\n".join(text))
(out / "compare_output.txt").write_text("\n".join(text) + "\n")

with plt.rc_context({"font.family": "Arial", "font.size": 10, "axes.edgecolor": INK2, "axes.labelcolor": INK,
                     "text.color": INK, "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
                     "axes.axisbelow": True, "savefig.dpi": 200, "savefig.bbox": "tight"}):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.4))
    for color, run in zip(COLORS, args.runs):
        e, mp, le, rp = curves[run]
        a1.plot(e, mp, color=color, lw=1.8, label=run)
        a2.plot(le, rp, color=color, lw=1.4, label=run)
    a1.set(title="mAP@0.5:0.95 trên tập val", xlabel="Epoch", ylim=(0.35, 0.62))
    a2.axhline(0.80, color=GRAY, lw=1, ls="--")
    a2.text(100, 0.80, " 0,80", va="center", fontsize=8, color=INK2)
    a2.set(title=f"Recall {PRIORITY} trên tập val", xlabel="Epoch", ylim=(0.55, 0.85))
    a1.legend(frameon=False, fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(out / "fig_compare.png")
print("Đã ghi", out)
