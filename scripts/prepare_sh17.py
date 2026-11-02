"""Tuần 9 (M3): lấy ảnh SH17 (8.099 ảnh Pexels công nhân sản xuất, nhãn Person/Head/Face/Helmet, CC BY-NC-SA 4.0) làm dữ liệu
huấn luyện thêm, chuyển sang 6 lớp của SHEL5K. Lý do: trên tập ngoài miền, M2 nhận nhầm người đầu trần chụp gần, cỡ lớn là
có đội mũ bảo hộ; SH17 có nhiều người cỡ lớn, phần lớn không đội mũ bảo hộ (đội mũ thường được gán vào lớp Head).

Không tải gói 14 GB trên Kaggle: chỉ đọc phần mục lục của file zip và các nhóm file nhãn (nằm liền nhau trong zip) bằng yêu cầu
HTTP Range; ảnh tải từ Pexels (giấy phép Pexels) ở cỡ thu nhỏ, cạnh dài MAX_SIDE, rồi kiểm tra tỉ lệ khung ảnh khớp kích thước
gốc ghi trong meta-data (lệch > ASPECT_TOL thì bỏ, phòng ảnh bị xoay khác lúc gán nhãn).

Tiêu chí chọn ảnh (chốt trước khi xem ảnh, giống prepare_openimages.py): có người; mỗi đầu nằm trong đúng một người (phần đầu
nằm trong hộp người ≥ HEAD_IN_PERSON, chọn hộp người nhỏ nhất) và mỗi người có đúng một đầu; mọi mũ bảo hộ nằm trên một đầu
(phần mũ nằm trong hộp đầu ≥ HELMET_ON_HEAD). Nhãn: helmet → helmet; đầu có mũ bảo hộ → head_with_helmet (hộp bao cả đầu và
mũ, như SHEL5K), đầu không có → head; người có đầu đội mũ bảo hộ → person_with_helmet, còn lại → person_no_helmet; face → face.
Tập train/val theo train_files.txt / val_files.txt của SH17.

    .venv/bin/python scripts/prepare_sh17.py
"""
import json, os, zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from PIL import Image, ImageDraw

from prepare_openimages import download, ioa

KAGGLE = "https://www.kaggle.com/api/v1/datasets/download/mugheesahmad/sh17-dataset-for-ppe-detection"
SH17 = {"person": 0, "face": 3, "helmet": 10, "head": 12}  # mã lớp trong nhãn YOLO của SH17 (sh17.yaml)
CLS = {"helmet": 0, "head": 1, "hwh": 2, "pwh": 3, "pnh": 4, "face": 5}  # thứ tự lớp SHEL5K
HEAD_IN_PERSON, HELMET_ON_HEAD, MAX_SIDE, ASPECT_TOL, WORKERS = 0.8, 0.3, 800, 0.01, 8
ROOT, REPORT = Path("data/external/sh17"), Path("reports/extra/sh17")


def fetch_annotations():
    """Đọc nhãn YOLO, meta-data (URL Pexels, kích thước gốc) và danh sách train/val trong zip Kaggle bằng HTTP Range."""
    if (ROOT / "ann" / "val_files.txt").exists():
        return
    (ROOT / "ann").mkdir(parents=True, exist_ok=True)
    signed = requests.get(KAGGLE, allow_redirects=False, timeout=60).headers["location"]
    size = int(requests.get(signed, headers={"Range": "bytes=0-0"}, timeout=60).headers["Content-Range"].split("/")[1])
    sparse = ROOT / "ann" / "sparse.zip"  # file thưa: chỉ có các đoạn đã tải, phần còn lại là 0

    def fetch(a, b, f):
        r = requests.get(signed, headers={"Range": f"bytes={a}-{b - 1}"}, timeout=300)
        assert r.status_code == 206 and len(r.content) == b - a, f"tải thiếu đoạn {a}-{b}"
        f.seek(a)
        f.write(r.content)

    with open(sparse, "wb") as f:
        f.truncate(size)
        fetch(size - 8_000_000, size, f)  # mục lục zip nằm ở cuối file
    infos = zipfile.ZipFile(sparse).infolist()
    nxt = dict(zip([i.filename for i in sorted(infos, key=lambda i: i.header_offset)],
                   [i.header_offset for i in sorted(infos, key=lambda i: i.header_offset)][1:] + [size]))
    groups = [[i for i in infos if i.filename.startswith(g)] for g in ("labels/", "meta-data/")]
    groups.append([i for i in infos if "/" not in i.filename])  # train_files.txt, val_files.txt
    with open(sparse, "r+b") as f:
        for g in groups:
            a, b = min(i.header_offset for i in g), max(nxt[i.filename] for i in g)
            assert b - a < 50e6, "nhóm file nằm rải rác trong zip"
            fetch(a, b, f)
    z = zipfile.ZipFile(sparse)
    for i in sum(groups, []):
        dst = ROOT / "ann" / i.filename
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(z.read(i))  # zipfile tự kiểm tra CRC
    sparse.unlink()


