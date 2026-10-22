"""Gom kết quả một lần huấn luyện trên Colab (giải nén ở runs/<RUN>/) vào reports/training/<RUN>/ cho báo cáo.

Chép số liệu và hình cần thiết (không chép trọng số), và trích log gọn từ output của notebook huấn luyện
(đã lưu kèm kết quả) thành run_output.txt.

    .venv/bin/python scripts/collect_training_run.py --run M0_yolo11n --nb notebooks/05_train_m0.ipynb
    Huấn luyện qua nhiều phiên (Colab ngắt, chạy lại để huấn luyện tiếp): liệt kê các notebook đã lưu theo thứ tự phiên.
"""
import argparse, json, re, shutil
from pathlib import Path

FILES = ["results.csv", "epoch_log.csv", "val_metrics.json", "args.yaml", "fig_curves.png",
         "val_best/confusion_matrix_normalized.png", "val_best/BoxPR_curve.png"]
# Dòng giữ lại theo ô notebook (nhận ô qua một đoạn mã nguồn); bỏ thanh tiến độ và bảng pandas in lặp
KEEP = {
    "EXPECTED.items()": ("train:", "val  :", "test :"),
    "model.train(": ("Ultralytics ", "Transferred", "optimizer: AdamW", "optimizer: SGD", "Resuming training", "[",
                     "epochs completed"),
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
    ap.add_argument("--nb", required=True, nargs="+")
    args = ap.parse_args()
    src, dst = Path("runs") / args.run, Path("reports/training") / args.run
    dst.mkdir(parents=True, exist_ok=True)
    for f in FILES:
        shutil.copy(src / f, dst / Path(f).name)

    # bỏ dòng lặp (dòng phiên bản in lại khi đánh giá best.pt, kiểm tra dữ liệu ở mỗi phiên)
    lines = list(dict.fromkeys(l for nb in args.nb for l in notebook_lines(nb)))
    out, prev = [], 0
    for l in lines:
        m = re.match(rf"\[{re.escape(args.run)}\] epoch (\d+)/", l)
        if m:
            e = int(m.group(1))
            assert e > prev, f"dòng epoch {e} trùng hoặc sai thứ tự phiên"
            if e > prev + 1:  # VS Code mất kết nối nên không nhận được log, Colab vẫn huấn luyện và ghi CSV
                out.append(f"… (không có log in ra cho epoch {prev + 1}–{e - 1}; số liệu đủ trong results.csv, epoch_log.csv)")
            prev = e
        out.append(l)
    assert prev == len(open(src / "epoch_log.csv").readlines()) - 1, "log không kết thúc ở epoch cuối"
    lines = out
    (dst / "run_output.txt").write_text("\n".join(lines) + "\n")
    print(f"Đã ghi {dst}: {len(FILES)} tệp + run_output.txt ({len(lines)} dòng)")


if __name__ == "__main__":
    main()
