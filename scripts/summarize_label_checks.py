"""Độ tin cậy của nhãn ngoài miền do Claude (AI) gán, ước lượng từ các phiếu kiểm tra sinh viên đã xem (label_ood.py check).

reports/ood_label_checks.csv: mỗi tập một dòng số ảnh trên phiếu (checked: ảnh có hộp "không chắc" xếp trước, rồi `random` ảnh
ngẫu nhiên seed 42) và một dòng cho mỗi ảnh sinh viên sửa (check_no = số thứ tự trên phiếu; kind: lỗi gán / làm rõ quy tắc).
Tỉ lệ ảnh có lỗi tính riêng cho phần ngẫu nhiên (ước lượng cho các ảnh không có hộp "không chắc": label_ood.py chỉ lấy
ảnh ngẫu nhiên trong số ảnh còn lại) và phần "không chắc" (được chọn vì khó),
kèm KTC 95% Wilson.

    .venv/bin/python scripts/summarize_label_checks.py
"""
from pathlib import Path

import pandas as pd

from summarize_label_audit import wilson

df = pd.read_csv("reports/ood_label_checks.csv")
sets = df.drop_duplicates("set")[["set", "checked", "random"]]
fix = df.dropna(subset=["image"]).merge(sets, on=["set", "checked", "random"])
fix["part"] = ["ngẫu nhiên" if n > c - r else "không chắc" for n, c, r in zip(fix.check_no, fix.checked, fix.random)]
pct = lambda k, n: f"{k}/{n} = {k / n:.1%} (KTC 95% {wilson(k, n)[0]:.1%}–{wilson(k, n)[1]:.1%})"
n_rand, n_unsure = int(sets.random.sum()), int((sets.checked - sets.random).sum())
lines = [f"Phiếu kiểm tra nhãn ngoài miền: {int(sets.checked.sum())} ảnh ({n_rand} ngẫu nhiên + {n_unsure} có hộp 'không chắc') ở "
         f"{len(sets)} đợt; sinh viên sửa {len(fix)} ảnh ({(fix.kind == 'lỗi gán').sum()} lỗi gán, {(fix.kind == 'làm rõ quy tắc').sum()} làm rõ quy tắc)."]
for part, n in (("ngẫu nhiên", n_rand), ("không chắc", n_unsure)):
    f = fix[fix.part == part]
    lines.append(f"  phần {part:<11} ảnh có lỗi gán: {pct(int((f.kind == 'lỗi gán').sum()), n)}; "
                 f"kể cả làm rõ quy tắc: {pct(len(f), n)}")
lines += [f"  {r.set} ảnh {r.check_no:.0f} ({r.part}, {r.kind}): {r.note}" for r in fix.itertuples()]
print("\n".join(lines))
Path("reports/ood_label_checks_output.txt").write_text("\n".join(lines) + "\n")
