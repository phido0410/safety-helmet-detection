"""Kiểm tra tính toàn vẹn bộ SHEL5K (nhãn Pascal VOC).

- Ghép ảnh với file XML theo tên tệp (không tính đuôi), báo ảnh thiếu XML và XML thiếu ảnh.
- Đọc toàn bộ XML, thống kê số đối tượng theo từng tên lớp thực tế.
- Đối chiếu kích thước ghi trong XML với kích thước thật của ảnh PNG (đọc phần header, không giải mã ảnh).
- Kiểm tra tọa độ hộp: 0 <= xmin < xmax <= width, 0 <= ymin < ymax <= height.
- Xuất bảng đối tượng (objects.csv) và tóm tắt (summary.json) để dùng cho báo cáo kiểm định nhãn.

Chỉ dùng thư viện chuẩn, không giải mã ảnh nên chạy nhẹ trên máy 8 GB RAM.

Cách chạy:
    python scripts/check_shel5k_integrity.py --root data/SHEL5K --out reports/integrity
"""

import argparse
import csv
import json
import struct
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

EXPECTED_OBJECTS = 75570
EXPECTED_IMAGES = 5000
EXPECTED_CLASSES = 6
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}


def index_by_stem(root: Path, exts: set[str]) -> dict[str, list[Path]]:
    index: dict[str, list[Path]] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in exts:
            index.setdefault(path.stem, []).append(path)
    return index


def png_size(path: Path) -> tuple[int, int] | None:
    with open(path, "rb") as f:
        header = f.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", header[16:24])


def box_is_valid(obj: dict, width: int | None, height: int | None) -> bool:
    try:
        xmin, ymin, xmax, ymax = (float(obj[k]) for k in ("xmin", "ymin", "xmax", "ymax"))
    except (TypeError, ValueError):
        return False
    if width is None or height is None:
        return False
    return 0 <= xmin < xmax <= width and 0 <= ymin < ymax <= height


def parse_xml(path: Path) -> tuple[int | None, int | None, list[dict]]:
    tree = ET.parse(path)
    size = tree.find("size")
    width = int(float(size.findtext("width"))) if size is not None else None
    height = int(float(size.findtext("height"))) if size is not None else None
    objects = []
    for obj in tree.iter("object"):
        box = obj.find("bndbox")
        objects.append({
            "class": obj.findtext("name"),
            "xmin": box.findtext("xmin") if box is not None else None,
            "ymin": box.findtext("ymin") if box is not None else None,
            "xmax": box.findtext("xmax") if box is not None else None,
            "ymax": box.findtext("ymax") if box is not None else None,
        })
    return width, height, objects


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True, help="Thư mục chứa dữ liệu SHEL5K đã giải nén")
    parser.add_argument("--out", type=Path, default=Path("reports/integrity"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    images = index_by_stem(args.root, IMAGE_EXTS)
    xmls = index_by_stem(args.root, {".xml"})

    dup_image_stems = sorted(s for s, p in images.items() if len(p) > 1)
    dup_xml_stems = sorted(s for s, p in xmls.items() if len(p) > 1)
    images_without_xml = sorted(images.keys() - xmls.keys())
    xmls_without_image = sorted(xmls.keys() - images.keys())

    class_counts: Counter[str] = Counter()
    raw_class_names: Counter[str] = Counter()  # giữ nguyên chuỗi gốc, kể cả khoảng trắng thừa
    parse_errors = []
    xml_without_objects = []
    size_mismatches = []
    invalid_boxes = []
    rows = []

    for stem, paths in xmls.items():
        xml_path = paths[0]
        try:
            width, height, objects = parse_xml(xml_path)
        except (ET.ParseError, TypeError, ValueError) as exc:
            parse_errors.append({"file": str(xml_path), "error": str(exc)})
            continue
        if not objects:
            xml_without_objects.append(stem)
        if stem in images:
            real_size = png_size(images[stem][0])
            if real_size is not None and real_size != (width, height):
                size_mismatches.append({"file": stem, "xml": [width, height], "image": list(real_size)})
        for obj in objects:
            if not box_is_valid(obj, width, height):
                invalid_boxes.append({"file": stem, **obj})
            raw_class_names[repr(obj["class"])] += 1
            class_counts[obj["class"]] += 1
            rows.append({"filename": stem, "width": width, "height": height, **obj})

    with open(args.out / "objects.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["filename", "width", "height", "class", "xmin", "ymin", "xmax", "ymax"])
        writer.writeheader()
        writer.writerows(rows)

    total_objects = sum(class_counts.values())
    summary = {
        "root": str(args.root),
        "n_images": len(images),
        "n_xml": len(xmls),
        "n_objects": total_objects,
        "n_classes": len(class_counts),
        "class_counts": dict(class_counts.most_common()),
        "raw_class_names": dict(raw_class_names.most_common()),
        "images_without_xml": images_without_xml,
        "xmls_without_image": xmls_without_image,
        "duplicate_image_stems": dup_image_stems,
        "duplicate_xml_stems": dup_xml_stems,
        "xml_without_objects": sorted(xml_without_objects),
        "parse_errors": parse_errors,
        "size_mismatches": size_mismatches,
        "invalid_boxes": invalid_boxes,
        "checks": {
            f"images == {EXPECTED_IMAGES}": len(images) == EXPECTED_IMAGES,
            f"objects == {EXPECTED_OBJECTS}": total_objects == EXPECTED_OBJECTS,
            f"classes == {EXPECTED_CLASSES}": len(class_counts) == EXPECTED_CLASSES,
            "every image has xml": not images_without_xml,
            "every xml has image": not xmls_without_image,
            "no parse errors": not parse_errors,
            "xml size == image size": not size_mismatches,
            "all boxes valid": not invalid_boxes,
        },
    }
    with open(args.out / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"Ảnh: {len(images)} | XML: {len(xmls)} | Đối tượng: {total_objects} | Số lớp: {len(class_counts)}")
    print("\nSố đối tượng theo lớp:")
    for name, count in class_counts.most_common():
        print(f"  {name!r:30} {count:>7}")
    print(f"\nẢnh thiếu XML: {len(images_without_xml)} | XML thiếu ảnh: {len(xmls_without_image)}")
    print(f"XML không có đối tượng: {len(xml_without_objects)} | XML lỗi đọc: {len(parse_errors)}")
    print(f"Kích thước XML khác ảnh thật: {len(size_mismatches)} | Hộp tọa độ không hợp lệ: {len(invalid_boxes)}")
    print(f"Tên tệp trùng — ảnh: {len(dup_image_stems)} | XML: {len(dup_xml_stems)}")
    print("\nKiểm tra:")
    for check, ok in summary["checks"].items():
        print(f"  [{'OK ' if ok else 'LỆCH'}] {check}")
    print(f"\nĐã ghi {args.out / 'objects.csv'} và {args.out / 'summary.json'}")


if __name__ == "__main__":
    main()
