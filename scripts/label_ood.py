"""Tuần 9: gán nhãn tập ngoài miền (data/ood/images) cho 2 lớp person_with_helmet / person_no_helmet.

YOLO26l COCO (không phải M2, không biết gì về mũ) chỉ đề xuất khung người; người gán nhãn xem từng ảnh để bỏ khung sai, thêm
người bị sót, quyết định đội mũ bảo hộ hay không. Quy tắc (chốt trước khi xem ảnh): gán mọi người có vùng đầu nhìn thấy và đủ
lớn để phán đoán (đầu cao khoảng ≥ 12 px); mũ không phải mũ bảo hộ (mũ vải, mũ lưỡi trai, nón lá) = không đội; khung bao phần
thân nhìn thấy; người không thấy đầu hoặc quá nhỏ thì không gán (ghi lại trong cột note); ảnh không phải công trường hoặc
không còn người nào gán được thì bỏ.

    .venv/bin/python scripts/label_ood.py propose     # khung đề xuất + ảnh duyệt (lưới tọa độ) + ảnh cắt từng người
    .venv/bin/python scripts/label_ood.py sheets      # chỉ vẽ lại ảnh cắt từ proposals.json (không chạy lại YOLO)
    .venv/bin/python scripts/label_ood.py build       # reports/ood/labels_review.csv → data/ood/labels/*.txt + kiểm tra
    .venv/bin/python scripts/label_ood.py check       # phiếu kiểm tra: CHECK_N ảnh ngẫu nhiên + mọi ảnh có hộp ghi "không chắc"
    (thêm --name ood2 cho tập ngoài miền thứ hai)
"""
import argparse, json
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont, ImageOps

PROPOSE_CONF = 0.25  # thấp để ít sót người; khung sai sẽ bị bỏ khi duyệt
CLASSES = {"pwh": 3, "pnh": 4}  # thứ tự lớp của dữ liệu: 3 person_with_helmet, 4 person_no_helmet
FONT = ImageFont.truetype("/System/Library/Fonts/SFNSMono.ttf", 18)
SMALL = ImageFont.truetype("/System/Library/Fonts/SFNSMono.ttf", 12)
GRID = 100
CHECK_N, SEED = 20, 42
COLORS = {"pwh": "#1baf7a", "pnh": "#eb6834"}  # như ảnh ghép tuần 8

ap = argparse.ArgumentParser()
ap.add_argument("step", choices=["propose", "sheets", "build", "check"])
ap.add_argument("--name", default="ood", help="tên tập: ảnh ở data/<name>, nhãn duyệt ở reports/<name> (tập thứ hai: ood2)")
args = ap.parse_args()
OUT, REPORT = Path("data", args.name), Path("reports", args.name)
images = sorted((OUT / "images").glob("*.jpg"))

if args.step == "propose":
    from ultralytics import YOLO
    det = YOLO("weights/yolo26l.pt")
    props = {}
    (OUT / "review").mkdir(exist_ok=True)
    for p in images:
        b = det.predict(p, conf=PROPOSE_CONF, classes=[0], device="mps", verbose=False)[0].boxes
        boxes = [[round(v, 1) for v in xy] + [round(float(c), 2)] for xy, c in zip(b.xyxy.cpu().tolist(), b.conf.cpu())]
        props[p.name] = boxes
        img = Image.open(p).convert("RGB")
        d = ImageDraw.Draw(img)
        for x in range(0, img.width, GRID):  # lưới tọa độ để ước lượng khung thêm tay
            d.line([(x, 0), (x, img.height)], fill=(255, 255, 255), width=1)
            d.text((x + 2, 2), str(x), fill="white", font=SMALL, stroke_width=2, stroke_fill="black")
        for y in range(0, img.height, GRID):
            d.line([(0, y), (img.width, y)], fill=(255, 255, 255), width=1)
            d.text((2, y + 2), str(y), fill="white", font=SMALL, stroke_width=2, stroke_fill="black")
        for i, (x1, y1, x2, y2, c) in enumerate(boxes):
            d.rectangle([x1, y1, x2, y2], outline="#ff2d55", width=2)
            d.text((x1 + 2, y1 + 2), str(i), fill="#ffd400", font=FONT, stroke_width=2, stroke_fill="black")
        img.save(OUT / "review" / p.name, quality=90)
    (REPORT / "proposals.json").write_text(json.dumps(props, ensure_ascii=False, indent=0))
