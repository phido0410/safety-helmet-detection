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
export const MATCH_IOU = 0.2, LOST_MS = 2000, REMEMBER_MS = 10000, VOTES = 5, CONFIRM = 3;

const center = (b) => [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2];
function iou(a, b) {
  const w = Math.min(a[2], b[2]) - Math.max(a[0], b[0]), h = Math.min(a[3], b[3]) - Math.max(a[1], b[1]);
  if (w <= 0 || h <= 0) return 0;
  const inter = w * h;
  return inter / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter);
}

// update(people, t): people là kết quả một khung (box, score, violation), t là thời điểm khung (ms, đồng hồ của nguồn).
// Trả về người kèm số theo dõi `n`, và `due`: số của những người vi phạm (đã xác nhận, khung này cũng báo vi phạm) chưa được chụp.
// Sau khi lưu ảnh thì gọi captured(due).
export function createTracker() {
  let tracks = [];
  const free = () => { let n = 1; while (tracks.some((tr) => tr.n === n)) n++; return n; };

  function update(people, t) {
    tracks = tracks.filter((tr) => t - tr.t <= (tr.captured ? REMEMBER_MS : LOST_MS));
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
    const due = out.filter(({ p, tr }) => p.violation && !tr.captured && tr.votes.filter(Boolean).length >= CONFIRM).map(({ p }) => p.n);
    return { people: out.map(({ p }) => p).sort((a, b) => a.n - b.n), due };
  }

  const captured = (ns) => tracks.forEach((tr) => { if (ns.includes(tr.n)) tr.captured = true; });
  return { update, captured };
}
