"""Tuần 9 (Hình 9.1): nguồn và tác giả của 24 ảnh trên mỗi phiếu kiểm tra data/external/{openimages,sh17}/check_sheet.jpg.
Lấy lại đúng 24 ảnh như prepare_openimages.py / prepare_sh17.py (danh sách ảnh đã sắp xếp, pandas sample(24, random_state=42),
6 ảnh mỗi hàng), ghép với reports/extra/<nguồn>/sources.csv → reports/extra/<nguồn>/check_sheet_credits.csv.
Tự kiểm tra: ảnh thu nhỏ của từng ảnh phải trùng ô của nó trên phiếu (khung nhãn vẽ thêm chỉ làm lệch ít), và lệch nhiều
so với ô của ảnh khác.

    .venv/bin/python scripts/figure_credits.py
"""
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

# cột của sources.csv: tên ảnh, tác giả, đường dẫn trang ảnh gốc, giấy phép
SOURCES = {"openimages": ("image", "Author", "OriginalLandingURL", "License"), "sh17": ("image", "photographer", "url", "license")}
MATCH_MAX = 20  # sai khác trung bình (0–255) tối đa giữa ảnh thu nhỏ và ô trên phiếu

for name, (key, author, url, lic) in SOURCES.items():
    root = Path("data/external") / name
    pick = pd.Series(sorted((root / "yolo" / "images").glob("*/*.jpg"))).sample(24, random_state=42)
    sheet = np.asarray(Image.open(root / "check_sheet.jpg").convert("RGB"), dtype=float)
    src = pd.read_csv(f"reports/extra/{name}/sources.csv").set_index(key)
    assert src.index.is_unique, f"{name}: tên ảnh trùng trong sources.csv"
    thumbs = []
    for p in pick:
        im = Image.open(p).convert("RGB")
        im.thumbnail((320, 320))
        thumbs.append(np.asarray(im, dtype=float))
    cell = lambda k, t: sheet[(k // 6) * 330 + 5:(k // 6) * 330 + 5 + t.shape[0], (k % 6) * 330 + 5:(k % 6) * 330 + 5 + t.shape[1]]
    diffs = [np.abs(t - cell(k, t)).mean() for k, t in enumerate(thumbs)]
    wrong = [np.abs(t - cell((k + 1) % 24, t)[:t.shape[0], :t.shape[1]]).mean() for k, t in enumerate(thumbs) if cell((k + 1) % 24, t).shape == t.shape]
    assert max(diffs) < MATCH_MAX < min(wrong), f"{name}: ảnh không khớp phiếu (đúng ô ≤ {max(diffs):.1f}, sai ô ≥ {min(wrong):.1f})"
    rows = [{"row": k // 6 + 1, "col": k % 6 + 1, "image": p.name, "author": src.loc[p.name, author], "url": src.loc[p.name, url],
             "license": src.loc[p.name, lic]} for k, p in enumerate(pick)]
    out = Path(f"reports/extra/{name}/check_sheet_credits.csv")
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"{name}: 24 ảnh khớp phiếu (sai khác đúng ô ≤ {max(diffs):.1f}, sai ô ≥ {min(wrong):.1f}) → {out}")