if args.step in ("propose", "sheets"):
    props, crops = json.loads((REPORT / "proposals.json").read_text()), []
    for p in images:
        for i, (x1, y1, x2, y2, c) in enumerate(props[p.name]):  # nửa trên người, phóng to để thấy đầu và mũ
            h = y2 - y1
            crop = Image.open(p).convert("RGB").crop((x1 - 0.1 * h, y1 - 0.1 * h, x2 + 0.1 * h, y1 + 0.5 * h))
            crops.append((f"{p.stem}#{i}", ImageOps.contain(crop, (210, 200), Image.LANCZOS)))
    for s in range(0, len(crops), 24):  # ảnh ghép 6 × 4 ảnh cắt
        sheet = Image.new("RGB", (6 * 220, 4 * 240), "white")
        d = ImageDraw.Draw(sheet)
        for k, (name, c) in enumerate(crops[s:s + 24]):
            x, y = (k % 6) * 220, (k // 6) * 240
            sheet.paste(c, (x + 5, y + 5))
            d.text((x + 5, y + 210), name[-26:], fill="black", font=SMALL)
        sheet.save(OUT / "review" / f"crops_{s // 24 + 1:02d}.png")
    print(f"{len(images)} ảnh, {sum(map(len, props.values()))} khung đề xuất, {(len(crops) + 23) // 24} ảnh ghép")
if args.step == "build":
    # labels_review.csv: image, box (số khung đề xuất hoặc trống nếu thêm tay), x1, y1, x2, y2 (khi thêm/sửa), cls (pwh, pnh,
    # drop = bỏ khung đề xuất sai, skip_image = bỏ cả ảnh), note, headwear (người không đội mũ bảo hộ: đầu trần, nón lá, mũ vải,
    # mũ lưỡi trai, mũ cối, mũ khác, không rõ) → thêm boxes.csv (tọa độ pixel từng hộp + headwear) cho eval_ood.py
    props = json.loads((REPORT / "proposals.json").read_text())
    rv = pd.read_csv(REPORT / "labels_review.csv", dtype={"box": "Int64"})
    assert rv["cls"].isin(["pwh", "pnh", "drop", "skip_image"]).all(), "cls không hợp lệ"
    skipped = set(rv.loc[rv["cls"] == "skip_image", "image"])
    decided = {(r.image, int(r.box)) for r in rv.itertuples() if pd.notna(r.box)}
    missing = [(im, i) for im, bs in props.items() if im not in skipped for i in range(len(bs)) if (im, i) not in decided]
    assert not missing, f"còn khung đề xuất chưa duyệt: {missing[:5]}"
    (OUT / "labels").mkdir(exist_ok=True)
    counts, n_img, boxes = {"pwh": 0, "pnh": 0}, 0, []
    for p in images:
        if p.name in skipped:  # chuyển khỏi images/ để không bị tính là ảnh nền khi đánh giá
            (OUT / "skipped").mkdir(exist_ok=True)
            p.rename(OUT / "skipped" / p.name)
            (OUT / "labels" / f"{p.stem}.txt").unlink(missing_ok=True)
            continue
        W, H = Image.open(p).size
        lines = []
        for r in rv[(rv["image"] == p.name) & rv["cls"].isin(["pwh", "pnh"])].itertuples():
            x1, y1, x2, y2 = (props[p.name][int(r.box)][:4] if pd.isna(r.x1) else [r.x1, r.y1, r.x2, r.y2])
            x1, y1, x2, y2 = max(0, x1), max(0, y1), min(W, x2), min(H, y2)
            assert x2 > x1 and y2 > y1, f"khung lỗi ở {p.name}"
            lines.append(f"{CLASSES[r.cls]} {(x1 + x2) / 2 / W:.6f} {(y1 + y2) / 2 / H:.6f} {(x2 - x1) / W:.6f} {(y2 - y1) / H:.6f}")
            counts[r.cls] += 1
            boxes.append({"image": p.name, "cls": r.cls, "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                          "headwear": r.headwear if r.cls == "pnh" else ""})
        (OUT / "labels" / f"{p.stem}.txt").write_text("\n".join(lines) + ("\n" if lines else ""))
        n_img += 1
    (OUT / "ood.yaml").write_text("# Tập ngoài miền tuần 9 (chỉ đánh giá). Ultralytics tìm nhãn ở labels/ cạnh images/\n"
                                  "train: images\nval: images\ntest: images\nnc: 6\n"
                                  'names: ["helmet", "head", "head_with_helmet", "person_with_helmet", "person_no_helmet", "face"]\n')
    pd.DataFrame(boxes).to_csv(REPORT / "boxes.csv", index=False)
    summary = (f"{n_img} ảnh được gán nhãn ({len(skipped)} ảnh bị bỏ: không phải công trường hoặc không có người gán được); "
               f"person_with_helmet {counts['pwh']} hộp, person_no_helmet {counts['pnh']} hộp")
    print(summary)
    (REPORT / "labels_output.txt").write_text(summary + "\n")
if args.step == "check":  # ảnh lấy từ mạng nên phiếu để ở data/ood/review (không commit)
    boxes = pd.read_csv(REPORT / "boxes.csv")
    rv = pd.read_csv(REPORT / "labels_review.csv")
    unsure = set(rv.loc[rv["note"].fillna("").str.contains("không chắc") & rv["cls"].isin(["pwh", "pnh"]), "image"])
    pool = sorted(set(boxes["image"]) - unsure)
    pick = sorted(unsure) + list(pd.Series(pool).sample(CHECK_N, random_state=SEED))
    for k, name in enumerate(pick, 1):
        img = Image.open(OUT / "images" / name).convert("RGB")
        d = ImageDraw.Draw(img)
        for i, b in enumerate(boxes[boxes["image"] == name].itertuples()):
            d.rectangle([b.x1, b.y1, b.x2, b.y2], outline=COLORS[b.cls], width=max(2, img.width // 400))
            d.text((b.x1 + 3, b.y1 + 3), f"{i} {b.cls}", fill="white", font=FONT, stroke_width=3, stroke_fill=COLORS[b.cls])
        img.thumbnail((1280, 1280))
        img.save(OUT / "review" / f"check_{k:02d}_{name}", quality=90)
    print(f"Phiếu kiểm tra: {len(unsure)} ảnh có hộp không chắc + {CHECK_N} ảnh ngẫu nhiên → {OUT / 'review'}/check_*.jpg")
