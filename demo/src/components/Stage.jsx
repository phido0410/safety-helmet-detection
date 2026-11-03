import { useLayoutEffect, useRef, useState } from "react";
import { IconAlert, IconCheck } from "./Icons.jsx";
import { placeBadges } from "../lib/badges.js";

const pct = (v, total) => `${(100 * v) / total}%`;
const score = (s) => `${Math.round(s * 100)}%`;

// Ảnh / video / camera giữ đúng tỉ lệ giữa khung ngắm (viền đen như app Ảnh); khung phát hiện tính theo % của chính khung hình nên
// luôn khớp. Người không đội mũ: viền cam dày, nền cam mờ, dấu "!"; người đội mũ: viền xanh, dấu ✓ (không chỉ dựa vào màu).
// Dấu tròn đặt theo pixel đang hiện (lib/badges.js) để không che đầu người nhỏ và không chồng nhau. Chạm một người để xem độ tin cậy,
// những người khác mờ đi. Người đang chọn có thể do bên ngoài điều khiển (focus / onFocus: danh sách người ở bảng bên phải).
export default function Stage({ width, height, people = [], children, live = false, focus: outer, onFocus }) {
  const [own, setOwn] = useState(null);
  const focus = onFocus ? outer : own, setFocus = onFocus ?? setOwn;
  const [shown, setShown] = useState(0);  // chiều rộng khung hình đang hiện (px)
  const ref = useRef();
  useLayoutEffect(() => {
    const ro = new ResizeObserver(([e]) => setShown(e.contentRect.width));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  const k = shown / width, spots = placeBadges(people, k, shown, height * k);
  const focused = people.some((p) => p.n === focus);
  return (
    <div className="stage" ref={ref} style={{ "--ar": width / height }}>
      {children}
      <div className={`boxes${live ? " live" : ""}`} onClick={(e) => e.target === e.currentTarget && setFocus(null)}>
        {people.map((p) => {
          const [x1, y1, x2, y2] = p.box, on = focus === p.n, spot = spots.get(p.n);
          const label = `${p.violation ? "Không đội mũ" : "Đội mũ"} · ${score(p.score)}`;
          const cls = ["box", p.violation ? "bad" : "ok", focused && !on && "dim", y1 < height * 0.06 && "edge-t",
            x2 > width * 0.7 && "edge-r"].filter(Boolean).join(" ");
          return (
            <button type="button" key={p.n} className={cls} aria-label={label} aria-pressed={on}
              style={{ left: pct(x1, width), top: pct(y1, height), width: pct(x2 - x1, width), height: pct(y2 - y1, height),
                ...(spot && { "--bx": `${spot[0]}px`, "--by": `${spot[1]}px` }) }}
              onClick={() => setFocus(on ? null : p.n)}>
              {spot && <span className="badge">
                {p.violation ? <IconAlert size={16} stroke={3} /> : <IconCheck size={15} stroke={3} />}</span>}
              {on && <span className="tag">{label}</span>}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// Kết luận ngắn cho viên nổi trên khung ngắm (có chấm màu và chữ, không chỉ màu)
export function verdictOf(people) {
  const bad = people.filter((p) => p.violation).length;
  if (bad) return { tone: "bad", text: `${bad} không mũ`, long: `${bad} người không đội mũ` };
  if (people.length) return { tone: "ok", text: "Tất cả đội mũ", long: "Tất cả đội mũ" };
  return { tone: "none", text: "Không thấy người", long: "Không thấy người" };
}

export const Capsule = ({ tone, text }) => (
  <p className="capsule" aria-live="polite"><span className={`dot ${tone}`} />{text}</p>
);
