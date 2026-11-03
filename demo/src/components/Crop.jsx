import { useEffect, useMemo } from "react";

export function useObjectUrl(blob) {
  const url = useMemo(() => blob && URL.createObjectURL(blob), [blob]);
  useEffect(() => () => url && URL.revokeObjectURL(url), [url]);
  return url;
}

// Ảnh cắt vuông quanh một người, lấy thẳng từ ảnh gốc bằng background-position (không lưu ảnh cắt riêng)
export function CropView({ url, width, height, box, className = "crop" }) {
  const [x1, y1, x2, y2] = box, w = x2 - x1, h = y2 - y1;
  const side = Math.min(Math.max(w, h) * 1.15, width - 1, height - 1), k = 100 / side;  // lệch về phía đầu
  const clamp = (v, hi) => Math.min(Math.max(v, 0), hi);
  const x0 = clamp((x1 + x2) / 2 - side / 2, width - side), y0 = clamp(y1 - h * 0.05, height - side);
  return (
    <span className={className} style={{ backgroundImage: `url(${url})`, backgroundSize: `${width * k}% ${height * k}%`,
      backgroundPosition: `${(x0 / (width - side)) * 100}% ${(y0 / (height - side)) * 100}%` }} />
  );
}

// Ảnh cắt quanh người vi phạm đầu tiên của một bản ghi lịch sử
export default function Crop({ rec, className = "crop" }) {
  const url = useObjectUrl(rec.image);
  const p = rec.people.find((q) => q.violation) ?? rec.people[0];
  if (!p) return <span className={className} />;
  return <CropView url={url} width={rec.width} height={rec.height} box={p.box} className={className} />;
}
