"""Tuần 10 (thử app trên iPhone): khi cầm ngang mà giao diện khóa dọc, khung camera vẫn dọc nhưng cảnh nằm ngang, và app báo cả cụm
người là "không đội mũ". Đo mô hình trên ảnh xoay: mọi ảnh OOD-4 ở 3 hướng (gốc, xoay 90°, xoay 270°), đếm dự đoán người có mũ / không
mũ ở ngưỡng của app (vi phạm theo part_rule.json, có mũ 0,399; chưa áp các quy tắc khác) và khung người phủ quá 30% ảnh, so với số
người trong nhãn. Lý do: mô hình chỉ học ảnh người đứng; app bù bằng cách xoay khung theo cảm biến hướng (demo/src/lib/orientation.js).

    .venv/bin/python scripts/eval_rotation.py --out reports/deployment/M3b_yolo26n_bg/rotation
"""
import argparse, json
from pathlib import Path

from PIL import Image, ImageOps
from ultralytics import YOLO

PWH, PNH, OTHER_CONF, BIG = "person_with_helmet", "person_no_helmet", 0.399, 0.3
ROTATIONS = {"ảnh gốc": None, "xoay 90°": Image.ROTATE_90, "xoay 270°": Image.ROTATE_270}

ap = argparse.ArgumentParser()
ap.add_argument("--weights", default="runs/M3b_yolo26n_bg/weights/best.pt")
ap.add_argument("--part-rule", default="reports/deployment/M3b_yolo26n_bg/part_rule/part_rule.json")
ap.add_argument("--images", default="data/ood4/images")
ap.add_argument("--out", required=True)
args = ap.parse_args()
model = YOLO(args.weights)
names = model.names
thr = {PWH: OTHER_CONF, PNH: json.loads(Path(args.part_rule).read_text())["conf"]}
imgs = sorted(Path(args.images).glob("*.jpg"))
gt = {PWH: 0, PNH: 0}
for p in imgs:
    for line in Path(str(p).replace("/images/", "/labels/")).with_suffix(".txt").read_text().splitlines():
        if line.strip() and names[int(line.split()[0])] in gt:
            gt[names[int(line.split()[0])]] += 1

lines = [f"{args.weights}, {len(imgs)} ảnh {args.images}, imgsz 800, ngưỡng có mũ {thr[PWH]:.3f}, không mũ {thr[PNH]:.3f} (chưa áp quy tắc của app)",
         f"  nhãn: có mũ {gt[PWH]}, không mũ {gt[PNH]}"]
result = {"gt": gt}
for name, rot in ROTATIONS.items():
    count, big = {PWH: 0, PNH: 0}, 0
    for p in imgs:
        im = ImageOps.exif_transpose(Image.open(p)).convert("RGB")
        im = im.transpose(rot) if rot is not None else im
        b = model.predict(im, imgsz=800, conf=min(thr.values()), device="mps", verbose=False)[0].boxes
        for xy, c, s in zip(b.xyxy.cpu().numpy(), b.cls.cpu().numpy(), b.conf.cpu().numpy()):
            if names[int(c)] in thr and s >= thr[names[int(c)]]:
                count[names[int(c)]] += 1
                big += (xy[2] - xy[0]) * (xy[3] - xy[1]) > BIG * im.width * im.height
    result[name] = {"pwh": count[PWH], "pnh": count[PNH], "big": int(big)}
    lines.append(f"  {name:<10} dự đoán có mũ {count[PWH]:>3}, không mũ {count[PNH]:>3}; khung người phủ > {BIG:.0%} ảnh: {big}")
assert result["ảnh gốc"]["pwh"] > 0, "ảnh gốc không có dự đoán có mũ: sai mô hình hoặc sai tập"
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
print("\n".join(lines))
(out / "rotation_output.txt").write_text("\n".join(lines) + "\n")
(out / "rotation.json").write_text(json.dumps(result, ensure_ascii=False, indent=1))
