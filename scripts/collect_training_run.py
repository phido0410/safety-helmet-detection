"""Gom kết quả một lần huấn luyện trên Colab (giải nén ở runs/<RUN>/) vào reports/training/<RUN>/ cho báo cáo.

Chép số liệu và hình cần thiết (không chép trọng số), và trích log gọn từ output của notebook huấn luyện
(đã lưu kèm kết quả) thành run_output.txt.

    .venv/bin/python scripts/collect_training_run.py --run M0_yolo11n --nb notebooks/05_train_m0.ipynb
"""
import argparse, json, re, shutil
from pathlib import Path

FILES = ["results.csv", "epoch_log.csv", "val_metrics.json", "args.yaml", "fig_curves.png",
         "val_best/confusion_matrix_normalized.png", "val_best/BoxPR_curve.png"]
# Dòng giữ lại theo ô notebook (nhận ô qua một đoạn mã nguồn); bỏ thanh tiến độ và bảng pandas in lặp
KEEP = {
    "EXPECTED.items()": ("train:", "val  :", "test :"),
    "model.train(": ("Ultralytics ", "Transferred", "optimizer: AdamW", "optimizer: SGD", "[", "epochs completed"),
    "best.val(": ("all ", "helmet ", "head ", "head_with_helmet ", "person_with_helmet ", "person_no_helmet ",
                  "face ", "Speed:", "mAP@0.5 =", "Recall ", "Tốc độ"),
}


def notebook_lines(nb_path):
    for cell in json.loads(Path(nb_path).read_text())["cells"]:
        keep = next((v for k, v in KEEP.items() if k in "".join(cell["source"])), None)
        for o in cell.get("outputs", []) if keep else []:
            if o.get("name") != "stdout":
                continue
            text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", "".join(o["text"]))
            yield from (l.rstrip() for l in re.split(r"[\r\n]", text)
                        if (l.strip().startswith(keep) or "epochs completed" in l) and "it/s" not in l and "s/it" not in l and "Fast image" not in l)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--nb", required=True)
    args = ap.parse_args()
    src, dst = Path("runs") / args.run, Path("reports/training") / args.run
    dst.mkdir(parents=True, exist_ok=True)
    for f in FILES:
        shutil.copy(src / f, dst / Path(f).name)

    lines = list(dict.fromkeys(notebook_lines(args.nb)))  # dòng phiên bản in lại khi đánh giá best.pt
    assert sum(l.startswith(f"[{args.run}] epoch") for l in lines) == len(open(src / "epoch_log.csv").readlines()) - 1
    (dst / "run_output.txt").write_text("\n".join(lines) + "\n")
    print(f"Đã ghi {dst}: {len(FILES)} tệp + run_output.txt ({len(lines)} dòng)")


if __name__ == "__main__":
    main()