def xyxy(rows, c):
    return np.array([[cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2] for k, cx, cy, w, h in rows if k == c]).reshape(-1, 4)


def convert(name):
    """Áp tiêu chí lên nhãn SH17 của một ảnh → (danh sách (lớp, x1, y1, x2, y2), lý do loại)."""
    rows = [tuple(map(float, l.split())) for l in (ROOT / "ann" / "labels" / f"{name}.txt").read_text().splitlines() if l]
    return to_classes(*(xyxy(rows, SH17[k]) for k in ("person", "head", "helmet", "face")))


def to_classes(persons, heads, helmets, faces):
    """Hộp người, đầu, mũ bảo hộ, mặt (xyxy 0–1) → 6 lớp SHEL5K theo tiêu chí ở đầu file; dùng chung với Open Images."""
    if not len(persons) or not len(heads):
        return None, "không có người hoặc đầu"
    m = ioa(heads, persons)
    area = (persons[:, 2:] - persons[:, :2]).prod(1)
    owner = np.where(m >= HEAD_IN_PERSON, area[None, :], np.inf).argmin(1)
    if not (m >= HEAD_IN_PERSON).any(1).all() or sorted(owner) != list(range(len(persons))):
        return None, "đầu/người không ghép một-một"
    on = ioa(helmets, heads) >= HELMET_ON_HEAD if len(helmets) else np.zeros((0, len(heads)), bool)
    if not on.any(1).all():
        return None, "mũ bảo hộ không nằm trên đầu"
    out = [("helmet", *b) for b in helmets] + [("face", *b) for b in faces]
    for i, hd in enumerate(heads):
        worn = helmets[on[:, i]]
        box = np.concatenate([hd[None], worn]) if len(worn) else hd[None]
        out.append(("hwh" if len(worn) else "head", *box[:, :2].min(0), *box[:, 2:].max(0)))
        out.append(("pwh" if len(worn) else "pnh", *persons[owner[i]]))
    return [(c, *np.clip(b, 0, 1)) for c, *b in out], ""


def fetch_image(name, split):
    """Ảnh Pexels thu nhỏ; bỏ nếu tỉ lệ khung khác kích thước gốc → (đường dẫn hoặc None, lý do)."""
    dst = ROOT / "yolo" / "images" / split / f"{name}.jpg"
    if dst.exists():
        return dst, ""
    meta = json.loads((ROOT / "ann" / "meta-data" / f"{name}.json").read_text())
    side = "w" if meta["width"] >= meta["height"] else "h"
    try:
        raw = download(f"{meta['src']['original']}?auto=compress&cs=tinysrgb&{side}={MAX_SIDE}", ROOT / "tmp" / f"{name}.jpg")
    except RuntimeError:
        return None, "tải lỗi"
    im = Image.open(raw).convert("RGB")
    raw.unlink()
    if abs(im.width / im.height / (meta["width"] / meta["height"]) - 1) > ASPECT_TOL:
        return None, "tỉ lệ khung khác ảnh gốc"
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, quality=90)
    return dst, ""


