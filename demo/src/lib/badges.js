export const BADGE = 24, GAP = 2;  // px: đường kính dấu tròn "!" / ✓, khoảng hở giữa hai dấu

// Vị trí dấu tròn của từng người, theo pixel của khung hình đang hiện (k = px hiện / px ảnh; W, H = cỡ khung hình đang hiện).
// Mặc định ở góc trên trái của khung. Khung thấp (người nhỏ, ở xa) thì đặt dấu phía trên mép khung để không che đầu.
// Người vi phạm đặt trước; dấu "!" chồng lên dấu "!" khác thì nhích lên đúng một nấc (không trôi xa khỏi người của nó). Dấu ✓ đặt
// sau, va vào bất kỳ dấu nào thì bỏ: người đội mũ vẫn còn viền xanh mảnh, không nền (khác hẳn viền cam dày, nền cam của người vi
// phạm), còn dấu ✓ lạc chỗ có thể nằm trên đầu người vi phạm và bị đọc nhầm.
// Trả về Map n → [dx, dy] (vị trí dấu so với góc trên trái của khung người đó) hoặc null khi không vẽ dấu.
export function placeBadges(people, k, W, H) {
  const placed = [], out = new Map();
  const hit = (x, y) => placed.some(([px, py]) => Math.abs(px - x) < BADGE + GAP && Math.abs(py - y) < BADGE + GAP);
  for (const p of [...people].sort((a, b) => b.violation - a.violation)) {
    if (p.far) { out.set(p.n, null); continue; }  // người ở xa: không đánh giá nên không có dấu
    const [x1, y1, x2, y2] = p.box.map((v) => v * k);
    const short = y2 - y1 < BADGE * 3;
    const x = Math.min(Math.max(short ? (x1 + x2) / 2 - BADGE / 2 : x1 - BADGE / 2, 2), W - BADGE - 2);
    const clampY = (y) => Math.min(Math.max(y, 2), H - BADGE - 2);
    let y = clampY(short ? y1 - BADGE - 4 : y1 - BADGE / 2);
    if (hit(x, y)) {
      if (!p.violation) { out.set(p.n, null); continue; }
      y = clampY(y - BADGE - GAP);
    }
    placed.push([x, y]);
    out.set(p.n, [x - x1, y - y1]);
  }
  return out;
}
