// Theo dõi người qua các khung video/camera để mỗi người không đội mũ chỉ bị chụp một lần. Hộp của khung mới được ghép với người
// đang theo dõi theo IoU (tham lam, cặp IoU cao trước); hộp cũ được dời theo vận tốc ước lượng vì iPhone chỉ chạy ~4 khung/s, người
// đi ngang có thể lệch gần hết bề ngang giữa hai khung. Ghép không phân biệt lớp: mô hình hay đổi qua lại có mũ / không mũ ở cùng
// một người, nên một người chỉ tính là vi phạm khi ít nhất CONFIRM trong VOTES khung gần nhất báo không đội mũ.
// Số hiển thị là số nhỏ nhất chưa dùng trong lúc người đó còn được theo dõi (bong bóng không phình ra 3 chữ số khi chạy lâu).
// Người đã bị chụp được nhớ thêm REMEMBER_MS sau khi mất dấu: người ở xa / bị che chỉ được mô hình thấy ở một phần khung, mất dấu
// quá LOST_MS là chuyện thường; nếu quên ngay thì lúc thấy lại sẽ bị coi là người mới và chụp lại. Đổi lại, người vi phạm khác đứng
// đúng chỗ đó trong REMEMBER_MS sẽ bị coi là người cũ và không được chụp. Hộp mới được so với cả hộp dự đoán lẫn hộp thấy lần cuối:
// với người đứng yên, vận tốc ước lượng chỉ là độ rung của hộp, dời theo nó vài giây là lệch khỏi người ở xa (hộp nhỏ).
// shortcut: chỉ dựa vào vị trí hộp (không so ngoại hình), hai người đi cắt nhau có thể đổi số → người vi phạm có thể bị chụp thêm
// một lần; nâng cấp lên ByteTrack/BoT-SORT nếu thấy chụp trùng còn nhiều.
// Người mới có khung nằm gần trọn trong (hoặc bao trọn) khung một người đã chụp (tỉ lệ giao / khung nhỏ ≥ CONTAIN) được tính là đã
// chụp: mô hình hay thêm khung nửa người hoặc khung bao hai người đứng sát nhau (video quay từ trên xuống: 3 người thành 3 ảnh).
// Đổi lại, người khác đứng sát ngay trước / sau người đã chụp có thể không được chụp riêng.
// Lia máy sang cảnh khác: khung lớn chạy qua nối số của người đã chụp sang người mới đứng đúng chỗ đó (giường → sofa: người ở sofa
// không được chụp). Camera (cảm biến hướng) lệch quá VIEW_DEG so với lúc chụp thì quên người đã chụp. So với lúc chụp chứ không
// so từng khung: lia 90° trong 2 s ở 2–4 khung/s chỉ lệch 15–20° mỗi khung. Đổi lại, lia đi rồi quay lại trong REMEMBER_MS có thể
// chụp lại người cũ một lần.
// Số vi phạm hiển thị (bad) chỉ đếm người đã xác nhận, kể cả người mất dấu chưa quá HOLD_MS: khung báo nhầm lúc có lúc không không
// làm số nhảy theo từng khung.
export const MATCH_IOU = 0.2, LOST_MS = 2000, REMEMBER_MS = 10000, VOTES = 5, CONFIRM = 3, CONTAIN = 0.8, VIEW_DEG = 30, HOLD_MS = 1000;

import { viewAngle } from "./orientation.js";

const center = (b) => [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2];
function iou(a, b) {
  const w = Math.min(a[2], b[2]) - Math.max(a[0], b[0]), h = Math.min(a[3], b[3]) - Math.max(a[1], b[1]);
  if (w <= 0 || h <= 0) return 0;
  const inter = w * h;
  return inter / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter);
}
function ios(a, b) {
  const w = Math.min(a[2], b[2]) - Math.max(a[0], b[0]), h = Math.min(a[3], b[3]) - Math.max(a[1], b[1]);
  return w <= 0 || h <= 0 ? 0 : (w * h) / Math.min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]));
}

