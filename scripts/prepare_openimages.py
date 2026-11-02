"""Tuần 9 (M3): lấy ảnh Open Images V7 có người đội mũ thường (không phải mũ bảo hộ) làm dữ liệu huấn luyện thêm, chuyển
sang 6 lớp của SHEL5K. Lý do: trên tập ngoài miền, M2 coi mũ thường (nón lá, mũ vải, mũ lưỡi trai…) là mũ bảo hộ.

Tiêu chí chọn ảnh (chốt trước khi xem ảnh):
  1. có ≥ 1 hộp mũ thường (Hat, Sun hat, Fedora, Cowboy hat, Sombrero) chồng lên một hộp đầu (giao ≥ HAT_ON_HEAD diện tích mũ),
     không có hộp mũ bảo hộ nào (Helmet, Bicycle helmet, Football helmet);
  2. nhãn mức ảnh Human head và Human face đã được người xác minh (có hoặc không) → hộp đầu, mặt được vẽ đủ; không có hộp nhóm
     (IsGroupOf) hay hình vẽ/tượng (IsDepiction) ở các lớp người, đầu, mặt, mũ; ảnh không bị xoay (cột Rotation);
  3. mỗi đầu nằm trong đúng một người (phần đầu nằm trong hộp người ≥ HEAD_IN_PERSON, chọn hộp người nhỏ nhất nếu nhiều) và mỗi
     người có đúng một đầu — nếu không thì bỏ cả ảnh (không biết người đó đội gì, hoặc có người chưa được vẽ hộp).
Nhãn: người → person_no_helmet, đầu → head (đầu không đội mũ bảo hộ, kể cả đội mũ thường), mặt → face. Tập train của Open
Images → train, validation → val (test cũng vào train vì tập train của Open Images ít ảnh đạt tiêu chí 2). Ảnh tải từ bản sao CVDF (song song), thu cạnh dài về ≤ MAX_SIDE (= imgsz huấn luyện,
lớn hơn cũng bị thu nhỏ khi huấn luyện); bỏ ảnh có EXIF xoay hoặc tải lỗi.
Nguồn, tác giả, giấy phép từng ảnh ghi vào reports/extra/openimages/sources.csv.

    .venv/bin/python scripts/prepare_openimages.py      # tải nhãn (~3 GB, chỉ giữ phần đã lọc), chọn ảnh, tải ảnh, phiếu kiểm tra
"""
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from PIL import Image, ImageDraw

URL, IMG_URL = "https://storage.googleapis.com/openimages/", "https://open-images-dataset.s3.amazonaws.com/{}/{}.jpg"
FILES = {"validation": ("v5/validation-annotations-bbox.csv", "v5/validation-annotations-human-imagelabels-boxable.csv",
                        "2018_04/validation/validation-images-with-rotation.csv"),
         "test": ("v5/test-annotations-bbox.csv", "v5/test-annotations-human-imagelabels-boxable.csv",
                  "2018_04/test/test-images-with-rotation.csv"),
         "train": ("v6/oidv6-train-annotations-bbox.csv", "v5/train-annotations-human-imagelabels-boxable.csv",
                   "2018_04/train/train-images-boxable-with-rotation.csv")}
OUR_SPLIT = {"train": "train", "validation": "val", "test": "train"}  # train chỉ chọn được 561 ảnh → thêm test vào train
HAT = {"/m/02dl1y": "Hat", "/m/02wbtzl": "Sun hat", "/m/02fq_6": "Fedora", "/m/025rp__": "Cowboy hat", "/m/02jfl0": "Sombrero"}
HELMET = {"/m/0zvk5", "/m/03p3bw", "/m/07qxg_"}  # Helmet, Bicycle helmet, Football helmet
PERSON = {"/m/01g317", "/m/04yx4", "/m/03bt1vf", "/m/01bl7v", "/m/05r655"}  # Person, Man, Woman, Boy, Girl
HEAD, FACE = "/m/04hgtk", "/m/0dzct"
KEEP = set(HAT) | HELMET | PERSON | {HEAD, FACE}
CLS = {"head": 1, "pnh": 4, "face": 5}  # thứ tự lớp SHEL5K
HEAD_IN_PERSON, HAT_ON_HEAD, MAX_SIDE, WORKERS = 0.8, 0.1, 800, 8
ROOT, REPORT = Path("data/external/openimages"), Path("reports/extra/openimages")


