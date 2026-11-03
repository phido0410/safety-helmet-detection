// Kiểm tra tracker (src/lib/tracker.js) trên chuỗi khung giả lập 4 khung/s (như iPhone 11): giữ số khi người đi nhanh, nhấp nháy
// lớp, mất dấu ngắn; mỗi người vi phạm chỉ được chụp một lần, kể cả người ở xa mô hình lúc thấy lúc không; người chỉ thoáng qua
// không bị chụp.
import { createTracker, LOST_MS, REMEMBER_MS } from "../src/lib/tracker.js";

const DT = 250;  // ms giữa hai khung
let failed = 0;
const check = (ok, msg) => { if (!ok) { failed++; console.log("SAI:", msg); } };
const person = (x, violation, y = 50, w = 60, h = 150) => ({ box: [x, y, x + w, y + h], score: 0.9, violation });

// Chạy chuỗi khung; khung nào có `due` thì "chụp" luôn (như khi đã qua khoảng cách tối thiểu giữa hai ảnh)
function run(frames) {
  const tr = createTracker(), ns = [], shots = [];
  frames.forEach((people, i) => {
    const r = tr.update(people, i * DT);
    ns.push(r.people.map((p) => p.n));
    if (r.due.length) { shots.push(...r.due); tr.captured(r.due); }
  });
  return { ns, shots };
}

// 1. Đi nhanh dần: 25 px/khung rồi 50 px/khung (hộp rộng 60 → IoU giữa hai khung liên tiếp chỉ 0,09, phải nhờ dự đoán vận tốc)
{
  let x = 0;
  const frames = Array.from({ length: 16 }, (_, i) => [person((x += i < 4 ? 25 : 50), true)]);
  const { ns, shots } = run(frames);
  check(ns.every((n) => n[0] === 1), `đi nhanh: đổi số ${ns.flat()}`);
  check(shots.length === 1, `đi nhanh: chụp ${shots.length} lần (phải 1)`);
}

// 2. Đứng yên, lớp nhấp nháy có mũ / không mũ trong 10 giây: một số, một ảnh
{
  const pattern = [1, 0, 1, 0, 1, 1, 0, 1, 1, 0];
  const { ns, shots } = run(Array.from({ length: 40 }, (_, i) => [person(100, !!pattern[i % 10])]));
  check(new Set(ns.flat()).size === 1, `nhấp nháy: nhiều số ${[...new Set(ns.flat())]}`);
  check(shots.length === 1, `nhấp nháy: chụp ${shots.length} lần (phải 1)`);
}

// 3. Thoáng qua 2 khung rồi biến mất: chưa đủ bằng chứng, không chụp
check(run([[person(100, true)], [person(100, true)], [], [], []]).shots.length === 0, "thoáng qua: bị chụp");

// 4. Chỉ 2/5 khung báo vi phạm: không chụp
check(run(Array.from({ length: 20 }, (_, i) => [person(100, i % 5 < 2)])).shots.length === 0, "2/5 khung vi phạm: bị chụp");

// 5. Người đã chụp mất dấu rồi xuất hiện lại cùng chỗ: trong REMEMBER_MS (kể cả lâu hơn LOST_MS) vẫn là người cũ, không chụp lại;
//    lâu hơn REMEMBER_MS: coi là người mới, chụp lại
{
  const gap = (k) => [...Array(6).fill([person(100, true)]), ...Array(k).fill([]), ...Array(6).fill([person(100, true)])];
  for (const ms of [1000, LOST_MS + DT, REMEMBER_MS]) {
    const k = ms / DT - 1, n = run(gap(k)).shots.length;  // k khung trống = thời gian không thấy (k + 1) × DT
    check(n === 1, `mất dấu ${ms / 1000} s: chụp ${n} lần (phải 1)`);
  }
  const k = REMEMBER_MS / DT, n = run(gap(k)).shots.length;
  check(n === 2, `mất dấu ${((k + 1) * DT) / 1000} s: chụp ${n} lần (phải 2)`);
}

// 6. Hai người đứng cạnh nhau, cùng vi phạm: hai số khác nhau, mỗi người một lần; người đội mũ không bị chụp
{
  const { ns, shots } = run(Array.from({ length: 12 }, () => [person(300, true), person(100, true), person(200, false)]));
  check(ns.every((n) => n.join() === "1,2,3"), `ba người: số ${ns[0]} → ${ns.at(-1)}`);
  check(shots.length === 2 && new Set(shots).size === 2, `ba người: chụp ${shots}`);
}

// 7. Đủ 3/5 nhưng khung hiện tại báo có mũ: không chụp ở khung đó (ảnh lưu phải thấy người đó vi phạm)
{
  const tr = createTracker();
  [1, 1, 1].forEach((v, i) => tr.update([person(100, !!v)], i * DT));
  check(tr.update([person(100, false)], 3 * DT).due.length === 0, "khung hiện tại có mũ nhưng vẫn báo cần chụp");
}

// 8. Người ở xa (hộp 20×40, rung ±3 px), mô hình chỉ thấy 30% số khung, đứng yên 20 giây: chỉ một ảnh. Thử 50 chuỗi ngẫu nhiên
//    (seed cố định): mất dấu liền 2–3 giây là thường, vận tốc ước lượng từ độ rung không được đẩy hộp dự đoán ra khỏi người đó.
{
  let seed = 42;
  const rnd = () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 2 ** 32), j = () => (rnd() * 2 - 1) * 3;
  const counts = Array.from({ length: 50 }, () => run(Array.from({ length: 20000 / DT }, () =>
    rnd() < 0.3 ? [{ box: [300 + j(), 200 + j(), 320 + j(), 240 + j()], score: 0.5, violation: rnd() < 0.9 }] : [])).shots.length);
  check(counts.every((n) => n === 1), `người ở xa: số ảnh mỗi chuỗi ${counts.filter((n) => n !== 1)} (phải 1)`);
}

console.log(`tracker: 8 tình huống: ${failed ? `${failed} chỗ SAI` : "đạt"}`);
process.exit(failed ? 1 : 0);
