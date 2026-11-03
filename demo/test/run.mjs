// So hậu xử lý JS (demo/detector.js) với Ultralytics trên dữ liệu mẫu của scripts/export_demo.py --fixtures:
// đầu ra thô ONNX → NMS → lọc ngưỡng từng lớp → tọa độ ảnh gốc, và thông số letterbox cho nhiều cỡ ảnh.
//   node demo/test/run.mjs
import { readFileSync, readdirSync } from "node:fs";
import { letterbox, postprocess, scaleBoxes, pyRound } from "../detector.js";

const dir = new URL("./fixtures/", import.meta.url);
const cfg = JSON.parse(readFileSync(new URL("../public/model/config.json", import.meta.url)));
const TOL = 2e-3;  // Ultralytics làm tròn 3 chữ số khi ghi dữ liệu mẫu
let failed = 0;
const check = (ok, msg) => { if (!ok) { failed++; console.log("SAI:", msg); } };
const close = (a, b) => a.every((v, i) => Math.abs(v - b[i]) <= TOL);

check(pyRound(0.5) === 0 && pyRound(1.5) === 2 && pyRound(2.5) === 2 && pyRound(-0.1) === 0 && pyRound(2.6) === 3, "pyRound khác round() của Python");

for (const p of JSON.parse(readFileSync(new URL("letterbox.json", dir)))) {
  const [h, w] = p.orig_shape, lb = letterbox(w, h, cfg.imgsz);
  check(lb.newW === p.new_unpad[0] && lb.newH === p.new_unpad[1] && lb.left === p.left && lb.top === p.top
    && Math.abs(lb.r - p.ratio[0]) < 1e-12, `letterbox ${w}×${h}: ${JSON.stringify(lb)} ≠ ${JSON.stringify(p)}`);
}

// Ngưỡng riêng từng lớp (dữ liệu mẫu không có hộp nào giữa hai ngưỡng): 2 hộp tách rời, cùng điểm nằm giữa ngưỡng lớp vi phạm
// và ngưỡng chung → chỉ giữ hộp lớp vi phạm
{
  const nc = cfg.names.length, other = cfg.conf.findIndex((c, i) => i !== cfg.violation);
  const mid = (cfg.conf[cfg.violation] + cfg.conf[other]) / 2, raw = new Float32Array((4 + nc) * 2);
  [[100, 100, 40, 80, cfg.violation], [400, 400, 40, 80, other]].forEach(([cx, cy, w, h, c], a) => {
    [cx, cy, w, h].forEach((v, k) => { raw[k * 2 + a] = v; });
    raw[(4 + c) * 2 + a] = mid;
  });
  const d = postprocess(raw, nc, cfg);
  check(cfg.conf[cfg.violation] < mid && mid < cfg.conf[other] && d.length === 1 && d[0].cls === cfg.violation,
    `ngưỡng riêng lớp vi phạm: ${JSON.stringify(d)}`);
}

let nBoxes = 0;
const names = readdirSync(dir).filter((f) => f.endsWith(".f32"));
for (const f of names) {
  const fx = JSON.parse(readFileSync(new URL(f.replace(".f32", ".json"), dir)));
  const buf = readFileSync(new URL(f, dir));
  const raw = new Float32Array(buf.buffer, buf.byteOffset, buf.length / 4);
  check(raw.length === fx.shape.reduce((a, b) => a * b), `${f}: kích thước đầu ra`);
  const dets = postprocess(raw, cfg.names.length, cfg);
  check(dets.length === fx.boxes.length, `${f}: ${dets.length} hộp, Ultralytics ${fx.boxes.length}`);
  const [h, w] = fx.orig_hw;
  const scaled = scaleBoxes(dets, letterbox(w, h, cfg.imgsz), w, h);
  fx.boxes.forEach((b, i) => {
    const d = dets[i];
    check(d && d.cls === b[5] && Math.abs(d.score - b[4]) <= TOL && close(d.box, b.slice(0, 4)), `${f} hộp ${i}: ${JSON.stringify(d)} ≠ ${b}`);
    check(d && close(scaled[i].box, fx.scaled[i]), `${f} hộp ${i} (ảnh gốc): ${scaled[i]?.box} ≠ ${fx.scaled[i]}`);
  });
  nBoxes += fx.boxes.length;
}
console.log(`${names.length} ảnh, ${nBoxes} hộp: ${failed ? `${failed} chỗ SAI` : "khớp Ultralytics"}`);
process.exit(failed ? 1 : 0);