def main():
    fetch_annotations()
    REPORT.mkdir(parents=True, exist_ok=True)
    (ROOT / "tmp").mkdir(parents=True, exist_ok=True)
    split_of = {Path(l.strip()).stem: s for s, f in (("train", "train_files.txt"), ("val", "val_files.txt"))
                for l in (ROOT / "ann" / f).read_text().splitlines() if l.strip()}
    names = sorted(p.stem for p in (ROOT / "ann" / "labels").glob("*.txt"))
    assert set(names) == set(split_of), "danh sách train/val không khớp nhãn"
    converted = {n: convert(n) for n in names}
    chosen = {n: boxes for n, (boxes, why) in converted.items() if boxes}
    reasons = pd.Series([why for boxes, why in converted.values() if not boxes]).value_counts().to_dict()
    with ThreadPoolExecutor(WORKERS) as pool:  # Pexels ~1–2 s mỗi ảnh
        fetched = list(pool.map(lambda n: fetch_image(n, split_of[n]), chosen))
    n_box, kept, sources = {(s, c): 0 for s in ("train", "val") for c in CLS}, {"train": 0, "val": 0}, []
    for (name, boxes), (path, why) in zip(chosen.items(), fetched):
        if path is None:
            reasons[why] = reasons.get(why, 0) + 1
            continue
        s = split_of[name]
        lbl = ROOT / "yolo" / "labels" / s / f"{name}.txt"
        lbl.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        for c, x1, y1, x2, y2 in boxes:
            assert 0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1, f"hộp lỗi ở {name}"
            rows.append(f"{CLS[c]} {(x1 + x2) / 2:.6f} {(y1 + y2) / 2:.6f} {x2 - x1:.6f} {y2 - y1:.6f}")
            n_box[s, c] += 1
        lbl.write_text("\n".join(rows) + "\n")
        kept[s] += 1
        meta = json.loads((ROOT / "ann" / "meta-data" / f"{name}.json").read_text())
        sources.append({"image": f"{name}.jpg", "split": s, "url": meta["url"], "photographer": meta["photographer"],
                        "license": "Pexels License; nhãn SH17 CC BY-NC-SA 4.0"})
    lines = [f"SH17: {len(names)} ảnh → chọn {len(chosen)} → giữ train {kept['train']}, val {kept['val']}; loại: {reasons}"]
    lines += [f"  {s}: " + ", ".join(f"{c} {n_box[s, c]}" for c in CLS) for s in ("train", "val")]
    print("\n".join(lines))
    pd.DataFrame(sources).to_csv(REPORT / "sources.csv", index=False)
    (REPORT / "prepare_output.txt").write_text("\n".join(lines) + "\n")

    # phiếu kiểm tra: 24 ảnh ngẫu nhiên (seed 42) có vẽ nhãn, để ở data/ (không commit)
    colors = {0: "#ffd400", 1: "#2f7ed8", 2: "#00b8d9", 3: "#1baf7a", 4: "#eb6834", 5: "#6250d6"}
    pick = pd.Series(sorted((ROOT / "yolo" / "images").glob("*/*.jpg"))).sample(24, random_state=42)
    sheet = Image.new("RGB", (6 * 330, 4 * 330), "white")
    for k, p in enumerate(pick):
        im = Image.open(p).convert("RGB")
        d = ImageDraw.Draw(im)
        for l in (ROOT / "yolo" / "labels" / p.parent.name / f"{p.stem}.txt").read_text().splitlines():
            c, cx, cy, w, h = map(float, l.split())
            d.rectangle([(cx - w / 2) * im.width, (cy - h / 2) * im.height, (cx + w / 2) * im.width, (cy + h / 2) * im.height],
                        outline=colors[int(c)], width=3)
        im.thumbnail((320, 320))
        sheet.paste(im, ((k % 6) * 330 + 5, (k // 6) * 330 + 5))
    sheet.save(ROOT / "check_sheet.jpg", quality=90)


if __name__ == "__main__":
    main()
