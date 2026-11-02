"""Tuần 9: thu thập tập ngoài miền vào data/ood/images (chỉ dùng để đánh giá, không bao giờ đưa vào huấn luyện; không commit).

Nguồn: (1) ảnh Wikimedia Commons tìm theo từ khóa về công nhân, công trường xây dựng Việt Nam, chỉ lấy ảnh giấy phép CC BY,
CC BY-SA, CC0 hoặc phạm vi công cộng và tiêu đề có địa danh Việt Nam; (2) ảnh trong các bài báo Việt Nam liệt kê ở
reports/ood/news_articles.txt (bản quyền tòa soạn, chỉ dùng nội bộ để đánh giá; bỏ ảnh có cạnh ngắn < 400 px để loại logo,
ảnh thu nhỏ); (3) khung hình trích từ video miễn phí của Mixkit (Mixkit Stock Video Free License),
mỗi 3 giây một khung. Tiêu chí chốt trước khi xem ảnh: tiêu đề ảnh Commons phải nhắc tới xây dựng / công nhân / công trường
(RELEVANT, vì tìm theo từ khóa trả về cả ảnh không liên quan); giữ ảnh có ≥ 1 người do YOLO26l COCO phát hiện (độ tin cậy ≥ 0,4,
khung cao ≥ 40 px); bỏ ảnh gần trùng (dHash, Hamming ≤ 6 như Tuần 3); tối đa MAX_IMAGES ảnh, ưu tiên khung video rồi lấy
ngẫu nhiên (seed 42) trong ảnh Commons. Nguồn, tác giả, giấy phép từng ảnh ghi vào reports/ood/sources.csv.

    .venv/bin/python scripts/collect_ood.py
    .venv/bin/python scripts/collect_ood.py --name ood2 --news-only --exclude data/ood/images data/ood/skipped   # tập thứ hai
"""
import argparse, hashlib, io, re, time
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import requests
from PIL import Image
from ultralytics import YOLO

ap = argparse.ArgumentParser()
ap.add_argument("--name", default="ood", help="tên tập: ảnh ở data/<name>, danh sách bài báo và báo cáo ở reports/<name>")
ap.add_argument("--news-only", action="store_true", help="chỉ lấy ảnh báo (tập thứ hai)")
ap.add_argument("--exclude", nargs="*", default=[], help="thư mục ảnh của tập đã có: bỏ ảnh gần trùng với chúng")
args = ap.parse_args()
OUT, REPORT = Path("data", args.name), Path("reports", args.name)
QUERIES = ["construction workers Vietnam", "Vietnam construction worker", "Vietnamese workers construction site",
           "Hanoi construction workers", "Saigon construction workers", "Ho Chi Minh City construction site workers"]
OK_LICENSE = ("CC BY", "CC0", "Public domain", "PD")
RELEVANT = r"construct|worker|labou?rer|building site|scaffold|xây dựng|công nhân|công trường"
VIETNAM = r"vietnam|việt nam|hanoi|hà nội|saigon|ho chi minh|da nang|đà nẵng|dien bien|lao cai|dong nai|tan son nhut|bac ha|hue"
NEWS_LIST, NEWS_MIN_SIDE = REPORT / "news_articles.txt", 400
MIXKIT = [1436, 1442, 1457, 1459, 4648, 23170, 23511, 31473, 32296, 49024]  # clip có người ở công trường, trang Mixkit "construction"
FRAME_EVERY_S, MAX_IMAGES, SEED = 3, 200, 42
PERSON_CONF, PERSON_MIN_H, DHASH_MAX = 0.4, 40, 6
UA = {"User-Agent": "DATN-helmet-detection-research/1.0 (university thesis; evaluation only)"}
API = "https://commons.wikimedia.org/w/api.php"


def get(url, **kw):
    for attempt in range(5):  # mạng chập chờn
        try:
            r = requests.get(url, headers=UA, timeout=120, **kw)
            r.raise_for_status()
            return r
        except requests.RequestException:
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"không tải được {url}")


def commons_files():
    titles = dict.fromkeys(t["title"] for q in QUERIES for t in get(API, params={
        "action": "query", "list": "search", "srsearch": q, "srnamespace": 6, "srlimit": 100, "format": "json"}).json()["query"]["search"]
        if t["title"].lower().endswith((".jpg", ".jpeg", ".png")) and pd.Series([t["title"]]).str.contains(RELEVANT, case=False)[0])
    rows = []
    for i in range(0, len(titles), 40):
        pages = get(API, params={"action": "query", "titles": "|".join(list(titles)[i:i + 40]), "prop": "imageinfo",
                                 "iiprop": "url|extmetadata", "iiurlwidth": 1280, "format": "json"}).json()["query"]["pages"]
        for p in pages.values():
            ii = p["imageinfo"][0]
            meta = {k: v.get("value", "") for k, v in ii.get("extmetadata", {}).items()}
            lic = meta.get("LicenseShortName", "")
            if lic.startswith(OK_LICENSE) and re.search(VIETNAM, p["title"], re.I):
                rows.append({"file": f"commons_{p['pageid']}.jpg", "source": "Wikimedia Commons", "title": p["title"],
                             "url": ii["descriptionurl"], "download": ii.get("thumburl", ii["url"]), "license": lic,
                             "author": pd.Series([meta.get("Artist", "")]).str.replace(r"<[^>]+>", "", regex=True)[0].strip()})
    return rows


