"""Tuần 10: vẽ biểu tượng ứng dụng HelmetCheck (demo/public/icons/) theo ngôn ngữ "bản vẽ thi công" của giao diện: nền giấy can
có lưới, mũ bảo hộ nét xanh kỹ thuật trong bốn góc khung mực đen, bong bóng chú thích màu cam. Vẽ ở 1024 px rồi thu nhỏ; phần
nét nằm trong vùng an toàn 80% để dùng được làm biểu tượng "maskable".

    .venv/bin/python scripts/make_demo_icons.py
"""
from pathlib import Path

from PIL import Image, ImageDraw
from PIL.PngImagePlugin import PngInfo

OUT = Path("demo/public/icons")
SIZES = (512, 192, 180)  # 180: apple-touch-icon của iPhone
ORIGIN = ("Origin: drawn programmatically (not generated, not stock) by scripts/make_demo_icons.py in this repository (Pillow): "
          "drafting-film ground #f7f8f5 with a technical-blue 32 px grid, ink corner ticks, a technical-blue hard-hat glyph and an "
          "orange annotation bubble on a leader. Re-run that script to reproduce.")  # nguồn gốc ảnh (khóa impeccable:prompt)
PAPER, INK, BLUE, GRID, ORANGE = "#f7f8f5", "#14171a", "#1f4fd1", (31, 79, 209, 30), "#e2541b"
S = 1024

img = Image.new("RGBA", (S, S), PAPER)
grid = Image.new("RGBA", (S, S), (0, 0, 0, 0))
g = ImageDraw.Draw(grid)
for v in range(0, S, 32):
    g.line([(v, 0), (v, S)], fill=GRID, width=2)
    g.line([(0, v), (S, v)], fill=GRID, width=2)
img = Image.alpha_composite(img, grid)
d = ImageDraw.Draw(img)

# bốn góc khung quanh mũ
x1, y1, x2, y2, t, w = 232, 300, 792, 760, 110, 30
for cx, cy, sx, sy in ((x1, y1, 1, 1), (x2, y1, -1, 1), (x1, y2, 1, -1), (x2, y2, -1, -1)):
    d.line([(cx, cy + sy * t), (cx, cy), (cx + sx * t, cy)], fill=INK, width=w, joint="curve")

# mũ bảo hộ: chỏm nửa elip, gờ giữa, vành
d.pieslice([322, 400, 702, 780], 180, 360, fill=BLUE)
d.rectangle([497, 400, 527, 590], fill=PAPER)
d.rounded_rectangle([282, 584, 742, 636], radius=26, fill=BLUE)

# đường dẫn và bong bóng chú thích
d.line([(512, 300), (512, 236)], fill=ORANGE, width=18)
d.ellipse([440, 128, 584, 272], fill=ORANGE, outline=PAPER, width=10)

OUT.mkdir(parents=True, exist_ok=True)
info = PngInfo()
info.add_text("impeccable:prompt", ORIGIN)
for size in SIZES:
    img.convert("RGB").resize((size, size), Image.LANCZOS).save(OUT / f"icon-{size}.png", optimize=True, pnginfo=info)
print("Đã ghi", ", ".join(str(OUT / f"icon-{s}.png") for s in SIZES))
