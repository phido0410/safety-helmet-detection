"""Chuyển nhãn SHEL5K từ Pascal VOC (XML) sang định dạng YOLO (TXT, tọa độ chuẩn hóa).

- Mỗi ảnh <stem>.png có một tệp <stem>.txt, mỗi dòng: class_id x_center y_center w h (chuẩn hóa [0; 1]).
- Lớp lạ `person` (8 hộp trong 5 ảnh, đã kiểm tra trực quan: đều đội mũ) được ánh xạ sang `person_with_helmet`.
- Kiểm chứng sau khi chuyển: đọc lại các tệp TXT, đối chiếu số đối tượng theo lớp với XML
  và khôi phục tọa độ pixel để so với hộp gốc.

Cách chạy:
    python scripts/convert_voc_to_yolo.py --src data/SHEL5K --dst data/SHEL5K_yolo --report reports/conversion
"""

import argparse
import json
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

CLASSES = ["helmet", "head", "head_with_helmet", "person_with_helmet", "person_no_helmet", "face"]
CLASS_REMAP = {"person": "person_with_helmet"}
MAX_PIXEL_ERROR = 1.0


def read_voc(path: Path) -> tuple[int, int, list[tuple[str, int, int, int, int]]]:
    tree = ET.parse(path)
    width = int(tree.findtext("size/width"))
    height = int(tree.findtext("size/height"))
    boxes = []
    for obj in tree.iter("object"):
        box = obj.find("bndbox")
        boxes.append((
            obj.findtext("name"),
            *(int(float(box.findtext(k))) for k in ("xmin", "ymin", "xmax", "ymax")),
        ))
    return width, height, boxes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", type=Path, required=True, help="Thư mục SHEL5K gốc (chứa Annotations/)")
    parser.add_argument("--dst", type=Path, required=True, help="Thư mục đầu ra nhãn YOLO")
    parser.add_argument("--report", type=Path, default=Path("reports/conversion"))
    args = parser.parse_args()

    labels_dir = args.dst / "labels"
    labels_dir.mkdir(parents=True, exist_ok=True)
    args.report.mkdir(parents=True, exist_ok=True)
    (args.dst / "classes.txt").write_text("\n".join(CLASSES) + "\n", encoding="utf-8")

    xml_counts: Counter[str] = Counter()  # tên lớp gốc trong XML
    expected_counts: Counter[str] = Counter()  # sau khi ánh xạ lớp
    remapped = []
    originals: dict[str, tuple[int, int, list]] = {}

    for xml_path in sorted((args.src / "Annotations").glob("*.xml")):
        width, height, boxes = read_voc(xml_path)
        originals[xml_path.stem] = (width, height, boxes)
        lines = []
        for name, xmin, ymin, xmax, ymax in boxes:
            xml_counts[name] += 1
            if name in CLASS_REMAP:
                remapped.append({"file": xml_path.stem, "from": name, "to": CLASS_REMAP[name],
                                 "box": [xmin, ymin, xmax, ymax]})
                name = CLASS_REMAP[name]
            expected_counts[name] += 1
            xc = (xmin + xmax) / 2 / width
            yc = (ymin + ymax) / 2 / height
            w = (xmax - xmin) / width
            h = (ymax - ymin) / height
            lines.append(f"{CLASSES.index(name)} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}")
        (labels_dir / f"{xml_path.stem}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Kiểm chứng: đọc lại TXT, đếm theo lớp và khôi phục tọa độ pixel
    yolo_counts: Counter[str] = Counter()
    empty_label_files = []
    max_error = 0.0
    for stem, (width, height, boxes) in originals.items():
        lines = (labels_dir / f"{stem}.txt").read_text(encoding="utf-8").split()
        rows = [lines[i:i + 5] for i in range(0, len(lines), 5)]
        if not rows:
            empty_label_files.append(stem)
        for row, (_, xmin, ymin, xmax, ymax) in zip(rows, boxes):
            cls, xc, yc, w, h = int(row[0]), *map(float, row[1:])
            yolo_counts[CLASSES[cls]] += 1
            restored = ((xc - w / 2) * width, (yc - h / 2) * height, (xc + w / 2) * width, (yc + h / 2) * height)
            max_error = max(max_error, *(abs(a - b) for a, b in zip(restored, (xmin, ymin, xmax, ymax))))

    n_xml = sum(xml_counts.values())
    n_yolo = sum(yolo_counts.values())
    summary = {
        "classes": CLASSES,
        "n_label_files": len(originals),
        "n_objects_xml": n_xml,
        "n_objects_yolo": n_yolo,
        "xml_class_counts": dict(xml_counts.most_common()),
        "yolo_class_counts": {c: yolo_counts[c] for c in CLASSES},
        "remapped_objects": remapped,
        "empty_label_files": empty_label_files,
        "max_pixel_error": round(max_error, 4),
        "checks": {
            "objects xml == yolo": n_xml == n_yolo,
            "class counts match after remap": yolo_counts == expected_counts,
            "no empty label files": not empty_label_files,
            f"max pixel error <= {MAX_PIXEL_ERROR}": max_error <= MAX_PIXEL_ERROR,
        },
    }
    with open(args.report / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"Tệp nhãn: {len(originals)} | Đối tượng XML: {n_xml} | Đối tượng YOLO: {n_yolo}")
    print(f"Đã ánh xạ lớp: {len(remapped)} hộp ({', '.join(f'{k} -> {v}' for k, v in CLASS_REMAP.items())})")
    print("\nSố đối tượng theo lớp (YOLO):")
    for i, c in enumerate(CLASSES):
        print(f"  {i} {c:20} {yolo_counts[c]:>7}")
    print(f"\nSai số tọa độ lớn nhất khi khôi phục: {max_error:.4f} px")
    print("\nKiểm tra:")
    for check, ok in summary["checks"].items():
        print(f"  [{'OK ' if ok else 'LỆCH'}] {check}")
    print(f"\nĐã ghi nhãn vào {labels_dir} và báo cáo vào {args.report / 'summary.json'}")


if __name__ == "__main__":
    main()