def mixkit_frames():
    rows = []
    for vid in MIXKIT:
        path = OUT / "videos" / f"mixkit_{vid}.mp4"
        if not path.exists():
            path.write_bytes(get(f"https://assets.mixkit.co/videos/{vid}/{vid}-720.mp4").content)
        cap = cv2.VideoCapture(str(path))
        fps, n = cap.get(cv2.CAP_PROP_FPS), int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        for f in range(0, n, round(fps * FRAME_EVERY_S)):
            cap.set(cv2.CAP_PROP_POS_FRAMES, f)
            ok, frame = cap.read()
            if ok:
                name = f"mixkit_{vid}_{f / fps:05.1f}s.jpg"
                cv2.imwrite(str(OUT / "candidates" / name), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
                rows.append({"file": name, "source": "Mixkit", "title": f"Mixkit video {vid}, khung {f / fps:.1f} s",
                             "url": f"https://mixkit.co/free-stock-video/{vid}/", "download": "", "license": "Mixkit Stock Video Free License",
                             "author": "Mixkit"})
        cap.release()
    return rows


def news_images():
    rows, seen = [], set()
    for url in [l.strip() for l in NEWS_LIST.read_text().splitlines() if l.strip() and not l.startswith("#")]:
        try:
            html = get(url).text
        except RuntimeError:
            continue
        for src in dict.fromkeys(re.findall(r'(?:src|data-src|data-original)="(https?://[^"]+?\.(?:jpe?g|png|webp)[^"]*)"', html, re.I)):
            if src in seen:
                continue
            seen.add(src)
            name = f"news_{hashlib.sha1(src.encode()).hexdigest()[:12]}.jpg"
            dst = OUT / "candidates" / name
            if not dst.exists():
                try:
                    img = Image.open(io.BytesIO(get(src).content)).convert("RGB")
                except (RuntimeError, OSError):
                    continue
                if min(img.size) < NEWS_MIN_SIDE:
                    continue
                img.save(dst, quality=92)
            rows.append({"file": name, "source": re.sub(r"^https?://(www\.)?([^/]+).*", r"\2", url), "title": url, "url": src,
                         "download": src, "license": "Bản quyền tòa soạn, chỉ dùng nội bộ để đánh giá", "author": ""})
    return rows


def dhash(img):
    g = np.asarray(img.convert("L").resize((9, 8), Image.LANCZOS), dtype=np.int16)
    return np.packbits((g[:, 1:] > g[:, :-1]).flatten())


for d in ("videos", "candidates", "images"):
    (OUT / d).mkdir(parents=True, exist_ok=True)
REPORT.mkdir(parents=True, exist_ok=True)
rows, failed = ([] if args.news_only else mixkit_frames()), []
for r in ([] if args.news_only else commons_files()):
    dst = OUT / "candidates" / r["file"]
    if not dst.exists():
        try:
            Image.open(io.BytesIO(get(r["download"]).content)).convert("RGB").save(dst, quality=92)
        except RuntimeError:
            failed.append(r["title"])
            continue
        time.sleep(1)  # giới hạn tốc độ tải của máy chủ Wikimedia
    rows.append(r)
rows += news_images()
cand = pd.DataFrame(rows)

det = YOLO("weights/yolo26l.pt")
keep, hashes = [], [dhash(Image.open(p)) for d in args.exclude for p in sorted(Path(d).glob("*.jpg"))]
for r in cand.itertuples():
    img = Image.open(OUT / "candidates" / r.file)
    b = det.predict(img, conf=PERSON_CONF, classes=[0], device="mps", verbose=False)[0].boxes.xyxy.cpu().numpy()
    if not len(b) or (b[:, 3] - b[:, 1]).max() < PERSON_MIN_H:
        continue
    h = dhash(img)
    if any(np.unpackbits(h ^ o).sum() <= DHASH_MAX for o in hashes):
        continue
    hashes.append(h)
    keep.append(r.Index)
kept = cand.loc[keep]
video, photo = kept[kept.source == "Mixkit"], kept[kept.source != "Mixkit"]
final = pd.concat([video, photo.sample(min(len(photo), MAX_IMAGES - len(video)), random_state=SEED)])
for f in final.file:
    (OUT / "images" / f).write_bytes((OUT / "candidates" / f).read_bytes())
final.drop(columns="download").to_csv(REPORT / "sources.csv", index=False)
count = lambda df: ", ".join(f"{n} {k}" for k, n in df.source.map(
    lambda x: "khung video" if x == "Mixkit" else "ảnh Commons" if x == "Wikimedia Commons" else "ảnh báo chí").value_counts().items())
summary = (f"Không tải được {len(failed)} ảnh Commons. Ứng viên: {len(cand)} ảnh ({count(cand)}); có người và không gần trùng: "
           f"{len(kept)}; chọn: {len(final)} ({count(final)})")
print(summary)
(REPORT / "collect_output.txt").write_text(summary + "\n" + final.groupby("license").size().to_string() + "\n")
