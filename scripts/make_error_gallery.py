"""Khảo sát định tính (tuần 8): lấy mẫu ngẫu nhiên các ca lỗi từ CSV của analyze_misses.py --cases và cắt ảnh quanh
từng ca để xếp nguyên nhân bằng mắt; sau khi điền cột category vào review CSV thì --summarize đếm theo nhóm nguyên nhân,
thêm --check N để vẽ phiếu kiểm tra lại (N ca ngẫu nhiên + mọi ca xếp "Lỗi nhãn", kèm nhóm đã xếp) cho người duyệt.

Ô ảnh: khung dày là ca lỗi (vàng: hộp nhãn bị bỏ sót / nhầm lớp, đỏ: dự đoán báo nhầm kèm độ tin cậy); khung mảnh là các
hộp nhãn khác cùng nhóm (xanh lá: person_with_helmet, cam: person_no_helmet, tím: face).

    .venv/bin/python scripts/make_error_gallery.py --cases reports/error_analysis/M2_yolo26n/cases_person_no_helmet.csv \\
        --sample "bỏ sót|nhầm lớp →=30" "báo nhầm=30" --out reports/error_analysis/M2_yolo26n/qualitative --tag pnh
    .venv/bin/python scripts/make_error_gallery.py --summarize reports/error_analysis/M2_yolo26n/qualitative/review.csv
"""
import argparse, ast, textwrap
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from summarize_label_audit import wilson

SEED = 42
CELL, COLS = 300, 5
COLORS = {3: "#1baf7a", 4: "#eb6834", 5: "#6250d6"}  # nhãn khác: person_with_helmet, person_no_helmet, face
FONT = ImageFont.truetype("/System/Library/Fonts/SFNSMono.ttf", 15)

ap = argparse.ArgumentParser()
ap.add_argument("--cases")
ap.add_argument("--sample", nargs="+", help='"mẫu regex trên cột kind=số ca", lấy theo thứ tự')
ap.add_argument("--data", default="data/SHEL5K_processed")
ap.add_argument("--split", default="test")
ap.add_argument("--out")
ap.add_argument("--tag")
ap.add_argument("--summarize")
ap.add_argument("--check", type=int, default=0)
ap.add_argument("--figure", nargs="+", help="mã ca để vẽ hình ví dụ cho báo cáo (figure_examples.png)")
args = ap.parse_args()


def crop(case):
    img = Image.open(Path(args.data, "images", args.split, f"{case.image}.png")).convert("RGB")
    W, H = img.size
    x1, y1, x2, y2 = ast.literal_eval(case.box)
    m = max(x2 - x1, y2 - y1, 40)  # lề quanh hộp: bằng cạnh dài của hộp, ít nhất 40 px để thấy ngữ cảnh
    box = (max(0, x1 - m), max(0, y1 - m), min(W, x2 + m), min(H, y2 + m))
    d = ImageDraw.Draw(img)
    lab = Path(args.data, "labels", args.split, f"{case.image}.txt").read_text().split("\n")
    for l in filter(None, lab):
        c, cx, cy, bw, bh = map(float, l.split())
        if int(c) in COLORS:
            d.rectangle([(cx - bw / 2) * W, (cy - bh / 2) * H, (cx + bw / 2) * W, (cy + bh / 2) * H], outline=COLORS[int(c)], width=1)
    d.rectangle([x1, y1, x2, y2], outline="#ff0000" if case.kind.startswith("báo nhầm") else "#ffd400", width=3)
    c = img.crop(box)
    scale = (CELL - 40) / max(c.size)  # phóng ca nhỏ cho dễ nhìn
    return c.resize((round(c.width * scale), round(c.height * scale)), Image.LANCZOS)


def render(part, path, label):
    rows = (len(part) + COLS - 1) // COLS
    sheet = Image.new("RGB", (COLS * CELL, rows * CELL), "white")
    d = ImageDraw.Draw(sheet)
    for i, case in enumerate(part.itertuples()):
        x, y = (i % COLS) * CELL, (i // COLS) * CELL
        c = crop(case)
        sheet.paste(c, (x + (CELL - c.width) // 2, y + 4))
        for k, line in enumerate(textwrap.wrap(label(case), 31)[:2]):  # ô rộng 300 px ≈ 31 ký tự SF Mono cỡ 15
            d.text((x + 6, y + CELL - 35 + 17 * k), line, fill="black", font=FONT)
    sheet.save(path)


if args.summarize:
    rv = pd.read_csv(args.summarize)
    assert rv["category"].notna().all(), "còn ca chưa xếp nguyên nhân"
    lines = []
    for grp, sub in rv.groupby("group", sort=False):
        counts = sub["category"].value_counts()
        lines += [f"{grp}: {len(sub)} ca"] + [f"  {cat}: {n} ({n / len(sub):.0%}, KTC 95% {lo:.0%}–{hi:.0%})"
                                              for cat, n in counts.items() for lo, hi in [wilson(n, len(sub))]]
    print("\n".join(lines))
    Path(args.summarize).with_name("qualitative_output.txt").write_text("\n".join(lines) + "\n")
    if args.check:
        pick = pd.concat([rv.sample(args.check, random_state=SEED), rv[rv["category"].str.startswith("Lỗi nhãn")]])
        pick = pick[~pick.index.duplicated()].sort_values("case_id")
        render(pick, Path(args.summarize).with_name("check_sheet.png"), lambda c: f"{c.case_id} {c.category}")
        print(f"Phiếu kiểm tra: {len(pick)} ca")
    if args.figure:
        render(rv.set_index("case_id").loc[args.figure].reset_index(), Path(args.summarize).with_name("figure_examples.png"),
               lambda c: f"{c.case_id} {c.category}")
else:
    cases = pd.read_csv(args.cases)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    picked = []
    for spec in args.sample:
        pattern, n = spec.rsplit("=", 1)
        pool = cases[cases["kind"].str.contains(pattern)]
        picked.append(pool.sample(min(int(n), len(pool)), random_state=SEED).assign(pool=len(pool), pattern=pattern))
    sample = pd.concat(picked, ignore_index=True)
    sample.insert(0, "case_id", [f"{args.tag}{i + 1:02d}" for i in range(len(sample))])
    sample.to_csv(out / f"sample_{args.tag}.csv", index=False)
    label = lambda c: f"{c.case_id} {c.kind.replace('báo nhầm: ', 'FP ')[:24]}{'' if pd.isna(c.conf) else f' {c.conf:.2f}'}"
    for s in range(0, len(sample), 20):
        render(sample.iloc[s:s + 20], out / f"sheet_{args.tag}_{s // 20 + 1}.png", label)
    print(sample.groupby("pattern", sort=False)["pool"].first().to_string(), f"\nĐã ghi {len(sample)} ca vào {out}")
