"""Tuần 10: ảnh KHÔNG có người từ Open Images V7. Hai mục đích, cùng một tiêu chí:
  1. tập đánh giá (mặc định, 200 ảnh tập validation → data/negatives): đo báo nhầm "người" khi camera chĩa vào cảnh vắng người
     (khi thử trên iPhone, M3 báo bàn phím MacBook là một người không đội mũ; SHEL5K và 3 tập ngoài miền ảnh nào cũng có người
     nên không đo được lỗi này);
  2. ảnh nền để huấn luyện M3b (--root data/backgrounds --empty-labels): ~10% số ảnh train / val của M3, như Ultralytics khuyên
     (0–10% ảnh nền để giảm báo nhầm); train lấy từ tập train của Open Images, val từ tập validation nhưng loại các ảnh của tập
     đánh giá (--exclude) → tập đánh giá không bao giờ được dùng khi huấn luyện hay chọn mô hình.

Tiêu chí (chốt trước khi xem ảnh): nhãn mức ảnh Person đã được người xác minh là KHÔNG có (Confidence 0 — nhãn chỉ được đưa đi
xác minh khi bộ phân loại của Open Images nghi ảnh có người, nên đây là ảnh dễ nhầm); bỏ ảnh có nhãn mức ảnh dương tính hoặc hộp
của bất kỳ lớp người, bộ phận người hay hình người (FIGURES, HUMAN_PARTS); bỏ ảnh xoay (cột Rotation, EXIF); chỉ lấy ảnh có
trong danh sách ảnh có hộp (boxable) của Open Images. Nhãn "không có Person" của Open Images không đủ tin cậy (xem tay 48 ảnh
nền: ~8 ảnh có người thật — tay, chân, người ở xa, ảnh phản chiếu) nên mỗi ảnh tải về còn được YOLO26l COCO (PERSON_CHECK) dò
người: thấy người ở độ tin cậy ≥ PERSON_CONF thì bỏ (YOLO26l bắt cả 8/8 ảnh đó, conf ≥ 0,62; ngưỡng thấp để chắc chắn, chấp nhận
bỏ cả tranh vẽ / linh vật). Duyệt theo thứ tự xáo trộn cố định (seed 42) của toàn bộ ảnh đạt tiêu chí, bỏ ảnh trong --exclude,
ảnh tải lỗi hay bị dò thấy người thì lấy ảnh kế tiếp, đến khi đủ N. Ảnh không commit; nguồn, tác giả, giấy phép từng ảnh ở
<report>/sources_<tập>.csv, ảnh bị bỏ vì có người ở <report>/dropped_<tập>.csv.

    .venv/bin/python scripts/prepare_negatives.py                     # tập đánh giá: 200 ảnh validation → data/negatives
    .venv/bin/python scripts/prepare_negatives.py --split train --n 880 --root data/backgrounds --empty-labels --report reports/backgrounds
    .venv/bin/python scripts/prepare_negatives.py --split validation --n 194 --root data/backgrounds --empty-labels \\
        --report reports/backgrounds --exclude data/negatives/yolo/images/val
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from ultralytics import YOLO

from prepare_openimages import OUR_SPLIT, ROOT as OI_ROOT, WORKERS, fetch_image

SEED = 42
PERSON_CHECK, PERSON_CONF = "weights/yolo26l.pt", 0.25  # YOLO26l COCO, lớp 0 = person
HUMAN_PARTS = ("arm", "body", "ear", "eye", "face", "foot", "hair", "hand", "head", "leg", "mouth", "nose")
FIGURES = ("Person", "Man", "Woman", "Boy", "Girl", "Baby", "Child", "Toddler", "Mannequin", "Doll", "Statue", "Sculpture",
           "Painting", "Poster", "Beard")
RAW = OI_ROOT / "raw"
FILES = {"validation": ("oidv7-val-annotations-human-imagelabels.csv", "validation-annotations-bbox.csv",
                        "validation-images-with-rotation.csv"),
         "train": ("oidv7-train-annotations-human-imagelabels.csv", "oidv6-train-annotations-bbox.csv",
                   "train-images-boxable-with-rotation.csv")}
CLASS_CSV = "https://storage.googleapis.com/openimages/v7/oidv7-class-descriptions.csv"

ap = argparse.ArgumentParser()
ap.add_argument("--split", choices=list(FILES), default="validation")
ap.add_argument("--n", type=int, default=200)
ap.add_argument("--root", default="data/negatives")
ap.add_argument("--report", default="reports/negatives")
ap.add_argument("--exclude", nargs="*", default=[], help="thư mục ảnh không được lấy lại")
ap.add_argument("--empty-labels", action="store_true", help="ghi file nhãn rỗng cạnh ảnh (ảnh nền cho huấn luyện)")
args = ap.parse_args()
root, report = Path(args.root), Path(args.report)


def read(path, cols, keep):
    """Đọc từng khúc (file nhãn tập train 2–3 GB, máy 8 GB RAM), chỉ giữ các dòng cần."""
    return pd.concat(c[keep(c)] for c in pd.read_csv(RAW / path, usecols=cols, chunksize=2_000_000))


classes = pd.read_csv(CLASS_CSV)
exclude = set(classes.loc[classes.DisplayName.isin(FIGURES + tuple(f"Human {p}" for p in HUMAN_PARTS)), "LabelName"])
assert len(exclude) == len(FIGURES) + len(HUMAN_PARTS), "thiếu mã lớp trong oidv7-class-descriptions.csv"
person = classes.loc[classes.DisplayName == "Person", "LabelName"].item()

f_labels, f_boxes, f_meta = FILES[args.split]
labels = read(f_labels, ["ImageID", "LabelName", "Confidence"],
              lambda c: ((c.LabelName == person) & (c.Confidence == 0)) | (c.LabelName.isin(exclude) & (c.Confidence == 1)))
boxes = read(f_boxes, ["ImageID", "LabelName"], lambda c: c.LabelName.isin(exclude))
meta = read(f_meta, ["ImageID", "OriginalLandingURL", "License", "Author", "Rotation"], lambda c: c.ImageID.notna())
verified_none = set(labels.loc[(labels.LabelName == person) & (labels.Confidence == 0), "ImageID"])
human = set(labels.loc[labels.LabelName.isin(exclude) & (labels.Confidence == 1), "ImageID"]) | set(boxes.ImageID)
rotated = set(meta.loc[meta.Rotation.fillna(0) != 0, "ImageID"])
used = {p.stem for d in args.exclude for p in Path(d).glob("*.jpg")}
pool = sorted(verified_none & set(meta.ImageID) - human - rotated)
# xáo trộn cả tập rồi mới bỏ ảnh đã dùng: thứ tự của các ảnh còn lại không đổi khi --exclude đổi
order = [pool[i] for i in np.random.default_rng(SEED).permutation(len(pool)) if pool[i] not in used]

(root / "tmp").mkdir(parents=True, exist_ok=True)  # fetch_image tải tạm vào <root>/tmp
detector = YOLO(PERSON_CHECK)
kept, dropped, skipped, pos = [], [], [], 0
with ThreadPoolExecutor(WORKERS) as ex:
    while len(kept) < args.n:
        batch = order[pos:pos + (args.n - len(kept)) * 3 // 2 + 8]  # dư ra vì ~1/3 ảnh bị dò thấy người
        assert batch, f"hết ảnh ứng viên, mới có {len(kept)} ảnh"
        pos += len(batch)
        for i, path, why in ex.map(lambda i: (i, *fetch_image(args.split, i, root=root)), batch):
            if not path:
                skipped.append((i, why))
                continue
            conf = detector.predict(path, conf=PERSON_CONF, classes=[0], verbose=False)[0].boxes.conf.tolist()
            if conf:
                dropped.append((i, round(max(conf), 3)))
                path.unlink()
            elif len(kept) < args.n:
                kept.append(i)
split = OUR_SPLIT[args.split]
img_dir, lbl_dir = root / "yolo" / "images" / split, root / "yolo" / "labels" / split
for f in [*img_dir.glob("*.jpg"), *lbl_dir.glob("*.txt")]:  # ảnh dư của lô cuối, ảnh / nhãn của lần chạy trước không còn thuộc mẫu
    if f.stem not in kept:
        f.unlink()
if args.empty_labels:
    lbl_dir.mkdir(parents=True, exist_ok=True)
    for i in kept:
        (lbl_dir / f"{i}.txt").write_text("")
assert sorted(p.stem for p in img_dir.glob("*.jpg")) == sorted(kept)

report.mkdir(parents=True, exist_ok=True)
meta.set_index("ImageID").loc[kept, ["OriginalLandingURL", "License", "Author"]].to_csv(report / f"sources_{split}.csv")
pd.DataFrame(dropped, columns=["ImageID", "person_conf"]).to_csv(report / f"dropped_{split}.csv", index=False)
lines = [f"Open Images V7 {args.split}: {len(verified_none)} ảnh có nhãn Person xác minh là không có; còn {len(pool)} ảnh sau khi bỏ ảnh có "
         f"nhãn/hộp người, bộ phận người hay hình người, ảnh xoay, ảnh ngoài danh sách có hộp"
         + (f", {len(used)} ảnh đã dùng ({', '.join(args.exclude)})" if used else ""),
         f"Duyệt {pos} ảnh theo thứ tự xáo trộn (seed {SEED}): bỏ {len(dropped)} ảnh {PERSON_CHECK} thấy người (conf ≥ {PERSON_CONF}), "
         f"{len(skipped)} ảnh tải lỗi / EXIF xoay → {len(kept)} ảnh ở {img_dir}{' + nhãn rỗng' if args.empty_labels else ''}"]
print("\n".join(lines))
(report / f"negatives_output_{split}.txt").write_text("\n".join(lines) + "\n")
