"""Tuần 9 (M3): nén dữ liệu huấn luyện thêm (Open Images, SH17 đã chuyển 6 lớp) thành data/M3_extra.zip để đưa lên Google
Drive cho notebooks/09_train_m3.ipynb; in MD5 và số ảnh, số hộp từng tập (notebook kiểm tra lại sau khi giải nén).
Tuần 10 (M3b): dùng lại cho ảnh nền (nhãn rỗng, scripts/prepare_negatives.py) → data/M3b_bg.zip cho notebooks/10_train_m3b.ipynb.

    .venv/bin/python scripts/pack_m3_extra.py
    .venv/bin/python scripts/pack_m3_extra.py --sources backgrounds=data/backgrounds/yolo --out data/M3b_bg.zip --top M3b_bg \\
        --report reports/backgrounds/pack_output.txt
"""
import argparse, hashlib, zipfile
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--sources", nargs="+", default=["openimages=data/external/openimages/yolo", "sh17=data/external/sh17/yolo"],
                help="tên=thư mục có images/{train,val}, labels/{train,val}")
ap.add_argument("--out", default="data/M3_extra.zip")
ap.add_argument("--top", default="M3_extra", help="thư mục gốc trong zip")
ap.add_argument("--report", default="reports/extra/pack_output.txt")
args = ap.parse_args()
SOURCES = {k: Path(v) for k, v in (s.split("=", 1) for s in args.sources)}
OUT, REPORT = Path(args.out), Path(args.report)

expected, n_files = {}, 0
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_STORED) as z:  # ảnh JPEG đã nén sẵn
    for name, base in SOURCES.items():
        expected[name] = {}
        for split in ("train", "val"):
            imgs = sorted((base / "images" / split).glob("*.jpg"))
            labels = [base / "labels" / split / f"{p.stem}.txt" for p in imgs]
            assert all(l.exists() for l in labels), f"{name} {split}: thiếu file nhãn"
            assert len(list((base / "labels" / split).glob("*.txt"))) == len(imgs), f"{name} {split}: thừa file nhãn"
            for p in imgs + labels:
                z.write(p, Path(args.top, name, p.relative_to(base)))
            expected[name][split] = (len(imgs), sum(len(l.read_text().splitlines()) for l in labels))
            n_files += 2 * len(imgs)
md5 = hashlib.md5(OUT.read_bytes()).hexdigest()
text = f"{OUT}: {OUT.stat().st_size / 1e6:.0f} MB, {n_files} file, MD5 {md5}\nEXTRA_EXPECTED = {expected}"
print(text)
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(text + "\n")
