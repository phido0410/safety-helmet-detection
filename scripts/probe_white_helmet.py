"""Tuần 10 (thử app bằng video): vì sao người đội mũ bảo hộ trắng trong video Mixkit 23243 bị báo "không đội mũ" ở mấy giây đầu.
Người đó đứng ngoài cùng bên trái. Theo dõi theo thời gian: điểm "có mũ" / "không mũ" của khung người đó và các khung bộ phận trong
vùng đầu (mặt có thấy không). Thí nghiệm đổi màu: giữ nguyên khung hình, chỉ tô vùng sáng – ít màu ở phần đầu (chiếc mũ trắng; áo
sơ mi nằm dưới vùng này) thành màu vàng rồi đoán lại; ảnh đã tô lưu kèm để kiểm tra vùng bị tô.

Video (Mixkit, giấy phép miễn phí, không commit): curl -L -o mixkit_23243.mp4 https://assets.mixkit.co/videos/23243/23243-720.mp4
    .venv/bin/python scripts/probe_white_helmet.py --video mixkit_23243.mp4 --out reports/deployment/M3b_yolo26n_bg/white_helmet
"""
import argparse
from pathlib import Path

import cv2
from ultralytics import YOLO

TIMES, RECOLOR_TIMES = [0.3, 0.6, 1, 1.5, 2, 3, 4, 5, 6, 8, 10, 12, 14], [0.3, 1.0, 2.0]
PWH, PNH, MIN_CONF = "person_with_helmet", "person_no_helmet", 0.15

ap = argparse.ArgumentParser()
ap.add_argument("--weights", default="runs/M3b_yolo26n_bg/weights/best.pt")
ap.add_argument("--video", required=True)
ap.add_argument("--out", required=True)
args = ap.parse_args()
model = YOLO(args.weights)
names = model.names
cap = cv2.VideoCapture(args.video)


def iou(a, b):
    w, h = min(a[2], b[2]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[1], b[1])
    return 0 if w <= 0 or h <= 0 else w * h / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - w * h)


def frame_at(t):
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, f = cap.read()
    assert ok, f"không đọc được khung {t} s"
    return f


def judge(f):
    """Điểm có mũ / không mũ của người ngoài cùng bên trái, các khung bộ phận có tâm trong vùng đầu của người đó, khung người."""
    b = model.predict(f, imgsz=800, conf=0.05, device="mps", verbose=False)[0].boxes
    dets = [(names[int(c)], float(s), x.tolist()) for x, c, s in zip(b.xyxy.cpu(), b.cls.cpu(), b.conf.cpu())]
    persons = [d for d in dets if d[0] in (PWH, PNH) and d[1] >= MIN_CONF]
    left = min(persons, key=lambda d: d[2][0])[2]
    score = lambda cls: max([d[1] for d in persons if d[0] == cls and iou(d[2], left) > 0.5] or [0])
    x1, y1, x2, y2 = left
    in_head = lambda d: x1 < (d[2][0] + d[2][2]) / 2 < x2 and (d[2][1] + d[2][3]) / 2 < y1 + (y2 - y1) * 0.25
    parts = {k: max([d[1] for d in dets if d[0] == k and in_head(d)] or [0]) for k in ("helmet", "head_with_helmet", "head", "face")}
    return score(PWH), score(PNH), parts, [int(v) for v in left]


assert judge(frame_at(8))[0] > judge(frame_at(8))[1], "khung 8 s (thấy mặt) phải được đoán là có mũ: sai người hoặc sai video"
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
lines = [f"{args.weights} trên {Path(args.video).name}, người ngoài cùng bên trái (đội mũ bảo hộ trắng), imgsz 800:"]
for t in TIMES:
    pw, pn, parts, _ = judge(frame_at(t))
    lines.append(f"  t = {t:>4} s: có mũ {pw:.2f} | không mũ {pn:.2f} | vùng đầu: " + ", ".join(f"{k} {v:.2f}" for k, v in parts.items()))
lines.append("Thí nghiệm đổi màu: chỉ tô chiếc mũ trắng thành vàng, phần còn lại giữ nguyên:")
for t in RECOLOR_TIMES:
    f = frame_at(t)
    pw, pn, _, (x1, y1, x2, y2) = judge(f)
    top, bottom, right = max(0, y1 - 30), y1 + int((y2 - y1) * 0.18), min(x2, x1 + 260)
    hsv = cv2.cvtColor(f[top:bottom, x1:right], cv2.COLOR_BGR2HSV)
    white = (hsv[..., 2] > 170) & (hsv[..., 1] < 60)
    hsv[..., 0][white], hsv[..., 1][white] = 25, 220
    g = f.copy()
    g[top:bottom, x1:right] = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    pw2, pn2, _, _ = judge(g)
    cv2.imwrite(str(out / f"recolor_{t}s.jpg"), g[max(0, y1 - 60):y1 + 300, max(0, x1 - 40):x1 + 400])
    lines.append(f"  t = {t} s: mũ trắng: có mũ {pw:.2f} / không mũ {pn:.2f} → mũ vàng ({int(white.sum())} px): có mũ {pw2:.2f} / không mũ {pn2:.2f}")
print("\n".join(lines))
(out / "white_helmet_output.txt").write_text("\n".join(lines) + "\n")
