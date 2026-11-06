import { useEffect, useMemo, useRef } from "react";
import { score } from "./Stage.jsx";
import { IconAlert, IconBack } from "./Icons.jsx";
import { cropStyle, fitCrop, fitIn, tileRatio, violators } from "../lib/crop.js";

export function useObjectUrl(blob) {
  const url = useMemo(() => blob && URL.createObjectURL(blob), [blob]);
  useEffect(() => () => url && URL.revokeObjectURL(url), [url]);
  return url;
}

// Ảnh cắt vuông quanh một người, lấy thẳng từ ảnh gốc bằng background-position (không lưu ảnh cắt riêng)
export function CropView({ url, width, height, box, className = "crop" }) {
  const [x1, y1, x2, y2] = box, w = x2 - x1, h = y2 - y1;
  const side = Math.min(Math.max(w, h) * 1.15, width - 1, height - 1);  // lệch về phía đầu
  const clamp = (v, hi) => Math.min(Math.max(v, 0), hi);
  const x0 = clamp((x1 + x2) / 2 - side / 2, width - side), y0 = clamp(y1 - h * 0.05, height - side);
  return <span className={className} style={cropStyle(url, width, height, [x0, y0, side, side])} />;
}

// Xem chi tiết: mỗi người vi phạm một ô, cắt vừa khung từ ảnh đã lưu; chạm một ô để xem lớn người đó
export function Zooms({ url, rec, onOpen }) {
  const bad = violators(rec.people), crops = bad.map((p) => fitCrop(p.box, rec.width, rec.height)), tile = tileRatio(crops);
  return (
    <ul className={`zooms${bad.length === 1 ? " one" : ""}`} style={{ "--tile": tile }}>
      {bad.map((p, i) => (
        <li key={p.n}>
          <button type="button" className="zoombtn" onClick={() => onOpen(i)} aria-label={`Xem lớn người ${i + 1}, độ tin cậy ${score(p.score)}`}>
            <span className="zoomtile bad" style={{ aspectRatio: tile }}>
              <span className="zoomimg" style={{ ...cropStyle(url, rec.width, rec.height, crops[i]), ...fitIn(crops[i][2] / crops[i][3], tile) }}>
                <span className="badge"><IconAlert size={16} stroke={3} /></span>
              </span>
            </span>
            <b>Người {i + 1}</b>
            <span>Độ tin cậy {score(p.score)}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}

// Một người vi phạm, cắt vừa khung và phóng hết chỗ trống của màn hình (vẫn chỉ đọc ảnh đã lưu)
export function PersonView({ url, rec, index, backLabel, onBack }) {
  const p = violators(rec.people)[index], crop = fitCrop(p.box, rec.width, rec.height), heading = useRef();
  useEffect(() => heading.current?.focus(), []);
  return (
    <section className="detail person">
      <nav className="navbar dark"><button type="button" className="link" onClick={onBack}><IconBack size={22} />{backLabel}</button><span /></nav>
      <div className="personhead">
        <h1 ref={heading} tabIndex={-1}>Người {index + 1}</h1>
        <p>Không đội mũ · Độ tin cậy {score(p.score)}</p>
      </div>
      <div className="personstage">
        <span className="personimg" role="img" aria-label={`Ảnh cắt người ${index + 1}`}
          style={{ ...cropStyle(url, rec.width, rec.height, crop), "--r": crop[2] / crop[3] }} />
      </div>
    </section>
  );
}

// Ảnh cắt quanh người vi phạm đầu tiên của một bản ghi lịch sử
export default function Crop({ rec, className = "crop" }) {
  const url = useObjectUrl(rec.image);
  const p = rec.people.find((q) => q.violation) ?? rec.people[0];
  if (!p) return <span className={className} />;
  return <CropView url={url} width={rec.width} height={rec.height} box={p.box} className={className} />;
}