def download(url, dst):
    """Tải có tiếp tục khi đứt mạng (Range); trả về đường dẫn file."""
    if dst.exists():
        return dst
    part = dst.with_name(dst.name + ".part")
    for attempt in range(10):
        try:
            pos = part.stat().st_size if part.exists() else 0
            with requests.get(url, headers={"Range": f"bytes={pos}-"}, stream=True, timeout=120) as r:
                if r.status_code != 416:  # 416: đã tải đủ
                    r.raise_for_status()
                    with open(part, "ab" if r.status_code == 206 else "wb") as f:
                        for chunk in r.iter_content(1 << 20):
                            f.write(chunk)
            part.rename(dst)
            return dst
        except requests.RequestException:
            time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"không tải được {url}")


def filtered(split):
    """Hộp, nhãn mức ảnh đã xác minh và thông tin ảnh của các lớp cần dùng; file gốc lớn bị xóa sau khi lọc."""
    out = [ROOT / "ann" / f"{split}-{k}.csv" for k in ("bbox", "labels", "meta")]
    if all(p.exists() for p in out):
        return [pd.read_csv(p) for p in out]
    (ROOT / "ann").mkdir(parents=True, exist_ok=True)
    raw = [download(URL + f, ROOT / "raw" / Path(f).name) for f in FILES[split]]
    bbox = pd.concat(c[c.LabelName.isin(KEEP)] for c in pd.read_csv(raw[0], chunksize=2_000_000))
    imgs = set(bbox.loc[bbox.LabelName.isin(HAT), "ImageID"])
    bbox = bbox[bbox.ImageID.isin(imgs)]
    labels = pd.concat(c[c.ImageID.isin(imgs) & c.LabelName.isin(KEEP)] for c in pd.read_csv(raw[1], chunksize=2_000_000))
    meta = pd.concat(c[c.ImageID.isin(imgs)] for c in pd.read_csv(raw[2], chunksize=1_000_000))
    meta = meta[["ImageID", "OriginalLandingURL", "License", "Author", "Rotation"]]
    for df, p in zip((bbox, labels, meta), out):
        df.to_csv(p, index=False)
    for p in raw:
        p.unlink()
    return bbox, labels, meta


def ioa(a, b):
    """Tỉ lệ diện tích của từng hộp a nằm trong từng hộp b (xyxy) → ma trận len(a) × len(b)."""
    lt, rb = np.maximum(a[:, None, :2], b[None, :, :2]), np.minimum(a[:, None, 2:], b[None, :, 2:])
    inter = np.clip(rb - lt, 0, None).prod(2)
    return inter / ((a[:, 2:] - a[:, :2]).prod(1)[:, None] + 1e-12)


def select(split, bbox, labels, meta):
    """Áp tiêu chí 1–3 → {ImageID: [(lớp, x1, y1, x2, y2) chuẩn hóa 0–1]} và số ảnh bị loại theo lý do."""
    verified = labels.groupby("ImageID").LabelName.apply(set)
    rotated = set(meta.loc[meta.Rotation.fillna(0) != 0, "ImageID"])
    reasons, out = {}, {}
    bad_flag = bbox.LabelName.isin(PERSON | {HEAD, FACE} | set(HAT)) & ((bbox.IsGroupOf == 1) | (bbox.IsDepiction == 1))
    flagged = set(bbox.loc[bad_flag, "ImageID"])
    for img, g in bbox.groupby("ImageID"):
        xy = lambda m: g.loc[m, ["XMin", "YMin", "XMax", "YMax"]].to_numpy(float)
        heads, persons, hats = xy(g.LabelName == HEAD), xy(g.LabelName.isin(PERSON)), xy(g.LabelName.isin(HAT))
        if g.LabelName.isin(HELMET).any():
            why = "có mũ bảo hộ"
        elif not {HEAD, FACE} <= verified.get(img, set()):
            why = "đầu/mặt chưa xác minh"
        elif img in flagged or img in rotated:
            why = "hộp nhóm, hình vẽ hoặc ảnh xoay"
        elif not len(heads) or not len(persons) or not (ioa(hats, heads) >= HAT_ON_HEAD).any():
            why = "không có mũ trên đầu người"
        else:
            m = ioa(heads, persons)
            area = (persons[:, 2:] - persons[:, :2]).prod(1)
            owner = np.where(m >= HEAD_IN_PERSON, area[None, :], np.inf).argmin(1)
            ok_head = (m >= HEAD_IN_PERSON).any(1)
            why = "" if ok_head.all() and sorted(owner) == list(range(len(persons))) else "đầu/người không ghép một-một"
        if why:
            reasons[why] = reasons.get(why, 0) + 1
            continue
        faces = xy(g.LabelName == FACE)
        out[img] = ([("pnh", *b) for b in persons] + [("head", *b) for b in heads] + [("face", *b) for b in faces])
    return out, reasons


