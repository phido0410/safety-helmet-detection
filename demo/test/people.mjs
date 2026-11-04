// Kiểm tra quy tắc bộ phận – toàn thể trong people() (src/lib/model.js): khung người chỉ được giữ khi có tâm một khung bộ phận
// (helmet, head, head_with_helmet, face) điểm ≥ partConf nằm trong nó. Dùng đúng bộ tự kiểm tra của keep_mask trong
// scripts/eval_part_rule.py để bản JS và bản Python (bản đã đánh giá) cho cùng kết quả.
import { people } from "../src/lib/model.js";

const names = ["helmet", "head", "head_with_helmet", "person_with_helmet", "person_no_helmet", "face"];
const id = (n) => names.indexOf(n);
const cfg = { names, violation: id("person_no_helmet"), iou: 0.7, parts: ["helmet", "head", "head_with_helmet", "face"].map(id), partConf: 0.1 };
const boxes = [[0, 0, 10, 20], [2, 1, 6, 5], [20, 0, 30, 20], [40, 0, 50, 20], [41, 1, 45, 5], [60, 0, 70, 20], [75, 1, 79, 5]];
const cls = ["person_no_helmet", "head", "person_with_helmet", "person_no_helmet", "face", "person_no_helmet", "head"].map(id);
const conf = [0.9, 0.5, 0.9, 0.9, 0.05, 0.9, 0.9];
const dets = boxes.map((box, i) => ({ box, cls: cls[i], score: conf[i] }));

let failed = 0;
const check = (ok, msg) => { if (!ok) { failed++; console.log("SAI:", msg); } };
// Python: keep_mask(...) == [True, True, False, False, True, False, True] → trong 4 khung người chỉ khung 0 được giữ
const kept = people(dets, cfg).map((p) => p.box[0]);
check(kept.join() === "0", `quy tắc bộ phận: giữ khung người x1 = ${kept} (phải 0: có đầu bên trong; bỏ người không có bộ phận, bộ phận dưới ngưỡng, bộ phận ở ngoài)`);
// Ảnh chỉ có chân (lỗi gặp khi thử camera): hai khung "không đội mũ", không có đầu / mặt / mũ nào → không còn người
check(people([{ box: [0, 0, 400, 700], cls: id("person_no_helmet"), score: 0.6 }, { box: [0, 0, 180, 690], cls: id("person_no_helmet"), score: 0.4 }], cfg).length === 0,
  "ảnh chỉ có chân: vẫn còn khung người");
// config không có parts (mô hình xuất không kèm quy tắc): giữ mọi khung người như trước
check(people(dets, { ...cfg, parts: undefined }).length === 4, "không có parts trong config: phải giữ cả 4 khung người");

// Chiều cao tối thiểu (minHeight px trên ảnh đưa vào mô hình): khung hình 1600×900, ảnh mô hình 800 → hệ số 0,5. Người vi phạm cao
// 300 px (= 150 < 160) là người ở xa: vẫn trả về (để vẽ mờ) nhưng không tính vi phạm; cao 340 px (= 170) vẫn là vi phạm.
{
  const c = { ...cfg, parts: undefined, imgsz: 800, minHeight: 160 }, v = id("person_no_helmet");
  const out = people([{ box: [0, 0, 100, 300], cls: v, score: 0.9 }, { box: [500, 0, 600, 340], cls: v, score: 0.9 }], c, 1600, 900);
  check(out.length === 2 && out[0].far && !out[0].violation && !out[1].far && out[1].violation,
    `chiều cao tối thiểu: ${JSON.stringify(out.map(({ far, violation }) => ({ far, violation })))}`);
}

// Chiều cao hiệu dụng (eval_min_size.py --height effective): ảnh nhỏ hơn ảnh mô hình bị phóng to không thêm chi tiết nên tính trên
// ảnh gốc. Ảnh 416×416: người cao 100 px (phóng lên 800 thành 192 px) vẫn là người ở xa với minHeight 120.
{
  const c = { ...cfg, parts: undefined, imgsz: 800, minHeight: 120 }, v = id("person_no_helmet");
  const [p] = people([{ box: [0, 0, 50, 100], cls: v, score: 0.9 }], c, 416, 416);
  check(p.far && !p.violation, `chiều cao hiệu dụng, ảnh nhỏ: ${JSON.stringify({ far: p.far, violation: p.violation })} (phải là người ở xa)`);
}

// Khung có mũ và khung không mũ trùng nhau (IoU > iou) ở cùng một người: giữ khung điểm cao hơn (eval_min_size.py --dup-rule score,
// cùng dữ liệu với bộ tự kiểm tra của script). Video 23243: người đội mũ đỏ có "có mũ" 0,78 và "không mũ" 0,40 → bị báo vi phạm.
{
  const c = { ...cfg, parts: undefined };
  const one = (pwh, pnh) => people([{ box: [0, 0, 10, 20], cls: id("person_with_helmet"), score: pwh }, { box: [0, 0, 10, 19], cls: id("person_no_helmet"), score: pnh }], c);
  const a = one(0.8, 0.4), b = one(0.4, 0.8);
  check(a.length === 1 && !a[0].violation && b.length === 1 && b[0].violation,
    `khung trùng khác lớp: có mũ 0,8 / không mũ 0,4 → ${JSON.stringify(a.map((p) => p.violation))}; có mũ 0,4 / không mũ 0,8 → ${JSON.stringify(b.map((p) => p.violation))}`);
}

console.log(`people: 6 trường hợp: ${failed ? `${failed} chỗ SAI` : "đạt"}`);
process.exit(failed ? 1 : 0);
