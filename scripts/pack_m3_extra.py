"""Tuần 9 (M3): nén dữ liệu huấn luyện thêm (Open Images, SH17 đã chuyển 6 lớp) thành data/M3_extra.zip để đưa lên Google
Drive cho notebooks/09_train_m3.ipynb; in MD5 và số ảnh, số hộp từng tập (notebook kiểm tra lại sau khi giải nén).

    .venv/bin/python scripts/pack_m3_extra.py
"""
import hashlib, zipfile
from pathlib import Path

SOURCES = {"openimages": Path("data/external/openimages/yolo"), "sh17": Path("data/external/sh17/yolo")}
OUT, REPORT = Path("data/M3_extra.zip"), Path("reports/extra/pack_output.txt")

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
                z.write(p, Path("M3_extra", name, p.relative_to(base)))
            expected[name][split] = (len(imgs), sum(len(l.read_text().splitlines()) for l in labels))
            n_files += 2 * len(imgs)
md5 = hashlib.md5(OUT.read_bytes()).hexdigest()
text = f"{OUT}: {OUT.stat().st_size / 1e6:.0f} MB, {n_files} file, MD5 {md5}\nEXTRA_EXPECTED = {expected}"
print(text)
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(text + "\n")