// update(people, t, view): people là kết quả một khung (box, score, violation), t là thời điểm khung (ms, đồng hồ của nguồn), view
// là hướng camera (viewDir, không có cảm biến thì bỏ trống). Trả về người kèm số theo dõi `n`, `due`: số của những người vi phạm
// (đã xác nhận, khung này cũng báo vi phạm) chưa được chụp, và `bad`: số người vi phạm đã xác nhận để hiển thị.
// Sau khi lưu ảnh khung đó thì gọi captured(): mọi người khung đó báo vi phạm đều có mặt trong ảnh nên đều tính là đã chụp, kể cả
// người chưa đủ CONFIRM khung (iPad: người thứ hai / khung báo nhầm bên cạnh từng bị chụp thêm ảnh riêng vài giây sau).
export function createTracker() {
  let tracks = [], lastBad = [], lastView;
  const free = () => { let n = 1; while (tracks.some((tr) => tr.n === n)) n++; return n; };

  const confirmed = (tr) => tr.votes.filter(Boolean).length >= CONFIRM;
  function update(people, t, view) {
    lastView = view;
    const turned = (tr) => tr.captured && tr.view && view && viewAngle(tr.view, view) > VIEW_DEG;
    tracks = tracks.filter((tr) => t - tr.t <= (tr.captured ? REMEMBER_MS : LOST_MS) && !turned(tr));
    const pairs = [];
    tracks.forEach((tr, i) => {
      const dx = tr.v[0] * (t - tr.t), dy = tr.v[1] * (t - tr.t), pred = [tr.box[0] + dx, tr.box[1] + dy, tr.box[2] + dx, tr.box[3] + dy];
      people.forEach((p, j) => { const o = Math.max(iou(pred, p.box), iou(tr.box, p.box)); if (o >= MATCH_IOU) pairs.push([o, i, j]); });
    });
    pairs.sort((a, b) => b[0] - a[0]);
    const taken = new Set(), owner = new Map();
    for (const [, i, j] of pairs) if (!taken.has(i) && !owner.has(j)) { taken.add(i); owner.set(j, tracks[i]); }

    const out = people.map((p, j) => {
      let tr = owner.get(j);
      if (tr) {
        const dt = t - tr.t, [ax, ay] = center(tr.box), [bx, by] = center(p.box);
        if (dt > 0) tr.v = [(tr.v[0] + (bx - ax) / dt) / 2, (tr.v[1] + (by - ay) / dt) / 2];
        Object.assign(tr, { box: p.box, t });
      } else {
        tr = { n: free(), box: p.box, t, v: [0, 0], votes: [], captured: false };
        tracks.push(tr);
      }
      tr.votes = [...tr.votes, p.violation].slice(-VOTES);
      return { p: { ...p, n: tr.n }, tr };
    });
    // xét lúc sắp chụp chứ không lúc tạo: khung nửa người có thể có từ đầu, cùng lúc với người, rồi mới thành vi phạm
    const ready = out.filter(({ p, tr }) => p.violation && !tr.captured && confirmed(tr));
    ready.forEach(({ tr }) => { if (tracks.some((o) => o.captured && ios(o.box, tr.box) >= CONTAIN)) Object.assign(tr, { captured: true, view }); });
    const due = ready.filter(({ tr }) => !tr.captured).map(({ p }) => p.n);
    lastBad = out.filter(({ p }) => p.violation).map(({ tr }) => tr);
    const bad = tracks.filter((tr) => t - tr.t <= HOLD_MS && confirmed(tr)).length;
    return { people: out.map(({ p }) => p).sort((a, b) => a.n - b.n), due, bad };
  }

  const captured = () => lastBad.forEach((tr) => { tr.captured = true; tr.view = lastView; });
  // Đổi nguồn (camera trước ↔ sau) là cảnh mới: người đã chụp ở cảnh cũ không được che người mới đứng đúng chỗ đó
  const reset = () => { tracks = []; lastBad = []; };
  return { update, captured, reset };
}