def fetch_image(split, img, root=ROOT):
    """Tải, bỏ ảnh có EXIF xoay, thu nhỏ → (đường dẫn ảnh đã lưu hoặc None, lý do bỏ)."""
    dst = root / "yolo" / "images" / OUR_SPLIT[split] / f"{img}.jpg"
    if dst.exists():
        return dst, ""
    try:
        raw = download(IMG_URL.format(split, img), root / "tmp" / f"{img}.jpg")
    except RuntimeError:
        return None, "tải lỗi"
    im = Image.open(raw)
    if im.getexif().get(274, 1) != 1:  # Open Images không nói rõ hộp ứng với ảnh trước hay sau khi xoay theo EXIF → bỏ
        raw.unlink()
        return None, "EXIF xoay"
    im = im.convert("RGB")
    im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, quality=90)
    raw.unlink()
    return dst, ""


def main():
    REPORT.mkdir(parents=True, exist_ok=True)
    (ROOT / "tmp").mkdir(parents=True, exist_ok=True)
    lines, sources = [], []
    for split in FILES:
        bbox, labels, meta = filtered(split)
        chosen, reasons = select(split, bbox, labels, meta)
        n_hat = bbox.loc[bbox.LabelName.isin(HAT), "ImageID"].nunique()
        kept, n_box, dropped = 0, {k: 0 for k in CLS}, {}
        with ThreadPoolExecutor(WORKERS) as pool:  # mỗi luồng tải ~165 KB/s từ S3
            fetched = list(pool.map(lambda i: fetch_image(split, i), chosen))
        for (img, boxes), (path, why) in zip(chosen.items(), fetched):
            if path is None:
                dropped[why] = dropped.get(why, 0) + 1
                continue
            lbl = path.parent.parent.parent / "labels" / OUR_SPLIT[split] / f"{img}.txt"
            lbl.parent.mkdir(parents=True, exist_ok=True)
            rows = []
            for c, x1, y1, x2, y2 in boxes:
                assert 0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1, f"hộp lỗi ở {img}"
                rows.append(f"{CLS[c]} {(x1 + x2) / 2:.6f} {(y1 + y2) / 2:.6f} {x2 - x1:.6f} {y2 - y1:.6f}")
                n_box[c] += 1
            lbl.write_text("\n".join(rows) + "\n")
            kept += 1
            sources.append({"image": f"{img}.jpg", "split": OUR_SPLIT[split], "oi_split": split,
                            **meta[meta.ImageID == img].iloc[0][["OriginalLandingURL", "License", "Author"]].to_dict()})
        lines.append(f"{split}: {n_hat} ảnh có mũ thường → chọn {len(chosen)}, bỏ {dropped} → {kept} ảnh ({OUR_SPLIT[split]}); "
                     f"hộp: " + ", ".join(f"{k} {v}" for k, v in n_box.items()) + "; loại: " +
                     ", ".join(f"{k} {v}" for k, v in sorted(reasons.items(), key=lambda kv: -kv[1])))
        print(lines[-1], flush=True)
    pd.DataFrame(sources).to_csv(REPORT / "sources.csv", index=False)
    (REPORT / "prepare_output.txt").write_text("\n".join(lines) + "\n")

    # phiếu kiểm tra: 24 ảnh ngẫu nhiên (seed 42) có vẽ nhãn, để ở data/ (ảnh có giấy phép riêng, không commit)
    colors = {1: "#2f7ed8", 4: "#eb6834", 5: "#6250d6"}
    pick = pd.Series(sorted((ROOT / "yolo" / "images").glob("*/*.jpg"))).sample(24, random_state=42)
    sheet = Image.new("RGB", (6 * 330, 4 * 330), "white")
    for k, p in enumerate(pick):
        im = Image.open(p).convert("RGB")
        d = ImageDraw.Draw(im)
        for l in (p.parent.parent.parent / "labels" / p.parent.name / f"{p.stem}.txt").read_text().split("\n"):
            if l:
                c, cx, cy, w, h = map(float, l.split())
                d.rectangle([(cx - w / 2) * im.width, (cy - h / 2) * im.height, (cx + w / 2) * im.width, (cy + h / 2) * im.height],
                            outline=colors[int(c)], width=max(2, im.width // 250))
        im.thumbnail((320, 320))
        sheet.paste(im, ((k % 6) * 330 + 5, (k // 6) * 330 + 5))
    sheet.save(ROOT / "check_sheet.jpg", quality=90)


if __name__ == "__main__":
    main()
