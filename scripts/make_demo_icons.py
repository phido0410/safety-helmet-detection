"""Vẽ biểu tượng ứng dụng HelmetCheck (demo/public/icons/): chiếc mũ của màn giới thiệu (demo/public/icons/hat.svg) trên nền vàng
an toàn, phần mũ nằm trong vùng an toàn 80% để dùng được làm biểu tượng "maskable". Chrome không giao diện vẽ SVG ở 1024 px, Pillow
thu nhỏ từng cỡ.

    .venv/bin/python scripts/make_demo_icons.py
"""
import subprocess
import tempfile
from pathlib import Path

from PIL import Image
from PIL.PngImagePlugin import PngInfo

OUT = Path("demo/public/icons")
SIZES = (512, 192, 180)  # 180: apple-touch-icon của iPhone
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
YELLOW, S = "#ffd60a", 1024
# khung SVG rộng 80% cạnh: phần có nét (82% × 50% khung) có nửa đường chéo 0,39 < 0,4, vừa vùng an toàn maskable. iPhone (180) không cắt theo
# vùng đó nên mũ to hơn cho dễ đọc trên màn hình chính.
HAT_WIDTH = {512: 0.8, 192: 0.8, 180: 0.86}
ORIGIN = ("Origin: drawn by hand as SVG for this project (demo/public/icons/hat.svg, not generated, not stock), rendered on safety yellow "
          "#ffd60a by scripts/make_demo_icons.py in this repository. Re-run that script to reproduce.")  # nguồn gốc ảnh (khóa impeccable:prompt)

svg = (OUT / "hat.svg").read_text(encoding="utf-8")
info = PngInfo()
info.add_text("impeccable:prompt", ORIGIN)
with tempfile.TemporaryDirectory() as tmp:
    for size in SIZES:
        html = (f'<!doctype html><style>html,body{{margin:0;height:100%;background:{YELLOW}}}body{{display:grid;place-items:center}}'
                f'svg{{width:{HAT_WIDTH[size] * 100}%}}</style>{svg}')
        page, shot = Path(tmp) / "icon.html", Path(tmp) / "icon.png"
        page.write_text(html, encoding="utf-8")
        subprocess.run([CHROME, "--headless=new", "--hide-scrollbars", "--force-device-scale-factor=1", f"--window-size={S},{S}",
                        f"--screenshot={shot}", f"--user-data-dir={tmp}/profile", page.as_uri()], check=True, capture_output=True, timeout=120)
        img = Image.open(shot).convert("RGB")
        assert img.size == (S, S), f"ảnh chụp {img.size}, cần {S}×{S}"
        assert img.getpixel((4, 4)) == (0xFF, 0xD6, 0x0A), f"nền {img.getpixel((4, 4))}"
        img.resize((size, size), Image.LANCZOS).save(OUT / f"icon-{size}.png", optimize=True, pnginfo=info)
print("Đã ghi", ", ".join(str(OUT / f"icon-{s}.png") for s in SIZES))
