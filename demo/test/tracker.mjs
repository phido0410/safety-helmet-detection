// Kiểm tra tracker (src/lib/tracker.js) trên chuỗi khung giả lập 4 khung/s (như iPhone 11): giữ số khi người đi nhanh, nhấp nháy
// lớp, mất dấu ngắn; mỗi người vi phạm chỉ được chụp một lần, kể cả người ở xa mô hình lúc thấy lúc không; người chỉ thoáng qua
// không bị chụp.
import { createTracker, CONFIRM, LOST_MS, REMEMBER_MS } from "../src/lib/tracker.js";
import { viewDir } from "../src/lib/orientation.js";
import { people as peopleOf } from "../src/lib/model.js";

const DT = 250;  // ms giữa hai khung
let failed = 0;
const check = (ok, msg) => { if (!ok) { failed++; console.log("SAI:", msg); } };
const person = (x, violation, y = 50, w = 60, h = 150) => ({ box: [x, y, x + w, y + h], score: 0.9, violation });

// Chạy chuỗi khung; khung nào có `due` thì "chụp" luôn (như khi đã qua khoảng cách tối thiểu giữa hai ảnh). Như trong app, mọi
// người đang báo vi phạm ở khung đó đều có mặt trong ảnh nên đều được đánh dấu đã chụp (shots: số người của từng ảnh).
function run(frames) {
  const tr = createTracker(), ns = [], shots = [];
  frames.forEach((people, i) => {
    const r = tr.update(people, i * DT);
    ns.push(r.people.map((p) => p.n));
    if (r.due.length) { shots.push(r.people.filter((p) => p.violation).map((p) => p.n)); tr.captured(); }
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

// 6. Hai người đứng cạnh nhau, cùng vi phạm: hai số khác nhau, một ảnh có cả hai; người đội mũ không tính là đã chụp
{
  const { ns, shots } = run(Array.from({ length: 12 }, () => [person(300, true), person(100, true), person(200, false)]));
  check(ns.every((n) => n.join() === "1,2,3"), `ba người: số ${ns[0]} → ${ns.at(-1)}`);
  check(shots.length === 1 && shots[0].join() === "1,2", `ba người: các ảnh ${JSON.stringify(shots)} (phải [[1,2]])`);
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

// 9. Một người ngồi yên, mô hình trả về cả hộp không mũ lẫn hộp có mũ gần trùng (NMS chỉ lọc trong từng lớp; lỗi gặp trên iPhone:
//    một người bị lưu hai ảnh). Hộp rung ±2 px nên mỗi khung hộp nào gần hộp cũ hơn là ngẫu nhiên. Đi qua people() như trong app:
//    giữ hộp điểm cao hơn → hộp không mũ cao hơn thì đúng một ảnh, hộp có mũ cao hơn thì không ảnh nào (người đội mũ).
{
  const cfg = { names: ["helmet", "head", "head_with_helmet", "person_with_helmet", "person_no_helmet", "face"], violation: 4, iou: 0.7 };
  let seed = 7;
  const rnd = () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 2 ** 32), j = () => (rnd() * 2 - 1) * 2;
  const box = () => [100 + j(), 50 + j(), 160 + j(), 200 + j()];
  const frame = (bad, good) => () => peopleOf([{ box: box(), score: good, cls: 3 }, ...(rnd() < 0.8 ? [{ box: box(), score: bad, cls: 4 }] : [])], cfg);
  for (const [bad, good, want] of [[0.6, 0.3, 1], [0.3, 0.6, 0]]) {
    const counts = Array.from({ length: 50 }, () => run(Array.from({ length: 20000 / DT }, frame(bad, good))).shots.length);
    check(counts.every((n) => n === want), `hộp không mũ ${bad} + có mũ ${good} trùng nhau: số ảnh mỗi chuỗi ${counts.filter((n) => n !== want)} (phải ${want})`);
  }
  const one = frame(0.6, 0.3)().length;
  check(one === 1, `hộp có mũ + không mũ trùng nhau: còn ${one} người (phải 1)`);
}

// 10. Một người vi phạm ngồi yên, bên cạnh mô hình lúc có lúc không báo nhầm một "người" thứ hai (khăn treo, lỗi gặp trên iPad:
//     3 ảnh trong 1 phút). Khung báo nhầm hiện lần đầu đúng ở khung được chụp (chưa đủ CONFIRM) nhưng đã có mặt trong ảnh đó
//     → không được chụp thêm ảnh riêng.
{
  let seed = 11;
  const rnd = () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 2 ** 32);
  const counts = Array.from({ length: 50 }, () => run(Array.from({ length: 60000 / DT }, (_, i) =>
    [person(100, true), ...(i === 2 || (i > 2 && rnd() < 0.5) ? [{ box: [200, 40, 250, 190], score: 0.3, violation: true }] : [])])).shots.length);
  check(counts.every((n) => n === 1), `người + khung báo nhầm bên cạnh: số ảnh mỗi chuỗi ${counts.filter((n) => n !== 1)} (phải 1)`);
}

// 11. Đổi camera trước → sau (lỗi gặp trên iPhone): camera trước thấy người A chiếm gần cả khung, A bị chụp; đổi sang camera sau
//     thấy người B cũng chiếm gần cả khung, đúng chỗ đó → B vẫn phải được chụp. Đổi camera là cảnh mới nên app gọi reset().
{
  const tr = createTracker(), big = { box: [20, 10, 700, 1270], score: 0.9, violation: true };
  let shots = 0, t = 0;
  const feed = (n) => { for (let i = 0; i < n; i++, t += DT) if (tr.update([big], t).due.length) { shots++; tr.captured(); } };
  feed(8); tr.reset(); feed(40);
  check(shots === 2, `đổi camera: chụp ${shots} lần (phải 2: người ở camera trước và người ở camera sau)`);
}

// 12. Video 4809 (họp, quay từ trên xuống): mô hình thêm khung chồng lên người đã chụp — khung nửa trên nằm gọn trong người đó, hoặc
//     khung bao cả người đó lẫn người bên cạnh — và tracker coi là người mới, chụp thêm 2 ảnh. Khung mới nằm gần trọn trong / bao trọn
//     một người đã chụp thì tính là đã chụp; người khác đứng tách ra vẫn được chụp.
{
  const a = { box: [100, 100, 200, 400], score: 0.9, violation: true };
  const inner = { box: [105, 105, 195, 250], score: 0.6, violation: true }, outer = { box: [90, 60, 330, 420], score: 0.5, violation: true };
  const other = { box: [500, 100, 600, 400], score: 0.9, violation: true };
  const frames = [...Array(8).fill([a]), ...Array(8).fill([a, inner]), ...Array(8).fill([a, outer]), ...Array(8).fill([a, other])];
  const { shots } = run(frames);
  check(shots.length === 2, `khung chồng lên người đã chụp: chụp ${shots.length} lần (phải 2: người đầu và người đứng tách ra)`);
}

// 13. Video 32296 (toàn cảnh): ngay từ đầu mô hình ra hai khung cho cùng một người, khung cả người (vi phạm) và khung nửa trên nằm
//     trong nó (thấp hơn chiều cao tối thiểu nên chưa tính); khung cả người được chụp. Vài giây sau khung nửa trên đủ cao, thành vi
//     phạm → không được chụp thêm ảnh, vì nó nằm gần trọn trong người đã chụp.
{
  const full = { box: [636, 241, 697, 415], score: 0.8, violation: true };
  const upper = (violation) => ({ box: [636, 242, 698, 365], score: 0.4, violation });
  const { shots } = run([...Array(12).fill([full, upper(false)]), ...Array(12).fill([full, upper(true)])]);
  check(shots.length === 1, `khung nửa người có từ đầu, sau mới thành vi phạm: chụp ${shots.length} lần (phải 1)`);
}

// 14. Lia máy sang cảnh khác (lỗi gặp trên iPhone: chụp người ở giường, quay sang sofa thì người ở sofa không được chụp). Người A
//     ở giường bị chụp; lia máy, các khung lớn chạy qua nối số theo dõi của A sang khung của người B ngồi đúng chỗ đó → B bị coi là
//     A, không được chụp. Hướng camera (cảm biến) đổi quá VIEW_DEG so với lúc chụp thì quên người đã chụp; chỉ rung tay thì vẫn nhớ.
{
  const toward = (alpha) => viewDir(alpha, 90, 0);  // cầm dọc, camera sau nhìn ngang, quay quanh trục đứng
  const pan = (turn) => {
    const tk = createTracker(); let t = 0, shots = 0;
    const step = (ppl, alpha) => { const r = tk.update(ppl, t, toward(alpha)); if (r.due.length) { shots++; tk.captured(); } t += 450; };
    for (let k = 0; k < 8; k++) step([person(100, true, 300, 500, 600)], 0);                          // A ở giường
    for (let k = 0; k < 4; k++) step([person(60 + k * 30, true, 250, 600, 700)], (turn * (k + 1)) / 5);  // lia máy
    for (let k = 0; k < 2; k++) step([], turn);                                                      // không thấy người
    for (let k = 0; k < 20; k++) step([person(90, true, 280, 520, 640)], turn);                       // B ở sofa
    return shots;
  };
  check(pan(90) === 2, `lia máy 90° sang cảnh khác: chụp ${pan(90)} lần (phải 2: A và B)`);
  check(pan(10) === 1, `rung tay 10°: chụp ${pan(10)} lần (phải 1: vẫn là A)`);
  // không có cảm biến (máy tính, video có sẵn): như cũ
  const tk = createTracker(); let shots = 0;
  for (let k = 0; k < 10; k++) { const r = tk.update([person(100, true)], k * DT); if (r.due.length) { shots++; tk.captured(); } }
  check(shots === 1, `không có cảm biến: chụp ${shots} lần (phải 1)`);
}

// 15. Số người vi phạm hiển thị không nhảy theo từng khung (cảnh giường: 2–3–4–5): chỉ đếm người đã xác nhận (CONFIRM/VOTES), người
//     mất dấu một hai khung vẫn được đếm thêm HOLD_MS; khung thoáng qua một lần không được đếm.
{
  const tk = createTracker(), counts = [];
  for (let k = 0; k < 24; k++) {
    const ppl = [person(100, true), ...(k % 2 ? [] : [person(400, true)]), ...(k === 15 ? [person(700, true)] : [])];
    counts.push(tk.update(ppl, k * DT).bad);
  }
  check(counts.slice(8).every((n) => n === 2), `người mất dấu một khung / khung thoáng qua: số vi phạm ${counts.slice(8)} (phải luôn 2)`);
  check(counts[0] === 0, `chưa đủ ${CONFIRM} khung: số vi phạm ${counts[0]} (phải 0)`);
}

console.log(`tracker: 15 tình huống: ${failed ? `${failed} chỗ SAI` : "đạt"}`);
process.exit(failed ? 1 : 0);
