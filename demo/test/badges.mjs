// Kiểm tra cách đặt dấu tròn (src/lib/badges.js) trên cảnh ngẫu nhiên (seed cố định), cả thưa lẫn đông người: dấu luôn nằm trong
// khung hình; dấu không rời người của nó quá một nấc; khung thấp thì dấu "!" ở trên mép khung (không che đầu); dấu ✓ không bao giờ
// chồng dấu khác (va thì bỏ); cảnh thưa thì mọi người đều có dấu và không dấu nào chồng nhau; dấu "!" được ưu tiên hơn dấu ✓.
import { placeBadges, BADGE, GAP } from "../src/lib/badges.js";

let seed = 42;
const rand = () => ((seed = (seed * 1103515245 + 12345) % 2 ** 31) / 2 ** 31);
let failed = 0;
const check = (ok, msg) => { if (!ok) { failed++; if (failed < 15) console.log("SAI:", msg); } };
const overlap = (a, b) => Math.abs(a[0] - b[0]) < BADGE && Math.abs(a[1] - b[1]) < BADGE;

for (let s = 0; s < 400; s++) {
  const W = 300 + rand() * 300, H = 200 + rand() * 500, sparse = s < 200, n = sparse ? 1 + Math.floor(rand() * 4) : 5 + Math.floor(rand() * 25);
  const people = Array.from({ length: n }, (_, i) => {
    const w = 8 + rand() * 120, h = Math.min(H - 1, w * (1.5 + rand() * 2)), x = rand() * (W - w), y = rand() * (H - h);
    return { n: i + 1, box: [x, y, x + w, y + h], violation: rand() < 0.4 };
  });
  const spots = placeBadges(people, 1, W, H);
  const abs = people.map((p) => { const d = spots.get(p.n); return d && [p.box[0] + d[0], p.box[1] + d[1]]; });
  people.forEach((p, i) => {
    const a = abs[i], [x1, y1, x2, y2] = p.box, short = y2 - y1 < BADGE * 3;
    if (!a) return check(!p.violation, `cảnh ${s}: người vi phạm ${i + 1} mất dấu "!"`);
    check(a[0] >= 0 && a[1] >= 0 && a[0] + BADGE <= W && a[1] + BADGE <= H, `cảnh ${s}: dấu ${i + 1} ra ngoài khung hình`);
    const natural = Math.min(Math.max(short ? y1 - BADGE - 4 : y1 - BADGE / 2, 2), H - BADGE - 2);
    check(Math.abs(a[1] - natural) <= BADGE + GAP + 0.01, `cảnh ${s}: dấu ${i + 1} trôi xa khỏi người (${Math.round(a[1] - natural)} px)`);
    if (p.violation && short && y1 >= 2 * (BADGE + GAP) + 6) check(a[1] + BADGE <= y1, `cảnh ${s}: dấu "!" ${i + 1} che đầu người nhỏ`);
    if (!p.violation) abs.forEach((b, j) => b && j !== i && check(!overlap(a, b), `cảnh ${s}: dấu ✓ ${i + 1} chồng dấu ${j + 1}`));
  });
  // cảnh thưa: các khung cách nhau đủ xa thì mọi người đều có dấu riêng
  const apart = people.every((p, i) => people.every((q, j) => i === j
    || Math.abs((p.box[0] + p.box[2]) / 2 - (q.box[0] + q.box[2]) / 2) > 2 * (BADGE + GAP) + (p.box[2] - p.box[0] + q.box[2] - q.box[0]) / 2));
  if (sparse && apart) {
    check(abs.every(Boolean), `cảnh ${s}: cảnh thưa mà có người mất dấu`);
    abs.forEach((a, i) => abs.forEach((b, j) => a && b && i < j && check(!overlap(a, b), `cảnh ${s}: dấu ${i + 1} chồng dấu ${j + 1}`)));
  }
}
// một người vi phạm, một người đội mũ đứng sát: dấu "!" giữ góc khung, dấu ✓ bị bỏ (không đẩy đi chỗ khác)
{
  const people = [{ n: 1, box: [100, 100, 160, 300], violation: false }, { n: 2, box: [104, 104, 164, 300], violation: true }];
  const spots = placeBadges(people, 1, 400, 400);
  check(spots.get(2)?.[0] === -BADGE / 2 && spots.get(2)?.[1] === -BADGE / 2, `dấu "!" bị dời: ${spots.get(2)}`);
  check(spots.get(1) === null, `dấu ✓ va dấu "!" mà không bị bỏ: ${spots.get(1)}`);
}
console.log(`badges: 400 cảnh ngẫu nhiên (thưa + đông) + 1 ca ưu tiên: ${failed ? `${failed} chỗ SAI` : "đạt"}`);
process.exit(failed ? 1 : 0);
